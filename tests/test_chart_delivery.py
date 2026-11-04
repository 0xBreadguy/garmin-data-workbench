"""Actual MCP image/resource transport, provenance and failure contracts."""
import base64
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from garmin_archive.archive import Archive
from garmin_archive.mcp_server import create_server
from garmin_archive.queries import get_trend, open_archive


class ChartDeliveryTest(unittest.IsolatedAsyncioTestCase):
    async def test_brand_resources_need_neither_archive_nor_plotting(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'missing'
            server = create_server(path)
            with patch.dict(sys.modules, {'matplotlib': None}):
                result = await server.call_tool('brand', {})
                # FastMCP's direct dict tools return content and structured data.
                data = result[1] if isinstance(result, tuple) else result
                if isinstance(data, list):
                    data = json.loads(data[0].text)
                self.assertEqual(data['colors']['primary'], '#0863E8')
                for name in ('icon_png', 'logo_svg', 'icon_svg'):
                    resources = await server.read_resource(data['assets'][name]['uri'])
                    item = next(iter(resources))
                    self.assertEqual(item.mime_type, data['assets'][name]['mime_type'])
                    self.assertGreater(len(item.content), 100)
            self.assertFalse(path.exists())

    @unittest.skipUnless(importlib.util.find_spec('matplotlib'), 'charts extra not installed')
    async def test_chart_stdio_returns_png_and_structured_coverage_without_writing_files(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            archive = Archive(path)
            archive.mark_synthetic('test', 42, '2026-01-03T00:00:00Z')
            archive.save_daily('sleep', '2026-01-01', {'sleepTimeSeconds': 27000,
                'sleepScores': {'overall': {'value': 80}}, 'sleepNeed': {'actual': 480}})
            archive.save_daily('sleep', '2026-01-02', {'sleepTimeSeconds': 26000})
            archive.mark_error('sleep', '2026-01-02', 'retained synthetic failure')
            archive.save_daily('sleep', '2026-01-03', {'sleepTimeSeconds': 26000})
            archive.close()
            before = (path / 'archive.sqlite3').read_bytes()
            files = sorted(p.name for p in path.iterdir())
            params = StdioServerParameters(command=sys.executable,
                args=['-m', 'garmin_archive.mcp_server', '--data-dir', root])
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=30)) as client:
                    await client.initialize()
                    for metric in ('sleep', 'sleep_need', 'body_battery_last'):
                        result = await client.call_tool('chart', {'metric': metric, 'start': '2026-01-01', 'end': '2026-01-04'})
                        self.assertFalse(result.isError, result.content)
                        meta = result.structuredContent
                        self.assertTrue(meta['synthetic'])
                        self.assertIn('Synthetic data', meta['caption'])
                        self.assertIn('Wearable estimate', meta['caption'])
                        png = next(c for c in result.content if c.type == 'image')
                        self.assertEqual(png.mimeType, 'image/png')
                        raw = base64.b64decode(png.data)
                        self.assertLessEqual(len(raw), 4 * 1024 * 1024)
                        with Image.open(io.BytesIO(raw)) as image:
                            self.assertEqual(image.info['Description'], meta['caption'])
                            self.assertLessEqual(image.width, 1600)
                            self.assertLessEqual(image.height, 4096)
                            image.verify()
                        if metric == 'sleep':
                            self.assertEqual(meta['coverage']['sleep_duration']['days_with_value'], 2)
                            self.assertEqual(meta['coverage']['sleep_score']['days_with_value'], 1)
                            self.assertEqual(meta['units']['sleep_duration'], 'hours')
                            self.assertEqual(meta['coverage']['sleep_duration']['statuses']['error'], 1)
                    for arguments in ({'metric': 'bad'}, {'metric': 'steps', 'layout': 'bad'},
                                      {'metric': 'steps', 'start': '2026-01-01', 'end': '2026-04-01'}):
                        self.assertTrue((await client.call_tool('chart', arguments)).isError)
                    resources = await client.read_resource('garmin-brand://assets/icon_png')
                    self.assertEqual(resources.contents[0].mimeType, 'image/png')
            self.assertEqual((path / 'archive.sqlite3').read_bytes(), before)
            self.assertEqual(sorted(p.name for p in path.iterdir()), files)

    @unittest.skipUnless(importlib.util.find_spec('matplotlib'), 'charts extra not installed')
    async def test_missing_dependencies_are_explicit_and_marker_cannot_be_overridden(self):
        from garmin_archive.charts import render_png
        from PIL import Image
        with tempfile.TemporaryDirectory() as root:
            path = Path(root); Archive(path).close()
            (path / 'SYNTHETIC.txt').write_text('legacy demo')
            with open_archive(path) as db:
                trend = get_trend(db, 'steps', '2026-01-01', '2026-01-02')
            raw, meta = render_png(trend, synthetic=False)
            self.assertTrue(meta['synthetic'])
            with Image.open(io.BytesIO(raw)) as image:
                self.assertIn('Synthetic data', image.info['Description'])
            with patch('garmin_archive.charts.render_png', side_effect=ImportError('unavailable')):
                result = await create_server(path).call_tool('chart', {'metric': 'steps'})
            self.assertTrue(result.isError)
            self.assertEqual(result.structuredContent['error']['code'], 'dependency_unavailable')
            self.assertFalse(any(c.type == 'image' for c in result.content))
