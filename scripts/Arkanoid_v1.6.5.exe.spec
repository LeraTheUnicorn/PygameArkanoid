# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\adm\\PycharmProjects\\PythonProject2\\PyGameBall.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\adm\\PycharmProjects\\PythonProject2\\game_resources\\sounds', 'sounds'), ('C:\\Users\\adm\\PycharmProjects\\PythonProject2\\game_resources\\images', 'images'), ('C:\\Users\\adm\\PycharmProjects\\PythonProject2\\game_resources\\highscores.py', '.'), ('C:\\Users\\adm\\PycharmProjects\\PythonProject2\\game_resources\\settings.py', '.'), ('C:\\Users\\adm\\PycharmProjects\\PythonProject2\\game_resources\\settings.json', '.')],
    hiddenimports=['pygame', 'numpy', 'pygame.sndarray', 'pygame.mixer'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'PIL', 'IPython', 'jupyter', 'notebook', 'pytest', 'unittest'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Arkanoid_v1.6.5.exe',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
