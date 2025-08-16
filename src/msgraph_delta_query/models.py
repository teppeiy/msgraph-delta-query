"""
Data models for Microsoft Graph delta query operations.

This module contains dataclass definitions for structured access to delta query
metadata, providing type safety and better developer experience.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class ChangeSummary:
    """Summary of changes detected in a delta query operation."""

    new_or_updated: int = 0  # Regular objects (no @removed property)
    deleted: int = 0  # Permanently deleted (reason: "deleted")
    changed: int = 0  # Soft deleted (reason: "changed")
    timestamp: Optional[datetime] = None  # When the change summary was created

    @property
    def total(self) -> int:
        """Total number of changes."""
        return self.new_or_updated + self.deleted + self.changed

    def _format_time_ago(self, dt: datetime) -> str:
        """Format a datetime as 'xx ago' string."""
        # Always use UTC for comparison to avoid timezone issues
        if dt.tzinfo is None:
            # Assume naive datetime is UTC
            dt = dt.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        delta = now - dt
        seconds = delta.total_seconds()

        # Handle negative values (future timestamps) by using absolute value
        seconds = abs(seconds)

        if seconds < 60:
            return f"{int(seconds)}s ago"
        elif seconds < 3600:
            return f"{int(seconds / 60)}m ago"
        elif seconds < 86400:
            return f"{int(seconds / 3600)}h ago"
        else:
            return f"{int(seconds / 86400)}d ago"

    def print_summary(self, title: str = "Change Summary") -> None:
        """Print a formatted summary of changes with timestamp information."""
        print(f"\n📊 {title}:")
        print(f"  New/Updated: {self.new_or_updated}")
        print(f"  Deleted (permanent): {self.deleted}")
        print(f"  Changed (soft deleted): {self.changed}")
        print(f"  Total changes: {self.total}")

        if self.timestamp:
            time_ago = self._format_time_ago(self.timestamp)
            # Always format as UTC, regardless of timezone info
            if self.timestamp.tzinfo is None:
                # Assume naive datetime is UTC
                formatted_time = self.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
            else:
                # Convert to UTC for display
                utc_time = self.timestamp.astimezone(timezone.utc)
                formatted_time = utc_time.strftime("%Y-%m-%d %H:%M:%S UTC")
            print(f"  Updates since: {formatted_time} ({time_ago})")
        else:
            print("  Query type: Full sync (no previous delta link)")

    def __str__(self) -> str:
        """String representation of the change summary."""
        time_info = ""
        if self.timestamp:
            time_ago = self._format_time_ago(self.timestamp)
            # Always format as UTC, regardless of timezone info
            if self.timestamp.tzinfo is None:
                # Assume naive datetime is UTC
                formatted_time = self.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
            else:
                # Convert to UTC for display
                utc_time = self.timestamp.astimezone(timezone.utc)
                formatted_time = utc_time.strftime("%Y-%m-%d %H:%M:%S UTC")
            time_info = f" (since: {formatted_time}, {time_ago})"
        else:
            time_info = " (full sync)"

        return (
            f"ChangeSummary: {self.total} total changes "
            f"({self.new_or_updated} new/updated, {self.deleted} deleted, "
            f"{self.changed} changed){time_info}"
        )


@dataclass
class ResourceParams:
    """Parameters used for the resource query."""

    select: Optional[List[str]] = None
    filter: Optional[str] = None
    top: Optional[int] = None
    deltatoken_latest: Optional[bool] = None
    max_objects: Optional[int] = None


@dataclass
class PageMetadata:
    """Metadata for a single page of delta query results."""

    page: int
    object_count: int
    has_next_page: bool
    delta_link: Optional[str]
    raw_response_size: int

    # Change counts for this page
    page_new_or_updated: int = 0
    page_deleted: int = 0
    page_changed: int = 0

    # Cumulative counts across all pages so far
    total_new_or_updated: int = 0
    total_deleted: int = 0
    total_changed: int = 0

    # Optional: timestamp for when the changes are relative to
    since_timestamp: Optional[datetime] = None

    @property
    def total_objects(self) -> int:
        """Total objects processed across all pages."""
        return self.total_new_or_updated + self.total_deleted + self.total_changed

    @property
    def page_change_summary(self) -> ChangeSummary:
        """Change summary for this page only."""
        return ChangeSummary(
            new_or_updated=self.page_new_or_updated,
            deleted=self.page_deleted,
            changed=self.page_changed,
            timestamp=self.since_timestamp,
        )

    @property
    def cumulative_change_summary(self) -> ChangeSummary:
        """Cumulative change summary across all pages."""
        return ChangeSummary(
            new_or_updated=self.total_new_or_updated,
            deleted=self.total_deleted,
            changed=self.total_changed,
            timestamp=self.since_timestamp,
        )


@dataclass
class DeltaQueryMetadata:
    """Complete metadata for a delta query operation."""

    changed_count: int
    pages_fetched: int
    duration_seconds: float
    start_time: str
    end_time: str
    used_stored_deltalink: bool
    change_summary: ChangeSummary
    resource_params: ResourceParams

    def print_sync_results(self, resource_name: str = "Objects") -> None:
        """Print complete sync results including timing, type, and change summary."""
        # Print basic sync info
        print(f"✓ Sync completed in {self.duration_seconds:.2f} seconds")
        sync_type = "Incremental" if self.used_stored_deltalink else "Full"
        print(f"✓ Sync type: {sync_type}")
        if self.pages_fetched > 1:
            print(f"✓ Pages processed: {self.pages_fetched}")

        # Print change summary using the built-in method
        self.change_summary.print_summary(f"{resource_name} Changes")

        # Print storage info
        if self.used_stored_deltalink:
            print(f"💾 Delta link used for incremental sync")
        else:
            print(f"💾 Delta link saved for future incremental syncs")

    def print_compact_results(self, resource_name: str = "Objects") -> None:
        """Print a compact one-line summary of sync results."""
        sync_type = "Incremental" if self.used_stored_deltalink else "Full"
        print(
            f"✓ {sync_type} sync completed in {self.duration_seconds:.2f}s - {self.change_summary.total} changes ({self.change_summary.new_or_updated} new/updated, {self.change_summary.deleted} deleted, {self.change_summary.changed} changed)"
        )
