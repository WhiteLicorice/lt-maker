# Build For Web

_last updated 2026-10-23_

LT can build a project into a web page that plays in any modern browser, including on phones. The editor does it in one step, with nothing else to install.

## Export

1. Give your project a **Game Unique Identifier** of its own under Edit > Constants. Players' browsers keep each game's saves by it, so two games on itch.io that both kept the default, `LT`, would share their saves. The editor asks before exporting a project that still has the default.
2. Choose File > Export for Web... The editor saves the project, then asks where to put the zip (`MyGame_web.zip` by default).

A project with fatal errors can't be exported, just as it can't be played; fix them first (Extra > View Error Report).

## Publish on itch.io

1. On itch.io, create a project and set its Kind of project to **HTML**.
2. Upload the zip, and tick **This file will be played in the browser**.
3. Under Embed options, tick **Mobile friendly**, or itch.io won't offer the game on phones, and **Fullscreen button**. A viewport of 960 × 640 or larger suits the game's 3:2 screen.

To try it before anyone else can, leave the project's Visibility as **Draft**: only you can open it, on any device you're logged in on.

itch.io allows 1,000 files, 500 MB unzipped and 200 MB per file. The export packs the game into one archive, and most music, sound effects and battle animations into bundles of about 4 MB, to stay well inside that.

## What to expect

- The game takes 5–20 seconds to start, behind a loading screen that shows how far along it is. On a phone, most of that is the browser starting Python.
- The game starts on its own, but music and sound effects play only after the player first clicks or taps.
- There is a short pause on a black screen while a level's music loads.
- Saves stay in the player's browser. The SAVES button exports them to a zip and imports them again, for moving to another browser or device.
- On a touch screen, the page draws a d-pad and A, B, L, R and START buttons around the game.
- The browser can't run threads. Custom components that start threads, pause with `time.sleep`, or read and write files outside `saves/`, may not work. The export lists each place in your custom components that may do so, by file and line, and asks before going on.

## From the source code

Developers working from the lt-maker source can build without the editor. From the lt-maker folder, with the same Python the editor runs on:

```
python utilities/build_tools/build_web.py MyGame.ltproj --zip
```

The path to the project is relative to the lt-maker folder. The page is built into `build/web/MyGame/`, and `--zip` also packs it into `build/web/MyGame.zip` for itch.io.

### Test on your computer

```
python utilities/build_tools/web/serve.py build/web/MyGame 127.0.0.1
```

Open http://127.0.0.1:8000/ in a browser. Stop the server with Ctrl+C.

Add `?level=<level nid>` to the address to start straight in that level, as the editor's Test Chapter does.

### Test on a phone

Serve on your computer's address on the local network instead, such as Windows Mobile Hotspot's:

```
python utilities/build_tools/web/serve.py build/web/MyGame 192.168.137.1 --log web_log.txt
```

Open `http://192.168.137.1:8000/?report` on the phone. With `?report`, the page sends its console output and errors back to the server, which prints them and writes them to `web_log.txt`.
