# Cube Net Application - Implementation Plan

## Overview

This document outlines the implementation plan for the Cube Net application — a desktop tool for visualizing and manipulating 2D cube nets that can be folded into 3D cubes.

The application follows the specification described in `idea.txt` with clarifications based on the user's feedback.

## Implementation Order: MVP First

1. **MVP** — Make it run in the existing virtualenv `cube_net_3.14.10` (from PyCharm). Only Ubuntu 24.
2. **Ubuntu packaging** — Create .deb / portable installation for Ubuntu 24.
3. **Other OS** — Optional: macOS and Windows packaging (PyInstaller / Briefcase).

---

## Technical Specifications

### Core Requirements
- **Platform**: Ubuntu 24 (minimum), macOS, Windows 10/11 — *first make it run in virtualenv, then package for Ubuntu, optionally other OS*
- **Language**: Python 3.14.10 (stable, good ecosystem)
- **GUI Framework**: PyQt6/PySide6 for cross-platform 2D rendering
- **Project Storage**: JSON-based format with action history
- **Max Undo Actions**: 1000 (hardcoded, can be made configurable later)
- **.gitignore**: `data/` directory should be ignored

---

## Architecture Overview

### 1. Core Data Models

#### CubeGraph
- **8 vertices**: Each vertex knows which cube faces meet there (1-3 faces)
- **12 edges**: Cube edges (the "letter labels" from spec)
- **6 faces**: Each face has an ID and assigned color

#### Project Structure
```python
class Project:
    vertices: Dict[CubeVertexID, Point2D]        # 2D positions
    faces: Dict[CubeFaceID, Face]               # geometry + colors
    cube_graph: CubeGraph                       # underlying 3D topology
    outer_perimeter: List[Segment2D]            # current boundary
    actions_history: Deque[Action]              # 1000 max (main history)
    redo_stack: Stack[Action]                   # undo redo history
    settings: ProjectSettings                   # user preferences
```

#### Action
```python
class Action:
    action_type: str                           # #1-#5 from spec
    timestamp: int                            # for history
    # Specific data varies by action type
```

### 2. State Machine

The application operates in the following states:

| State | Purpose | Key Actions |
|-------|---------|-------------|
| **DEFAULT** | Ready for new operations | Start new cut, activate ruler, load project |
| **CUTTING** | Creating new cut line | Add points, move points, delete points, cancel |
| **CUT_EDITING** | Editing cut line | Add/remove/move points, glue segment |
| **GLUING** | Rearranging parts of net | Select segment, validate, approve/reject |
| **RULER_ACTIVE** | Measurement tool | Click for points, show measurements |

### 3. Application Flow

1. **Startup** → Load last project → Show DEFAULT state
2. **New Project** → Create default cube net → Show DEFAULT state
3. **Cut Creation** → DEFAULT → CUTTING → Add points → Cancel/Commit
4. **Cut Gluing** → CUTTING → CUT_EDITING → GLUING → Validate → Approve/Reject
5. **Undo/Redo** → Modify history stacks → Update state
6. **Project Save/Load** → Serialize/deserialize state

---

## Implementation Phases

### Phase 1: MVP in Virtualenv (Weeks 1-2)

#### 1.1 Project Setup
- [ ] Activate virtualenv `cube_net_3.14.10`
- [ ] Create project directory structure under `cube_net/`
- [ ] Set up PyQt6 in the virtualenv
- [ ] Create minimal main.py that shows the default cube net
- [ ] Test it runs: `python -m cube_net.main`
- [ ] Add `data/` to `.gitignore`

#### 1.2 Basic UI Framework
- [ ] Create main window with toolbar and workspace
- [ ] Implement viewport/zoom system (50% of screen height default)
- [ ] Add instrument panel (ruler button, bounding rectangle button)
- [ ] Create coordinate overlay system
- [ ] Test on Ubuntu within virtualenv

### Phase 2: Data Models and Cube Graph (Weeks 3-4)

#### 2.1 Core Geometry Classes
- [ ] Implement `Point2D` with coordinate system support
- [ ] Implement `Segment2D` with intersection detection
- [ ] Create `Face` class with color system and subdivision logic
- [ ] Build `CubeGraph` with 8 vertices, 12 edges, 6 faces

#### 2.2 Default Cube Net
- [ ] Implement default cube net layout (cross shape)
- [ ] Create face coloring system (6 stable colors)
- [ ] Generate face subdivisions (50 rectangles × 2 triangles each)
- [ ] Implement edge rendering (dashed lines between faces)

### Phase 3: Visualization System (Weeks 5-6)

#### 3.1 Rendering Pipeline
- [ ] Implement QGraphicsView for the sheet
- [ ] Create face rendering with color patterns
- [ ] Implement edge rendering (dashed, colored)
- [ ] Add vertex rendering (colored sectors)
- [ ] Create grid overlay system
- [ ] Add bounding rectangle visualization

#### 3.2 Interaction Feedback
- [ ] Implement hover highlighting for cuts/segments
- [ ] Add click feedback and selection states
- [ ] Create visual feedback for invalid operations
- [ ] Implement ruler tool (points, distances)
- [ ] Add mouse coordinate display in footer

### Phase 4: Cut Editing System (Weeks 7-8)

#### 4.1 State Management
- [ ] Implement DEFAULT → CUTTING transition
- [ ] Create point addition logic
- [ ] Implement point movement and deletion
- [ ] Add intersection validation

