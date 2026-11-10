# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Russian texts, by their English ones. Every text given to `tr` or `bind` must be here (a test checks that)."""

RUSSIAN: dict[str, str] = {
    # The menus.
    "&File": "&Файл",
    "&New": "&Новый",
    "&Open...": "&Открыть...",
    "&Save": "&Сохранить",
    "Save &As...": "Сохранить &как...",
    "&Quit": "&Выход",
    "&Edit": "&Правка",
    "&Approve cut": "&Утвердить разрез",
    "&Undo": "&Отменить",
    "&Redo": "&Повторить",
    "&Settings": "&Настройки",
    "Settings of the application (not of the project)": "Настройки приложения (не проекта)",
    "&Help": "&Справка",
    "&About": "&О программе",
    "Check for &updates": "Проверить &обновления",
    # The instruments panel.
    "Instruments": "Инструменты",
    "Ruler": "Линейка",
    "Ruler (R): click on the sheet to measure; turn off to clear": (
        "Линейка (R): щёлкайте по листу, чтобы измерять; выключите, чтобы очистить"
    ),
    "Total length of the placed ruler segments": "Общая длина отрезков линейки",
    "Area": "Площадь",
    "Area of the smallest rectangle (any orientation) that contains the net": (
        "Площадь наименьшего прямоугольника (повёрнутого как угодно), в который помещается развёртка"
    ),
    "Target area": "Цель",
    "The project's goal: an area below this is a success": "Цель проекта: площадь меньше этой — успех",
    "Bounds": "Рамка",
    "Show the smallest bounding rectangle (B)": "Показать наименьший описанный прямоугольник (B)",
    "Start logging": "Начать логирование",
    "Stop logging": "Остановить логирование",
    "Logs": "Журналы",
    "Open the folder with session logs": "Открыть папку с журналами сеансов",
    # The status bar and the window's title.
    "Recording session to {path}": "Сеанс записывается в {path}",
    "Session recording stopped": "Запись сеанса остановлена",
    "Could not open the folder with session logs": "Не удалось открыть папку с журналами сеансов",
    "Untitled": "Без имени",
    # Projects: files and questions.
    "Open project": "Открыть проект",
    "Save project as": "Сохранить проект как",
    "Cube Net projects (*{suffix})": "Проекты Cube Net (*{suffix})",
    "Save changes?": "Сохранить изменения?",
    'Save changes to "{name}"?': "Сохранить изменения в проекте «{name}»?",
    "Don't save": "Не сохранять",
    "Can't open the project": "Не удалось открыть проект",
    "Start a new project, or open another one?": "Начать новый проект или открыть другой?",
    "New project": "Новый проект",
    # Why a project can't be saved or opened (from core.project; values are as the system or the file has them).
    "It isn't a Cube Net project.": "Это не проект Cube Net.",
    "It is damaged.": "Файл повреждён.",
    "It is damaged ({detail}).": "Файл повреждён ({detail}).",
    "It was saved by a newer version of the application.": "Он сохранён более новой версией приложения.",
    "It has an unknown format version: {version}.": "У него неизвестная версия формата: {version}.",
    "Can't save {path}: {reason}.": "Не удалось сохранить {path}: {reason}.",
    "Can't open {path}: {reason}.": "Не удалось открыть {path}: {reason}.",
    "Can't open {path}. {problem}": "Не удалось открыть {path}. {problem}",
    # The approve button.
    "Approve": "Утвердить",
    "Cancel": "Отменить",
    # The settings panel.
    "Preferences": "Основные",
    "Style": "Оформление",
    "Hide settings": "Скрыть настройки",
    "Language": "Язык",
    "Show vertex labels": "Показывать метки вершин",
    "Auto-start logging": "Автоматически начинать логирование",
    "Blink when target area achieved": "Мигать, когда цель достигнута",
    "Maximum zoom:": "Макс. масштаб:",
    "px per unit": "пикс. на ед.",
    "How far in the sheet can be zoomed: how many pixels the edge of the cube takes": (
        "Насколько можно приблизить лист: сколько пикселей занимает ребро куба"
    ),
    "px": "пикс.",
    "Faces colors": "Цвета граней",
    "Faces tiling": "Разбиение граней",
    "Cuts and folds": "Разрезы и сгибы",
    "Vertices": "Вершины",
    "Grid": "Сетка",
    "Restore default": "По умолчанию",
    'Restore the default values of "{section}"?': "Вернуть значения по умолчанию в разделе «{section}»?",
    "Dashes": "Штрихи",
    "Thickness": "Толщина",
    "Radius": "Радиус",
    # The Help menu's windows.
    "About {name}": "О программе {name}",
    "Version {version}, {date}": "Версия {version}, {date}",
    "by UNDEFEAT in attempts to solve {puzzle}": "разработано UNDEFEAT в попытках решить {puzzle}",
    "this puzzle": "эту задачу",
    "Copy and close": "Скопировать и закрыть",
    "Copyright © 2026 Viktor Podust": "© 2026 Viktor Podust",
    "GNU GPL v3 or later": "GNU GPL версии 3 или более поздней",
    "Free software under the {license}, with ABSOLUTELY NO WARRANTY": (
        "Свободная программа под лицензией {license}, БЕЗ КАКИХ-ЛИБО ГАРАНТИЙ"
    ),
    "Source code: {source}": "Исходный код: {source}",
    "Close": "Закрыть",
    "Check for updates": "Проверка обновлений",
    "Under development...": "В разработке...",
    # Help -> Help.
    "{name} Help": "{name} — справка",
    "How it works": "Как это работает",
    (
        "This application lets you build cube nets: simple polygons (without self-intersections) that, when folded, "
        "cover the whole surface of the unit cube without overlaps. So the area of such a polygon is always equal to "
        "the surface area of the unit cube: 6 square units."
    ): (
        "Это приложение позволяет строить развёртки куба: простые многоугольники (без самопересечений), которые после "
        "сгибания покрывают всю поверхность единичного куба без наложений. Поэтому площадь такого многоугольника "
        "всегда равна площади поверхности единичного куба: 6 квадратных единиц."
    ),
    (
        "If a cube net is cut into two pieces, they can be rearranged and glued together again along a pair of edges "
        "that meet on the cube. That's exactly what the application is for:"
    ): (
        "Если разрезать развёртку на две части, их можно переставить и снова склеить по паре рёбер, которые сходятся "
        "на кубе. Именно для этого и создано приложение:"
    ),
    "Make a cut": "Сделайте разрез",
    (
        "Click on any edge or vertex of the perimeter to start a cut: one or more segments joined end to end. A cut "
        "starts and ends on the perimeter, and all its other points must lie strictly inside the net, so it ends as "
        "soon as you click on the perimeter again."
    ): (
        "Щёлкните по любому ребру или вершине периметра, чтобы начать разрез: один или несколько отрезков, соединённых "
        "друг за другом. Разрез начинается и заканчивается на периметре, а все остальные его точки должны лежать "
        "строго внутри развёртки, поэтому он заканчивается, как только вы снова щёлкнете по периметру."
    ),
    "Adjust it": "Поправьте его",
    (
        "Adjust the cut if needed: drag any of its vertices, click the circle in the middle of a segment to add a "
        "vertex there, or hold Ctrl and click a vertex to delete it."
    ): (
        "При необходимости поправьте разрез: перетащите любую его вершину, щёлкните по кружку в середине отрезка, "
        "чтобы добавить там вершину, или щёлкните по вершине с нажатой Ctrl, чтобы удалить её."
    ),
    "Glue the halves together": "Склейте половины",
    (
        "Then click on a suitable edge of the perimeter to glue the other half of the net there. An edge is suitable "
        "if its counterpart, the edge it meets on the cube's surface when the net is folded, is in the other half: "
        "while you hover such an edge, its counterpart blinks. If the halves don't overlap after rearrangement, the "
        "cut can be approved; if they do, the button cancels it."
    ): (
        "Затем щёлкните по подходящему ребру периметра, чтобы приклеить к нему другую половину развёртки. Ребро "
        "подходит, если его пара (ребро, с которым оно сходится на поверхности куба, когда развёртка свёрнута) "
        "находится в другой половине: пока указатель над таким ребром, его пара мигает. Если после перестановки "
        "половины не накладываются друг на друга, разрез можно утвердить; если накладываются, кнопка его отменяет."
    ),
    "No overlaps: approved": "Без наложений: утверждено",
    "Overlaps: cancelled": "С наложениями: отменено",
    "Good to know": "Полезно знать",
    "Undo and redo work for up to 1000 actions: use Ctrl+Z and Ctrl+Y.": (
        "Можно отменить и повторить до 1000 действий: используйте Ctrl+Z и Ctrl+Y."
    ),
    (
        "The application keeps track of the minimum-area bounding rectangle of the net. To see the rectangle itself, "
        "press the {bounds} button on the instrument panel."
    ): (
        "Приложение следит за прямоугольником наименьшей площади, описанным вокруг развёртки. Чтобы увидеть сам "
        "прямоугольник, нажмите кнопку {bounds} на панели инструментов."
    ),
    "Hold Shift while cutting or dragging a vertex to make the segment horizontal or vertical.": (
        "Удерживайте Shift, когда делаете разрез или перетаскиваете вершину, чтобы отрезок был горизонтальным или "
        "вертикальным."
    ),
    "Zoom with the mouse wheel; drag the sheet to move it.": (
        "Масштаб меняется колёсиком мыши, а лист можно двигать, перетаскивая его."
    ),
    "Ctrl": "Ctrl",
}
