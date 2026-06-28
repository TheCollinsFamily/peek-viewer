"""Fix grab handle - use ASCII dots grid that renders everywhere."""
import pathlib

p = pathlib.Path(r'C:\Users\Merry\dev\peek-viewer\peek\grid_view.py')
src = p.read_text(encoding='utf-8')

# Replace the broken unicode with simple ASCII and bigger size
old_init = (
    "        self.setText('\u2807\u2807')\n"
    "        self.setFixedSize(28, 24)\n"
    "        self.setAlignment(Qt.AlignmentFlag.AlignCenter)\n"
    "        self.setStyleSheet(\n"
    "            'QLabel { color: white; font-size: 16px; '\n"
    "            'background: rgba(40,40,40,0.85); border: none; '\n"
    "            'border-radius: 4px; letter-spacing: 2px; }'"
)

new_init = (
    "        self.setText('\u2261')\n"  # ≡ (triple bar - renders everywhere)
    "        self.setFixedSize(30, 26)\n"
    "        self.setAlignment(Qt.AlignmentFlag.AlignCenter)\n"
    "        self.setStyleSheet(\n"
    "            'QLabel { color: white; font-size: 20px; font-weight: bold; '\n"
    "            'background: rgba(50,50,50,0.9); border: 1px solid rgba(255,255,255,0.3); '\n"
    "            'border-radius: 5px; }'"
)

src = src.replace(old_init, new_init)

p.write_text(src, encoding='utf-8')
print('Done')
