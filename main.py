# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Thin launcher, e.g. for running from the IDE. All logic lives in the `cube_net` package."""

import sys

from cube_net.app import main

if __name__ == "__main__":
    sys.exit(main())
