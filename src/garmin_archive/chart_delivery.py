"""Deterministic chart captions and metadata, independent of plotting libraries."""
from .queries import METRIC_TITLES


def chart_metadata(result: dict, *, synthetic: bool = False, layout: str = 'chat') -> dict:
    if layout not in {'chat', 'wide'}:
        raise ValueError('Chart layout must be chat or wide')
    sleep = result.get('dataset') == 'sleep' and 'nights' in result
    metric = 'sleep' if sleep else result['metric']
    title = 'Sleep overview' if sleep else METRIC_TITLES[metric]
    if sleep:
        coverage = {key: {k: v for k, v in result['coverage']['fields'][key].items()
                          if k != 'mean_of_available_days'} for key in ('sleep_duration', 'sleep_score', 'sleep_need')}
        units = {'sleep_duration': 'hours', 'sleep_score': 'score', 'sleep_need': 'hours'}
        points = [dict(status=n['status'], fetched_at=n['fetched_at'], value=n['values']['sleep_duration']) for n in result['nights']]
    else:
        coverage = {metric: result['coverage']}
        unit = result.get('display', {}).get('unit', result['unit'])
        units = {metric: 'hours' if unit in {'s', 'min'} else unit}
        points = result['points']
    provenance = result.get('archive_provenance', {})
    synthetic = bool(synthetic or provenance.get('synthetic'))
    estimate = sleep or metric.startswith('sleep_') or metric.startswith('body_battery_') or metric in {'nap_duration', 'spo2_average', 'spo2_lowest'}
    denominator = '; '.join(f"{METRIC_TITLES[name]} {c['days_with_value']}/{c['requested_days']} days ({units[name]})"
                            for name, c in coverage.items())
    caption = f"{title}. {result['from']} to {result['to']} inclusive. {denominator}."
    caption += ' Synthetic data.' if synthetic else ''
    caption += ' Wearable estimate.' if estimate else ''
    stamps = sorted(p['fetched_at'] for p in points if p.get('fetched_at') and p['status'] == 'ok' and p['value'] is not None)
    explanations = []
    if sleep:
        explanations.extend(['Dotted need line: Garmin adjusted sleep-need estimate, not a prescribed target.',
                             'Sleep score has an independent 0–100 panel and its own coverage.'])
    primary = coverage['sleep_duration'] if sleep else coverage[metric]
    statuses = {status for status, count in primary['statuses'].items() if count and status != 'ok'}
    symbols = {'error': '× failed refresh', 'empty': '□ empty response', 'not_checked': '| not checked',
               'metric_not_returned': '◇ metric not returned', 'response_missing': '+ response missing'}
    if statuses:
        explanations.append('Gap strip: ' + '; '.join(symbols.get(s, s) for s in sorted(statuses)) + '. Gaps are not zero.')
    return {'contract_version': 1, 'metric': metric, 'title': title, 'from': result['from'], 'to': result['to'],
            'inclusive': True, 'layout': layout, 'units': units, 'coverage': coverage,
            'synthetic': synthetic, 'archive_provenance': provenance, 'wearable_estimate': estimate,
            'freshness': {'earliest_available_fetch': stamps[0] if stamps else None,
                          'latest_available_fetch': stamps[-1] if stamps else None,
                          'meaning': provenance.get('freshness_meaning', 'Fetch time is not measurement time.')},
            'caption': caption, 'alt_text': caption + ' Unavailable values remain gaps.',
            'explanations': explanations, 'delivery': 'Image content returned; host display must be verified separately.'}
