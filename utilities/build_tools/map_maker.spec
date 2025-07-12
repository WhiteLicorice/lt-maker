# -*- mode: python -*-
import sys

block_cipher = None

a = Analysis(['run_map_maker.py'],
             pathex=['.'],
             binaries=[],
             datas=[('favicon.ico', '.'),
                    ('icons', 'icons'),
                    ('app', 'app')],
             hiddenimports=['json', 'dataclasses'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

Key = ['mkl', 'libopenblas']

def remove_from_list(input, keys):
    outlist = []
    for item in input:
        name, _, _ = item
        flag = 0
        for key_word in keys:
            if name.find(key_word) > -1:
                flag = 1
        if flag != 1:
            outlist.append(item)
    return outlist

# a.binaries = remove_from_list(a.binaries, Key)

exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='lt_map_maker',
          debug=False,
          strip=False,
          upx=True,
          console=True,
          icon='favicon.ico',
          contents_directory='.' )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='lt_map_maker')
