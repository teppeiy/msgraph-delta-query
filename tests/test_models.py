"""Tests for the data models module."""

import pytest
from datetime import datetime, timezone, timedelta
from io import StringIO
import sys
from msgraph_delta_query.models import (
    ChangeSummary, 
    ResourceParams, 
    PageMetadata, 
    DeltaQueryMetadata
)


class TestChangeSummary:
    """Test ChangeSummary dataclass."""
    
    def test_empty_change_summary(self):
        """Test empty change summary."""
        summary = ChangeSummary()
        assert summary.new_or_updated == 0
        assert summary.deleted == 0
        assert summary.changed == 0
        assert summary.total == 0
    
    def test_change_summary_with_values(self):
        """Test change summary with values."""
        summary = ChangeSummary(new_or_updated=5, deleted=2, changed=1)
        assert summary.new_or_updated == 5
        assert summary.deleted == 2
        assert summary.changed == 1
        assert summary.total == 8
    
    def test_total_property(self):
        """Test total property calculation."""
        summary = ChangeSummary(new_or_updated=10, deleted=3, changed=2)
        assert summary.total == 15
    
    def test_change_summary_with_timestamp(self):
        """Test change summary with timestamp."""
        now = datetime.now(timezone.utc)
        summary = ChangeSummary(new_or_updated=5, deleted=2, changed=1, timestamp=now)
        assert summary.timestamp == now
        assert summary.total == 8
    
    def test_format_time_ago_seconds(self):
        """Test time ago formatting for seconds."""
        now = datetime.now(timezone.utc)
        past = now - timedelta(seconds=30)
        summary = ChangeSummary(timestamp=past)
        time_ago = summary._format_time_ago(past)
        assert "30s ago" == time_ago
    
    def test_format_time_ago_minutes(self):
        """Test time ago formatting for minutes."""
        now = datetime.now(timezone.utc)
        past = now - timedelta(minutes=15)
        summary = ChangeSummary(timestamp=past)
        time_ago = summary._format_time_ago(past)
        assert "15m ago" == time_ago
    
    def test_format_time_ago_hours(self):
        """Test time ago formatting for hours."""
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=3)
        summary = ChangeSummary(timestamp=past)
        time_ago = summary._format_time_ago(past)
        assert "3h ago" == time_ago
    
    def test_format_time_ago_days(self):
        """Test time ago formatting for days."""
        now = datetime.now(timezone.utc)
        past = now - timedelta(days=2)
        summary = ChangeSummary(timestamp=past)
        time_ago = summary._format_time_ago(past)
        assert "2d ago" == time_ago
    
    def test_print_summary_without_timestamp(self, capsys):
        """Test print_summary method without timestamp."""
        summary = ChangeSummary(new_or_updated=5, deleted=2, changed=1)
        summary.print_summary("Test Summary")
        
        captured = capsys.readouterr()
        assert "📊 Test Summary:" in captured.out
        assert "New/Updated: 5" in captured.out
        assert "Deleted (permanent): 2" in captured.out
        assert "Changed (soft deleted): 1" in captured.out
        assert "Total changes: 8" in captured.out
        assert "Updates since:" not in captured.out
        assert "Query type: Full sync (no previous delta link)" in captured.out
    
    def test_print_summary_with_timestamp(self, capsys):
        """Test print_summary method with timestamp."""
        past = datetime.now(timezone.utc) - timedelta(minutes=5)
        summary = ChangeSummary(new_or_updated=3, deleted=1, changed=0, timestamp=past)
        summary.print_summary()
        
        captured = capsys.readouterr()
        assert "📊 Change Summary:" in captured.out
        assert "New/Updated: 3" in captured.out
        assert "Deleted (permanent): 1" in captured.out
        assert "Changed (soft deleted): 0" in captured.out
        assert "Total changes: 4" in captured.out
        assert "Updates since:" in captured.out
        assert "(5m ago)" in captured.out
        # Should contain both date/time and "x ago"
        assert "2025-" in captured.out  # Year should be present
    
    def test_str_representation_without_timestamp(self):
        """Test string representation without timestamp."""
        summary = ChangeSummary(new_or_updated=5, deleted=2, changed=1)
        expected = ("ChangeSummary: 8 total changes "
                   "(5 new/updated, 2 deleted, 1 changed) (full sync)")
        assert str(summary) == expected
    
    def test_str_representation_with_timestamp(self):
        """Test string representation with timestamp."""
        past = datetime.now(timezone.utc) - timedelta(minutes=10)
        summary = ChangeSummary(new_or_updated=3, deleted=1, changed=2, timestamp=past)
        str_repr = str(summary)
        assert "ChangeSummary: 6 total changes (3 new/updated, 1 deleted, 2 changed)" in str_repr
        assert "(10m ago)" in str_repr
        assert "since:" in str_repr
        assert "2025-" in str_repr  # Year should be present


