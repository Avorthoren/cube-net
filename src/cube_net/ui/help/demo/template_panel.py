# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`TemplatePanel`: the instrument panel of an animation of making a template, down its sheet's left side, as the
window has it while a template is made: Net area, Draw hole, Validate and Create network, made of the window's own
widgets. They're enabled when the window's are, and look hovered and pushed as the pointer goes over them and clicks
(the animation's mouse isn't the real one, which Qt would follow)."""

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QAbstractButton, QApplication, QToolBar, QWidget

from cube_net.core.template import Template, TemplateState, ValidationStatus, template_area
from cube_net.ui import palette
from cube_net.ui.help.demo.steps import DRAW_HOLE, VALIDATE
from cube_net.ui.instruments.button_look import tool_buttons_style
from cube_net.ui.template.create_network_button import CreateNetworkButton
from cube_net.ui.template.draw_hole_button import DrawHoleButton
from cube_net.ui.template.net_area import NetArea
from cube_net.ui.template.template_tool import TemplateTool
from cube_net.ui.template.validate_button import ValidateButton


class TemplatePanel:
    def __init__(self, parent: QWidget, height: int) -> None:
        self.toolbar = toolbar = QToolBar(parent)
        toolbar.setOrientation(Qt.Orientation.Vertical)
        toolbar.setMovable(False)
        border = palette.TOOL_BUTTON_BORDER.name()
        window = QApplication.palette().color(QPalette.ColorRole.Window).name()  # (the sheet's would be white)
        panel = f"QToolBar {{ background: {window}; border: none; border-right: 1px solid {border}; }}"
        toolbar.setStyleSheet(f"{tool_buttons_style()} {panel}")
        toolbar.setFixedHeight(height)
        self.net_area = NetArea(toolbar)
        self.draw_hole = DrawHoleButton(toolbar)
        self.validate = ValidateButton(toolbar, with_separator=False)
        self.create_network = CreateNetworkButton(toolbar)  # (it does nothing in an animation)
        # Its buttons, by name.
        self.buttons: dict[str, QAbstractButton] = {DRAW_HOLE: self.draw_hole.button, VALIDATE: self.validate.button}
        self.fit()
        toolbar.move(0, 0)
        toolbar.show()

    def fit(self) -> None:
        """As wide as what it says needs (that changes with the language)."""
        self.toolbar.setFixedWidth(self.toolbar.sizeHint().width())

    def width(self) -> int:
        return self.toolbar.width()

    def area(self) -> QRect:
        return self.toolbar.geometry()

    def update(self, tool: TemplateTool) -> None:
        """Net area and which buttons can be clicked, as the window has them for the template as it is now (the
        window's `_update_edit_actions` and `TemplateMode.can_validate`)."""
        template: Template = tool.editor.template
        self.net_area.set_area(template_area(template))
        self.draw_hole.set_enabled(tool.can_start_hole())
        self.validate.set_enabled(
            tool.editor.state is TemplateState.FINALIZATION
            and template.complete
            and not tool.drawing_hole
            and not tool.busy()
            and self.validate.status is not ValidationStatus.VALID
        )
        self.create_network.set_enabled(
            self.validate.status is ValidationStatus.VALID and not tool.busy() and not tool.drawing_hole
        )

    def hover(self, button: QAbstractButton | None) -> None:
        """`button` looks as it does under the mouse; the others don't."""
        for each in self.buttons.values():
            under = each is button and each.isEnabled()
            if each.testAttribute(Qt.WidgetAttribute.WA_UnderMouse) != under:
                each.setAttribute(Qt.WidgetAttribute.WA_UnderMouse, under)
                each.update()
