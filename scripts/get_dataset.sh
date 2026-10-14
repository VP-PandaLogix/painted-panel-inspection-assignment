#!/usr/bin/env bash
# Download the assignment dataset into ./data (about 55 MB).
set -euo pipefail
cd "$(dirname "$0")/.."
URL="https://github.com/VP-PandaLogix/painted-panel-inspection-assignment/releases/download/dataset-v1/painted-panel-dataset-v1.zip"
mkdir -p data
if [ -f data/station.yaml ]; then echo "data/ already present"; exit 0; fi
echo "downloading dataset..."
curl -fL --retry 3 -o data/dataset.zip "$URL"
unzip -q data/dataset.zip -d data
rm data/dataset.zip
echo "done: $(find data -name '*.jpg' | wc -l | tr -d ' ') images in data/"
