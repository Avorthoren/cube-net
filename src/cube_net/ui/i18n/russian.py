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
    "Settings: Style is the open project's or template's, the rest the application's": (
        "Настройки: Стиль относится к открытому проекту или шаблону, остальное — к приложению"
    ),
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
    "Center": "Центрировать",
    "Put the net's center of mass in the middle of the view, zoomed out as far as allowed": (
        "Поместить центр масс развёртки в середину вида, уменьшив масштаб настолько, насколько разрешено"
    ),
    "Start logging": "Начать логирование",
    "Stop logging": "Остановить логирование",
    "Logs": "Журналы",
    "Open the folder with session logs": "Открыть папку с журналами сеансов",
    # The crash window (ui/crash).
    "An unexpected error occurred, and the application has to close.": (
        "Произошла непредвиденная ошибка, и приложение будет закрыто."
    ),
    "Crash report couldn't be saved.": "Не удалось сохранить отчёт о сбое.",
    "Application encountered an unexpected error and refused your action, because it would corrupt the project.": (
        "Приложение столкнулось с непредвиденной ошибкой и отклонило ваше действие, потому что оно повредило бы проект."
    ),
    (
        "Application encountered an unexpected error and refused your action, because it would corrupt the project. "
        "Error report saved to:"
    ): (
        "Приложение столкнулось с непредвиденной ошибкой и отклонило ваше действие, потому что оно повредило бы "
        "проект. Отчёт об ошибке сохранён в:"
    ),
    "Error report couldn't be saved.": "Не удалось сохранить отчёт об ошибке.",
    # A file with numbers too long (ui/repair_messages.py).
    "Unable to open the file.": "Не удалось открыть файл.",
    (
        "This version of the application supports numbers up to {max} decimal digits long, while selected file has "
        "vertices ({names}) whose coordinates numerators and/or denominators are longer."
    ): (
        "Эта версия приложения поддерживает числа длиной до {max} десятичных цифр, а в выбранном файле есть вершины "
        "({names}), у координат которых числители и/или знаменатели длиннее."
    ),
    (
        'Do you want to apply automatic fix that will move "bad" vertices in closest appropriate positions (vertices '
        "on body edges will be moved along those edges)? Caution: this will wipe out undo/redo history, any "
        "unfinished cut or unapproved rearrangement."
    ): (
        "Применить автоматическое исправление, которое переместит «плохие» вершины в ближайшие подходящие положения "
        "(вершины на рёбрах тела будут перемещены вдоль этих рёбер)? Внимание: это сотрёт историю отмены и повтора, "
        "любой незаконченный разрез и неутверждённую перестановку."
    ),
    (
        'Do you want to apply automatic fix that will move "bad" vertices in closest appropriate positions? Caution: '
        "this will wipe out undo/redo history."
    ): (
        "Применить автоматическое исправление, которое переместит «плохие» вершины в ближайшие подходящие положения? "
        "Внимание: это сотрёт историю отмены и повтора."
    ),
    "Unexpected error during project repairment.": "Непредвиденная ошибка при исправлении проекта.",
    "Unexpected error during template repairment.": "Непредвиденная ошибка при исправлении шаблона.",
    "Automatic repairment completed.": "Автоматическое исправление завершено.",
    "Vertices {names} were adjusted.": "Вершины {names} были скорректированы.",
    # A number too long (ui/too_long_message.py).
    "Your action was rejected.": "Ваше действие отклонено.",
    (
        "The application supports numbers up to {max} digits long, while you tried to create {object}, whose {axis} "
        "coordinate would require a numerator {n} digits long."
    ): (
        "Приложение поддерживает числа длиной до {max} цифр, а вы пытались создать {object}: для координаты {axis} "
        "потребовался бы числитель длиной в {n} цифр."
    ),  # see RUSSIAN_PLURALS
    (
        "The application supports numbers up to {max} digits long, while you tried to create {object}, whose {axis} "
        "coordinate would require a denominator {n} digits long."
    ): (
        "Приложение поддерживает числа длиной до {max} цифр, а вы пытались создать {object}: для координаты {axis} "
        "потребовался бы знаменатель длиной в {n} цифр."
    ),  # see RUSSIAN_PLURALS
    "x ≈ {x}, y ≈ {y}": "x ≈ {x}, y ≈ {y}",
    "a vertex ({at})": "вершину ({at})",
    "the point where the cut crosses segment {segment} ({at})": "точку, где разрез пересекает отрезок {segment} ({at})",
    "the cut's end on segment {segment} ({at})": "конец разреза на отрезке {segment} ({at})",
    "the point where the cut crosses fold {segment} ({at})": (
        "точку, где разрез пересекает линию сгиба {segment} ({at})"
    ),
    "vertex {name} of the glued half ({at})": "вершину {name} приклеенной половины ({at})",
    "the origin ({at})": "начало координат ({at})",
    "the point where the hole's side crosses fold {segment} ({at})": (
        "точку, где сторона отверстия пересекает линию сгиба {segment} ({at})"
    ),
    "An unexpected error occurred, and the application has to close. Crash report saved to:": (
        "Произошла непредвиденная ошибка, и приложение будет закрыто. Отчёт о сбое сохранён в:"
    ),
    "You can contact the author of this app, providing this report and some context about how this happened.": (
        "Вы можете связаться с автором приложения, предоставив этот отчёт и некоторые подробности о том, как это "
        "произошло."
    ),
    "Contacts:": "Контакты:",
    "GitHub issue": "Issue на GitHub",
    "Open folder": "Открыть папку",
    "Close application": "Закрыть приложение",
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
    'Save changes to "{name}"?': "Сохранить изменения в «{name}»?",
    "Don't save": "Не сохранять",
    "Can't open the file": "Не удалось открыть файл",
    "Start a new project, or open another one?": "Начать новый проект или открыть другой?",
    "New project": "Новый проект",
    # Why a project can't be saved or opened (from core.project; values are as the system or the file has them).
    "It isn't a Cube Net project.": "Это не проект Cube Net.",
    "It isn't a Cube Net template.": "Это не шаблон Cube Net.",
    "It's a template, not a project.": "Это шаблон, а не проект.",
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
    "Style": "Стиль",
    "Hide settings": "Скрыть настройки",
    "Language": "Язык",
    "Show vertex labels": "Показывать метки вершин",
    "Hotkey: L": "Клавиша: L",
    "Show vertex coordinates": "Показывать координаты вершин",
    "Hotkey: C": "Клавиша: C",
    "Hotkey: V": "Клавиша: V",
    "Place a vertex": "Поставить вершину",
    "Set slope": "Задать наклон",
    "Set": "Задать",
    "Enter a slope: whole numbers, not both 0 (x = 0 is vertical).": (
        "Введите наклон: целые числа, не оба 0 (x = 0 — вертикаль)."
    ),
    "Slope locked: y {y}, x {x} (until the point is placed; Escape unlocks)": (
        "Наклон закреплён: y {y}, x {x} (пока точка не поставлена; Escape снимает)"
    ),
    "Place": "Поставить",
    "Move the origin": "Сдвинуть начало координат",
    "Move": "Сдвинуть",
    "Coordinates of the point were set to:": "Координаты точки были изменены на:",
    "Coordinates of {name} were set to:": "Координаты {name} были изменены на:",
    "Enter whole numbers, with denominators above 0.": "Введите целые числа; знаменатели больше 0.",
    "The point is on the perimeter: only a point put on a cut can be there.": (
        "Точка на периметре: там может быть только точка, поставленная на разрез."
    ),
    "The point is beyond the ends of its edge.": "Точка за концами своего ребра.",
    "The point is beyond the ends of its fold line.": "Точка за концами своей линии сгиба.",
    "The line already has as many points as it can have.": "В линии уже столько точек, сколько может быть.",
    "From there, the line would touch the perimeter, or touch or cross itself.": (
        "Оттуда линия коснулась бы периметра или коснулась бы себя или пересекла себя."
    ),
    "The point is where its neighbour on the line is.": "Точка там же, где её соседняя точка на линии.",
    "From there, the line would run along the perimeter or touch it.": (
        "Оттуда линия шла бы вдоль периметра или касалась бы его."
    ),
    "From its first point, the line has to go into the net.": (
        "От своей первой точки линия должна идти внутрь развёртки."
    ),
    "Where the line meets the perimeter, it has to go into the net or out of it.": (
        "Там, где линия встречает периметр, она должна входить в развёртку или выходить из неё."
    ),
    "From there, the line would touch or cross itself.": "Оттуда линия коснулась бы себя или пересекла себя.",
    "The line would no longer cut the net in two exactly at its last point.": (
        "Линия больше не разрезала бы развёртку надвое ровно в своей последней точке."
    ),
    "Auto-start logging": "Автоматически начинать логирование",
    "Blink when target area achieved": "Мигать, когда цель достигнута",
    "Maximum zoom:": "Макс. масштаб:",
    "px per unit": "пикс. на ед.",
    "How far in the sheet can be zoomed: how many pixels a unit of length takes": (
        "Насколько можно приблизить лист: сколько пикселей занимает единица длины"
    ),
    "px": "пикс.",
    "per unit": "на единицу",
    "Faces colors": "Цвета граней",
    "Choose the color": "Выбрать цвет",
    "Face {face} color": "Цвет грани {face}",
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
    "Network": "Развёртка",
    "Template": "Шаблон",
    (
        "This application lets you build networks of solid bodies: polygons without self-intersections that, when "
        "folded, can cover the whole surface of that body without overlaps. So the area of such a polygon is always "
        "equal to the surface area of the body."
    ): (
        "Это приложение позволяет строить развёртки объёмных тел: многоугольники без самопересечений, которые после "
        "сгибания могут покрыть всю поверхность этого тела без наложений. Поэтому площадь такого многоугольника всегда "
        "равна площади поверхности тела."
    ),
    (
        "If a network is cut into two pieces, they can be rearranged and glued together again along a pair of edges "
        "that meet on the body. That's exactly what the application is for:"
    ): (
        "Если разрезать развёртку на две части, их можно переставить и снова склеить по паре рёбер, которые сходятся "
        "на теле. Именно для этого и создано приложение:"
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
    "Advanced features": "Расширенные возможности",
    # The Template tab of Help -> Help.
    (
        "In addition to bodies available by default (cube and cube with a hole a.k.a. torus) user can define custom "
        "bodies by drawing one of the networks. That's what Templates are for (File → New Template)."
    ): (
        "Помимо тел, доступных по умолчанию (куб и куб с отверстием, он же тор), пользователь может задавать свои "
        "тела, рисуя одну из развёрток. Для этого и нужны шаблоны (Файл → Новый шаблон)."
    ),
    (
        "Validated template then can be used: File → New → Custom template. Or use {create} button while template is "
        "opened."
    ): (
        "Проверенный шаблон затем можно использовать: Файл → Новый → Свой шаблон. Или используйте кнопку {create}, "
        "пока шаблон открыт."
    ),
    "Create network": "Создать развёртку",
    (
        'The application supports only templates in which every pair of related (those that were cut to "unfold" the '
        'body, and that should be glued again to "wrap" the body) boundary segments are either parallel or '
        "perpendicular. In this case it's guaranteed that if all initial vertices coordinates are rational - they'll "
        "stay rational after any chain of rearrangements. It allows the application to store all coordinates exactly "
        "(up to {max} decimal digits), making exact calculations, not losing anything due to rounding errors."
    ): (
        "Приложение поддерживает только шаблоны, в которых каждая пара связанных отрезков границы (тех, что были "
        "разрезаны, чтобы «развернуть» тело, и должны быть снова склеены, чтобы «свернуть» его) параллельна или "
        "перпендикулярна. В этом случае гарантируется, что если координаты всех начальных вершин рациональны, они "
        "останутся рациональными после любой цепочки перестановок. Это позволяет приложению хранить все координаты "
        "точно (до {max} десятичных цифр) и вести точные вычисления, ничего не теряя из-за ошибок округления."
    ),
    (
        "The application doesn't prove formally that figure you drew is in fact valid network of some body, but it "
        "performs various checks to exclude most of invalid cases. Most of them are not performed automatically and "
        "should be triggered by the user with {validate} button. For example, if you move points P2, N2, L2, I2 and "
        'P3 of the default "Cube with a hole" template same distance to the right (or left) - such template would pass '
        "all the checks, but, obviously, it would not correspond to any real body, because it would change the length "
        "of the interior of the hole, but it's obviously fixed and equal to the \"cube's\" edge length."
    ): (
        "Приложение не доказывает формально, что нарисованная вами фигура действительно является корректной "
        "развёрткой какого-то тела, но выполняет различные проверки, чтобы исключить большинство некорректных случаев. "
        "Большинство из них не выполняются автоматически, и пользователь должен запустить их кнопкой {validate}. "
        "Например, если сдвинуть точки P2, N2, L2, I2 и P3 шаблона по умолчанию «Куб с отверстием» на одно и то же "
        "расстояние вправо (или влево), такой шаблон пройдёт все проверки, но, очевидно, не будет соответствовать "
        "никакому реальному телу, потому что это изменило бы длину внутренней части отверстия, а она, очевидно, "
        "фиксирована и равна длине ребра «куба»."
    ),
    "Validate": "Проверить",
    "Draw outer boundary loop": "Нарисуйте внешний контур границы",
    "Add fold-lines and inner loops": "Добавьте линии сгиба и внутренние контуры",
    "Fold-lines and boundaries define faces of the body (and their parts):": (
        "Линии сгиба и границы задают грани тела (и их части):"
    ),
    (
        "Adjust the template if needed: drag any of its vertices, click the circle in the middle of a segment to add "
        "a vertex there, or hold Ctrl and click a vertex (or fold-line segment) to delete it. All similar to "
        "{networks}."
    ): (
        "При необходимости поправьте шаблон: перетащите любую его вершину, щёлкните по кружку в середине отрезка, "
        "чтобы добавить там вершину, или щёлкните по вершине (или отрезку линии сгиба) с нажатой Ctrl, чтобы удалить "
        "её. Всё как в {networks}."
    ),
    "Networks": "Развёртках",
    "Define vertices and faces": "Задайте вершины и грани",
    (
        "Faces of the body defined by their color: double-click on the area to set its color. This means, that pieces "
        "of <b>exactly</b> the same color are considered parts of the same body face, and they have to be able to be "
        "glued accordingly."
    ): (
        "Грани тела задаются их цветом: дважды щёлкните по области, чтобы задать её цвет. Это значит, что куски "
        "<b>в точности</b> одного цвета считаются частями одной грани тела, и они должны склеиваться соответственно."
    ),
    (
        "Vertices of the template that represent the same vertex of the body should have the same unique name (one or "
        "two latin letters). Different images of the same body's vertex should have unique integer indices: "
        "right-click on the vertex → {assign}."
    ): (
        "Вершины шаблона, представляющие одну и ту же вершину тела, должны иметь одно и то же уникальное имя (одна или "
        "две латинские буквы). Разные образы одной вершины тела должны иметь уникальные целые индексы: правый щелчок "
        "по вершине → {assign}."
    ),
    (
        "Keep in mind, that every image of body's edge or cut on the surface of the body should have images of all "
        "vertices that belong to that edge or cut. For example: since green body's face (D-B-F-G) shown in animation "
        "below is cut through its edge D-B in point S we should create not only S1 (on the boundary of the top piece "
        "of the green face of the network) and S2 (bottom piece of the green face), but also S3 (on the boundary of "
        "the top blue face of the network), because it has another representation of the B-D body's edge."
    ): (
        "Помните, что каждый образ ребра тела или разреза на поверхности тела должен содержать образы всех вершин, "
        "лежащих на этом ребре или разрезе. Например: поскольку зелёная грань тела (D-B-F-G), показанная на анимации "
        "ниже, разрезана по своему ребру D-B в точке S, нужно создать не только S1 (на границе верхнего куска зелёной "
        "грани развёртки) и S2 (нижний кусок зелёной грани), но и S3 (на границе верхней синей грани развёртки), "
        "потому что на ней есть ещё одно представление ребра B-D тела."
    ),
    "Validate it": "Проверьте его",
    (
        "Similar to {networks} you can set specific coordinates for vertices or slopes for lines when creating or "
        "dragging vertices. And you can move the origin."
    ): (
        "Как и в {networks}, можно задать точные координаты вершин или наклон линий, когда вы создаёте или "
        "перетаскиваете вершины. А ещё можно сдвинуть начало координат."
    ),
    "Exact validation steps": "Точные шаги проверки",
    (
        "Drawing rules are kept all the time: an action that breaks them (sides crossing, for example) is refused at "
        "once. {validate} checks the rest, in this order, and tells about the first check that fails:"
    ): (
        "Правила рисования соблюдаются всё время: действие, которое их нарушает (например, пересечение сторон), "
        "отклоняется сразу. {validate} проверяет остальное, в таком порядке, и сообщает о первой непройденной проверке:"
    ),
    "Every face has a color.": "У каждой грани есть цвет.",
    "Every vertex has a label.": "У каждой вершины есть метка.",
    (
        "No segment of a boundary or of a fold-line joins two images of the same vertex of the body (like A1-A3): an "
        "edge can't go from a vertex to itself."
    ): (
        "Ни один отрезок границы или линии сгиба не соединяет два образа одной и той же вершины тела (как A1-A3): "
        "ребро не может идти из вершины в неё же."
    ),
    (
        "Every segment of the boundaries (the outer one and the inner loops) has exactly one counterpart: another "
        "boundary segment between vertices with the same two names. They are the two sides of one cut, glued together "
        "when the body is wrapped."
    ): (
        "У каждого отрезка границ (внешней и внутренних контуров) есть ровно одна пара: другой отрезок границы между "
        "вершинами с теми же двумя именами. Это две стороны одного разреза, которые склеиваются, когда тело "
        "сворачивается."
    ),
    "Counterparts are parallel or perpendicular (so that coordinates stay rational).": (
        "Пары параллельны или перпендикулярны (чтобы координаты оставались рациональными)."
    ),
    "Counterparts have the same length.": "Пары одинаковой длины.",
    (
        "Counterparts run in opposite directions along their loops (otherwise one of them would have to be turned "
        "over to glue them). To check imagine outer loop running counter-clockwise and every inner loop running "
        "clockwise."
    ): (
        "Пары идут вдоль своих контуров в противоположных направлениях (иначе одну из них пришлось бы перевернуть, "
        "чтобы их склеить). Для проверки представьте, что внешний контур идёт против часовой стрелки, а каждый "
        "внутренний контур — по часовой стрелке."
    ),
    (
        "No edge of the body is both a cut and a fold. If two boundary segments are counterparts, they are the two "
        "sides of a cut along the body's edge between their two names, so no fold-line segment may join the same two "
        "names. For example, if boundary segments A3-B1 and A2-B4 exist (the cut along the edge A-B), a "
        "fold-line segment A1-B2 is forbidden: it would make the same edge A-B a fold too."
    ): (
        "Ни одно ребро тела не является одновременно разрезом и сгибом. Если два отрезка границы — пара, то они — две "
        "стороны разреза вдоль ребра тела между их двумя именами, поэтому ни один отрезок линии сгиба не может "
        "соединять те же два имени. Например, если существуют отрезки границы A3-B1 и A2-B4 (разрез вдоль ребра A-B), "
        "отрезок линии сгиба A1-B2 запрещён: он сделал бы то же ребро A-B ещё и сгибом."
    ),
    (
        "No two fold-line segments join the same two names (i.e. having fold-line segments A1-B3 and A2-B1 at the same "
        "time is forbidden)."
    ): (
        "Никакие два отрезка линий сгиба не соединяют одни и те же два имени (т. е. одновременное наличие отрезков "
        "линий сгиба A1-B3 и A2-B1 запрещено)."
    ),
    "All images of each vertex of the body are glued together into one point.": (
        "Все образы каждой вершины тела склеиваются в одну точку."
    ),
    "Every fold-line separates two faces of different colors.": "Каждая линия сгиба разделяет две грани разных цветов.",
    "The pieces of each color are glued together into one face.": "Куски каждого цвета склеиваются в одну грань.",
    "The body has at least 4 faces.": "У тела не меньше 4 граней.",
    ("No face touches itself: a slit, or a point where a boundary touches itself, must lie between two faces."): (
        "Ни одна грань не касается сама себя: прорезь или точка, где граница касается сама себя, должна лежать между "
        "двумя гранями."
    ),
    "Every face, glued from its pieces, is one flat piece of paper: it doesn't overlap itself.": (
        "Каждая грань, склеенная из своих кусков, — один плоский лист бумаги: она не накладывается сама на себя."
    ),
    "The indices of every name go starting from 1 without gaps.": (
        "Индексы каждого имени идут начиная с 1 без пропусков."
    ),
    (
        "If the indices of some names have gaps (and nothing else is wrong), the application offers to renumber them: "
        "the images of each name keep their order, and get the indices 1, 2, 3, ... (A2 and A5 become A1 and A2). The "
        "template is valid then."
    ): (
        "Если в индексах некоторых имён есть пропуски (а всё остальное в порядке), приложение предлагает "
        "перенумеровать их: образы каждого имени сохраняют свой порядок и получают индексы 1, 2, 3, ... (A2 и A5 "
        "становятся A1 и A2). После этого шаблон корректен."
    ),
    (
        "You can set specific coordinates for vertices or slopes for lines when creating or dragging vertices: try "
        "right-click."
    ): (
        "Можно задать точные координаты вершин или наклон линий, когда вы создаёте или перетаскиваете вершины: "
        "попробуйте правый щелчок."
    ),
    (
        "Cut should always start on the boundary, but other vertices of the cut line can even be outside the net: as "
        "soon as net is divided into two pieces - cut line ends."
    ): (
        "Разрез всегда должен начинаться на границе, но остальные вершины линии разреза могут находиться даже за "
        "пределами развёртки: как только развёртка разделится на две части, линия разреза заканчивается."
    ),
    (
        "You can also move the origin by assigning desired coordinates to any vertex. Although, axes orientation and "
        "the scale is constant."
    ): (
        "Также можно сдвинуть начало координат, назначив нужные координаты любой вершине. Однако ориентация осей и "
        "масштаб постоянны."
    ),
    "Good to know": "Полезно знать",
    "Undo and redo work for up to 1000 actions: use Ctrl+Z and Ctrl+Y.": (
        "Можно отменить и повторить до 1000 действий: используйте Ctrl+Z и Ctrl+Y."
    ),
    (
        "The application keeps track of the minimum-area bounding rectangle of the net. To see the rectangle itself, "
        "press the {bounds} button on the instrument panel. You can see the exact area value by hovering the mouse "
        "over its approximate value."
    ): (
        "Приложение следит за прямоугольником наименьшей площади, описанным вокруг развёртки. Чтобы увидеть сам "
        "прямоугольник, нажмите кнопку {bounds} на панели инструментов. Точное значение площади можно увидеть, "
        "наведя указатель мыши на её приближённое значение."
    ),
    "Hotkeys": "Горячие клавиши",
    "Projects and templates": "Проекты и шаблоны",
    "New template": "Новый шаблон",
    "Open a project or a template": "Открыть проект или шаблон",
    "Save the project or the template": "Сохранить проект или шаблон",
    "Save it under another name": "Сохранить под другим именем",
    "Quit": "Выйти",
    "Undo and redo": "Отмена и повтор",
    "Undo the last action": "Отменить последнее действие",
    "Redo it": "Повторить его",
    "Exact values": "Точные значения",
    "right-click": "щёлкнуть правой кнопкой",
    "Place a vertex, set a slope, or move the origin (on a vertex)": (
        "Поставить вершину, задать наклон или сдвинуть начало координат (на вершине)"
    ),
    "Making a cut": "Создание разреза",
    "hold {key}": "удерживать {key}",
    "The new segment is horizontal or vertical": "Новый отрезок горизонтален или вертикален",
    "Unlock the slope set with Set slope": "Снять наклон, заданный через «Задать наклон»",
    "Adjusting the cut": "Правка разреза",
    "drag a vertex": "перетаскивать вершину",
    "The segment from the vertex before it is horizontal or vertical": (
        "Отрезок от предыдущей вершины горизонтален или вертикален"
    ),
    "click a vertex": "щёлкнуть по вершине",
    "Delete it (any but the first and the last)": "Удалить её (кроме первой и последней)",
    "Gluing": "Склейка",
    "Making a template": "Создание шаблона",
    "Give up the fold line being drawn or the drag, and unlock the slope set with Set slope": (
        "Отменить рисуемую линию сгиба или перетаскивание и снять наклон, заданный через «Задать наклон»"
    ),
    "Draw a hole": "Нарисовать отверстие",
    "Validate the template": "Проверить шаблон",
    "Delete it and its fold lines": "Удалить её и её линии сгиба",
    "click a fold line segment": "щёлкнуть по отрезку линии сгиба",
    "Delete it, with whatever is left hanging": "Удалить его вместе со всем, что останется висеть",
    "double-click a face": "дважды щёлкнуть по грани",
    "Choose its color": "Выбрать её цвет",
    "Approve the rearranged net (when its halves don't overlap)": (
        "Утвердить новую развёртку (когда её половины не перекрываются)"
    ),
    "Switch the ruler on or off (off, it forgets its points)": (
        "Включить или выключить линейку (выключенная, она забывает свои точки)"
    ),
    (
        "While measuring: the ruler's segment is horizontal or vertical; the next ones, parallel or perpendicular to "
        "the one before"
    ): (
        "При измерении: отрезок линейки горизонтален или вертикален; следующие параллельны или перпендикулярны "
        "предыдущему"
    ),
    "Show or hide the smallest bounding rectangle": "Показать или скрыть наименьший описанный прямоугольник",
    "Copy the area's hint (while it's shown)": "Скопировать подсказку площади (пока она видна)",
    "The view": "Вид",
    "mouse wheel": "колёсико мыши",
    "Zoom in or out": "Увеличить или уменьшить",
    "drag the sheet": "перетаскивать лист",
    "Move the sheet": "Двигать лист",
    "Show or hide the vertex labels": "Показать или скрыть метки вершин",
    "Show or hide the vertex coordinates": "Показать или скрыть координаты вершин",
    "Copy the coordinates shown next to the mouse": "Скопировать координаты, показанные возле мыши",
    "Help": "Справка",
    "This help": "Эта справка",
    "Close it": "Закрыть её",
    "Zoom with the mouse wheel; drag the sheet to move it.": (
        "Масштаб меняется колёсиком мыши, а лист можно двигать, перетаскивая его."
    ),
    "Ctrl": "Ctrl",
    # Templates (docs/template_idea.txt).
    "New &Template": "Новый &шаблон",
    "&Validate": "&Проверить",
    "Validate\ntemplate": "Проверить\nшаблон",
    "Validated": "Проверен",
    "Invalid": "Найдены\nошибки",
    "Save template as": "Сохранить шаблон как",
    "Cube Net templates (*{suffix})": "Шаблоны Cube Net (*{suffix})",
    "Cube Net projects and templates (*{project} *{template})": "Проекты и шаблоны Cube Net (*{project} *{template})",
    "Net area": "Площадь\nразвёртки",  # two lines: the panel stays narrow
    "Area of the net the loop draws": "Площадь развёртки, которую очерчивает контур",
    "Face color": "Цвет грани",
    "Assign label": "Назначить метку",
    "Name (1-2 Latin letters) and index (1-99):": "Имя (1-2 латинские буквы) и индекс (1-99):",
    "Assign": "Назначить",
    "Such label already exists. Assign first free index?": "Такая метка уже есть. Назначить первый свободный индекс?",
    "The point is off the sheet.": "Точка за пределами листа.",
    "The loop needs 3 segments at least.": "В контуре должно быть хотя бы 3 отрезка.",
    "The loop would turn inside out.": "Контур вывернулся бы наизнанку.",
    "The net would come apart: its parts may touch, but it must stay one piece.": (
        "Развёртка распалась бы: её части могут касаться, но она должна остаться одним куском."
    ),
    "A fold would be outside the loop.": "Линия сгиба оказалась бы снаружи контура.",
    "The loop would touch or cross itself, or a fold.": "Контур коснулся бы себя или линии сгиба либо пересёк бы их.",
    "A loop keeps 6 vertices at least: this one can't be deleted.": (
        "В контуре должно остаться хотя бы 6 вершин: эту удалить нельзя."
    ),
    "{items} and {last}": "{items} и {last}",
    "{first} and {others}": "{first} и {others}",
    "Some vertices don't have assigned labels. Name each vertex.": (
        "У некоторых вершин нет меток. Назначьте метку каждой вершине."
    ),
    "You have edges that connect a vertex to itself, which is impossible: {list}.": (
        "Есть рёбра, соединяющие вершину саму с собой, что невозможно: {list}."
    ),
    "You have an edge that connects a vertex to itself, which is impossible: {list}.": (
        "Есть ребро, соединяющее вершину саму с собой, что невозможно: {list}."
    ),
    "Segments {list} don't have counterparts. Each segment should appear exactly twice, because that's what gluing "
    "implies.": (
        "У отрезков {list} нет пары. Каждый отрезок должен встречаться ровно дважды, потому что это то, что "
        "подразумевает склеивание."
    ),
    "Segment {list} doesn't have a counterpart. Each segment should appear exactly twice, because that's what gluing "
    "implies.": (
        "У отрезка {list} нет пары. Каждый отрезок должен встречаться ровно дважды, потому что это то, что "
        "подразумевает склеивание."
    ),
    "Counterparts for {list} are neither parallel nor perpendicular. Cube Net accepts only nets with parallel or "
    "perpendicular counterparts, to stay within rational numbers.": (
        "Пары для {list} ни параллельны, ни перпендикулярны. Cube Net принимает только развёртки с параллельными или "
        "перпендикулярными парами, чтобы оставаться в рациональных числах."
    ),
    "Counterparts for {list} have different lengths, thus it would be impossible to glue them.": (
        "Пары для {list} разной длины, поэтому склеить их невозможно."
    ),
    "Counterparts for {list} run in the same direction along the loop, so one of them would have to be turned over to "
    "glue them. Counterparts must run in opposite directions.": (
        "Пары для {list} идут по контуру в одном направлении, поэтому для склейки одну из них пришлось бы перевернуть. "
        "Пары должны идти в противоположных направлениях."
    ),
    "You have cuts that also exist as folds, which is impossible: {list}.": (
        "Есть разрезы, которые встречаются и как линии сгиба, что невозможно: {list}."
    ),
    "You have a cut that also exists as a fold, which is impossible: {list}.": (
        "Есть разрез, который встречается и как линия сгиба, что невозможно: {list}."
    ),
    "You have folds that connect the same vertices, which is impossible: {list}.": (
        "Есть линии сгиба, соединяющие одни и те же вершины, что невозможно: {list}."
    ),
    "Some of your vertices are not glued to themselves, which is impossible: {list}.": (
        "Некоторые вершины не склеены сами с собой, что невозможно: {list}."
    ),
    "Vertex {name} is not glued to itself, which is impossible.": (
        "Вершина {name} не склеена сама с собой, что невозможно."
    ),
    "Net should have at least 4 faces.": "В развёртке должно быть хотя бы 4 грани.",
    "You have folds between faces of the same color: {list}. A fold separates two faces: give them different "
    "colors.": "У вас есть линии сгиба между гранями одного цвета: {list}. Линия сгиба разделяет две грани: "
    "назначьте им разные цвета.",
    "You have a fold between faces of the same color: {list}. A fold separates two faces: give them different "
    "colors.": "У вас есть линия сгиба между гранями одного цвета: {list}. Линия сгиба разделяет две грани: "
    "назначьте им разные цвета.",
    "Pieces of some faces aren't glued together: {list}.": "Части некоторых граней не склеены друг с другом: {list}.",
    "Pieces of this face aren't glued together: {list}.": "Части этой грани не склеены друг с другом: {list}.",
    "Some faces self-intersect after gluing: {list}.": "Некоторые грани самопересекаются после склеивания: {list}.",
    "This face self-intersects after gluing: {list}.": "Эта грань самопересекается после склеивания: {list}.",
    "Indices for vertices {list} have gaps. Reindex automatically?": (
        "В индексах вершин {list} есть пропуски. Перенумеровать автоматически?"
    ),
    "Indices for vertex {list} have gaps. Reindex automatically?": (
        "В индексах вершины {list} есть пропуски. Перенумеровать автоматически?"
    ),
    "Vertices automatically reindexed.\nNo other problems found.": (
        "Вершины перенумерованы автоматически.\nДругих проблем не найдено."
    ),
    "No problems found.": "Проблем не найдено.",
    "Save the template?": "Сохранить шаблон?",
    "Create\nnetwork": "Создать\nразвёртку",
    "You have faces without a color. Double-click on a face to assign its color.": (
        "У некоторых граней нет цвета. Щёлкните дважды по грани, чтобы назначить ей цвет."
    ),
    "You have a face without a color. Double-click on the face to assign its color.": (
        "У одной грани нет цвета. Щёлкните дважды по грани, чтобы назначить ей цвет."
    ),
    "A face touches itself at {list}, which a face can't do: a slit, or a point where the loop touches itself, must "
    "lie between two faces. Divide the face there with a fold.": (
        "Грань касается сама себя в {list}, чего грань делать не может: прорезь или точка, где контур касается "
        "сам себя, должна лежать между двумя гранями. Разделите там грань линией сгиба."
    ),
    # File -> New.
    "Cube": "Куб",
    "Cube with a hole": "Куб с отверстием",
    "Custom template": "Свой шаблон",
    "Template file (.nettemplate)": "Файл шаблона (.nettemplate)",
    "Browse...": "Обзор...",
    "Create": "Создать",
    "Choose template": "Выбор шаблона",
    "{path} is a project, not a template.": "{path} — это проект, а не шаблон.",
    "Template is not valid. Open template?": "Шаблон некорректен. Открыть шаблон?",
    "Template is not valid.": "Шаблон некорректен.",
    "Try to restore the last valid state?": "Попробовать восстановить последнее корректное состояние?",
    "Unable to restore the file. Open another?": "Не удалось восстановить файл. Открыть другой?",
    "Unable to restore the file.": "Не удалось восстановить файл.",
    "State {n} action ago was restored.": "Восстановлено состояние {n} действие назад.",
    "State {n} actions ago was restored.": "Восстановлено состояние {n} действий назад.",  # see RUSSIAN_PLURALS
    "Draw\nhole": "Нарисовать\nотверстие",
    "Draw &hole": "Нарисовать &отверстие",
    "Hotkey: H": "Клавиша: H",
}


