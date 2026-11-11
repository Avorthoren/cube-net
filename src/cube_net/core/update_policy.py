# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""When to check for updates, and which release to offer (docs/idea.txt, updates).

- Help -> Check for updates offers the latest release whenever it's newer than the app.
- The automatic check (if switched on) runs at most once a calendar day, by the system's clock: at the first start of
  a day whose check worked. It offers the latest release only if it's newer than the app, and newer than the version
  the user turned down last time it was offered so (that one is never offered again automatically; the menu still
  offers it).
"""

import datetime

from cube_net.core.version import newer


def due_today(last_check: datetime.date | None, today: datetime.date) -> bool:
    """Is an automatic check due? Not if one worked today already."""
    return last_check != today


def offer_automatically(latest: str, current: str, skipped: str | None) -> bool:
    """Should the automatic check offer `latest`? If it's newer than the app, and than the version turned down."""
    return newer(latest, current) and (skipped is None or newer(latest, skipped))