class TestResourceParams:
    """Test ResourceParams dataclass."""
    
    def test_empty_resource_params(self):
        """Test empty resource params."""
        params = ResourceParams()
        assert params.select is None
        assert params.filter is None
        assert params.top is None
        assert params.deltatoken_latest is None
        assert params.max_objects is None
    
    def test_resource_params_with_values(self):
        """Test resource params with values."""
        params = ResourceParams(
            select=["id", "displayName"],
            filter="startswith(displayName,'Test')",
            top=100,
            deltatoken_latest=True,
            max_objects=1000
        )
        assert params.select == ["id", "displayName"]
        assert params.filter == "startswith(displayName,'Test')"
        assert params.top == 100
        assert params.deltatoken_latest is True
        assert params.max_objects == 1000


class TestPageMetadata:
    """Test PageMetadata dataclass."""
    
    def test_page_metadata_creation(self):
        """Test basic page metadata creation."""
        metadata = PageMetadata(
            page=1,
            object_count=50,
            has_next_page=True,
            delta_link=None,
            raw_response_size=1024
        )
        assert metadata.page == 1
        assert metadata.object_count == 50
        assert metadata.has_next_page is True
        assert metadata.delta_link is None
        assert metadata.raw_response_size == 1024
    
    def test_page_metadata_with_change_counts(self):
        """Test page metadata with change counts."""
        metadata = PageMetadata(
            page=2,
            object_count=25,
            has_next_page=False,
            delta_link="https://example.com/delta?token=abc",
            raw_response_size=512,
            page_new_or_updated=20,
            page_deleted=3,
            page_changed=2,
            total_new_or_updated=45,
            total_deleted=5,
            total_changed=4
        )
        assert metadata.page_new_or_updated == 20
        assert metadata.page_deleted == 3
        assert metadata.page_changed == 2
        assert metadata.total_new_or_updated == 45
        assert metadata.total_deleted == 5
        assert metadata.total_changed == 4
    
    def test_total_objects_property(self):
        """Test total_objects property."""
        metadata = PageMetadata(
            page=1, object_count=10, has_next_page=False, 
            delta_link=None, raw_response_size=100,
            total_new_or_updated=15, total_deleted=3, total_changed=2
        )
        assert metadata.total_objects == 20
    
    def test_page_change_summary_property(self):
        """Test page_change_summary property."""
        metadata = PageMetadata(
            page=1, object_count=10, has_next_page=False,
            delta_link=None, raw_response_size=100,
            page_new_or_updated=8, page_deleted=1, page_changed=1
        )
        summary = metadata.page_change_summary
        assert isinstance(summary, ChangeSummary)
        assert summary.new_or_updated == 8
        assert summary.deleted == 1
        assert summary.changed == 1
        assert summary.total == 10
    
    def test_cumulative_change_summary_property(self):
        """Test cumulative_change_summary property."""
        metadata = PageMetadata(
            page=2, object_count=5, has_next_page=False,
            delta_link=None, raw_response_size=50,
            total_new_or_updated=15, total_deleted=3, total_changed=2
        )
        summary = metadata.cumulative_change_summary
        assert isinstance(summary, ChangeSummary)
        assert summary.new_or_updated == 15
        assert summary.deleted == 3
        assert summary.changed == 2
        assert summary.total == 20