#### 4.2 Cut Editing Rules
- [ ] Validate cut starts/ends on outer perimeter
- [ ] Prevent self-intersections
- [ ] Handle SHIFT+click for point deletion
- [ ] Implement point dragging with validation
- [ ] Show preview segment to mouse cursor
- [ ] Handle CUTTING → CUT_EDITING transition

### Phase 5: Gluing System (Weeks 9-10)

#### 5.1 Gluing Logic
- [ ] Implement segment counterpart finding (using vertex identity)
- [ ] Create rearrangement algorithm
- [ ] Add self-intersection validation
- [ ] Implement automatic validation (CTRL+ENTER)
- [ ] Add adjacency/collinearity detection for auto-gluing
- [ ] Handle GLUING → DEFAULT transition

### Phase 6: Undo/Redo System (Weeks 11-12)

#### 6.1 History Management
- [ ] Implement circular buffer (deque maxlen=1000)
- [ ] Create redo stack system
- [ ] Add action types #1-#5 from spec
- [ ] Implement save/load with history
- [ ] Handle edge cases (type #5, invalid actions)

### Phase 7: Project System (Weeks 13-14)

#### 7.1 Persistence
- [ ] Design JSON project format
- [ ] Implement save/load functions
- [ ] Add auto-recovery on startup
- [ ] Create project backup system

#### 7.2 Project Features
- [ ] Load last project on startup
- [ ] Create new project with default net
- [ ] Project settings storage

### Phase 8: Polish and Testing (Weeks 15-16)

#### 8.1 Final Polish
- [ ] Add UI polish and visual improvements
- [ ] Implement keyboard shortcuts (CTRL+Z, CTRL+Y, CTRL+ENTER)
- [ ] Add error handling and user feedback
- [ ] Optimize performance

#### 8.2 Testing
- [ ] Create unit tests for core logic
- [ ] Add integration tests for workflows
- [ ] Create UI interaction tests
- [ ] Performance testing

---

## Technical Decisions

### GUI Framework: PyQt6
**Pros:**
- Mature cross-platform 2D rendering
- Good for complex UI + graphics
- Excellent package management (pip)
- Good Qt Designer support
- Strong community

**Cons:**
- Larger binary size
- GUI-specific learning curve

### Data Format: JSON
**Pros:**
- Human-readable
- Easy to version
- Standard format
- Simple serialization

**Cons:**
- Slightly larger than binary formats
- Need to handle large structures efficiently

### History Storage: deque + stack
**Pros:**
- O(1) append/pop operations
- Memory efficient
- Built-in maxlen support
- Thread-safe operations

**Cons:**
- Limited data types (only supports picklable objects)
- Need to handle special cases for serialization

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Complex geometry algorithms | Medium | High | Start with simple cases, test thoroughly |
| Performance issues | Low | Medium | Optimize early, use efficient data structures |
| Cross-platform compatibility | Low | Medium | Test on all target platforms |
| File format changes | Low | Medium | Version control schema |

---

## Dependencies

The project dependencies are listed in `requirements.txt` at the project root.

```bash
# Install all dependencies in your virtualenv
pip install -r requirements.txt
```

### Core dependencies:
- **PyQt6>=6.7.0** — GUI framework (cross-platform)
- **numpy>=1.26.0** — numerical computing
- **shapely>=2.0.0** — polygon geometry operations
- **python-json-logger>=2.0.0** — structured logging (optional)
- **pyyaml>=6.0.0** — config file support (optional)

---

## Development Workflow

1. **Daily commits**: Small, focused changes
2. **Feature branches**: Each major feature in separate branch
3. **Code reviews**: Pair programming on complex logic
4. **Testing**: Unit tests + manual testing each feature
5. **Integration**: Combine features weekly

---

## Success Criteria

The application should:

1. **Basic Functionality**
   - ✅ Display default cube net (50% screen height)
   - ✅ Support pan/zoom with mouse
   - ✅ Save/load projects
   - ✅ Basic undo/redo (1000 actions)

2. **Core Features**
   - ✅ Create and validate cut lines
   - ✅ Glue segments with counterpart detection
   - ✅ Face coloring (50 rectangles + triangles)
   - ✅ Edge rendering (dashed lines)
   - ✅ Vertex rendering (colored sectors)
   - ✅ Ruler tool functionality
   - ✅ Bounding rectangle calculation and display

3. **User Experience**
   - ✅ Intuitive UI with visual feedback
   - ✅ Keyboard shortcuts (CTRL+Z, CTRL+Y, CTRL+ENTER)
   - ✅ Error handling with clear messages
   - ✅ Help/documentation for tools

4. **Quality**
   - ✅ No crashes or data corruption
   - ✅ All edge cases handled
   - ✅ Performance acceptable
   - ✅ Code well-documented and maintainable

---

## Timeline

**Total Estimated Time**: 4 months (16 weeks)

- **Weeks 1-2**: MVP in virtualenv + Project Setup
- **Weeks 3-4**: Data models and cube graph
- **Weeks 5-6**: Visualization and rendering
- **Weeks 7-8**: Cut editing system
- **Weeks 9-10**: Gluing system
- **Weeks 11-12**: Undo/redo system
- **Weeks 13-14**: Project system
- **Weeks 15-16**: Polish, testing, deployment

---

## Open Questions

1. Should we implement a coordinate system for cuts (parametric)? (Spec says no)
2. Should we support importing/exporting net formats? (Not in spec)
3. Should we add 3D preview mode? (Nice-to-have, not in spec)
4. Should we add version control for projects? (Not in spec)
5. Should we implement plugin system for future features? (Not in spec)

Current implementation focuses on the core requirements from the specification.

---

*Last updated: 2026-11-03*