"""Schedule setup is opt-in, bounded and restores previous settings on failure."""
from __future__ import annotations

import plistlib
import subprocess
import tempfile
import unittest
from pathlib import Path

from filelock import FileLock
from garmin_archive.schedule import LABEL, configure_schedule, schedule_status


class FakeLaunchctl:
    def __init__(self):
        self.loaded = False
        self.calls = []
        self.fail_bootstrap_once = False

    def __call__(self, command, *, check=True):
        self.calls.append(command)
        op = command[1]
        if op == 'print':
            return subprocess.CompletedProcess(command, 0 if self.loaded else 1)
        if op == 'bootout':
            self.loaded = False
        elif op == 'bootstrap':
            if self.fail_bootstrap_once:
                self.fail_bootstrap_once = False
                raise RuntimeError('simulated activation failure')
            self.loaded = True
        return subprocess.CompletedProcess(command, 0)


class ScheduleTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.archive = self.home / 'archive'
        self.executable = self.home / 'garmin-archive'
        self.executable.write_text('#!/bin/sh\n')
        self.executable.chmod(0o700)
        self.launchctl = FakeLaunchctl()
        self.args = {'home': self.home, 'platform': 'darwin', 'executable': self.executable, 'run': self.launchctl}
        self.path = self.home / 'Library/LaunchAgents' / f'{LABEL}.plist'

    def test_setup_and_update_without_starting_a_sync(self):
        self.assertEqual(schedule_status(home=self.home, platform='darwin', run=self.launchctl)['status'], 'not_configured')
        result = configure_schedule(self.archive, 6, 2, **self.args)
        self.assertEqual(result['status'], 'scheduled')
        data = plistlib.loads(self.path.read_bytes())
        self.assertEqual(data['StartInterval'], 21600)
        self.assertEqual(data['ProgramArguments'][-4:], ['sync', '--catch-up', '--lookback-days', '2'])
        self.assertEqual(schedule_status(home=self.home, platform='darwin', run=self.launchctl)['every_hours'], 6)
        self.assertEqual(schedule_status(data_dir=self.home / 'other', home=self.home,
                                         platform='darwin', run=self.launchctl)['status'], 'different_archive')
        self.assertNotIn('kickstart', [c[1] for c in self.launchctl.calls])
        configure_schedule(self.archive, 12, 3, **self.args)
        self.assertEqual(plistlib.loads(self.path.read_bytes())['StartInterval'], 43200)
        self.assertEqual(schedule_status(home=self.home, platform='darwin', run=self.launchctl)['lookback_days'], 3)

    def test_failed_replacement_restores_previous_configuration(self):
        configure_schedule(self.archive, 6, 2, **self.args)
        previous = self.path.read_bytes()
        self.launchctl.fail_bootstrap_once = True
        with self.assertRaises(RuntimeError):
            configure_schedule(self.archive, 12, 2, **self.args)
        self.assertEqual(self.path.read_bytes(), previous)
        self.assertTrue(self.launchctl.loaded)

    def test_unmanaged_file_is_preserved(self):
        self.path.parent.mkdir(parents=True)
        previous = plistlib.dumps({'Label': LABEL, 'ProgramArguments': ['/custom']})
        self.path.write_bytes(previous)
        with self.assertRaises(RuntimeError):
            configure_schedule(self.archive, 6, 2, **self.args)
        self.assertEqual(self.path.read_bytes(), previous)
        self.assertEqual(schedule_status(home=self.home, platform='darwin', run=self.launchctl)['status'], 'unmanaged')

    def test_different_archive_and_running_sync_are_not_modified(self):
        configure_schedule(self.archive, 6, 2, **self.args)
        previous = self.path.read_bytes()
        with self.assertRaises(RuntimeError):
            configure_schedule(self.home / 'other', 6, 2, **self.args)
        with FileLock(str(self.archive / 'sync.lock'), timeout=0):
            with self.assertRaises(RuntimeError):
                configure_schedule(self.archive, 6, 2, **self.args)
        self.assertEqual(self.path.read_bytes(), previous)

    def test_bounds_and_platform(self):
        for hours, days in [(0, 2), (169, 2), (6, 0), (6, 32)]:
            with self.assertRaises(ValueError):
                configure_schedule(self.archive, hours, days, **self.args)
        self.assertEqual(schedule_status(home=self.home, platform='linux')['status'], 'unsupported')
