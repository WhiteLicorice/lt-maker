# -*- mode: python -*-
from pathlib import Path
import sys, os


block_cipher = None

name = sys.argv[1]
project = name + '.ltproj'

root = Path('../../')
def path(orig_path: str):
    if os.path.isabs(orig_path):
        return orig_path
    return root / orig_path

# this is a really stupid way to do IPC
# we pass in a "tag" from the editor, and use this "tag"
# to print out log messages formatted like `tag: 100`
# which we use on the editor side to parse the logs
# to read the progress messages.
progress_sentinel_message = sys.argv[2]
def log_progress(pct: int):
    print(progress_sentinel_message + str(pct), flush=True)

# Also need to pass custom icon in, since options are disabled when we use a spec file (...why?)
icon_path = sys.argv[3]

log_progress(20)
a = Analysis([path('run_engine.py')],
             pathex=['.'],
             binaries=[],
             datas=[(path('saves/save_storage.txt'), 'saves'),
                    (path('resources'), 'resources'),
                    (path('sprites'), 'sprites'),
                    (project, os.path.basename(project)),
                    (path(icon_path), '.'),
                    (path('app'), 'app')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
log_progress(20)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
log_progress(40)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name=name,
          debug=False,
          strip=False,
          upx=True,
          console=False,
          icon=path(icon_path),
          contents_directory='.' )
log_progress(60)
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name=name)
log_progress(80)
