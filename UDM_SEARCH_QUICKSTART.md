# UDM Search Quick Start

## What's New?

Logstory now supports replaying logs directly from UDM searches without requiring pre-existing `.log` files. This is **Option 1** from issue #27: extend logstory's ingestion pipeline to accept UDM search results and apply timestamp shifting.

## Quick Examples

### Search for process execution events and replay with 1-day shift
```bash
logstory replay from-udm-search "metadata.event_type='PROCESS_EXECUTION'" \
  --customer-id=YOUR_CUSTOMER_ID \
  --credentials-path=/path/to/credentials.json
```

### Search for network connections from a specific IP
```bash
logstory replay from-udm-search "event.principal.ip_address='192.168.1.100'" \
  --timestamp-delta=7d
```

### Search with time filtering
```bash
logstory replay from-udm-search "metadata.event_type='USER_LOGIN' AND metadata.severity='WARNING'"
```

### Use environment variables for credentials
```bash
export LOGSTORY_CUSTOMER_ID=01234567-0123-4321-abcd-01234567890a
export LOGSTORY_CREDENTIALS_PATH=/path/to/credentials.json
export LOGSTORY_REGION=US

logstory replay from-udm-search "metadata.ingestion_time >= '2024-01-01'"
```

## How It Works

1. **Query UDM** — Logstory queries Chronicle's UDM Search API with your query
2. **Get Results** — Chronicle returns matching UDM events as JSON
3. **Shift Timestamps** — Logstory applies your timestamp delta (e.g., `--timestamp-delta=1d`)
4. **Ingest** — Updated events are replayed back into Chronicle
5. **Verify** — Special ingestion labels mark events as replayed from UDM search

## Finding Your Replayed Logs

After replay, search Chronicle with:
```
metadata.ingested_timestamp.seconds >= <EXECUTION_TIME>
metadata.ingestion_labels["source_type"]="udm_search"
```

## Command Options

```
logstory replay from-udm-search [OPTIONS] QUERY

Options:
  --customer-id TEXT               Chronicle customer ID
  --credentials-path TEXT          Path to service account JSON
  --region TEXT                    Chronicle region (US or EU)
  --timestamp-delta TEXT           Time shift (e.g., 1d, 2h, 30m)
  --env-file TEXT                  Path to .env file
  --api-type TEXT                  API type (rest or legacy)
  --project-id TEXT                GCP project ID for REST API
  --forwarder-name TEXT            Forwarder name for REST API
  --impersonate-service-account    Service account to impersonate
  --local-file-output              Write to local files instead of API
```

## Use Cases

- **Incident Response** — Replay security events with current timestamps to test detections
- **Testing** — Validate Chronicle configuration changes with historical UDM data
- **Demos** — Show security scenarios with realistic event sequences
- **Research** — Analyze subsets of historical data in a controlled replay scenario

## What Changed in the Code?

See `UDM_SEARCH_IMPLEMENTATION.md` for full technical details.

### Files Modified:
- `src/logstory/main.py` — Core UDM search and replay logic
- `src/logstory/logstory.py` — New CLI command
- `src/logstory/logtypes_events_timestamps.yaml` — UDM event timestamp patterns
- `tests/test_udm_search.py` — Unit tests

### Key New Functions:
- `_search_udm()` — Execute UDM search queries
- `_replay_from_udm()` — Orchestrate UDM search + replay

## FAQ

**Q: Do I still need `.log` files?**  
A: No, not for UDM search replay. Regular file-based replay still works as before.

**Q: Can I combine multiple UDM searches?**  
A: Use a complex query: `(metadata.event_type='PROCESS_EXECUTION' OR metadata.event_type='FILE_MODIFICATION')`

**Q: What timestamp delta values are supported?**  
A: Combinations like `1d`, `2h`, `30m`, or `1d2h30m`

**Q: How far back can I search?**  
A: By default, the last 30 days. Customize with start/end times (future enhancement).

**Q: Are replayed events marked differently?**  
A: Yes, they have ingestion labels: `replayed_from=logstory` and `source_type=udm_search`
