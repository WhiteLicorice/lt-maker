'''
Builds the browser version of a project, as the editor's Export for Web does
(app/utilities/web_export.py), from the command line.

    python utilities/build_tools/build_web.py [project.ltproj] [--zip]

The result is build/web/<project>/, a folder any web server serves as it is
(web/serve.py serves it to a phone on the local network). --zip also packs it
into build/web/<project>.zip for itch.io. Run it from the repo root
'''
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.engine.codegen import source_generator
from app.utilities import web_export

def warn_of_shared_game_nid(constants: dict):
    '''
    The page keeps a game's saves in the browser by its game_nid (page.js). A
    site that serves many games from one address, as itch.io does, would have
    two of them with the same game_nid share their saves
    '''
    if constants['game_nid'] == web_export.DEFAULT_GAME_NID:
        print("Warning: this project's game_nid is still the default, %s. Another game "
              "with the same one, on the same site, would share its saves in the browser. "
              "Give it a game_nid of its own in the editor's constants" % web_export.DEFAULT_GAME_NID)

def main(args: list[str]):
    names = [arg for arg in args if not arg.startswith('--')]
    project = (ROOT / (names[0] if names else 'default.ltproj')).resolve()
    if not project.is_dir():
        raise SystemExit('No project at %s' % project)
    warn_of_shared_game_nid(web_export.read_constants(project))
    # The editor generates these as it starts; a build from here may come first
    source_generator.generate_all()
    web_dir = ROOT / 'build' / 'web' / project.stem
    if web_dir.exists():
        shutil.rmtree(web_dir)
    web_export.build(project, web_dir)
    print('Built', web_dir)
    if '--zip' in args:
        zip_path = web_dir.with_suffix('.zip')
        web_export.package(web_dir, zip_path)
        print('Packed', zip_path)

if __name__ == '__main__':
    main(sys.argv[1:])
