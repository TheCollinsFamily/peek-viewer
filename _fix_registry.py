"""Repoint the RFab Viewer file associations at the current build.

Windows stores an ABSOLUTE path for a file association, so moving or rebuilding
the viewer silently breaks "open with RFab Viewer" for every image and video
type - Windows then refuses to set it as the default, because the exe it has on
record does not exist. Re-run this after any move or rebuild.

History: on Sep 2 2026 the workspace moved from
C:/Users/Merry/.windsurf/Reality Fabricator/ to C:/Users/Merry/dev/reality-fabricator/
and every association broke. This script itself had a stale path too - it pointed
at dev/peek-viewer/dist/RFab Viewer/RFab Viewer.exe, which was both the wrong
parent AND a PyInstaller *onedir* layout while the spec builds *onefile*. It now
derives the path from its own location, so a future move cannot break it again.
"""

import os
import sys
import winreg

SEP = chr(92)  # backslash, spelled this way to keep this file escape-free

HERE = os.path.dirname(os.path.abspath(__file__))
EXE = os.path.join(HERE, 'dist', 'RFab Viewer.exe')

# PyInstaller onedir builds nest the exe one level deeper; accept either.
if not os.path.exists(EXE):
    alt = os.path.join(HERE, 'dist', 'RFab Viewer', 'RFab Viewer.exe')
    if os.path.exists(alt):
        EXE = alt

if not os.path.exists(EXE):
    print('ERROR: no viewer build found under ' + os.path.join(HERE, 'dist'))
    print('Build it (pyinstaller "RFab Viewer.spec"), or copy the shipped binary')
    print('from ../RFAB App Upload/RFab Viewer.exe into dist/.')
    sys.exit(1)

command = '"' + EXE + '" "%1"'
print('Setting command to: ' + command)

def key_path(*parts):
    return SEP.join(parts)

for progid in ('RFabViewer', 'PeekViewer'):
    base = key_path('Software', 'Classes', progid)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base) as key:
        winreg.SetValueEx(key, '', 0, winreg.REG_SZ, 'RFab Viewer')
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                          key_path(base, 'shell', 'open', 'command')) as key:
        winreg.SetValueEx(key, '', 0, winreg.REG_SZ, command)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                          key_path(base, 'DefaultIcon')) as key:
        winreg.SetValueEx(key, '', 0, winreg.REG_SZ, EXE + ',0')

# Register under Applications so it appears in the "Open with" list at all.
app = key_path('Software', 'Classes', 'Applications', 'RFab Viewer.exe')
with winreg.CreateKey(winreg.HKEY_CURRENT_USER, app) as key:
    winreg.SetValueEx(key, 'FriendlyAppName', 0, winreg.REG_SZ, 'RFab Viewer')
with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                      key_path(app, 'shell', 'open', 'command')) as key:
    winreg.SetValueEx(key, '', 0, winreg.REG_SZ, command)

print('Registry fixed. If Explorer still shows stale icons, restart it:')
print('  Stop-Process -Name explorer -Force   (it relaunches automatically)')
