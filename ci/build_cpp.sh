#!/bin/bash
# Copyright (c) 2022, NVIDIA CORPORATION.

set -euo pipefail

source rapids-env-update

export CMAKE_GENERATOR=Ninja

rapids-print-env

version=$(rapids-generate-version)

rapids-logger "Begin cpp build"

RAPIDS_PACKAGE_VERSION=${version} rapids-conda-retry mambabuild conda/recipes/libcucim

rapids-upload-conda-to-s3 cpp
