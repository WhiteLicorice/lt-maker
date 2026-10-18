'''
Builds the browser version of the engine with pygbag.

    python utilities/build_tools/build_web.py [project.ltproj] [--serve]

pygbag packs everything in the folder holding main.py, so this first stages
what the engine needs (the engine's code, its sprites, one project) into
build/web_stage/<project>/, then runs pygbag on that folder. The result is
build/web_stage/<project>/build/web/, which index.html serves. Most of the
project's music, sound effects and combat animation sheets sit beside it in
deferred/ instead of in the game's download, for the page to fetch while the
game runs (DEFERRED).

--serve starts pygbag's test server on http://localhost:8000 after building,
serving its own index.html without INDEX_ADDITIONS, so that a tap on an
iPhone may not start the game; web/serve.py serves a build without that.
Run it from the repo root under Python 3.12, the browser's, with the packages
in web/requirements_web.txt installed
'''
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import typing_extensions

# The Python pygbag 0.9.3 runs in the browser. The build runs under the same,
# so that the code it generates, and anything that differs between versions,
# is as the browser will have it
BROWSER_PYTHON = (3, 12)

ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = Path(__file__).resolve().parent / 'web'

# Parts of app/ the engine never imports
APP_EXCLUDES = ('editor', 'tests', 'map_maker', 'dungeon_maker', 'world_maker', 'shaders')
# page.js shows the Lex Talionis logo around the game, and the icon on a phone's home screen
PAGE_IMAGES = ('lt_logo.png', 'apple-touch-icon.png')
# Added to the end of pygbag's index.html, to run before the game does.
# pygbag starts the game on the first click after loading, as a browser lets a
# page play sound only once it has been touched. iOS sends no click for a tap
# on most of a page, so a tap would not start it; any touch does here
INDEX_ADDITIONS = '''
<style>
  body { background: radial-gradient(ellipse at center, #1d2856 0%, #151d40 55%, #0d1230 100%) !important; }
  #infobox { background: rgba(13, 18, 48, 0.9) !important; color: #fff07a !important;
             border: 2px solid rgba(255, 236, 110, 0.6); border-radius: 12px; font-family: sans-serif; }
</style>
<script>
  for (const name of ['touchend', 'pointerup']) {
    window.addEventListener(name, () => {
      if (window.MM && !MM.UME) {
        MM.UME = 1;
      }
    }, {passive: true, capture: true});
  }
</script>
'''
# What the page fetches while the game runs rather than in the game's download,
# the soonest wanted first: (folder in the project's resources, file extension).
# The engine opens each through app/engine/deferred_files.py
DEFERRED = (('sfx', '.ogg'), ('music', '.ogg'), ('combat_effects', '.png'), ('combat_anims', '.png'))
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
    shutil.copy(WEB_DIR / 'page.js', stage / 'page.js')
    # main.py prints it, to tell which build a device ran
    (stage / 'built.txt').write_text(time.strftime('%Y-%m-%d %H:%M:%S'), encoding='utf-8')

def defer_files(stage: Path, project: Path, web: Path):
    '''
    Moves the files DEFERRED names out of the stage, and so out of the game's
    download, into web/deferred/, and lists them in web/deferred.json for the
    page to fetch while the game runs. The title screen's music stays, as the
    game plays it at once
    '''
    constants = dict(json.loads((project / 'game_data' / 'constants.json').read_text(encoding='utf-8')))
    title_music = constants.get('music_main')
    keep = {'%s%s.ogg' % (title_music, suffix) for suffix in ('', '-intro', '-battle')} if title_music else set()
    deferred = web / 'deferred'
    if deferred.exists():
        shutil.rmtree(deferred)
    paths = []
    for folder, extension in DEFERRED:
        for source in sorted((stage / project.name / 'resources' / folder).rglob('*' + extension)):
            if folder == 'music' and source.name in keep:
                continue
            path = source.relative_to(stage).as_posix()
            target = deferred / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(source, target)
            paths.append(path)
    (web / 'deferred.json').write_text(json.dumps(paths), encoding='utf-8')
    print('Deferred %d files, %.1f MB' % (len(paths), sum((deferred / path).stat().st_size for path in paths) / 2**20))

def main(args: list[str]):
    if sys.version_info[:2] != BROWSER_PYTHON:
        raise SystemExit('Build under Python %d.%d, as the browser runs; this is %d.%d. See web/requirements_web.txt'
                         % (*BROWSER_PYTHON, *sys.version_info[:2]))
    serve = '--serve' in args
    names = [arg for arg in args if not arg.startswith('--')]
    project = (ROOT / (names[0] if names else 'default.ltproj')).resolve()
    if not project.is_dir():
        raise SystemExit('No project at %s' % project)

    generate_sources()
    stage = ROOT / 'build' / 'web_stage' / project.stem
    clean_stage(stage)
    stage_files(stage, project)
    # Served beside index.html rather than packed with the game, for the page itself
    web = stage / 'build' / 'web'
    web.mkdir(parents=True, exist_ok=True)
    for image in PAGE_IMAGES:
        shutil.copy(WEB_DIR / image, web / image)
    defer_files(stage, project, web)

    command = [sys.executable, '-m', 'pygbag', '--title', project.stem, '--ume_block', '1']
    if not serve:
        command.append('--build')
    command.append(str(stage))
    print(' '.join(command))
    subprocess.run(command, check=True, cwd=stage)
    # pygbag writes index.html as it builds. With --serve it returns only once
    # its server stops, so the page it serves goes without these
    if not serve:
        index = web / 'index.html'
        html = index.read_text(encoding='utf-8')
        index.write_text(html.replace('</body>', INDEX_ADDITIONS + '</body>', 1), encoding='utf-8')

if __name__ == '__main__':
    main(sys.argv[1:])
