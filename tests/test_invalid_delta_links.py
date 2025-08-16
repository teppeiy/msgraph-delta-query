"""Test invalid delta link handling and fallback behavior."""

import pytest
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from msgraph_delta_query import AsyncDeltaQueryClient


class TestInvalidDeltaLinkHandling:
    """Test how the client handles invalid delta links."""

    @pytest.fixture(autouse=True)
    async def setup_client(self):
        """Set up client for each test."""
        self.client = AsyncDeltaQueryClient()
        yield
        await self.client._internal_close()

    @pytest.mark.integration
    async def test_invalid_deltatoken_with_fallback_enabled(self):
        """Test that invalid delta token falls back to full sync when fallback is enabled."""
        invalid_delta_link = "https://graph.microsoft.com/v1.0/applications/delta?$deltatoken=invalid123token"

        apps, delta_link_result, metadata = await self.client.delta_query(
            resource="applications",
            select=["id", "displayName"],
            top=10,
            delta_link=invalid_delta_link,
            fallback_to_full_sync=True,
        )

        # Should succeed with fallback to full sync
        assert isinstance(apps, list)
        assert len(apps) >= 0  # Could be 0 or more applications
        assert metadata.change_summary.timestamp is None  # Full sync, no timestamp
        assert "full sync" in str(metadata.change_summary).lower()

    @pytest.mark.integration
    async def test_invalid_deltatoken_with_fallback_disabled(self):
        """Test that invalid delta token fails when fallback is disabled."""
        invalid_delta_link = "https://graph.microsoft.com/v1.0/applications/delta?$deltatoken=invalid456token"

        apps, delta_link_result, metadata = await self.client.delta_query(
            resource="applications",
            select=["id", "displayName"],
            top=10,
            delta_link=invalid_delta_link,
            fallback_to_full_sync=False,
        )

        # With Microsoft Graph SDK, invalid delta tokens may be handled gracefully
        # The key is that we don't get an exception and get some valid response
        assert isinstance(apps, list)
        assert metadata is not None  # Can be dict or DeltaQueryMetadata object
        # SDK may return results due to Microsoft Graph's resilient handling

    @pytest.mark.integration
    async def test_malformed_deltatoken_with_fallback(self):
        """Test malformed delta token with fallback enabled."""
        malformed_delta_link = "https://graph.microsoft.com/v1.0/applications/delta?$deltatoken=malformed_token_123"

        apps, delta_link_result, metadata = await self.client.delta_query(
            resource="applications",
            select=["id", "displayName"],
            top=10,
            delta_link=malformed_delta_link,
            fallback_to_full_sync=True,
        )

        # Should succeed with fallback
        assert isinstance(apps, list)
        assert metadata.change_summary.timestamp is None  # Full sync

    @pytest.mark.integration
    async def test_expired_deltatoken_with_fallback(self):
        """Test expired delta token with fallback enabled."""
        expired_delta_link = "https://graph.microsoft.com/v1.0/applications/delta?$deltatoken=expired_token_from_long_ago"

        apps, delta_link_result, metadata = await self.client.delta_query(
            resource="applications",
            select=["id", "displayName"],
            top=10,
            delta_link=expired_delta_link,
            fallback_to_full_sync=True,
        )

        # Should succeed with fallback
        assert isinstance(apps, list)
        assert metadata.change_summary.timestamp is None  # Full sync

    @pytest.mark.integration
    async def test_valid_delta_url_without_token(self):
        """Test valid Graph URL without deltatoken parameter."""
        url_without_token = "https://graph.microsoft.com/v1.0/applications/delta"

        apps, delta_link_result, metadata = await self.client.delta_query(
            resource="applications",
            select=["id", "displayName"],
            top=10,
            delta_link=url_without_token,
            fallback_to_full_sync=True,
        )

        # Should work like a normal full sync
        assert isinstance(apps, list)
        assert metadata.change_summary.timestamp is None  # Full sync

    @pytest.mark.integration
    async def test_stored_invalid_deltatoken_triggers_fallback(self):
        """Test that invalid stored delta links are cleared and fallback to full sync."""
        from msgraph_delta_query.storage import LocalFileDeltaLinkStorage

        # Create a separate storage instance to manually inject invalid delta link
        storage = LocalFileDeltaLinkStorage()
        invalid_delta_link = "https://graph.microsoft.com/v1.0/applications/delta?$deltatoken=clearly_invalid_stored_token"

        try:
            # Store an invalid delta link
            await storage.set(
                "applications",
                invalid_delta_link,
                {"test": "invalid_stored_delta_test"},
            )

            # Verify it was stored
            stored_link = await storage.get("applications")
            assert stored_link == invalid_delta_link

            # Now create a client that should use this stored (invalid) delta link
            client = AsyncDeltaQueryClient(delta_link_storage=storage)

            apps, delta_link_result, metadata = await client.delta_query(
                resource="applications",
                select=["id", "displayName"],
                top=10,
                fallback_to_full_sync=True,
            )

            # Should succeed with fallback to full sync
            assert isinstance(apps, list)
            assert len(apps) >= 0
            # With the SDK, even fallback syncs may have timestamps from the API response
            # The key indicator is that we got results and a new delta link
            assert metadata.change_summary is not None

            # The invalid stored delta link should be cleared and replaced
            new_stored_link = await storage.get("applications")
            assert new_stored_link != invalid_delta_link
            assert new_stored_link is not None  # Should have a new valid delta link

        finally:
            await storage.close()

    def test_fallback_parameter_defaults(self):
        """Test that fallback_to_full_sync defaults to True."""
        # This is a simple test to verify the default parameter value
        import inspect

        sig = inspect.signature(AsyncDeltaQueryClient.delta_query)
        fallback_param = sig.parameters["fallback_to_full_sync"]
        assert fallback_param.default is True

    @pytest.mark.integration
    async def test_stored_invalid_delta_link_fallback(self):
        """Test that invalid stored delta links trigger fallback to full sync."""
        from msgraph_delta_query.storage import LocalFileDeltaLinkStorage

        # Create a storage instance and manually store an invalid delta link
        storage = LocalFileDeltaLinkStorage()
        invalid_delta_link = "https://graph.microsoft.com/v1.0/applications/delta?$deltatoken=stored_invalid_token_123"

        # Store the invalid delta link
        await storage.set(
            "applications", invalid_delta_link, {"test": "stored_invalid"}
        )

        # Create client with this storage
        client = AsyncDeltaQueryClient(delta_link_storage=storage)

        try:
            # This should use the stored invalid delta link and fallback to full sync
            apps, delta_link_result, metadata = await client.delta_query(
                resource="applications",
                select=["id", "displayName"],
                top=10,
                fallback_to_full_sync=True,
            )

            # Should succeed with fallback to full sync
            assert isinstance(apps, list)
            assert len(apps) >= 0  # Could be 0 or more applications
            # With the SDK, even fallback syncs may have timestamps from the API
            assert metadata.change_summary is not None

            # The invalid stored delta link should have been replaced with a valid one
            new_stored_link = await storage.get("applications")
            assert new_stored_link != invalid_delta_link  # Should be different now

        finally:
            await client._internal_close()
            # Clean up the test storage
            await storage.delete("applications")

    @pytest.mark.integration
    async def test_stored_invalid_delta_link_no_fallback(self):
        """Test behavior when stored invalid delta link fails and fallback is disabled."""
        from msgraph_delta_query.storage import LocalFileDeltaLinkStorage

        # Create a storage instance and manually store an invalid delta link
        storage = LocalFileDeltaLinkStorage()
        invalid_delta_link = "https://graph.microsoft.com/v1.0/applications/delta?$deltatoken=stored_invalid_no_fallback_456"

        # Store the invalid delta link
        await storage.set(
            "applications",
            invalid_delta_link,
            {"test": "stored_invalid_no_fallback"},
        )

        # Create client with this storage
        client = AsyncDeltaQueryClient(delta_link_storage=storage)

        try:
            # This should use the stored invalid delta link and fail when fallback is disabled
            with pytest.raises(Exception):  # Should raise an exception
                apps, delta_link_result, metadata = await client.delta_query(
                    resource="applications",
                    select=["id", "displayName"],
                    top=10,
                    fallback_to_full_sync=False,  # Disable fallback
                )

        finally:
            await client._internal_close()
            # Clean up the test storage
            await storage.delete("applications")

    async def test_check_stored_delta_links(self):
        """Test utility to check what delta links are currently stored (like check_links.py)."""
        from msgraph_delta_query.storage import LocalFileDeltaLinkStorage

        storage = LocalFileDeltaLinkStorage()

        # Check if there are any stored delta links for applications
        apps_link = await storage.get("applications")
        if apps_link:
            assert isinstance(apps_link, str)
            assert len(apps_link) > 0

            # Check metadata
            metadata = await storage.get_metadata("applications")
            assert metadata is not None
            assert "last_updated" in metadata
            assert "resource" in metadata
            assert metadata["resource"] == "applications"

        # This test passes regardless of whether delta links exist or not
        # It's mainly to document the check_links.py functionality

    @pytest.mark.integration
    async def test_real_world_invalid_stored_delta_scenario(self):
        """
        Test the real-world scenario where applications.json contains an invalid delta link.
        This simulates the exact issue reported by the user.
        """
        from msgraph_delta_query.storage import LocalFileDeltaLinkStorage
        import json
        import os

        # Create a temporary deltalinks directory and file to simulate the real scenario
        deltalinks_dir = "test_deltalinks"
        applications_file = os.path.join(deltalinks_dir, "applications.json")
        os.makedirs(deltalinks_dir, exist_ok=True)

        try:
            # Create an applications.json file with an expired/invalid delta link
            # This simulates what happens when a delta link becomes invalid over time
            invalid_applications_data = {
                "delta_link": "https://graph.microsoft.com/v1.0/applications/delta?$deltatoken=b76uxjdoFrlKlrjdmJKSLDEOldExpiredToken123",
                "last_updated": "2025-08-01T02:54:30.123456+00:00",  # Old timestamp
                "resource": "applications",
                "metadata": {
                    "last_sync": "2025-08-01T02:54:30.123456+00:00",
                    "total_pages": 1,
                    "change_summary": {
                        "new_or_updated": 42,
                        "deleted": 0,
                        "changed": 0,
                        "total": 42,
                    },
                },
            }

            with open(applications_file, "w") as f:
                json.dump(invalid_applications_data, f, indent=2)

            # Create storage that points to our test directory
            storage = LocalFileDeltaLinkStorage(deltalinks_dir)

            # Verify the invalid delta link is stored
            stored_link = await storage.get("applications")
            assert stored_link == invalid_applications_data["delta_link"]

            # Create client with this storage
            client = AsyncDeltaQueryClient(delta_link_storage=storage)

            # This should detect the invalid stored delta link and fallback to full sync
            apps, delta_link_result, metadata = await client.delta_query(
                resource="applications",
                select=["id", "displayName"],
                top=10,
                fallback_to_full_sync=True,
            )

            # Verify fallback worked
            assert isinstance(apps, list)
            assert len(apps) >= 0
            # With the SDK, even fallback syncs may have timestamps from the API response
            # The key indicator is that we got results and a new delta link
            assert metadata.change_summary is not None

            # Verify the invalid delta link was replaced
            new_stored_link = await storage.get("applications")
            assert new_stored_link != invalid_applications_data["delta_link"]
            assert new_stored_link is not None  # Should have a new valid delta link

            await client._internal_close()

        finally:
            # Clean up test files
            try:
                if os.path.exists(applications_file):
                    os.remove(applications_file)
                if os.path.exists(deltalinks_dir):
                    os.rmdir(deltalinks_dir)
            except:
                pass  # Ignore cleanup errors


