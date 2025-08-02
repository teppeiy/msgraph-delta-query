"""
Demo of enhanced ChangeSummary functionality with timestamps and print methods.
"""

import time
from datetime import datetime, timezone, timedelta
from msgraph_delta_query.models import ChangeSummary


def demo_timestamp_functionality():
    """Demonstrate timestamp functionality in ChangeSummary."""
    print("🔍 ChangeSummary Enhanced Timestamp Demo")
    print("=" * 60)
    
    # Create summaries at different time points
    print("\n1. Creating change summaries with different timestamps...")
    
    # Current summary
    current_summary = ChangeSummary(
        new_or_updated=10,
        deleted=2,
        changed=1,
        timestamp=datetime.now(timezone.utc)
    )
    
    # Summary from 5 minutes ago
    past_5min = ChangeSummary(
        new_or_updated=8,
        deleted=1,
        changed=0,
        timestamp=datetime.now(timezone.utc) - timedelta(minutes=5)
    )
    
    # Summary from 2 hours ago
    past_2hours = ChangeSummary(
        new_or_updated=15,
        deleted=3,
        changed=2,
        timestamp=datetime.now(timezone.utc) - timedelta(hours=2)
    )
    
    # Summary from 3 days ago
    past_3days = ChangeSummary(
        new_or_updated=25,
        deleted=5,
        changed=3,
        timestamp=datetime.now(timezone.utc) - timedelta(days=3)
    )
    
    print("\n2. Using print_summary() method with BOTH datetime and 'x ago':")
    current_summary.print_summary("Current Changes")
    past_5min.print_summary("Changes from 5 minutes ago")
    past_2hours.print_summary("Changes from 2 hours ago")  
    past_3days.print_summary("Changes from 3 days ago")
    
    print("\n3. Using string representation with enhanced timestamps:")
    print(f"Current: {current_summary}")
    print(f"5min ago: {past_5min}")
    print(f"2h ago: {past_2hours}")
    print(f"3d ago: {past_3days}")
    
    print("\n4. Summary without timestamp (full sync case):")
    no_timestamp = ChangeSummary(new_or_updated=5, deleted=1, changed=0)
    no_timestamp.print_summary("Full Sync Summary")
    print(f"No timestamp: {no_timestamp}")
    
    print("\n5. Testing real-time progression...")
    # Create a summary and show how the time changes
    test_summary = ChangeSummary(
        new_or_updated=3,
        deleted=1,
        changed=0,
        timestamp=datetime.now(timezone.utc)
    )
    
    print("Initial:")
    test_summary.print_summary("Real-time test")
    
    # Wait a few seconds and show again
    print("\nAfter 3 seconds:")
    time.sleep(3)
    test_summary.print_summary("Real-time test")
    
    print("\n✅ Demo completed!")


if __name__ == "__main__":
    demo_timestamp_functionality()
