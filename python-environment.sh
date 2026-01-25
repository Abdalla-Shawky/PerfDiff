#!/usr/bin/env bash

# this script will creates and activate a python environment we use it after a recent distribution in PEP-668 https://peps.python.org/pep-0668/
# the script also updates the setuptools as it needs to be updated

set -e
export HOMEBREW_NO_AUTO_UPDATE=1
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PIP_NO_PROGRESS_BAR=off
ROOT_DIR=$(git rev-parse --show-toplevel)

echo "Creating Python virtual environment...🐍"
brew install python@3.13 > /dev/null
python3.13 -m venv $ROOT_DIR/performance-venv

echo "Activating Python virtual environment...🐍"
source $ROOT_DIR/performance-venv/bin/activate
