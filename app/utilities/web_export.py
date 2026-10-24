'''
Builds the browser version of a game: a folder that a web server, or itch.io,
serves as it is. The page runs the engine under pygbag's Python for the
browser, which it fetches from pygbag's CDN; all the rest is written here,
with no pygbag needed:

    index.html              pygbag's page (app/web/pygbag_default.tmpl), filled in,
                            with app/web/loading.js in its head
    game.apk                a zip of the engine and the project, which the page
                            unpacks before it runs main.py (app/web/main.py)
    deferred/, deferred.json
                            most of the project's music, sound effects and
                            combat animation sheets, in bundles the page
                            fetches while the game runs (DEFERRED)
    favicon.png, lt_logo.png, apple-touch-icon.png
                            the page's own images

The engine's files are the ones beside this file, so a release of the editor,
which ships app/, sprites/ and resources/ as they are, builds the engine it
runs. The editor's Export for Web and utilities/build_tools/build_web.py both
build through here
'''
from __future__ import annotations

import ast
import html
import json
import shutil
import time
import zipfile
from pathlib import Path
from typing import Callable, Optional

from app.data.metadata import Metadata
from app.data.serialization.dataclass_serialization import dataclass_from_dict

ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = ROOT / 'app' / 'web'

# Parts of app/ the engine never imports. app/web is the page's, not the engine's
APP_EXCLUDES = ('editor', 'tests', 'map_maker', 'dungeon_maker', 'world_maker', 'shaders', 'web')
# Beside app/ in the archive, where main.py finds them. The rest of resources/
# is the editor's own images
ENGINE_FOLDERS = ('sprites', 'resources/platforms')
ENGINE_FILES = ('favicon.ico',)
PAGE_SCRIPTS = ('main.py', 'bench.py', 'page.js')
# Served beside index.html rather than packed with the game: page.js shows the
# Lex Talionis logo around the game, and the icon on a phone's home screen
PAGE_IMAGES = ('favicon.png', 'lt_logo.png', 'apple-touch-icon.png')

# The page's name for the game's archive, the same for every game
ARCHIVE = 'game'
# pygbag's page and its Python for the browser, which the page fetches from
# the CDN. Upgrading pygbag means a new pygbag_default.tmpl, fetched from the
# new version's CDN folder, and checking each patch below still applies
PYGBAG_VERSION = '0.9.3'
BROWSER_PYTHON = '3.12'
PYGBAG_CDN = 'https://pygame-web.github.io/cdn/%s/' % PYGBAG_VERSION
# What pygbag fills the template's {{cookiecutter.<key>}} with, as pygbag
# --build does by default; the title is the game's own
TEMPLATE_VALUES = {
    'cdn': PYGBAG_CDN,
    'xtermjs': '1',
    'width': '1280',
    'height': '720',
    # pygbag would hold the game until a click or a touch, as a browser lets a
    # page play sound only once it has been touched. In itch.io's frame on an
    # iPhone, no touch reaches the page until the game lays it out, so the game
    # starts at once, and page.js starts its sound on the first touch
    'ume_block': '0',
    'can_close': '0',
    'archive': ARCHIVE,
    'autorun': '0',
    'authors': 'pgw',
    'directory': ARCHIVE,
    'spdx': 'cookiecutter.spdx',
    'version': PYGBAG_VERSION,
    'PYBUILD': BROWSER_PYTHON,
}