# Texts with a number {n} whose Russian depends on it: the forms for 1 (21, 31...), for 2-4 (22-24...), for the rest.
RUSSIAN_PLURALS: dict[str, tuple[str, str, str]] = {
    (
        "The application supports numbers up to {max} digits long, while you tried to create {object}, whose {axis} "
        "coordinate would require a numerator {n} digits long."
    ): tuple(  # type: ignore[assignment]
        "Приложение поддерживает числа длиной до {max} цифр, а вы пытались создать {object}: для координаты {axis} "
        f"потребовался бы числитель длиной в {{n}} {form}."
        for form in ("цифру", "цифры", "цифр")
    ),
    (
        "The application supports numbers up to {max} digits long, while you tried to create {object}, whose {axis} "
        "coordinate would require a denominator {n} digits long."
    ): tuple(  # type: ignore[assignment]
        "Приложение поддерживает числа длиной до {max} цифр, а вы пытались создать {object}: для координаты {axis} "
        f"потребовался бы знаменатель длиной в {{n}} {form}."
        for form in ("цифру", "цифры", "цифр")
    ),
    "State {n} actions ago was restored.": (
        "Восстановлено состояние {n} действие назад.",
        "Восстановлено состояние {n} действия назад.",
        "Восстановлено состояние {n} действий назад.",
    ),
}
