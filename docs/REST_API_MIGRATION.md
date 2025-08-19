# REST API Migration Guide

This guide helps you migrate from the legacy malachite ingestion API to the new Chronicle REST API.

## Overview

Logstory now supports both the legacy malachite ingestion API and the new Chronicle REST API. The system automatically detects which API to use based on your credentials, or you can explicitly specify the API type.

## Key Differences

### Legacy API (Malachite)
- Endpoint: `malachiteingestion-pa.googleapis.com`
- Scope: `https://www.googleapis.com/auth/malachite-ingestion`
- Simple authentication with service account
- Batch endpoints: `/v2/unstructuredlogentries:batchCreate`, `/v2/udmevents:batchCreate`

### REST API (Chronicle)
- Endpoint: `chronicle.googleapis.com`
- Scope: `https://www.googleapis.com/auth/cloud-platform`
- Requires Google Cloud project ID
- Supports forwarder management
- Supports service account impersonation
- Enhanced regional support

## Migration Steps

### 1. Obtain New Credentials

The REST API requires service account credentials with the `cloud-platform` scope instead of the `malachite-ingestion` scope.

**To create new credentials:**
1. Go to the Google Cloud Console
2. Navigate to IAM & Admin > Service Accounts
3. Create a new service account or update an existing one
4. Grant the necessary Chronicle API permissions
5. Download the JSON key file

### 2. Update Configuration

#### Option A: Using Environment Files

**For Legacy API (.env.legacy):**
```bash
LOGSTORY_CUSTOMER_ID=01234567-0123-4321-abcd-01234567890a
LOGSTORY_CREDENTIALS_PATH=/path/to/malachite-credentials.json
LOGSTORY_REGION=US
```

**For REST API (.env.rest):**
```bash
LOGSTORY_CUSTOMER_ID=01234567-0123-4321-abcd-01234567890a
LOGSTORY_PROJECT_ID=my-project-123
LOGSTORY_CREDENTIALS_PATH=/path/to/rest-credentials.json
LOGSTORY_REGION=US
LOGSTORY_API_TYPE=rest  # Optional, auto-detected if not set
```

#### Option B: Using Command Line

**Legacy API:**
```bash
logstory replay usecase RULES_SEARCH_WORKSHOP \
  --customer-id=01234567-0123-4321-abcd-01234567890a \
  --credentials-path=/path/to/malachite-credentials.json
```

**REST API:**
```bash
logstory replay usecase RULES_SEARCH_WORKSHOP \
  --customer-id=01234567-0123-4321-abcd-01234567890a \
  --project-id=my-project-123 \
  --credentials-path=/path/to/rest-credentials.json \
  --api-type=rest
```

### 3. Test the Migration

1. **Start with a small test:**
   ```bash
   # Test with a single usecase
   logstory replay usecase RULES_SEARCH_WORKSHOP --env-file .env.rest
   ```

2. **Verify ingestion:**
   - Check your Chronicle dashboard for the ingested logs
   - Verify timestamps and labels are correct
   - Ensure no data loss or errors

3. **Gradual rollout:**
   - Test with different usecases
   - Monitor for any issues
   - Switch production workloads after validation

## Auto-Detection

Logstory can automatically detect which API to use based on:

1. **Environment variable:** `LOGSTORY_API_TYPE` (if set)
2. **Project ID presence:** If `LOGSTORY_PROJECT_ID` is set, uses REST API
3. **Credential analysis:** Examines credential file for API indicators
4. **Default:** Falls back to legacy API for backward compatibility

## Advanced Features (REST API Only)

### Custom Forwarder Names
```bash
export LOGSTORY_FORWARDER_NAME=MyCustomForwarder
```

### Service Account Impersonation
```bash
export LOGSTORY_IMPERSONATE_SERVICE_ACCOUNT=service-account@project.iam.gserviceaccount.com
```

### Enhanced Regional Support
```bash
# REST API supports more regions
export LOGSTORY_REGION=EUROPE  # or UK, ASIA, SYDNEY, etc.
```

## Backward Compatibility

**Important:** Existing scripts and configurations continue to work without any changes. The legacy API remains fully supported.

### No Changes Required For:
- Existing .env files without API_TYPE
- Current command-line scripts
- Cloud Functions using Secret Manager
- CI/CD pipelines

### Gradual Migration Path:
1. Continue using legacy API (no action required)
2. Test REST API in development environment
3. Update credentials and add project ID
4. Switch to REST API when ready

## Troubleshooting

### Common Issues

**1. Authentication Error with REST API**
- Ensure credentials have `cloud-platform` scope
- Verify project ID is correct
- Check service account permissions in Google Cloud Console

**2. Auto-detection choosing wrong API**
- Explicitly set `LOGSTORY_API_TYPE=rest` or `LOGSTORY_API_TYPE=legacy`
- Ensure environment variables are properly set

**3. Forwarder Creation Fails**
- Check project permissions for creating forwarders
- Verify region is correctly specified
- Try with a different forwarder name

### Debug Mode

Enable verbose logging to troubleshoot:
```bash
PYTHONLOGLEVEL=DEBUG logstory replay usecase RULES_SEARCH_WORKSHOP --env-file .env.rest
```

## Benefits of REST API

1. **Better Performance:** Optimized for modern cloud infrastructure
2. **Enhanced Security:** Support for service account impersonation
3. **Forwarder Management:** Automatic forwarder creation and caching
4. **Regional Flexibility:** Support for more geographic regions
5. **Future-Proof:** Aligned with Google Cloud's API standards

## Support

For issues or questions:
- Check the [main README](../README.md) for general usage
- Review example .env files: `.env.legacy.example`, `.env.rest.example`
- Enable debug logging for detailed error messages
- Report issues on the GitHub repository

## Summary

The REST API migration is optional but recommended for new deployments. Existing users can continue using the legacy API without any changes. The system provides auto-detection and smooth migration paths to ensure a seamless transition when you're ready to upgrade.