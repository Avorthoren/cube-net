#!/usr/bin/env bash
# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

# Makes a release: ./release.sh 1.2.0 (./release.sh 1.2.0 --dry-run to only check). Everything it does and checks is
# in scripts/release.py. It runs with the python of the active virtual environment, or with $PYTHON if that's set.
set -euo pipefail
cd "$(dirname "$0")"
exec "${PYTHON:-python}" scripts/release.py "$@"
