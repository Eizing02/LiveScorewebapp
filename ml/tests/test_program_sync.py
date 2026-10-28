import json
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from scripts.program_sync import run


NOW = datetime(2026, 10, 28, 12, tzinfo=timezone.utc)


def test_program_sync_respects_free_date_window_and_bangkok_round_without_calls():
    assert run(day='2026-10-28', now=NOW)['source_dates'] == ['2026-10-28', '2026-10-29']
    assert run(now=datetime(2026, 10, 28, 21, tzinfo=timezone.utc))['source_dates'] == ['2026-10-28', '2026-10-29', '2026-10-30']
    with pytest.raises(ValueError, match='approval'):
        run(execute=True)


def test_schedule_import_is_independent_of_model_training(tmp_path, monkeypatch):
    broker, probe = Mock(), Mock()
    probe.remaining = 100
    probe.get.side_effect = [{'response': {'subscription': {'plan': 'Free', 'active': True}, 'requests': {'current': 0, 'limit_day': 100}}}]+[{'errors': [], 'paging': {'total': 1}, 'response': []}]*3
    output = tmp_path/'program'
    output.mkdir()
    (output/'import-batches.json').write_text(json.dumps([[{'kind': 'source', 'values': []}]]))
    monkeypatch.setattr('scripts.program_sync.build', lambda **kwargs: {'unique_fixtures': 0, 'quarantined': 0})
    report = run(True, True, '2026-10-28', probe, broker, Path(tmp_path), output, now=NOW)
    assert report['status'] == 'complete' and report['model_promoted'] is False
    assert [c.args[1]['date'] for c in probe.get.call_args_list[1:]] == ['2026-10-28', '2026-10-29']
    assert [c.args[0] for c in broker.request.call_args_list] == ['program_status', 'program_import', 'program_status']


def test_provider_failure_preserves_database_snapshot_and_reports_safe_failure():
    broker, probe = Mock(), Mock()
    probe.get.side_effect = ValueError('sensitive upstream detail')
    report = run(True, True, '2026-10-28', probe, broker)
    assert report['status'] == 'failed' and 'sensitive' not in json.dumps(report)
    assert all(c.args[0] != 'program_import' for c in broker.request.call_args_list)
