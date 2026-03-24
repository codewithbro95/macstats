#!/usr/bin/env bash
# build.sh — Build a self-contained MacStats.app using PyInstaller
# Requires: conda with the macstats environment set up (run ./start.sh first, or manually:
#   conda env create -f environment.yml)
set -e

ENV_NAME="macstats"

# Ensure the conda environment is up to date
if ! conda env list | grep -q "^${ENV_NAME}\s"; then
    echo "Creating conda environment '${ENV_NAME}'..."
    conda env create -f environment.yml
else
    echo "Updating conda environment '${ENV_NAME}'..."
    conda env update -n "${ENV_NAME}" -f environment.yml --prune
fi

# Activate the conda env in this subshell
eval "$(conda shell.bash hook)"
conda activate "${ENV_NAME}"

echo ""
echo "Building MacStats.app with PyInstaller..."
pyinstaller MacStats.spec --clean --noconfirm

echo ""
echo "Done! Your app is at: dist/MacStats.app"
echo "You can open it with:  open dist/MacStats.app"
echo "Or distribute the entire dist/MacStats.app directory to users — no Python needed."
