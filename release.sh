#!/bin/sh
# Publish the library to PyPi

set -e

rm -rf dist
python3 setup.py sdist bdist_wheel
python3 -m twine upload dist/* --skip-existing