# pygbag's page unpacks a zip of the game (.apk) on itch.io and a .tar.gz
# anywhere else. itch.io marks gzip content as Content-Encoding: gzip, so the
# browser would unpack a .tar.gz before Python could, while a zip arrives as
# it is on any host. The page unpacks the zip everywhere instead, and rather
# than fetch it once Python runs, takes it from loading.js, which fetched it
# as the page opened. It unpacks a file at a time, giving the page a moment
# now and then to show how far it is
ARCHIVE_UNPACKING = '''    if platform.window.location.host.find('.itch.zone')>0:
        import zipfile
        async with platform.fopen("{{cookiecutter.archive}}.apk", "rb") as archive:
            with zipfile.ZipFile(archive) as zip_ref:
                zip_ref.extractall(appdir.as_posix())
    else:
        import tarfile
        async with platform.fopen("{{cookiecutter.archive}}.tar.gz", "rb") as archive:
            tar = tarfile.open(fileobj=archive, mode="r:gz")
            tar.extractall(path=appdir.as_posix(), filter='tar')
            tar.close()
'''
ZIP_UNPACKING = '''    import os
    import time
    import zipfile
    while not platform.window.__ltLoading.archiveReady():
        await asyncio.sleep(.1)
    archive_path = "/tmp/{{cookiecutter.archive}}.apk"
    error = str(platform.window.__ltLoading.putArchive(archive_path))
    if error:
        raise RuntimeError(error)
    with zipfile.ZipFile(archive_path) as zip_ref:
        members = zip_ref.infolist()
        shown = time.monotonic()
        for done, member in enumerate(members):
            zip_ref.extract(member, appdir.as_posix())
            if time.monotonic() - shown > .1:
                platform.window.__ltLoading.progress(done / len(members))
                await asyncio.sleep(0)
                shown = time.monotonic()
    os.remove(archive_path)
    platform.window.__ltLoading.unpacked()
'''
# In place of pygbag's two viewports in the page's head, so that the page has
# its last from the start: a viewport set later moves what iOS draws but not
# where it takes touches, until the phone is turned. The page fills the whole
# screen, under the notch and status bar too, and page.js keeps the game and
# its buttons clear of them. Added to the home screen, it opens without
# Safari's bars, under the icon
PYGBAG_VIEWPORTS = ('    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
                    '    <meta name="viewport" content="height=device-height, initial-scale=1.0">\n')
HEAD_ADDITIONS = '''
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <link rel="apple-touch-icon" href="apple-touch-icon.png">
'''
# Added to the end of the page
BODY_ADDITIONS = '''
<style>
  body { background: radial-gradient(ellipse at center, #1d2856 0%, #151d40 55%, #0d1230 100%) !important; }
  #infobox { background: rgba(13, 18, 48, 0.9) !important; color: #fff07a !important;
             border: 2px solid rgba(255, 236, 110, 0.6); border-radius: 12px; font-family: sans-serif; }
</style>
'''

# What the page fetches while the game runs rather than in the game's download,
# the soonest wanted first: (folder in the project's resources, file extension).
# The engine opens each through app/engine/deferred_files.py
DEFERRED = (('sfx', '.ogg'), ('music', '.ogg'), ('combat_effects', '.png'), ('combat_anims', '.png'))
# The page fetches deferred files in bundles of about this many bytes: few
# enough files for any host (itch.io takes 1,000 at most), and small enough
# that the soonest wanted arrive soon
BUNDLE_SIZE = 4 * 2**20
# A new project's game_nid (app/data/database/constants.py)
DEFAULT_GAME_NID = 'LT'

# What a project's own code (resources/custom_components) may do that the
# browser can't, or can't keep, and why: the modules it imports, the
# functions it calls, by the names they have once its imports are followed,
# and the methods it calls on anything. browser_concerns finds each
THREADS = "the browser can't start threads or processes"
FILES = ("in the browser, files written outside saves/ are lost when the page closes, and the "
         "project's music, sounds and battle sheets are in place only while the engine loads them")
WAITS = "in the browser it holds the whole page, its screen and sound, while it waits"
CONCERN_MODULES = {'threading': THREADS, '_thread': THREADS, 'multiprocessing': THREADS,
                   'concurrent.futures': THREADS, 'subprocess': THREADS}
CONCERN_CALLS = {'open': FILES, 'os.remove': FILES, 'os.unlink': FILES, 'os.rename': FILES, 'os.replace': FILES,
                 'os.mkdir': FILES, 'os.makedirs': FILES, 'os.rmdir': FILES, 'time.sleep': WAITS}
CONCERN_CALL_MODULES = {'shutil': FILES}
CONCERN_METHODS = {'write_text': FILES, 'write_bytes': FILES, 'unlink': FILES, 'touch': FILES}

# Called with the share of the build done so far, from 0 to 1
Progress = Callable[[float], None]

def read_constants(project: Path) -> dict:
    return dict(json.loads((project / 'game_data' / 'constants.json').read_text(encoding='utf-8')))

def page_html(title: str, archive_size: int) -> str:
    '''pygbag's page, filled in for the game called title, whose archive is archive_size bytes'''
    page = (WEB_DIR / 'pygbag_default.tmpl').read_text(encoding='utf-8')
    page = _replace_once(page, ARCHIVE_UNPACKING, ZIP_UNPACKING)
    page = _replace_once(page, PYGBAG_VIEWPORTS, '')
    loading = '<script>\nwindow.__ltLoadingConfig = %s;\n%s</script>\n' % (
        json.dumps({'archive': ARCHIVE + '.apk', 'size': archive_size}),
        (WEB_DIR / 'loading.js').read_text(encoding='utf-8'))
    page = _replace_once(page, '</head>', HEAD_ADDITIONS + loading + '</head>')
    page = _replace_once(page, '</body>', BODY_ADDITIONS + '</body>')
    # The title also stands in a Python string in the page's script, where a
    # backslash would start an escape
    values = dict(TEMPLATE_VALUES, title=html.escape(title).replace('\\', '&#92;'))
    for key, value in values.items():
        page = page.replace('{{cookiecutter.%s}}' % key, value)
    return page

