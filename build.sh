#!/usr/bin/env bash
# exit on error
set -o errexit

# Install the latest version of pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Make sure setuptools is properly installed
pip install --upgrade setuptools wheel

# Print versions for debugging
echo "Python version:"
python --version
echo "Pip version:"
pip --version
echo "Setuptools version:"
pip show setuptools
