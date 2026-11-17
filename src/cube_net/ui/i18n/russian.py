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
    "Style": "Оформление",
    "Hide settings": "Скрыть настройки",
    "Language": "Язык",
    "Show vertex labels": "Показывать метки вершин",
    "Hotkey: L": "Клавиша: L",
    "Show vertex coordinates": "Показывать координаты вершин",
    "Hotkey: C": "Клавиша: C",
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
    "The point is outside the net.": "Точка вне развёртки.",
    "The point is on the perimeter: only the line's ends can be there.": (
        "Точка на периметре: там могут быть только концы линии."
    ),
    "The point is beyond the ends of its edge.": "Точка за концами своего ребра.",
    "The point is beyond the ends of its fold line.": "Точка за концами своей линии сгиба.",
    "The line already has as many points as it can have.": "В линии уже столько точек, сколько может быть.",
    "From there, the line would leave the net, or touch or cross itself.": (
        "Оттуда линия вышла бы за развёртку или коснулась бы себя или пересекла себя."
    ),
    "Auto-start logging": "Автоматически начинать логирование",
    "Blink when target area achieved": "Мигать, когда цель достигнута",
    "Maximum zoom:": "Макс. масштаб:",
    "px per unit": "пикс. на ед.",
    "How far in the sheet can be zoomed: how many pixels the edge of the cube takes": (
        "Насколько можно приблизить лист: сколько пикселей занимает ребро куба"
    ),
    "px": "пикс.",
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
    "You can set specific coordinates for points or slopes for lines: try right-click (even when dragging a point).": (
        "Можно задать точные координаты точек или наклон отрезков: попробуйте правый щелчок (даже при перетаскивании "
        "точки)."
    ),
    "You can move the working sheet origin: right-click on any vertex.": (
        "Начало координат рабочего листа можно сдвинуть: щёлкните правой кнопкой по любой вершине."
    ),
    "Hotkeys": "Горячие клавиши",
    "Projects": "Проекты",
    "Open a project": "Открыть проект",
    "Save the project": "Сохранить проект",
    "Save it under another name": "Сохранить под другим именем",
    "Quit": "Выйти",
    "Undo and redo": "Отмена и повтор",
    "Undo the last action": "Отменить последнее действие",
    "Redo it": "Повторить его",
    "Making a cut": "Разрез",
    "hold {key}": "удерживать {key}",
    "The new segment is horizontal or vertical": "Новый отрезок горизонтален или вертикален",
    "Unlock the slope set with Set slope": "Снять наклон, заданный через «Задать наклон»",
    "Adjusting the cut": "Правка разреза",
    "drag a vertex": "перетаскивать вершину",
    "The segment from the vertex before it is horizontal or vertical": (
        "Отрезок от предыдущей вершины горизонтален или вертикален"
    ),
    "click a vertex": "щелчок по вершине",
    "Delete it (any but the first and the last)": "Удалить её (кроме первой и последней)",
    "Gluing": "Склейка",
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
    "Save template as": "Сохранить шаблон как",
    "Cube Net templates (*{suffix})": "Шаблоны Cube Net (*{suffix})",
    "Cube Net projects and templates (*{project} *{template})": "Проекты и шаблоны Cube Net (*{project} *{template})",
    "Net area": "Площадь развёртки",
    "Area of the net the loop draws": "Площадь развёртки, которую очерчивает контур",
    "Face color": "Цвет грани",
    "Assign the vertex": "Назначить вершину",
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
        "Есть рёбра, соединяющие вершину саму с собой, а так не бывает: {list}."
    ),
    "You have an edge that connects a vertex to itself, which is impossible: {list}.": (
        "Есть ребро, соединяющее вершину саму с собой, а так не бывает: {list}."
    ),
    "Segments {list} don't have counterparts. Each segment should appear exactly twice, because that's what gluing "
    "implies.": (
        "У отрезков {list} нет пары. Каждый отрезок должен встречаться ровно дважды: так получается при склейке."
    ),
    "Segment {list} doesn't have a counterpart. Each segment should appear exactly twice, because that's what gluing "
    "implies.": (
        "У отрезка {list} нет пары. Каждый отрезок должен встречаться ровно дважды: так получается при склейке."
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
        "Есть разрезы, которые встречаются и как линии сгиба, а так не бывает: {list}."
    ),
    "You have a cut that also exists as a fold, which is impossible: {list}.": (
        "Есть разрез, который встречается и как линия сгиба, а так не бывает: {list}."
    ),
    "You have folds that connect the same vertices, which is impossible: {list}.": (
        "Есть линии сгиба, соединяющие одни и те же вершины, а так не бывает: {list}."
    ),
    "Some of your vertices are not glued to themselves, which is impossible: {list}.": (
        "Некоторые вершины не склеены сами с собой, а так не бывает: {list}."
    ),
    "Vertex {name} is not glued to itself, which is impossible.": (
        "Вершина {name} не склеена сама с собой, а так не бывает."
    ),
    "Net should have at least 4 faces.": "В развёртке должно быть хотя бы 4 грани.",
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
    "A face touches itself at {list}, which a face can't do: a slit, or a point where the loop touches itself, must "
    "lie between two faces. Divide the face there with a fold.": (
        "Грань касается сама себя в {list}, а так быть не может: прорезь или точка, где контур касается сам себя, "
        "должна лежать между двумя гранями. Разделите там грань линией сгиба."
    ),
}
