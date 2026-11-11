#!/usr/bin/env bash
# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

# Makes a release of Cube Net.
#
# Usage:
#   ./release.sh 1.2.0             release version 1.2.0 (tag v1.2.0)
#   ./release.sh 1.2.0 --dry-run   only run the checks; change nothing
#   ./release.sh 1.2.0 --fix       tag 1.2.0 again, on the commit that fixes
#                                  what made its workflow fail (only while
#                                  the release isn't published)
#
# Before releasing, write what's new under "## Unreleased" in CHANGELOG.md:
# that becomes the release's notes.
#
# Every check and step is described in scripts/release.py, which this runs.
#
# Python: the one of the active virtual environment, or $PYTHON if set:
#   PYTHON=~/.pyenv/versions/cube_net_3.14.10/bin/python ./release.sh 1.2.0
set -euo pipefail
cd "$(dirname "$0")"
exec "${PYTHON:-python}" scripts/release.py "$@"
