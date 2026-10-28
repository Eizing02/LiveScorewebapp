"""Bounded programme collection, shared D1 quota and signed import; no ML calls."""
import argparse
import json
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from ml.pipeline import write_json
from ml.program_catalog import SOURCE, OUTPUT, build
from ml.provider_broker import BrokerClient, local_settings
from scripts.api_football_probe import ManagedProbe, ProbeError, account_summary, load_key


def run(execute=False, approved_remote=False, day=None, probe=None, broker=None, source=SOURCE, output=OUTPUT, now=None):
    now = now or datetime.now(timezone.utc)
    day = day or (now.astimezone(ZoneInfo('Asia/Bangkok'))-timedelta(hours=6)).date().isoformat()
    next_calendar_day = now.astimezone(ZoneInfo('Asia/Bangkok')).date()+timedelta(days=1)
    count = min(3, max(2, (next_calendar_day-datetime.fromisoformat(day).date()).days+1))
    days = [(datetime.fromisoformat(day)+timedelta(days=i)).date().isoformat() for i in range(count)]
    report = {'status': 'dry_run', 'business_date': day, 'source_dates': days, 'maximum_billable_requests': count, 'maximum_http_requests': count+1, 'model_promoted': False, 'training_labels_added': 0}
    if not execute:
        return report
    if not approved_remote:
        raise ValueError('explicit_program_sync_approval_required')
    broker = broker or BrokerClient(local_settings())
    run_info = {'id': str(uuid.uuid4()), 'started_at': now.isoformat().replace('+00:00', 'Z'), 'business_date': day, 'source_dates': days}
    try:
        broker.request('program_status', {**run_info, 'status': 'running'})
        probe = probe or ManagedProbe(load_key())
        account = account_summary(probe.get('/status'))
        if not account['active'] or account['plan'].lower() != 'free' or account['daily_limit'] != 100 or account['daily_remaining'] < 19:
            raise ProbeError('account_or_quota_blocked')
        probe.remaining = min(probe.remaining, account['daily_remaining'])
        for date in days:
            payload = probe.get('/fixtures', {'date': date, 'timezone': 'Asia/Bangkok'})
            if payload.get('errors') or payload.get('paging', {}).get('total') != 1 or not isinstance(payload.get('response'), list):
                raise ProbeError('invalid_program_response')
        summary = build(source=source, output=output)
        batches = json.loads((output/'import-batches.json').read_text(encoding='utf-8'))
        imported = 0
        for batch in batches:
            broker.request('program_import', {'records': batch})
            imported += len(batch)
        broker.request('program_status', {**run_info, 'status': 'complete', 'fixtures_count': summary['unique_fixtures'], 'quarantined_count': summary['quarantined']})
        report.update(status='complete', imported_records=imported, fixtures=summary['unique_fixtures'], quarantined=summary['quarantined'], remaining=probe.remaining)
    except (ProbeError, ValueError, KeyError, TypeError, OSError):
        report.update(status='failed', error_code='provider_or_import_failed')
        try:
            broker.request('program_status', {**run_info, 'status': 'failed', 'error_code': report['error_code']})
        except ValueError:
            pass
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--approved-remote', action='store_true')
    args = parser.parse_args()
    result = run(args.execute, args.approved_remote)
    write_json('.cloudflare/program-sync-report.json', result)
    print(json.dumps(result))
    if result['status'] == 'failed':
        raise SystemExit(1)
