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
LOGSTORY_API_TYPE=legacy  # Required
```

**For REST API (.env.rest):**
```bash
LOGSTORY_CUSTOMER_ID=01234567-0123-4321-abcd-01234567890a
LOGSTORY_PROJECT_ID=my-project-123
LOGSTORY_CREDENTIALS_PATH=/path/to/rest-credentials.json
LOGSTORY_REGION=US
LOGSTORY_API_TYPE=rest  # Required
```

#### Option B: Using Command Line

**Legacy API:**
```bash
logstory replay usecase RULES_SEARCH_WORKSHOP \
  --customer-id=01234567-0123-4321-abcd-01234567890a \
  --credentials-path=/path/to/malachite-credentials.json \
  --api-type=legacy
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

## API Type Configuration

**Important:** `LOGSTORY_API_TYPE` is now **required** and must be explicitly set to either `rest` or `legacy`. 

- **No auto-detection** is performed
- **No fallback behavior** - the system will fail with clear error messages if misconfigured  
- This ensures predictable behavior and prevents silent failures

To specify the API type:
- Set `LOGSTORY_API_TYPE=rest` for the new Chronicle REST API
- Set `LOGSTORY_API_TYPE=legacy` for the legacy malachite API

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

## Migration Requirements

**Breaking Change:** `LOGSTORY_API_TYPE` is now **required** for all configurations.

### Required Updates:
- **All .env files** must include `LOGSTORY_API_TYPE=legacy` or `LOGSTORY_API_TYPE=rest`
- **All command-line scripts** must include `--api-type=legacy` or `--api-type=rest`
- **Cloud Functions** must set the `LOGSTORY_API_TYPE` environment variable
- **CI/CD pipelines** must set the `LOGSTORY_API_TYPE` environment variable

### Migration Steps:
1. **Update existing configurations** to explicitly set `LOGSTORY_API_TYPE=legacy`
2. **Test that existing workflows still work** with the explicit API type
3. **For new REST API usage:** Set `LOGSTORY_API_TYPE=rest` and add required `LOGSTORY_PROJECT_ID`
4. **No silent fallbacks** - any misconfiguration will fail with clear error messages

## Troubleshooting

### Common Issues

**1. Missing API Type Error**
```
LOGSTORY_API_TYPE environment variable must be set to 'rest' or 'legacy'
```
- **Solution:** Add `LOGSTORY_API_TYPE=rest` or `LOGSTORY_API_TYPE=legacy` to your environment

**2. Missing Project ID for REST API**
```
LOGSTORY_API_TYPE=rest is specified but LOGSTORY_PROJECT_ID is missing!
```
- **Solution:** Add `LOGSTORY_PROJECT_ID=your-project-id` when using REST API

**3. Authentication Error with REST API**
- Ensure credentials have `cloud-platform` scope
- Verify project ID is correct
- Check service account permissions in Google Cloud Console

**4. Forwarder Creation Fails**
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

## Environment Variable to CLI Parameter Mapping

| Environment Variable | CLI Parameter | Description |
|---------------------|---------------|-------------|
| `LOGSTORY_CUSTOMER_ID` | `--customer-id` | Chronicle customer ID |
| `LOGSTORY_PROJECT_ID` | `--project-id` | Google Cloud project ID (REST API only) |
| `LOGSTORY_CREDENTIALS_PATH` | `--credentials-path` | Path to service account credentials JSON file |
| `LOGSTORY_REGION` | `--region` | Geographic region (US, EUROPE, UK, ASIA, SYDNEY) |
| `LOGSTORY_API_TYPE` | `--api-type` | **Required:** API type to use (rest or legacy) |
| `LOGSTORY_FORWARDER_NAME` | `--forwarder-name` | Custom forwarder name (REST API only) |
| `LOGSTORY_IMPERSONATE_SERVICE_ACCOUNT` | `--impersonate-service-account` | Service account to impersonate (REST API only) |

## Support

For issues or questions:
- Check the [main README](../README.md) for general usage
- Review example .env files: `.env.legacy.example`, `.env.rest.example`
- Enable debug logging for detailed error messages
- Report issues on the GitHub repository

## Summary

**Breaking Change:** `LOGSTORY_API_TYPE` is now required for all configurations. This ensures predictable behavior and eliminates silent fallbacks that could cause debugging issues.

### For Existing Users:
- **Update configurations** to explicitly set `LOGSTORY_API_TYPE=legacy` to continue using the legacy API
- **No automatic detection** - you must specify which API to use
- **Clear error messages** when configuration is missing or incorrect

### For New REST API Users:
- Set `LOGSTORY_API_TYPE=rest` and `LOGSTORY_PROJECT_ID`
- Follow the enhanced error messages for any missing configuration
- Benefit from improved performance and features