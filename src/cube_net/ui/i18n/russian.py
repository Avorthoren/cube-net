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
    "Hotkey: L": "Клавиша: L",
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
    "Copyright © 2026 Viktor Podust <undefeatvip@gmail.com>": "© 2026 Viktor Podust <undefeatvip@gmail.com>",
    "GNU GPL v3 or later": "GNU GPL версии 3 или более поздней",
    "Free software under the {license}, with ABSOLUTELY NO WARRANTY": (
        "Свободная программа под лицензией {license}, БЕЗ КАКИХ-ЛИБО ГАРАНТИЙ"
    ),
    "Source code: {source}": "Исходный код: {source}",
    "Close": "Закрыть",
    "Check for updates": "Проверка обновлений",
    # The applications menu (Linux, an AppImage).
    "Show in the applications menu": "Показывать в меню приложений",
    "Add Cube Net to the applications menu?": "Добавить Cube Net в меню приложений?",
    (
        "It will be there with its icon, and project files (.cubenet) will open in it with a double-click. You can "
        "change this any time in Settings → Preferences."
    ): (
        "Он появится там со своим значком, а файлы проектов (.cubenet) будут открываться в нём двойным щелчком. "
        "Это можно изменить в любой момент: Настройки → Основные."
    ),
    "Couldn't change the applications menu: {problem}": "Не удалось изменить меню приложений: {problem}",
    "Remove Cube Net from the applications menu?": "Убрать Cube Net из меню приложений?",
    (
        "Cube Net will no longer be in the applications menu, project files (.cubenet) will no longer open in it with "
        "a double-click or appear with it in Open With, and the Dock will show a generic icon for it.\n\n"
        "The AppImage itself, your projects and your settings stay as they are. You can add it to the menu again "
        "here any time."
    ): (
        "Cube Net пропадёт из меню приложений, файлы проектов (.cubenet) перестанут открываться в нём двойным щелчком "
        "и не будут предлагать его в «Открыть с помощью», а в доке у него будет стандартный значок.\n\n"
        "Сам AppImage, ваши проекты и настройки останутся как есть. Вернуть его в меню можно здесь в любой момент."
    ),
    "Remove": "Убрать",
    # Updates.
    "Periodically check for updates": "Периодически проверять обновления",
    "Once a day": "Раз в день",
    "Checking for updates...": "Проверка обновлений...",
    "Update available": "Доступно обновление",
    "{name} {new} is available (you have {current}).": "Доступна версия {name} {new} (у вас {current}).",
    "What's new:": "Что нового:",
    "Copy": "Скопировать",
    "Copied": "Скопировано",
    "Copy what's new (to translate it, say)": "Скопировать, что нового (например, чтобы перевести)",
    "This release has no notes.": "У этой версии нет описания.",
    "Download size: {size}": "Размер загрузки: {size}",
    "{megabytes} MB": "{megabytes} МБ",
    "Open the download page": "Открыть страницу загрузки",
    "Not now": "Не сейчас",
    "No newer version found: you have the latest one ({current}).": (
        "Более новой версии не найдено: у вас последняя ({current})."
    ),
    "Couldn't check for updates: {problem}": "Не удалось проверить обновления: {problem}",
    "Download and update": "Скачать и обновить",
    "Update": "Обновление",
    "Downloading {name} {version}...": "Загрузка {name} {version}...",
    "{done} of {total}": "{done} из {total}",
    "Couldn't update: {problem}": "Не удалось обновить: {problem}",
    "{name} {version} is downloaded, but it couldn't take the old one's place.": (
        "{name} {version} загружен, но не смог заменить старую версию."
    ),
    (
        "The new version is {downloaded}. Start it from there (the applications menu follows it), or put it in "
        "place yourself, in a terminal:"
    ): (
        "Новая версия: {downloaded}. Запустите её оттуда (меню приложений последует за ней) или поставьте на место "
        "сами, в терминале:"
    ),
    "Start the new version": "Запустить новую версию",
    (
        "{name} {version} is downloaded and open in Finder. To finish, drag {name} onto Applications there, "
        "replacing the old one, then start it again."
    ): (
        "{name} {version} загружен и открыт в Finder. Чтобы закончить, перетащите там {name} в «Программы», "
        "заменив старую версию, и запустите его снова."
    ),
    # Whether the project is saved.
    "Unsaved changes": "Не сохранено",
    "Saved": "Сохранено",
    "Saved to {path}": "Сохранено в {path}",
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
