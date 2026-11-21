# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Crash reports: an exception nothing caught (in a Qt callback, or in a background thread) writes a report next to
the session logs, tells the user where it is, and the application closes (`CrashHandler`)."""
