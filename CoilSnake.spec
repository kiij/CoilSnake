# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import platform
from setuptools.sandbox import run_setup

run_setup('setup.py', ['build_ext'])

hiddenimports = []
hidden_import_list = ['PIL._tkinter_finder']

with open(os.path.join("coilsnake", "assets", "modulelist.txt"), "r") as f:
    for line in f:
        line = line.rstrip("\n")

        if line[0] == "#":
            continue

        module = "coilsnake.modules." + line
        hidden_import_list.append(module)

pyver = '{}.{}'.format(sys.version_info[0], sys.version_info[1])

binaries = [(
    'build/lib.{}*{}/coilsnake/util/eb/native_comp.cp*{}*'.format(
        sys.platform if sys.platform != 'darwin' else 'macosx',
        pyver,
        sys.platform
    ),
    'coilsnake/util/eb'
)]

a = Analysis(
    ['script/gui.py'],
    pathex = ['.'],
    binaries = binaries,
    datas = [('coilsnake/assets', 'coilsnake/assets')],
    hiddenimports = hidden_import_list,
    hookspath = [],
    runtime_hooks = [],
    excludes = [
        '_bz2',
        '_ssl',
        '_lzma',
        'readline',
        'termios',
        'PIL._webp',
        'PySide',
        'PyQt4',
        'PyQt5'
    ],
    win_no_prefer_redirects = False,
    win_private_assemblies = False,
    cipher = None,
    noarchive = False
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=None
)

# --- Workaround for https://github.com/pyinstaller/pyinstaller/issues/3820 ---
if platform.system() == 'Darwin':
    index = 0

    for i, item in enumerate(a.scripts):
        name, loc, info = item

        if loc.endswith('script/gui.py'):
            index = i
            break

    scripts = a.scripts[i:i + 1]
    scripts.extend(a.scripts[:i])
    scripts.extend(a.scripts[i + 1:])
else:
    scripts = a.scripts
# -------------------

if len(sys.argv) > 1 and sys.argv[1] == 'debug':
    exe = EXE(
        pyz,
        scripts,
        [],
        exclude_binaries=True,
        name='CoilSnake_bin',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        icon='coilsnake/assets/images/CoilSnake.ico'
    )

    final = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='CoilSnake'
    )
else:
    final = EXE(
        pyz,
        scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='CoilSnake',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        icon='coilsnake/assets/images/CoilSnake.ico'
    )

if platform.system() != 'Darwin':
    exit()

app = BUNDLE(
    final,
    name='CoilSnake.app',
    icon='coilsnake/assets/images/CoilSnake.icns',
    bundle_identifier='com.github.mrtenda.CoilSnake'
)

# --- Workaround for https://github.com/pyinstaller/pyinstaller/issues/3753 ---
indirbase = '/Library/Frameworks/Python.framework/Versions/{}/lib/{}*'
outdir    = 'dist/CoilSnake.app/Contents/lib'
tcldir    = indirbase.format(pyver, 'tcl')
tkdir     = indirbase.format(pyver, 'tk')
os.mkdir(outdir)
os.system('cp -r {} {}'.format(tcldir, outdir))
os.system('cp -r {} {}'.format(tkdir,  outdir))
# -------------------