# Authentication Setup for Microsoft Graph Delta Query

This library uses Azure Identity's `DefaultAzureCredential` which automatically tries multiple authentication methods in order.

## Authentication Methods (tried in order)

### 1. Environment Variables (Recommended for local development)
Set these environment variables:
```bash
AZURE_CLIENT_ID=your-app-registration-client-id
AZURE_CLIENT_SECRET=your-app-registration-client-secret
AZURE_TENANT_ID=your-azure-tenant-id
```

**Using .env file:**
1. Copy `.env.example` to `.env`
2. Fill in your Azure App Registration details
3. The examples will automatically load the .env file

### 2. Managed Identity (Automatic in Azure)
When running in Azure (App Service, Functions, VMs, etc.), managed identity is automatically used.

### 3. Azure CLI
```bash
az login
```

### 4. Visual Studio / VS Code
Sign in through Visual Studio or VS Code Azure extensions.

### 5. Azure PowerShell
```powershell
Connect-AzAccount
```

## Setting up Azure App Registration

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** > **App registrations**
3. Click **New registration**
4. Give it a name (e.g., "Graph Delta Query App")
5. Select **Accounts in this organizational directory only**
6. Click **Register**

### Get the credentials:
- **Application (client) ID** → `AZURE_CLIENT_ID`
- **Directory (tenant) ID** → `AZURE_TENANT_ID`

### Create a client secret:
1. Go to **Certificates & secrets**
2. Click **New client secret**
3. Add description and set expiry
4. Copy the **Value** (not Secret ID) → `AZURE_CLIENT_SECRET`

### Grant permissions:
1. Go to **API permissions**
2. Click **Add a permission** > **Microsoft Graph** > **Application permissions**
3. Add required permissions:
   - `Application.Read.All` - for applications delta queries
   - `User.Read.All` - for users delta queries  
   - `Group.Read.All` - for groups delta queries
   - `Directory.Read.All` - for service principals delta queries
4. Click **Grant admin consent**

## Troubleshooting

### "Environment variables are not fully configured"
Make sure all three variables are set:
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET` 
- `AZURE_TENANT_ID`

### "No response from the IMDS endpoint"
This is normal when not running in Azure - it will fall back to other methods.

### "SharedTokenCacheCredential authentication unavailable"
This is normal if you haven't used Azure CLI or Visual Studio - it will fall back to other methods.

### Azure CLI UTF-8 error
Try running:
```bash
az login --use-device-code
```

## Testing Authentication

Run any example script to test your authentication setup:
```bash
cd examples
python simple_applications_sync.py
```

The script will show which authentication method is being attempted and provide helpful guidance.
