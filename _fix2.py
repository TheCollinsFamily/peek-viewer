"""Fix: 1) Layout buttons force column count, 2) Arrow keys go to GridView not child focus."""
import pathlib

p = pathlib.Path(r'C:\Users\Merry\.windsurf\Reality Fabricator\peek-viewer\peek\grid_view.py')
content = p.read_text(encoding='utf-8')
changes = []

# Fix 1: GridCell should not accept keyboard focus (prevents Qt arrow-key focus navigation)
old = '''class GridCell(QFrame):
    remove_requested = Signal(int)

    def __init__(self, index, file_path, aspect, parent=None):
        super().__init__(parent)
        self.index = index
        self.file_path = Path(file_path)
        self.aspect = aspect
        self.setStyleSheet("background-color: black;")
        self.setMouseTracking(True)'''
new = '''class GridCell(QFrame):
    remove_requested = Signal(int)

    def __init__(self, index, file_path, aspect, parent=None):
        super().__init__(parent)
        self.index = index
        self.file_path = Path(file_path)
        self.aspect = aspect
        self.setStyleSheet("background-color: black;")
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)'''
if old in content:
    content = content.replace(old, new)
    changes.append('GridCell: set NoFocus policy (prevents Qt arrow navigation)')

# Fix 2: GridView should grab keyboard focus
old = '''        self.setStyleSheet("background-color: #0a0a0a;")
        self.setMinimumSize(400, 300)'''
new = '''        self.setStyleSheet("background-color: #0a0a0a;")
        self.setMinimumSize(400, 300)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)'''
if old in content:
    content = content.replace(old, new)
    changes.append('GridView: set StrongFocus policy (receives key events)')

# Fix 3: _do_layout should force column count when layout mode is explicit
old = '''        n = len(self._aspects)
        use_cols = 1
        use_score = float('inf')
        for tc in range(1, min(n, self._max_columns) + 1):
            tr = _compute_rows(self._aspects, tc)
            tg = _GAP * (len(tr) + 1)
            nh = tg
            for ri in tr:
                nh += content_w / max(sum(self._aspects[k] for k in ri), 0.1)
            sc = h / max(nh, 1)
            s = abs(math.log(max(sc, 0.01)))
            if s < use_score:
                use_score = s
                use_cols = tc

        rows = _compute_rows(self._aspects, use_cols)'''
new = '''        n = len(self._aspects)
        if self._layout_mode == '1row':
            use_cols = n
        elif self._layout_mode == '2row':
            use_cols = max(1, math.ceil(n / 2))
        else:
            # Auto mode: find best column count by scoring
            use_cols = 1
            use_score = float('inf')
            for tc in range(1, min(n, self._max_columns) + 1):
                tr = _compute_rows(self._aspects, tc)
                tg = _GAP * (len(tr) + 1)
                nh = tg
                for ri in tr:
                    nh += content_w / max(sum(self._aspects[k] for k in ri), 0.1)
                sc = h / max(nh, 1)
                s = abs(math.log(max(sc, 0.01)))
                if s < use_score:
                    use_score = s
                    use_cols = tc

        rows = _compute_rows(self._aspects, use_cols)'''
if old in content:
    content = content.replace(old, new)
    changes.append('_do_layout: force column count for 1row/2row modes')

# Fix 4: GridView.show() should grab focus so key events work immediately
old = '''        # Default focused cell to last cell
        if self._cells:
            self._focused_cell_idx = len(self._cells) - 1'''
new = '''        # Default focused cell to last cell
        if self._cells:
            self._focused_cell_idx = len(self._cells) - 1
        self.setFocus()'''
if old in content:
    content = content.replace(old, new)
    changes.append('GridView: grab focus on init so arrow keys work immediately')

# Fix 5: mouseReleaseEvent should also give focus back to GridView
old = '''            # Set this cell as focused if it wasn't a drag
            if not was_dragging and parent and hasattr(parent, '_set_focused_cell'):
                parent._set_focused_cell(self.index)'''
new = '''            # Set this cell as focused if it wasn't a drag
            if not was_dragging and parent and hasattr(parent, '_set_focused_cell'):
                parent._set_focused_cell(self.index)
                parent.setFocus()'''
if old in content:
    content = content.replace(old, new)
    changes.append('GridCell click: return focus to GridView after setting focused cell')

p.write_text(content, encoding='utf-8')
print(f'Applied {len(changes)} fixes:')
for c in changes:
    print(f'  - {c}')