def _replace_once(text: str, old: str, new: str) -> str:
    '''A patch to pygbag's page, which must find what it replaces exactly once'''
    if text.count(old) != 1:
        raise ValueError("pygbag's page has %d of %r, where the build expects 1" % (text.count(old), old))
    return text.replace(old, new)

def files_to_defer(project: Path, constants: dict) -> list[Path]:
    '''
    The project's files DEFERRED names, the soonest wanted first. The title
    screen's music stays in the download, as the game plays it at once, and so
    do empty files, which cost the download nothing and have no range to fetch
    '''
    title_music = constants['music_main']
    keep = {'%s%s.ogg' % (title_music, suffix) for suffix in ('', '-intro', '-battle')} if title_music else set()
    return [source for folder, extension in DEFERRED
            for source in sorted((project / 'resources' / folder).rglob('*' + extension))
            if not (folder == 'music' and source.name in keep) and source.stat().st_size]

def engine_files() -> list[tuple[Path, str]]:
    '''Each file of the engine and the page's scripts, with its path in the archive'''
    files = []
    for source in sorted((ROOT / 'app').iterdir()):
        if source.name in APP_EXCLUDES:
            continue
        files.extend(_walk(source, 'app/' + source.name))
    for folder in ENGINE_FOLDERS:
        files.extend(_walk(ROOT / folder, folder))
    files.extend((ROOT / name, name) for name in ENGINE_FILES)
    files.extend((WEB_DIR / name, name) for name in PAGE_SCRIPTS)
    return files

def _walk(source: Path, name: str) -> list[tuple[Path, str]]:
    '''
    The files at source, a file or a folder, each with its path under name.
    Dotfiles are kept: a project's .orderkeys hold the order of its units,
    items, levels and the rest. Folders starting with a dot, and Python's
    caches, are not the game's
    '''
    if source.is_file():
        return [] if source.suffix == '.pyc' else [(source, name)]
    if source.name == '__pycache__' or source.name.startswith('.'):
        return []
    files = []
    for child in sorted(source.iterdir()):
        files.extend(_walk(child, name + '/' + child.name))
    return files

def check(project: Path):
    '''Raises ValueError for a project the engine would refuse to start, as main.py does'''
    metadata = dataclass_from_dict(Metadata, json.loads((project / 'metadata.json').read_text(encoding='utf-8')))
    if metadata.has_fatal_errors:
        raise ValueError("%s has fatal errors, so the engine would refuse to start it" % project.name)

def browser_concerns(project: Path) -> list[str]:
    '''
    What the project's own code may do that the browser can't, or can't keep,
    each as "<file>:<line>: <what it does>; <why>". Its code may well keep
    clear of it in the browser (sys.platform == 'emscripten'), so these are
    for its author to look at, not reasons to refuse it
    '''
    concerns = []
    for source in sorted((project / 'resources' / 'custom_components').rglob('*.py')):
        name = source.relative_to(project).as_posix()
        try:
            tree = ast.parse(source.read_text(encoding='utf-8'), name)
        except SyntaxError as error:
            concerns.append((name, error.lineno or 0, "can't be read: %s" % error.msg))
            continue
        concerns.extend((name, line, what) for line, what in _code_concerns(tree))
    return ['%s:%d: %s' % concern for concern in sorted(concerns)]

