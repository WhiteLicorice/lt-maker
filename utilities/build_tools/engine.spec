# -*- mode: python -*-
from pathlib import Path
import shutil
import sys, os

from PyInstaller.log import logger


block_cipher = None

name = sys.argv[1]
project = name + '.ltproj'

root = Path('../../')
def path(orig_path: str):
    if os.path.isabs(orig_path):
        return orig_path
    return root / orig_path

# Also need to pass custom icon in, since options are disabled when we use a spec file (...why?)
icon_path = sys.argv[2]

a = Analysis([path('run_engine.py')],
             pathex=['.'],
             binaries=[],
             datas=[(path('saves/save_storage.txt'), 'saves'),
                    (path(icon_path), '.')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             # Only the editor uses Qt, but PyInstaller still follows the
             # function-local and TYPE_CHECKING Qt imports in app/data
             excludes=['PyQt5'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name=name,
          debug=False,
          strip=False,
          upx=False,
          console=False,
          icon=path(icon_path),
          contents_directory='.' )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               name=name)

# Files the engine reads from disk are copied in here instead of listed
# in datas, since PyInstaller opens every datas file to check whether it
# is a binary, which takes about a minute for a project plus app/
logger.info("Copying game files")
ignore = shutil.ignore_patterns('__pycache__')
for src, dst in [(path('resources/platforms'), 'resources/platforms'),
                 (path('sprites'), 'sprites'),
                 (path(project), os.path.basename(project)),
                 (path('app'), 'app')]:
    shutil.copytree(Path(SPECPATH) / src, Path(coll.name) / dst, ignore=ignore, dirs_exist_ok=True)
