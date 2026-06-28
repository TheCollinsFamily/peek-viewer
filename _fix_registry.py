import winreg

exe_path = r'C:\Users\Merry\dev\peek-viewer\dist\RFab Viewer\RFab Viewer.exe'
command = f'"{exe_path}" "%1"'
print(f'Setting command to: {command}')

with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Classes\RFabViewer\shell\open\command') as key:
    winreg.SetValueEx(key, '', 0, winreg.REG_SZ, command)

with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Classes\PeekViewer\shell\open\command') as key:
    winreg.SetValueEx(key, '', 0, winreg.REG_SZ, command)

print('Registry fixed!')
