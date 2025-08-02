"""
Azure Blob Storage delta link storage implementation.
"""

import os
import json
import logging
import hashlib
from typing import Optional, Dict
from datetime import datetime, timezone

from .base import DeltaLinkStorage
from azure.storage.blob.aio import BlobServiceClient
from azure.identity.aio import DefaultAzureCredential
from azure.core.exceptions import ResourceNotFoundError


class AzureBlobDeltaLinkStorage(DeltaLinkStorage):
    """
    Stores delta links in Azure Blob Storage with metadata.
    
    Authentication priority:
    1. Explicit connection_string parameter (for local dev)
    2. Explicit account_url + credential parameters
    3. Managed identity with AZURE_STORAGE_ACCOUNT_NAME env var (production)
    4. Azure Functions local.settings.json (local dev fallback)
    5. Environment variables (AzureWebJobsStorage, AZURE_STORAGE_CONNECTION_STRING)
    6. Default Azurite configuration (localhost fallback)
    
    Args:
        account_url: Storage account URL (e.g., https://myaccount.blob.core.windows.net)
        container_name: Container name for storing delta links (default: "deltalinks")
        credential: Azure credential (if None, uses DefaultAzureCredential)
        connection_string: Alternative to account_url+credential for local dev
        local_settings_path: Path to local.settings.json for Azure Functions local dev
    """
    
    def __init__(
        self,
        account_url: Optional[str] = None,
        container_name: str = "deltalinks",
        credential: Optional[DefaultAzureCredential] = None,
        connection_string: Optional[str] = None,
        local_settings_path: str = "local.settings.json"
    ):
        self.container_name = container_name
        self._local_settings_path = local_settings_path
        self._blob_service_client = None
        self._credential_created = False
        
        # Priority order initialization:
        if connection_string:
            # 1. Explicit connection string (highest priority for local dev)
            self._connection_string = connection_string
            self._account_url = None
            self._credential = None
        elif account_url and credential:
            # 2. Explicit account_url + credential
            self._account_url = account_url
            self._credential = credential
            self._connection_string = None
        else:
            # 3-5. Auto-detection with managed identity priority
            detected = self._detect_connection_with_priority()
            self._connection_string = detected.get('connection_string')
            self._account_url = detected.get('account_url')
            self._credential = detected.get('credential')
            
            # With the default Azurite fallback, we should always have a connection
            if not self._connection_string and not self._account_url:
                raise ValueError(
                    "Could not establish Azure Blob Storage connection. Please provide:\n"
                    "- connection_string parameter, or\n"
                    "- account_url + credential parameters, or\n"
                    "- Set AZURE_STORAGE_ACCOUNT_NAME env var for managed identity, or\n"
                    "- Create local.settings.json with AzureWebJobsStorage, or\n"
                    "- Set AZURE_STORAGE_CONNECTION_STRING or AzureWebJobsStorage env vars\n"
                    "- Ensure Azurite is running for local development"
                )

    def _detect_connection_with_priority(self) -> dict:
        """
        Detect connection details using priority order:
        1. Managed identity with AZURE_STORAGE_ACCOUNT_NAME (production)
        2. Environment variables (AZURE_STORAGE_CONNECTION_STRING, AzureWebJobsStorage)
        3. Azure Functions local.settings.json (local dev fallback)
        4. Default Azurite configuration (localhost fallback)
        """
        # Priority 1: Managed identity with environment account name (production)
        account_name = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
        if account_name:
            account_url = f"https://{account_name}.blob.core.windows.net"
            logging.info(f"Azure Blob Storage: Using managed identity with account '{account_name}' (production)")
            return {
                'account_url': account_url,
                'credential': None,  # Will create DefaultAzureCredential later
                'connection_string': None
            }
        
        # Priority 2: Environment variables
        conn_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING') or os.getenv('AzureWebJobsStorage')
        if conn_str:
            # Extract account name from connection string for logging
            account_info = "unknown"
            if "AccountName=" in conn_str:
                try:
                    account_part = conn_str.split("AccountName=")[1].split(";")[0]
                    account_info = account_part
                except:
                    pass
            
            env_var_name = "AZURE_STORAGE_CONNECTION_STRING" if os.getenv('AZURE_STORAGE_CONNECTION_STRING') else "AzureWebJobsStorage"
            logging.info(f"Azure Blob Storage: Using connection string from {env_var_name} (account: {account_info})")
            return {
                'connection_string': conn_str,
                'account_url': None,
                'credential': None
            }
        
        # Priority 3: Azure Functions local.settings.json (local dev fallback)
        try:
            if os.path.exists(self._local_settings_path):
                with open(self._local_settings_path, 'r') as f:
                    settings = json.load(f)
                    
                # Check Values section for AzureWebJobsStorage
                values = settings.get('Values', {})
                conn_str = values.get('AzureWebJobsStorage')
                if conn_str:
                    # Extract account name for logging
                    account_info = "unknown"
                    if "AccountName=" in conn_str:
                        try:
                            account_part = conn_str.split("AccountName=")[1].split(";")[0]
                            account_info = account_part
                        except:
                            pass
                    
                    logging.info(f"Azure Blob Storage: Using connection string from {self._local_settings_path} (account: {account_info})")
                    return {
                        'connection_string': conn_str,
                        'account_url': None,
                        'credential': None
                    }
        except Exception as e:
            # Log but don't fail - local.settings.json is optional
            logging.debug(f"Could not read {self._local_settings_path}: {e}")
        
        # Priority 4: Default Azurite configuration (localhost fallback)
        logging.info("Azure Blob Storage: Using Azurite emulator (localhost:10000) - local development fallback")
        return {
            'connection_string': 'DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;',
            'account_url': None,
            'credential': None
        }
    
    async def _get_blob_service_client(self) -> BlobServiceClient:
        """Get or create blob service client."""
        if self._blob_service_client is None:
            if self._connection_string:
                # Use connection string
                self._blob_service_client = BlobServiceClient.from_connection_string(
                    self._connection_string
                )
                logging.debug("Created BlobServiceClient from connection string")
            else:
                # Use account URL with credential
                if not self._account_url:
                    raise ValueError("No account URL or connection string available for Azure Blob Storage")
                
                credential = self._credential
                if credential is None:
                    # Create DefaultAzureCredential for managed identity/local dev
                    credential = DefaultAzureCredential()
                    self._credential = credential
                    self._credential_created = True
                    logging.debug("Created DefaultAzureCredential for Azure Blob Storage")
                
                self._blob_service_client = BlobServiceClient(
                    account_url=self._account_url,
                    credential=credential
                )
                logging.debug(f"Created BlobServiceClient for {self._account_url}")
        
        return self._blob_service_client
    
    def _get_blob_name(self, resource: str) -> str:
        """Convert resource name to safe blob name."""
        # Similar to LocalFileDeltaLinkStorage but for blob names
        safe_name = resource.replace('/', '_').replace('\\', '_').replace(':', '_')
        if len(safe_name) > 200:
            safe_name = hashlib.md5(resource.encode()).hexdigest()
        return f"{safe_name}.json"
    
    async def _ensure_container_exists(self):
        """Ensure the container exists."""
        try:
            blob_service_client = await self._get_blob_service_client()
            container_client = blob_service_client.get_container_client(self.container_name)
            
            # Check if container exists, create if not
            try:
                await container_client.get_container_properties()
            except ResourceNotFoundError:
                await container_client.create_container()
                logging.info(f"Created container '{self.container_name}' in Azure Blob Storage")
                
        except Exception as e:
            logging.error(f"Failed to ensure container exists: {e}")
            raise
    
    async def get(self, resource: str) -> Optional[str]:
        """Get delta link for a resource."""
        try:
            await self._ensure_container_exists()
            blob_service_client = await self._get_blob_service_client()
            blob_name = self._get_blob_name(resource)
            
            blob_client = blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            # Download and parse blob content
            download_stream = await blob_client.download_blob()
            content = await download_stream.readall()
            data = json.loads(content.decode('utf-8'))
            
            return data.get("delta_link")
            
        except ResourceNotFoundError:
            # Blob doesn't exist - this is normal for first-time usage
            return None
        except Exception as e:
            logging.warning(f"Failed to read delta link for {resource} from Azure Blob Storage: {e}")
            return None
    
    async def get_metadata(self, resource: str) -> Optional[Dict]:
        """Get metadata for a resource including last sync time."""
        try:
            await self._ensure_container_exists()
            blob_service_client = await self._get_blob_service_client()
            blob_name = self._get_blob_name(resource)
            
            blob_client = blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            # Download and parse blob content
            download_stream = await blob_client.download_blob()
            content = await download_stream.readall()
            data = json.loads(content.decode('utf-8'))
            
            return {
                "last_updated": data.get("last_updated"),
                "metadata": data.get("metadata", {}),
                "resource": data.get("resource")
            }
            
        except ResourceNotFoundError:
            # Blob doesn't exist - this is normal for first-time usage
            return None
        except Exception as e:
            logging.warning(f"Failed to read metadata for {resource} from Azure Blob Storage: {e}")
            return None
    
    async def set(self, resource: str, delta_link: str, metadata: Optional[Dict] = None):
        """Set delta link and metadata for a resource."""
        try:
            await self._ensure_container_exists()
            blob_service_client = await self._get_blob_service_client()
            blob_name = self._get_blob_name(resource)
            
            data = {
                "delta_link": delta_link,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "resource": resource,
                "metadata": metadata or {}
            }
            
            blob_client = blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            # Upload blob content
            content = json.dumps(data, indent=2).encode('utf-8')
            await blob_client.upload_blob(content, overwrite=True)
            
            logging.debug(f"Saved delta link for {resource} to Azure Blob Storage")
            
        except Exception as e:
            logging.error(f"Failed to save delta link for {resource} to Azure Blob Storage: {e}")
            raise
    
    async def delete(self, resource: str):
        """Delete delta link and metadata for a resource."""
        try:
            blob_service_client = await self._get_blob_service_client()
            blob_name = self._get_blob_name(resource)
            
            blob_client = blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            await blob_client.delete_blob()
            logging.debug(f"Deleted delta link for {resource} from Azure Blob Storage")
            
        except ResourceNotFoundError:
            # Blob doesn't exist - this is fine
            pass
        except Exception as e:
            logging.warning(f"Failed to delete delta link for {resource} from Azure Blob Storage: {e}")
    
    async def close(self):
        """Close the blob service client and credential."""
        if self._blob_service_client:
            await self._blob_service_client.close()
            self._blob_service_client = None
        
        if self._credential and hasattr(self._credential, 'close'):
            try:
                await self._credential.close()
            except Exception as e:
                logging.debug(f"Error closing credential: {e}")
            self._credential = None
            self._credential_created = False
