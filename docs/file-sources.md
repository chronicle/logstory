# Local File System Sources

Logstory supports using local file system directories as usecase sources through `file://` URIs. This is useful for development, testing, private usecase collections, and Chronicle replay use cases.

## Overview

Local file system sources allow you to:
- Use Chronicle replay use cases directly from your local machine
- Develop and test custom usecases locally before publishing
- Access private usecase collections that can't be shared via cloud storage
- Work offline without internet connectivity
- Integrate with local development workflows

## URI Format

```bash
file:///absolute/path/to/directory
```

**Important:** 
- Must use absolute paths (starting with `/`)
- Requires three slashes: `file:///`
- Uses forward slashes on all platforms (Windows paths are converted internally)

## Directory Structure Requirements

Your local usecase directory must follow the standard logstory usecase structure:

```
/path/to/usecases/
├── USECASE_1/
│   ├── USECASE_1.md          # Metadata and documentation
│   ├── EVENTS/               # Event log files
│   │   ├── LOGTYPE1.log
│   │   └── LOGTYPE2.log
│   ├── ENTITIES/             # Entity log files (optional)
│   │   └── ENTITY_LOGTYPE.log
│   ├── RULES/                # YARA-L detection rules (optional)
│   │   └── rule_name.yl2
│   └── PARSER_EXTENSIONS/    # Custom parsers (optional)
│       └── CUSTOM_PARSER.proto
├── USECASE_2/
│   ├── USECASE_2.md
│   └── EVENTS/
│       └── ANOTHER_LOGTYPE.log
└── USECASE_3/
    └── ...
```

## Configuration

### Environment Variable

Set the source in your environment:

```bash
# Single local source
export LOGSTORY_USECASES_BUCKETS=file:///path/to/usecases

# Multiple sources including local
export LOGSTORY_USECASES_BUCKETS=gs://remote-bucket,file:///local/usecases

# Multiple local sources
export LOGSTORY_USECASES_BUCKETS=file:///dev/usecases,file:///prod/usecases
```

### .env File

Create environment files for different local setups:

**`.env.local`:**
```bash
LOGSTORY_USECASES_BUCKETS=file:///Users/developer/chronicle-usecases
LOGSTORY_LOCAL_LOG_DIR=/tmp/logstory-local
```

**`.env.chronicle`:**
```bash
LOGSTORY_USECASES_BUCKETS=file:///Users/analyst/chronicle-replay-use-cases
LOGSTORY_CUSTOMER_ID=01234567-0123-4321-abcd-01234567890a
LOGSTORY_CREDENTIALS_PATH=/secure/chronicle-credentials.json
```

### Command Line Override

Override configured sources on individual commands:

```bash
# List usecases from specific local directory
logstory usecases list-available --usecases-bucket file:///path/to/custom/usecases

# Download from local directory
logstory usecases get MY_USECASE --usecases-bucket file:///path/to/source/usecases
```

## Usage Examples

### Chronicle Replay Use Cases

If you have Chronicle replay use cases downloaded locally:

```bash
# Set the path to your Chronicle use cases
export LOGSTORY_USECASES_BUCKETS=file:///Users/analyst/chronicle-replay-use-cases

# List available use cases
logstory usecases list-available

# Download a specific use case
logstory usecases get AWS

# Replay the use case
logstory replay usecase AWS --env-file .env.chronicle
```

### Development Workflow

Working with custom usecases during development:

```bash
# Development directory structure
mkdir -p /dev/my-usecases/CUSTOM_TEST/{EVENTS,ENTITIES,RULES}

# Create a simple test usecase
cat > /dev/my-usecases/CUSTOM_TEST/CUSTOM_TEST.md << 'EOF'
---
title: CUSTOM_TEST
description: Custom test usecase for development
events:
  - log_type: TEST.log
    product_name: Test Product
    vendor_name: Test Vendor
---

# Custom Test Usecase

This is a test usecase for development.
EOF

# Add some test logs
echo '{"timestamp": "2024-01-01T10:00:00Z", "message": "test log"}' > /dev/my-usecases/CUSTOM_TEST/EVENTS/TEST.log

# Use the development usecases
export LOGSTORY_USECASES_BUCKETS=file:///dev/my-usecases
logstory usecases list-available
logstory usecases get CUSTOM_TEST
logstory replay usecase CUSTOM_TEST --local-file-output
```

### Testing and Validation

Use local files for testing without affecting production:

```bash
# Test configuration
export LOGSTORY_USECASES_BUCKETS=file:///test/usecases
export LOGSTORY_LOCAL_LOG_DIR=/test/output

# Test usecase structure validation
logstory usecases list-available

# Test replay to local files
logstory replay usecase TEST_CASE --local-file-output

# Validate generated logs
ls -la /test/output/
```

## Platform-Specific Paths

### Linux/macOS
```bash
# Standard Unix paths
file:///home/user/usecases
file:///Users/analyst/chronicle-usecases
file:///opt/logstory/usecases
file:///var/data/usecases
```

### Windows
```bash
# Windows paths (converted internally)
file:///C:/Users/analyst/usecases
file:///D:/Chronicle/replay-usecases
file:///C:/data/logstory/usecases
```

**Note:** On Windows, use forward slashes in the URI even though the underlying path uses backslashes.

## Performance Considerations

### Local vs Remote Sources

