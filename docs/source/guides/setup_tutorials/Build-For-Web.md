# Build For Web

_last updated 2026-10-18_

LT can build a project into a web page that plays in any modern browser, including on phones. The build runs from the command line in the lt-maker source folder.

## Setup

You need Python 3.12, the same version the browser runs. Make a separate environment for the build and install pygbag in it. On Windows, from the lt-maker folder:

```
py -3.12 -m venv venv_web
venv_web\Scripts\python -m pip install -r utilities/build_tools/web/requirements_web.txt
```

On Linux or macOS, use `python3.12 -m venv venv_web` and `venv_web/bin/python` instead.

## Build

```
venv_web\Scripts\python utilities/build_tools/build_web.py MyGame.ltproj
```

The path to the project is relative to the lt-maker folder. The finished page is in `build/web_stage/MyGame/build/web/`.

Give your project a `game_nid` of its own in the editor's constants before you publish. The browser keeps saves by `game_nid`, so two games with the same one on the same site share their saves. The build warns you if yours is still the default, `LT`.

## Test on your computer

```
venv_web\Scripts\python utilities/build_tools/web/serve.py build/web_stage/MyGame/build/web 127.0.0.1
```

Open http://127.0.0.1:8000/ in a browser and click to start. Stop the server with Ctrl+C.

Add `?level=<level nid>` to the address to start straight in that level, as the editor's Test Chapter does.

## Test on a phone

Serve on your computer's address on the local network instead, such as Windows Mobile Hotspot's:

```
venv_web\Scripts\python utilities/build_tools/web/serve.py build/web_stage/MyGame/build/web 192.168.137.1 --log web_log.txt
```

Open `http://192.168.137.1:8000/?report` on the phone. With `?report`, the page sends its console output and errors back to the server, which prints them and writes them to `web_log.txt`.

## Publish on itch.io

1. Zip the contents of the `web` folder, so `index.html` sits at the top of the zip.
2. On itch.io, set the project's kind to HTML, upload the zip, and tick "This file will be played in the browser".

itch.io allows 1,000 files, 500 MB unzipped and 200 MB per file; the build packs most audio and battle animations into bundles of about 4 MB to stay well inside that.

## What to expect

- The first load takes 10–20 seconds while the browser downloads Python.
- Music and sound effects play only after the player first clicks or taps.
- There is a short pause on a black screen while a level's music loads.
- Saves stay in the player's browser. The SAVES button exports them to a zip and imports them again, for moving to another browser or device.
- The browser can't run threads. Custom components that start threads, or read and write files outside `saves/`, may not work.
