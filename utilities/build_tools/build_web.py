'''
Builds the browser version of the engine with pygbag.

    python utilities/build_tools/build_web.py [project.ltproj] [--serve]

pygbag packs everything in the folder holding main.py, so this first stages
what the engine needs (the engine's code, its sprites, one project) into
build/web_stage/<project>/, then runs pygbag on that folder. The result is
build/web_stage/<project>/build/web/, which index.html serves.

--serve starts pygbag's test server on http://localhost:8000 after building.
Run it from the repo root, with pygbag installed (pip install pygbag)
'''
import shutil
import subprocess
import sys
from pathlib import Path

import typing_extensions

ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = Path(__file__).resolve().parent / 'web'

# Parts of app/ the engine never imports
APP_EXCLUDES = ('editor', 'tests', 'map_maker', 'dungeon_maker', 'world_maker', 'shaders')
# The one editor module the engine does import
EDITOR_MODULES = ('editor/__init__.py', 'editor/lib/math/math_utils.py')

def generate_sources():
    sys.path.insert(0, str(ROOT))
    from app.engine.codegen import source_generator
    source_generator.generate_all()

def clean_stage(stage: Path):
    '''Empties the stage except pygbag's own build folder, whose cache saves a download'''
    stage.mkdir(parents=True, exist_ok=True)
    for child in stage.iterdir():
        if child.name == 'build':
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()

def stage_files(stage: Path, project: Path):
    ignore = shutil.ignore_patterns('__pycache__', '*.pyc')
    app_ignore = shutil.ignore_patterns('__pycache__', '*.pyc', *APP_EXCLUDES)
    shutil.copytree(ROOT / 'app', stage / 'app', ignore=lambda d, names: app_ignore(d, names) if Path(d) == ROOT / 'app' else ignore(d, names))
    for module in EDITOR_MODULES:
        target = stage / 'app' / module
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / 'app' / module, target)
    shutil.copytree(ROOT / 'sprites', stage / 'sprites', ignore=ignore)
    shutil.copytree(ROOT / 'resources', stage / 'resources', ignore=ignore)
    shutil.copytree(project, stage / project.name, ignore=ignore)
    shutil.copy(ROOT / 'favicon.ico', stage / 'favicon.ico')
    # Not in the browser's Python
    shutil.copy(typing_extensions.__file__, stage / 'typing_extensions.py')
    shutil.copy(WEB_DIR / 'main.py', stage / 'main.py')
    shutil.copy(WEB_DIR / 'bench.py', stage / 'bench.py')

def main(args: list[str]):
    serve = '--serve' in args
    names = [arg for arg in args if not arg.startswith('--')]
    project = (ROOT / (names[0] if names else 'default.ltproj')).resolve()
    if not project.is_dir():
        raise SystemExit('No project at %s' % project)

    generate_sources()
    stage = ROOT / 'build' / 'web_stage' / project.stem
    clean_stage(stage)
    stage_files(stage, project)

    command = [sys.executable, '-m', 'pygbag', '--title', project.stem, '--ume_block', '1']
    if not serve:
        command.append('--build')
    command.append(str(stage))
    print(' '.join(command))
    subprocess.run(command, check=True, cwd=stage)

if __name__ == '__main__':
    main(sys.argv[1:])