**Advantages of local sources:**
- Faster access (no network latency)
- Works offline
- No authentication required
- Full control over content
- Easy to modify and test

**Considerations:**
- Limited to single machine
- No automatic synchronization
- Manual management required
- Storage space on local machine

### Large Usecase Collections

For large usecase collections:

```bash
# Use symbolic links to organize
ln -s /shared/storage/chronicle-usecases /local/usecases
export LOGSTORY_USECASES_BUCKETS=file:///local/usecases

# Or mount network storage
mkdir -p /mnt/usecases
# mount network storage to /mnt/usecases
export LOGSTORY_USECASES_BUCKETS=file:///mnt/usecases
```

## Security Considerations

### File Permissions

Ensure proper file permissions:

```bash
# Make usecases readable
chmod -R 644 /path/to/usecases/**/*.log
chmod -R 644 /path/to/usecases/**/*.md
chmod 755 /path/to/usecases/*/

# Secure credentials if stored locally
chmod 600 /path/to/credentials.json
```

### Access Control

```bash
# Restrict access to usecase directory
chmod 750 /secure/usecases/
chown analyst:logstory-users /secure/usecases/

# Use in configuration
export LOGSTORY_USECASES_BUCKETS=file:///secure/usecases
```

## Integration Examples

### Docker Development

**Dockerfile:**
```dockerfile
FROM python:3.12-slim
RUN pip install logstory

# Mount local usecases as volume
VOLUME ["/usecases"]

ENV LOGSTORY_USECASES_BUCKETS=file:///usecases
WORKDIR /app

CMD ["logstory", "usecases", "list-available"]
```

**Usage:**
```bash
# Mount local directory into container
docker run -v /local/usecases:/usecases logstory-dev

# Or with docker-compose
```

**docker-compose.yml:**
```yaml
version: '3.8'
services:
  logstory:
    image: logstory-dev
    volumes:
      - ./usecases:/usecases:ro
      - ./config/.env:/app/.env:ro
    environment:
      - LOGSTORY_USECASES_BUCKETS=file:///usecases
```

### CI/CD Pipeline

**GitHub Actions:**
```yaml
name: Test Usecases
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v3
        with:
          python-version: '3.12'
          
      - name: Install logstory
        run: pip install logstory
        
      - name: Test local usecases
        env:
          LOGSTORY_USECASES_BUCKETS: file://${{ github.workspace }}/test-usecases
        run: |
          logstory usecases list-available
          logstory usecases get TEST_CASE
          logstory replay usecase TEST_CASE --local-file-output
          
      - name: Validate output
        run: |
          ls -la /tmp/var/log/logstory/
          # Add validation logic here
```

### VS Code Integration

**`.vscode/settings.json`:**
```json
{
  "terminal.integrated.env.linux": {
    "LOGSTORY_USECASES_BUCKETS": "file:///workspaces/project/usecases"
  },
  "terminal.integrated.env.osx": {
    "LOGSTORY_USECASES_BUCKETS": "file:///Users/developer/project/usecases"
  }
}
```

**`.vscode/tasks.json`:**
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "List Local Usecases",
      "type": "shell",
      "command": "logstory",
      "args": ["usecases", "list-available"],
      "group": "build"
    },
    {
      "label": "Test Usecase Locally",
      "type": "shell", 
      "command": "logstory",
      "args": [
        "replay", "usecase", "${input:usecaseName}",
        "--local-file-output"
      ],
      "group": "test"
    }
  ],
  "inputs": [
    {
      "id": "usecaseName",
      "description": "Usecase name to test",
      "default": "TEST_CASE",
      "type": "promptString"
    }
  ]
}
```

## Troubleshooting

### Common Issues

**1. Permission denied:**
```bash
# Error: Permission denied accessing directory: /path/to/usecases
# Solution: Check file permissions
chmod 755 /path/to/usecases
chmod 644 /path/to/usecases/**/*
```

**2. Directory not found:**
```bash
# Error: Directory does not exist: /path/to/usecases
# Solution: Verify absolute path and directory exists
ls -la /path/to/usecases
```

**3. No usecases found:**
```bash
# Issue: Directory exists but no usecases listed
# Solution: Check directory structure and file permissions
ls -la /path/to/usecases/*/
```

**4. Invalid path format:**
```bash
# Error: Relative paths not supported
# Wrong: file://./usecases
# Right: file:///absolute/path/to/usecases
```

### Debugging

**Verify directory structure:**
```bash
# Check if directory follows expected structure
find /path/to/usecases -name "*.md" -o -name "*.log" | head -10
```

**Test with simple example:**
```bash
# Create minimal test case
mkdir -p /tmp/test-usecases/SIMPLE_TEST/EVENTS
echo '{"test": "data"}' > /tmp/test-usecases/SIMPLE_TEST/EVENTS/TEST.log
cat > /tmp/test-usecases/SIMPLE_TEST/SIMPLE_TEST.md << 'EOF'
---
title: SIMPLE_TEST
description: Simple test
events:
  - log_type: TEST.log
    product_name: Test
    vendor_name: Test
---
# Simple Test
EOF

# Test with logstory
export LOGSTORY_USECASES_BUCKETS=file:///tmp/test-usecases
logstory usecases list-available
```

**Enable debug logging:**
```bash
PYTHONLOGLEVEL=DEBUG logstory usecases list-available \
  --usecases-bucket file:///path/to/usecases
```