class TestDeltaQueryMetadata:
    """Test DeltaQueryMetadata dataclass."""
    
    def test_delta_query_metadata_creation(self):
        """Test delta query metadata creation."""
        change_summary = ChangeSummary(new_or_updated=10, deleted=2, changed=1)
        resource_params = ResourceParams(select=["id", "displayName"], top=100)
        
        metadata = DeltaQueryMetadata(
            changed_count=13,
            pages_fetched=2,
            duration_seconds=1.23,
            start_time="2025-08-01T12:00:00+00:00",
            end_time="2025-08-01T12:00:01+00:00",
            used_stored_deltalink=True,
            change_summary=change_summary,
            resource_params=resource_params
        )
        
        assert metadata.changed_count == 13
        assert metadata.pages_fetched == 2
        assert metadata.duration_seconds == 1.23
        assert metadata.start_time == "2025-08-01T12:00:00+00:00"
        assert metadata.end_time == "2025-08-01T12:00:01+00:00"
        assert metadata.used_stored_deltalink is True
        assert metadata.change_summary == change_summary
        assert metadata.resource_params == resource_params
    
    def test_delta_query_metadata_with_nested_objects(self):
        """Test accessing nested objects in delta query metadata."""
        change_summary = ChangeSummary(new_or_updated=5, deleted=1, changed=2)
        resource_params = ResourceParams(
            select=["id", "mail"],
            filter="department eq 'Engineering'",
            top=50
        )
        
        metadata = DeltaQueryMetadata(
            changed_count=8,
            pages_fetched=1,
            duration_seconds=0.85,
            start_time="2025-08-01T10:00:00+00:00",
            end_time="2025-08-01T10:00:01+00:00",
            used_stored_deltalink=False,
            change_summary=change_summary,
            resource_params=resource_params
        )
        
        # Test nested access
        assert metadata.change_summary.total == 8
        assert metadata.resource_params.select == ["id", "mail"]
        assert metadata.resource_params.filter == "department eq 'Engineering'"
        assert metadata.resource_params.top == 50


class TestModelsIntegration:
    """Test integration between different models."""
    
    def test_models_work_together(self):
        """Test that all models work together properly."""
        # Create a complete set of metadata as would be used in practice
        change_summary = ChangeSummary(new_or_updated=25, deleted=5, changed=3)
        resource_params = ResourceParams(
            select=["id", "displayName", "userPrincipalName"],
            filter="accountEnabled eq true",
            top=100,
            deltatoken_latest=False,
            max_objects=500
        )
        
        page_metadata = PageMetadata(
            page=3,
            object_count=33,
            has_next_page=False,
            delta_link="https://graph.microsoft.com/v1.0/users/delta?$deltatoken=final",
            raw_response_size=2048,
            page_new_or_updated=30,
            page_deleted=2,
            page_changed=1,
            total_new_or_updated=95,
            total_deleted=8,
            total_changed=4
        )
        
        delta_metadata = DeltaQueryMetadata(
            changed_count=107,
            pages_fetched=3,
            duration_seconds=2.45,
            start_time="2025-08-01T15:30:00+00:00",
            end_time="2025-08-01T15:30:02+00:00",
            used_stored_deltalink=True,
            change_summary=change_summary,
            resource_params=resource_params
        )
        
        # Verify everything works together
        assert delta_metadata.change_summary.total == 33
        assert page_metadata.total_objects == 107
        assert page_metadata.page_change_summary.total == 33
        assert page_metadata.cumulative_change_summary.total == 107
        assert delta_metadata.resource_params.max_objects == 500