def _code_concerns(tree: ast.AST) -> list[tuple[int, str]]:
    '''The line and the concern of each of CONCERN_MODULES, CONCERN_CALLS and CONCERN_METHODS in tree'''
    concerns = []
    # Each name an import binds to something other than itself (import shutil
    # as sh, from os import remove), to the module or function it stands for
    imported = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
            for alias in node.names:
                if alias.asname:
                    imported[alias.asname] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules = [node.module] + [node.module + '.' + alias.name for alias in node.names]
            for alias in node.names:
                imported[alias.asname or alias.name] = node.module + '.' + alias.name
        else:
            continue
        for module in modules:
            if module in CONCERN_MODULES:
                concerns.append((node.lineno, 'imports %s; %s' % (module, CONCERN_MODULES[module])))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        called = _dotted_name(node.func)
        if called:
            first, _, rest = called.partition('.')
            called = imported.get(first, first) + ('.' + rest if rest else '')
            why = CONCERN_CALLS.get(called) or CONCERN_CALL_MODULES.get(called.rpartition('.')[0])
            if why:
                concerns.append((node.lineno, 'calls %s; %s' % (called, why)))
                continue
        if isinstance(node.func, ast.Attribute) and node.func.attr in CONCERN_METHODS:
            concerns.append((node.lineno, 'calls .%s(); %s' % (node.func.attr, CONCERN_METHODS[node.func.attr])))
    return concerns

def _dotted_name(node: ast.AST) -> Optional[str]:
    '''The name a call is made by, as written (os.path.join), when it is only names and dots'''
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        owner = _dotted_name(node.value)
        return owner and owner + '.' + node.attr
    return None

def build(project: Path, web_dir: Path, progress: Optional[Progress] = None):
    '''
    Builds the browser version of project into web_dir, which must be empty or
    not yet exist. Raises ValueError for a project the engine would refuse to
    start (check), or a web_dir with files in it
    '''
    check(project)
    if web_dir.exists() and any(web_dir.iterdir()):
        raise ValueError("%s is not empty" % web_dir)
    web_dir.mkdir(parents=True, exist_ok=True)
    constants = read_constants(project)

    deferred = files_to_defer(project, constants)
    left_out = set(deferred)
    packed = engine_files() + [(source, name) for source, name in _walk(project, project.name) if source not in left_out]
    total = len(packed) + len(deferred)
    done = 0
    def advance():
        nonlocal done
        done += 1
        if progress:
            progress(done / total)

    # main.py runs from assets/, where the page unpacks the archive's assets/
    with zipfile.ZipFile(web_dir / (ARCHIVE + '.apk'), 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source, name in packed:
            archive.write(source, 'assets/' + name)
            advance()
        # main.py prints it, to tell which build a device ran
        archive.writestr('assets/built.txt', time.strftime('%Y-%m-%d %H:%M:%S'))
    _write_bundles(deferred, project, web_dir, advance)
    archive_size = (web_dir / (ARCHIVE + '.apk')).stat().st_size
    (web_dir / 'index.html').write_text(page_html(constants['title'], archive_size), encoding='utf-8')
    for image in PAGE_IMAGES:
        shutil.copy(WEB_DIR / image, web_dir / image)

def _write_bundles(deferred: list[Path], project: Path, web_dir: Path, advance: Callable[[], None]):
    '''
    Puts the deferred files in bundles in web_dir/deferred/ (0.zip, 1.zip, ...),
    for the page to fetch while the game runs. A bundle is its files' bytes one
    after another, in the order the game is likely to want them.
    web_dir/deferred.json lists the bundles in that order, each with the path,
    offset and size of each file in it, the path as main.py's folder holds it:
    [{"name": "0.zip", "files": [[path, offset, size], ...]}, ...]
    A bundle is no zip, but is named as one so that a host serves it as it is.
    itch.io serves a .bin by what it guesses from the first bytes (application/ogg),
    and its CDN then compresses it, answering a request for some of the bundle's
    bytes with those of the compressed bundle, which no browser can open
    '''
    (web_dir / 'deferred').mkdir()
    bundles = []
    for source in deferred:
        if not bundles or bundles[-1]['size'] >= BUNDLE_SIZE:
            bundles.append({'name': '%d.zip' % len(bundles), 'files': [], 'size': 0})
        bundle = bundles[-1]
        data = source.read_bytes()
        with (web_dir / 'deferred' / bundle['name']).open('ab') as out:
            out.write(data)
        path = project.name + '/' + source.relative_to(project).as_posix()
        bundle['files'].append([path, bundle['size'], len(data)])
        bundle['size'] += len(data)
        advance()
    (web_dir / 'deferred.json').write_text(json.dumps([{'name': bundle['name'], 'files': bundle['files']} for bundle in bundles]),
                                           encoding='utf-8')

def package(web_dir: Path, zip_path: Path):
    '''
    Zips the build in web_dir for itch.io, with index.html at the top. Its
    files are compressed already, or small, so the zip only stores them
    '''
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_STORED) as out:
        for source in sorted(web_dir.rglob('*')):
            if source.is_file():
                out.write(source, source.relative_to(web_dir).as_posix())
