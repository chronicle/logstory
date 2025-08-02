#!/bin/bash

BUCKET="file:///Users/dandye/Projects/all_usecases/ggl195-chronicle-replay-use-cases-aa6c1d50ac58702b5f85"
USECASES=("THW2")

for usecase in "${USECASES[@]}"; do
  echo "Processing usecase: $usecase"

  # Replay the usecase with automatic download if missing
  LOGSTORY_USECASES_BUCKETS=$BUCKET \
  uvx --refresh --from . logstory replay usecase $usecase \
  --get \
  --credentials-path=/Users/dandye/.ssh/malachite-blkht-cd32c011e9c4.json \
  --customer-id=f504dab3-dbf5-4fdd-88f9-e0a4f0f116cc \
  --region=US \
  --timestamp-delta=29d \
  --entities \
  --local-file-output
done
