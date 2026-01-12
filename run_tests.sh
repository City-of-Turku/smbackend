#!/bin/bash

set -xe
# Run Python side code neatness tests
flake8
black --check .
isort . -c
pytest --cov=.