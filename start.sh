#!/usr/bin/env bash
set -e

ENV_NAME="macstats"

# Check if conda environment exists
if ! conda env list | grep -q "^${ENV_NAME}\s"; then
    echo "Creating conda environment '${ENV_NAME}'..."
    conda env create -f environment.yml
else
    echo "Updating conda environment '${ENV_NAME}'..."
    conda env update -n "${ENV_NAME}" -f environment.yml --prune
fi

echo "Starting MacStats..."
# Initialize conda in this subshell and activate
eval "$(conda shell.bash hook)"
conda activate "${ENV_NAME}"
python main.py
