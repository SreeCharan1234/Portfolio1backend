#!/usr/bin/env bash
# exit on error
set -o errexit

# Install the latest version of pip
pip install --upgrade pip

# Install setuptools and wheel first
pip install setuptools==68.2.2 wheel==0.41.2

# Install dependencies with specific versions
pip install -r requirements.txt

# Print versions for debugging
echo "Python version:"
python --version
echo "Pip version:"
pip --version
echo "Setuptools version:"
pip show setuptools
echo "Wheel version:"
pip show wheel

# Make sure port is set correctly
echo "PORT: $PORT"
echo "Setting up port binding for Render deployment"
