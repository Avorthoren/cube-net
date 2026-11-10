# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The application's languages (Settings -> Preferences -> Language): English and Russian.

Every text the user sees goes through `tr` (or `bind`, which also retranslates it when the language changes). The
English text is the key; `russian.RUSSIAN` has its translation (a test makes sure every one has one).
"""

from cube_net.ui.i18n.language import Language
from cube_net.ui.i18n.translator import TRANSLATIONS, bind, tr

__all__ = ["TRANSLATIONS", "Language", "bind", "tr"]
