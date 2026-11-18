# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`ValidationStatus`: what the last explicit Validate said about the template as it is now (docs/template_plan.md,
§8.2). A template starts Undefined; Validate makes it Valid or Invalid; any change to the template makes it Undefined
again. Saved in the template's file."""

from enum import Enum


class ValidationStatus(Enum):
    # Not validated since it last changed.
    UNDEFINED = "undefined"

    # Validated, no problem found.
    VALID = "valid"

    # Validated, a problem found.
    INVALID = "invalid"
