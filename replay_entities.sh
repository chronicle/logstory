#!/bin/bash

BUCKET="file:///Users/dandye/Projects/all_usecases/ggl195-chronicle-replay-use-cases-aa6c1d50ac58702b5f85"
USECASES=("MALWARE_IOC")

for usecase in "${USECASES[@]}"; do
  echo "Processing usecase: $usecase"

  # Replay the usecase with automatic download if missing
  LOGSTORY_USECASES_BUCKETS=$BUCKET \
  uvx --refresh --from . logstory replay usecase $usecase \
  --get \
  --credentials-path=/Users/dandye/.ssh/malachite-ltstr740-5526c600e791-ingestion-api.json \
  --customer-id=7e977ce4-f45d-43b2-aea0-52f8b66acd80 \
  --region=US \
  --timestamp-delta=1d \
  --entities \
  --local-file-output
done
