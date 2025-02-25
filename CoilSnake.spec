# -*- mode: python ; coding: utf-8 -*-

import os
import glob
import platform
import shutil
import sys
import sysconfig

from setuptools.sandbox import run_setup

run_setup('setup.py', ['build_ext'])

debug = False

# This logic is specific to setuptools. It may change in future versions, as it did in 62.1.0.
plat_specifier = f'.{sysconfig.get_platform()}-{sys.implementation.cache_tag}'
if sysconfig.get_config_var('Py_GIL_DISABLED'):
    plat_specifier += 't'


if len(sys.argv) > 1 and sys.argv[1] == 'debug':
    debug = True

hiddenimports = ['PIL._tkinter_finder']

with open(os.path.join("coilsnake", "assets", "modulelist.txt"), "r") as f:
    for line in f:
        line = line.rstrip("\n")

        if line[0] == "#":
            continue

        module = "coilsnake.modules." + line
        hiddenimports.append(module)

pyver = '{}.{}'.format(sys.version_info[0], sys.version_info[1])

binaries = [(
    'build/lib{}/coilsnake/util/eb/native_comp.cp*'.format(
        plat_specifier
    ),
    'coilsnake/util/eb'
)]

a = Analysis(
    ['script/gui.py'],
    pathex = ['.'],
    binaries = binaries,
    datas = [('coilsnake/assets', 'coilsnake/assets')],
    hiddenimports = hiddenimports,
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

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CoilSnake',
    debug=debug,
    bootloader_ignore_signals=False,
    strip=(sys.platform != 'win32'),
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    hide_console='hide-early',
    icon='coilsnake/assets/images/CoilSnake.ico',
    manifest=None,
    console=True
)

if platform.system() != 'Darwin':
    exit()

app = BUNDLE(
    exe,
    name='CoilSnake.app',
    icon='coilsnake/assets/images/CoilSnake.icns',
    bundle_identifier='com.github.pkhack.CoilSnake'
)

# --- Workaround for https://github.com/pyinstaller/pyinstaller/issues/3820 ---
infile = glob.glob('/Library/Frameworks/Python.framework/Versions/{}/lib/tcl8/8.5/msgcat*.tm'.format(pyver))[0]
outdir = 'dist/CoilSnake.app/Contents/lib/tcl8/8.5'
os.makedirs(outdir, exist_ok=True)
shutil.copy(infile, outdir)
# -------------------