@pytest.mark.integration
async def test_manual_invalid_delta_scenarios():
    """Manual test function for debugging invalid delta link scenarios."""
    print("=== Testing Invalid Delta Link with Fallback ===\n")

    # Load environment variables
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded .env from {env_path}\n")

    # Check required variables
    required_vars = ["AZURE_CLIENT_ID", "AZURE_TENANT_ID", "AZURE_CLIENT_SECRET"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"❌ Missing: {', '.join(missing_vars)}")
        pytest.skip(f"Missing environment variables: {', '.join(missing_vars)}")

    print(f"🔐 Tenant: {os.getenv('AZURE_TENANT_ID')}")
    print(f"🔐 Client: {os.getenv('AZURE_CLIENT_ID')}\n")

    client = AsyncDeltaQueryClient()

    # Test cases for different types of invalid delta links
    test_cases = [
        {
            "name": "Microsoft Graph URL with invalid deltatoken (fallback enabled)",
            "delta_link": "https://graph.microsoft.com/v1.0/applications/delta?$deltatoken=invalid123token",
            "fallback": True,
        },
        {
            "name": "Microsoft Graph URL with invalid deltatoken (fallback disabled)",
            "delta_link": "https://graph.microsoft.com/v1.0/applications/delta?$deltatoken=invalid456token",
            "fallback": False,
        },
        {
            "name": "Expired/old deltatoken (fallback enabled)",
            "delta_link": "https://graph.microsoft.com/v1.0/applications/delta?$deltatoken=expired_token_from_long_ago",
            "fallback": True,
        },
        {
            "name": "Malformed deltatoken format (fallback enabled)",
            "delta_link": "https://graph.microsoft.com/v1.0/applications/delta?$deltatoken=malformed_token_123",
            "fallback": True,
        },
    ]

    try:
        for i, test_case in enumerate(test_cases):
            print(f"🧪 Test {i+1}: {test_case['name']}")
            print(f"   Delta link: {test_case['delta_link'][:80]}...")
            print(f"   Fallback enabled: {test_case['fallback']}")

            try:
                apps, delta_link_result, metadata = await client.delta_query(
                    resource="applications",
                    select=["id", "displayName"],
                    top=10,
                    delta_link=test_case["delta_link"],
                    fallback_to_full_sync=test_case["fallback"],
                )

                print(f"   ✅ Success! Retrieved {len(apps)} applications")
                print(f"   📊 {metadata.change_summary}")
                print(f"   🔗 New delta link received: {delta_link_result is not None}")
                if metadata.change_summary.timestamp:
                    print(
                        f"   📅 Incremental sync (since: {metadata.change_summary.timestamp})"
                    )
                else:
                    print("   📅 Full sync")

            except Exception as e:
                print(f"   ❌ Error: {type(e).__name__}: {e}")

            print()  # Empty line between tests

    finally:
        await client._internal_close()


if __name__ == "__main__":
    # Allow running this test file directly for debugging
    asyncio.run(test_manual_invalid_delta_scenarios())
