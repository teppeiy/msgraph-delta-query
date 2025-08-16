import pytest
from datetime import datetime, timedelta, timezone
from src.msgraph_delta_query.models import ChangeSummary, PageMetadata, DeltaQueryMetadata, ResourceParams


def test_change_summary_total_and_str():
    cs = ChangeSummary(new_or_updated=2, deleted=3, changed=4)
    assert cs.total == 9
    s = str(cs)
    assert "9 total changes" in s
    assert "2 new/updated" in s
    assert "3 deleted" in s
    assert "4 changed" in s
    # No timestamp: should say full sync
    assert "full sync" in s


def test_change_summary_format_time_ago():
    now = datetime.now(timezone.utc)
    cs = ChangeSummary(timestamp=now)
    # <60s ago
    assert "s ago" in cs._format_time_ago(now)
    # <1h ago
    assert "m ago" in cs._format_time_ago(now - timedelta(minutes=5))
    # <1d ago
    assert "h ago" in cs._format_time_ago(now - timedelta(hours=2))
    # >1d ago
    assert "d ago" in cs._format_time_ago(now - timedelta(days=3))
    # Negative (future)
    assert "s ago" in cs._format_time_ago(now + timedelta(seconds=10))


def test_change_summary_print_summary_and_str_with_timestamp(capsys):
    now = datetime(2020, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    cs = ChangeSummary(new_or_updated=1, deleted=1, changed=1, timestamp=now)
    cs.print_summary("Test Title")
    out = capsys.readouterr().out
    assert "Test Title" in out
    assert "New/Updated: 1" in out
    assert "Deleted (permanent): 1" in out
    assert "Changed (soft deleted): 1" in out
    assert "Total changes: 3" in out
    assert "Updates since: 2020-01-01 12:00:00 UTC" in out
    # __str__ with timestamp
    s = str(cs)
    assert "since: 2020-01-01 12:00:00 UTC" in s


def test_page_metadata_properties():
    pm = PageMetadata(
        page=1,
        object_count=2,
        has_next_page=False,
        delta_link="foo",
        raw_response_size=123,
        page_new_or_updated=1,
        page_deleted=2,
        page_changed=3,
        total_new_or_updated=4,
        total_deleted=5,
        total_changed=6,
        since_timestamp=None,
    )
    assert pm.total_objects == 15
    pcs = pm.page_change_summary
    assert isinstance(pcs, ChangeSummary)
    assert pcs.new_or_updated == 1
    assert pcs.deleted == 2
    assert pcs.changed == 3
    ccs = pm.cumulative_change_summary
    assert ccs.new_or_updated == 4
    assert ccs.deleted == 5
    assert ccs.changed == 6


def test_delta_query_metadata_print_methods(capsys):
    cs = ChangeSummary(new_or_updated=1, deleted=2, changed=3)
    rp = ResourceParams(select=["id"], filter="foo", top=5, deltatoken_latest=True, max_objects=10)
    meta = DeltaQueryMetadata(
        changed_count=6,
        pages_fetched=2,
        duration_seconds=1.23,
        start_time="2020-01-01T00:00:00Z",
        end_time="2020-01-01T00:01:00Z",
        used_stored_deltalink=True,
        change_summary=cs,
        resource_params=rp,
    )
    meta.print_sync_results("Users")
    out = capsys.readouterr().out
    assert "Sync completed in" in out
    assert "Sync type: Incremental" in out
    assert "Pages processed: 2" in out
    assert "Users Changes" in out
    assert "Delta link used for incremental sync" in out
    meta.used_stored_deltalink = False
    meta.print_sync_results("Users")
    out2 = capsys.readouterr().out
    assert "Sync type: Full" in out2
    assert "Delta link saved for future incremental syncs" in out2
    meta.print_compact_results("Users")
    out3 = capsys.readouterr().out
    assert "Full sync completed in" in out3 or "Incremental sync completed in" in out3
