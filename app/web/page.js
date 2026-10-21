// Sets up the page for the game: shows the game's screen as large as the
// window allows, keeps its sound going, keeps its saves (with a button to
// export and import them), and on a touch screen draws the buttons a keyboard
// would give. main.py runs this file, then __ltSaves.restore, then
// __ltSetupPage once the engine is imported, and __ltSaves.offer once the
// game's data is loaded.
// Presses wait in a queue that main.py drains each frame (__ltTouch.take) and
// hands the engine as presses of the player's keys for those buttons.
(() => {
  // The colours of the Lex Talionis logo: its night sky, and its gold
  const BACKGROUND = 'radial-gradient(ellipse at center, #1d2856 0%, #151d40 55%, #0d1230 100%)';
  const STYLE = `
    html, body { height: 100%; margin: 0; overflow: hidden; overscroll-behavior: none;
                 touch-action: none; -webkit-user-select: none; user-select: none;
                 -webkit-touch-callout: none; -webkit-tap-highlight-color: transparent; }
    canvas#canvas, canvas#lt-screen { image-rendering: pixelated; image-rendering: crisp-edges; }
    canvas#lt-screen { position: absolute; z-index: 4; pointer-events: none;
                       box-shadow: 0 0 24px rgba(0, 0, 0, 0.6); }
    img.lt-logo { position: fixed; z-index: 2; pointer-events: none; display: none; }
    #lt-pad { position: fixed; left: 0; right: 0; bottom: 0; top: 0; pointer-events: none; z-index: 10;
              font-family: sans-serif; font-weight: bold; }
    #lt-pad > div { position: absolute; pointer-events: auto; touch-action: none;
                    display: flex; align-items: center; justify-content: center;
                    color: rgba(255, 244, 150, 0.9); background: rgba(255, 240, 120, 0.08);
                    border: 2px solid rgba(255, 236, 110, 0.5); box-sizing: border-box; }
    #lt-pad > div.pressed, #lt-dpad > div.pressed { background: rgba(255, 240, 120, 0.4); }
    #lt-pad .face { width: 58px; height: 58px; border-radius: 50%; font-size: 20px; }
    #lt-pad .shoulder { width: 70px; height: 34px; border-radius: 10px; font-size: 16px; }
    #lt-pad .start { width: 72px; height: 30px; border-radius: 15px; font-size: 12px; }
    #lt-pad #lt-dpad { width: 138px; height: 138px; border: none; background: none; }
    #lt-dpad > div { position: absolute; width: 46px; height: 46px; background: rgba(255, 240, 120, 0.08);
                     border: 2px solid rgba(255, 236, 110, 0.5); box-sizing: border-box; pointer-events: none; }
    #lt-dpad .UP { left: 46px; top: 0; border-radius: 8px 8px 0 0; }
    #lt-dpad .DOWN { left: 46px; top: 92px; border-radius: 0 0 8px 8px; }
    #lt-dpad .LEFT { left: 0; top: 46px; border-radius: 8px 0 0 8px; }
    #lt-dpad .RIGHT { left: 92px; top: 46px; border-radius: 0 8px 8px 0; }

    #lt-pad.landscape .L { left: calc(12px + env(safe-area-inset-left)); top: 12px; }
    #lt-pad.landscape .R { right: calc(12px + env(safe-area-inset-right)); top: 12px; }
    /* Low, where the thumbs rest, as phone emulators place them */
    #lt-pad.landscape #lt-dpad { left: calc(14px + env(safe-area-inset-left)); bottom: calc(40px + env(safe-area-inset-bottom)); }
    #lt-pad.landscape .A { right: calc(14px + env(safe-area-inset-right)); bottom: calc(100px + env(safe-area-inset-bottom)); }
    #lt-pad.landscape .B { right: calc(84px + env(safe-area-inset-right)); bottom: calc(54px + env(safe-area-inset-bottom)); }
    #lt-pad.landscape .start { right: calc(20px + env(safe-area-inset-right)); bottom: calc(12px + env(safe-area-inset-bottom)); }

    #lt-pad.portrait .L { left: 16px; top: 16px; }
    #lt-pad.portrait .R { right: 16px; top: 16px; }
    #lt-pad.portrait #lt-dpad { left: 20px; top: 76px; }
    #lt-pad.portrait .A { right: 20px; top: 86px; }
    #lt-pad.portrait .B { right: 92px; top: 136px; }
    #lt-pad.portrait .start { left: calc(50% - 36px); top: 236px; }

    /* In the window's corner, or under the D-pad, level with START */
    #lt-saves { position: fixed; right: 12px; top: 12px; z-index: 10; width: 64px; height: 22px;
                display: flex; align-items: center; justify-content: center; box-sizing: border-box;
                border-radius: 11px; font: bold 11px sans-serif; letter-spacing: 1px; cursor: pointer;
                color: rgba(255, 244, 150, 0.9); background: rgba(255, 240, 120, 0.08);
                border: 2px solid rgba(255, 236, 110, 0.5); }
    #lt-pad.landscape #lt-saves { right: auto; top: auto; left: calc(51px + env(safe-area-inset-left));
                                  bottom: calc(10px + env(safe-area-inset-bottom)); }
    #lt-pad.portrait #lt-saves { right: auto; left: 57px; top: 240px; }
    #lt-saves-panel { position: fixed; left: 0; top: 0; right: 0; bottom: 0; z-index: 20; display: none;
                      align-items: center; justify-content: center; background: rgba(5, 8, 24, 0.6);
                      font-family: sans-serif; }
    #lt-saves-panel .box { width: min(420px, calc(100% - 32px)); padding: 16px 20px; box-sizing: border-box;
                           border-radius: 12px; background: rgba(13, 18, 48, 0.95); color: #fff6c8;
                           border: 2px solid rgba(255, 236, 110, 0.6); }
    #lt-saves-panel h2 { margin: 0 0 8px; font-size: 18px; color: #fff07a; }
    #lt-saves-panel p { margin: 0 0 12px; font-size: 14px; line-height: 1.4; }
    #lt-saves-panel .choices { display: flex; gap: 10px; }
    #lt-saves-panel button { flex: 1; min-height: 40px; border-radius: 10px; font: bold 14px sans-serif;
                             cursor: pointer; color: #fff07a; background: rgba(255, 240, 120, 0.12);
                             border: 2px solid rgba(255, 236, 110, 0.5); }
    #lt-saves-panel .status { margin: 12px 0 0; min-height: 1.4em; }
  `;
  // On-screen label, and the engine's button it presses
  const BUTTONS = [['A', 'SELECT', 'face'], ['B', 'BACK', 'face'], ['L', 'AUX', 'shoulder'],
                   ['R', 'INFO', 'shoulder'], ['START', 'START', 'start']];

  const changes = [];
  window.__ltTouch = { take() { return JSON.stringify(changes.splice(0)); } };
  // The page's listeners only watch touches. A listener that could cancel one
  // has iOS wait for the page to answer each touch, holding up the screen's
  // next refresh; touch-action in STYLE already keeps touches from scrolling
  // or zooming the page
  const WATCH = {passive: true};
  const WATCH_FIRST = {passive: true, capture: true};

  function holdable(element, button) {
    const release = () => {
      if (!element.classList.contains('pressed')) return;
      element.classList.remove('pressed');
      changes.push([button, false]);
    };
    element.addEventListener('pointerdown', (event) => {
      element.setPointerCapture(event.pointerId);
      element.classList.add('pressed');
      changes.push([button, true]);
    }, WATCH);
    element.addEventListener('pointerup', release, WATCH);
    element.addEventListener('pointercancel', release, WATCH);
  }

  // One pad for all four directions, so a thumb can roll from one to the next
  function dpad() {
    const pad = document.createElement('div');
    pad.id = 'lt-dpad';
    const arms = {};
    for (const direction of ['UP', 'DOWN', 'LEFT', 'RIGHT']) {
      arms[direction] = document.createElement('div');
      arms[direction].className = direction;
      pad.appendChild(arms[direction]);
    }
    const held = new Set();
    const hold = (wanted) => {
      for (const direction of ['UP', 'DOWN', 'LEFT', 'RIGHT']) {
        if (wanted.has(direction) && !held.has(direction)) {
          held.add(direction); arms[direction].classList.add('pressed'); changes.push([direction, true]);
        } else if (!wanted.has(direction) && held.has(direction)) {
          held.delete(direction); arms[direction].classList.remove('pressed'); changes.push([direction, false]);
        }
      }
    };
    const aim = (event) => {
      const box = pad.getBoundingClientRect();
      const dx = event.clientX - (box.left + box.width / 2);
      const dy = event.clientY - (box.top + box.height / 2);
      const dead = box.width * 0.12;
      const wanted = new Set();
      // A diagonal only when the thumb is well off both axes
      if (Math.abs(dx) > dead && Math.abs(dx) > Math.abs(dy) * 0.5) wanted.add(dx < 0 ? 'LEFT' : 'RIGHT');
      if (Math.abs(dy) > dead && Math.abs(dy) > Math.abs(dx) * 0.5) wanted.add(dy < 0 ? 'UP' : 'DOWN');
      hold(wanted);
    };
    pad.addEventListener('pointerdown', (event) => {
      pad.setPointerCapture(event.pointerId);
      aim(event);
    }, WATCH);
    pad.addEventListener('pointermove', (event) => { if (pad.hasPointerCapture(event.pointerId)) aim(event); }, WATCH);
    pad.addEventListener('pointerup', () => hold(new Set()), WATCH);
    pad.addEventListener('pointercancel', () => hold(new Set()), WATCH);
    return pad;
  }

  function buildPad() {
    const pad = document.createElement('div');
    pad.id = 'lt-pad';
    pad.appendChild(dpad());
    for (const [label, button, kind] of BUTTONS) {
      const element = document.createElement('div');
      element.className = kind + ' ' + label;
      element.textContent = label;
      holdable(element, button);
      pad.appendChild(element);
    }
    document.body.appendChild(pad);
    return pad;
  }

  // SDL plays sound through a ScriptProcessorNode, which asks the page's
  // thread for each next 10 ms of it. While the game holds the thread (a song
  // takes most of a second to load on a phone), the node plays its last 10 ms
  // over and over, a robotic buzz. Here SDL fills buffers scheduled to play
  // PLAY_AHEAD later instead, so that a hold runs out into silence. The node
  // SDL asked for still runs, silent, to ask for them on time, as the page's
  // timers slow down while it is in the background
  const PLAY_AHEAD = 0.04;  // s
  // How long the buffers after a hold wait to start, as a buffer scheduled for
  // the past starts late and would overlap the next
  const RESTART_AFTER = 0.01;  // s
  // For ?audio_log (main.py)
  window.__ltSound = {node: 'none yet', buffers: 0, holds: 0, silentMs: 0, busyMs: 0, longestMs: 0};
  function playAhead(Context) {
    const create = Context.prototype.createScriptProcessor;
    Context.prototype.createScriptProcessor = function (size, inputs, outputs) {
      const clock = create.call(this, size, inputs, outputs);
      const context = this;
      let fill = null, destination = null, playAt = 0;
      __ltSound.node = size + ' frames, ' + outputs + ' channels at ' + context.sampleRate + ' Hz';
      clock.onaudioprocess = () => {
        if (!fill || !destination) return;
        const began = performance.now();
        if (playAt < context.currentTime) {
          if (playAt) {
            __ltSound.holds++;
            __ltSound.silentMs += (context.currentTime + RESTART_AFTER - playAt) * 1000;
          }
          playAt = context.currentTime + RESTART_AFTER;
        }
        while (playAt < context.currentTime + PLAY_AHEAD) {
          const buffer = context.createBuffer(outputs, size, context.sampleRate);
          fill({outputBuffer: buffer, playbackTime: playAt});
          const source = context.createBufferSource();
          source.buffer = buffer;
          source.connect(destination);
          source.start(playAt);
          playAt += size / context.sampleRate;
          __ltSound.buffers++;
        }
        const took = performance.now() - began;
        __ltSound.busyMs += took;
        __ltSound.longestMs = Math.max(__ltSound.longestMs, took);
      };
      // What SDL sees as the node
      return {
        bufferSize: size,
        get onaudioprocess() { return fill; },
        set onaudioprocess(callback) { fill = callback; },
        connect(target) { destination = target; clock.connect(target); },
        disconnect() { destination = null; clock.disconnect(); },
      };
    };
  }

  // iOS stops the page's sound when the phone locks and leaves it stopped, so
  // every audio context the page makes is restarted when the page is back,
  // and on the next touch, where iOS only allows it from one
  function keepSoundGoing() {
    const contexts = [];
    for (const name of ['AudioContext', 'webkitAudioContext']) {
      const Original = window[name];
      if (!Original) continue;
      playAhead(Original);
      window[name] = class extends Original {
        constructor(...args) { super(...args); contexts.push(this); }
      };
    }
    const resume = () => {
      for (const context of contexts) {
        if (context.state !== 'running') context.resume().catch(() => {});
      }
    };
    document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') resume(); });
    window.addEventListener('pageshow', resume);
    window.addEventListener('focus', resume);
    window.addEventListener('pointerup', resume, WATCH_FIRST);
    window.addEventListener('touchend', resume, WATCH_FIRST);
  }

  // The files the build left out of the game's download, in bundles that
  // deferred.json lists, the soonest wanted first (web_export.py's
  // _write_bundles). The bundles are fetched a few at a time, and their files
  // put in the game's filesystem beside the rest, under root. The engine
  // fetches any it opens before they arrive itself, with fetchNow
  // (app/engine/deferred_files.py)
  const DOWNLOADS_AT_ONCE = 2;
  // Each deferred file's [bundle, offset, size], by its path
  let bundled = null;
  const learn = (bundles) => {
    bundled = new Map();
    for (const bundle of bundles) {
      for (const [path, offset, size] of bundle.files) bundled.set(path, [bundle.name, offset, size]);
    }
  };
  window.__ltDeferred = {
    start(root) {
      fetch('deferred.json').then((response) => response.json()).then((bundles) => {
        if (!bundled) learn(bundles);
        const next = () => {
          const bundle = bundles.shift();
          if (bundle === undefined) return;
          fetch('deferred/' + bundle.name).then((response) => {
            if (!response.ok) throw new Error(response.status + ' for ' + bundle.name);
            return response.arrayBuffer();
          }).then((data) => {
            for (const [path, offset, size] of bundle.files) {
              const target = root + '/' + path;
              if (!python.FS.analyzePath(target).exists) python.FS.writeFile(target, new Uint8Array(data, offset, size));
            }
          }).catch((error) => console.warn('LTDEFERRED', error)).finally(next);
        };
        for (let i = 0; i < DOWNLOADS_AT_ONCE; i++) next();
      }).catch((error) => console.warn('LTDEFERRED no deferred.json', error));
    },
    // Holds the game until the file is in place, at target. It asks for only
    // the file's own bytes of its bundle; a server that sends the whole
    // bundle anyway takes longer. Returns why it could not, or '' once it is
    fetchNow(path, target) {
      if (!bundled) learn(JSON.parse(holdFor('deferred.json').text));
      const [name, offset, size] = bundled.get(path) || [];
      if (name === undefined) return 'it is in no bundle';
      const response = holdFor('deferred/' + name, 'bytes=' + offset + '-' + (offset + size - 1));
      if (response.status !== 206 && response.status !== 200) return 'the server answered ' + response.status + ' for ' + name;
      const start = response.status === 206 ? 0 : offset;
      const data = new Uint8Array(size);
      for (let i = 0; i < size; i++) data[i] = response.text.charCodeAt(start + i) & 0xff;
      python.FS.writeFile(target, data);
      console.log('LTDEFERRED waited for', path);
      return '';
    },
  };
  // Fetches url's text, or a range of its bytes, holding the page until it arrives
  function holdFor(url, range) {
    const request = new XMLHttpRequest();
    request.open('GET', url, false);
    if (range) {
      request.setRequestHeader('Range', range);
      // A request that holds the page must take text; this keeps each byte as it is
      request.overrideMimeType('text/plain; charset=x-user-defined');
    }
    request.send();
    return {status: request.status, text: request.responseText};
  }

  // The game's filesystem is only memory, and empties when the page closes.
  // The saves folder (save files, settings, records) is kept in the browser's
  // IndexedDB instead: restore puts it back before the engine starts, and from
  // then on each file written or removed there is written to IndexedDB as soon
  // as the engine's frame hands the page back. Each game keeps its own, by its
  // game_nid, so that a new upload of the game, at another address, keeps the
  // saves of the last. Two games with the same game_nid on one site share them
  const SAVES_DATABASE = 'lex-talionis saves ';
  // Once restored: the saves folder, the game's nid, and the database keeping
  // the folder (null without IndexedDB)
  let savesFolder = null, savesGameNid = null, savesDatabase = null;
  window.__ltSaves = {
    ready: false,
    restore(folder, gameNid) {
      savesFolder = folder;
      savesGameNid = gameNid;
      const opened = new Promise((resolve, reject) => {
        const request = indexedDB.open(SAVES_DATABASE + gameNid, 1);
        request.onupgradeneeded = () => request.result.createObjectStore('files');
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
      });
      opened.then((database) => new Promise((resolve, reject) => {
        const store = database.transaction('files').objectStore('files');
        const names = store.getAllKeys();
        const files = store.getAll();
        files.onsuccess = () => {
          names.result.forEach((name, i) => python.FS.writeFile(folder + '/' + name, files.result[i]));
          console.log('LTSAVES restored', names.result.length, 'files');
          resolve(database);
        };
        files.onerror = () => reject(files.error);
      })).then((database) => {
        savesDatabase = database;
        const written = new Map(savedFiles(folder));
        const look = () => {
          const now = new Map(savedFiles(folder));
          const changed = [...now].filter(([name, stamp]) => written.get(name) !== stamp).map(([name]) => name);
          const removed = [...written.keys()].filter((name) => !now.has(name));
          if (!changed.length && !removed.length) return;
          const transaction = database.transaction('files', 'readwrite');
          const store = transaction.objectStore('files');
          for (const name of changed) store.put(python.FS.readFile(folder + '/' + name), name);
          for (const name of removed) store.delete(name);
          // Taken as written now; a failed write forgets them, to try again at the next look
          for (const name of changed) written.set(name, now.get(name));
          for (const name of removed) written.delete(name);
          transaction.onerror = () => {
            console.warn('LTSAVES could not write', changed, removed, transaction.error);
            for (const name of changed.concat(removed)) written.set(name, null);
          };
        };
        // Each file closed, removed or renamed in the folder calls for a look.
        // The engine's frame holds the page, so the look comes after it, once
        // for however many files the frame wrote
        let looking = false;
        const inFolder = (path) => typeof path === 'string' && path.startsWith(folder + '/');
        const after = (name, pathsOf) => {
          const original = python.FS[name];
          python.FS[name] = function (...args) {
            const result = original.apply(this, args);
            if (!looking && pathsOf(...args).some(inFolder)) {
              looking = true;
              setTimeout(() => { looking = false; look(); }, 0);
            }
            return result;
          };
        };
        after('close', (stream) => [stream.path]);
        after('unlink', (path) => [path]);
        after('rename', (oldPath, newPath) => [oldPath, newPath]);
        // Asks the browser not to clear them when it runs short of space
        if (navigator.storage && navigator.storage.persist) {
          navigator.storage.persist().then((granted) => console.log('LTSAVES kept for good:', granted));
        }
      }).catch((error) => {
        console.warn('LTSAVES no IndexedDB, so saves last only until the page closes:', error);
      }).finally(() => { window.__ltSaves.ready = true; });
    },
    // Adds the SAVES button, for the game's files: those starting with its nid and a dash
    offer(title) {
      savesButton(savesGameNid + '-', title);
    },
  };
  // Each file in the folder, with when it last changed and its size
  function savedFiles(folder) {
    return python.FS.readdir(folder).filter((name) => name !== '.' && name !== '..').map((name) => {
      const stat = python.FS.stat(folder + '/' + name);
      return python.FS.isFile(stat.mode) ? [name, +stat.mtime + ':' + stat.size] : null;
    }).filter(Boolean);
  }

  // The SAVES button opens a panel that exports the game's saves and the
  // player's settings as a zip of their files in the saves folder, named as a
  // desktop copy of the game names them in its own, and imports such a zip.
  // The game's own files are those starting with prefix
  function savesButton(prefix, title) {
    const carried = (name) => name.startsWith(prefix) || name === SETTINGS_FILE;
    const pad = document.getElementById('lt-pad');
    const button = document.createElement('div');
    button.id = 'lt-saves';
    button.textContent = 'SAVES';
    (pad || document.body).appendChild(button);
    const panel = document.createElement('div');
    panel.id = 'lt-saves-panel';
    panel.innerHTML = `
      <div class="box">
        <h2>Saves</h2>
        <p>This browser keeps your saves and settings, but it may clear them. Export a copy to keep
           them safe, or to carry them to another device. A desktop copy of the game takes the same
           files in its saves folder.</p>
        <div class="choices">
          <button class="export">Export</button><button class="import">Import</button><button class="close">Close</button>
        </div>
        <p class="status"></p>
        <input type="file" accept=".zip,application/zip" hidden>
      </div>`;
    document.body.appendChild(panel);
    const status = panel.querySelector('.status');
    const input = panel.querySelector('input');
    const show = (shown) => {
      panel.style.display = shown ? 'flex' : 'none';
      status.textContent = '';
    };
    button.addEventListener('click', () => show(true));
    panel.querySelector('.close').addEventListener('click', () => show(false));

    panel.querySelector('.export').addEventListener('click', () => {
      const names = savedFiles(savesFolder).map(([name]) => name).filter(carried);
      if (!names.some((name) => name.startsWith(prefix))) {
        status.textContent = 'There are no saves yet.';
        return;
      }
      const zip = makeZip(names.map((name) => {
        const path = savesFolder + '/' + name;
        const data = python.FS.readFile(path);
        return [name, name === SETTINGS_FILE ? settings(data, false) : data, python.FS.stat(path).mtime];
      }));
      const fileName = (title + ' saves ' + new Date().toISOString().slice(0, 10) + '.zip').replace(/[\\/:*?"<>|]/g, '');
      offerFile(new File([zip], fileName, {type: 'application/zip'}));
      status.textContent = 'Exported ' + names.length + ' files.';
    });

    panel.querySelector('.import').addEventListener('click', () => input.click());
    input.addEventListener('change', () => {
      const file = input.files[0];
      input.value = '';
      if (!file) return;
      status.textContent = 'Reading ' + file.name + '...';
      file.arrayBuffer().then((data) => readZip(data, carried)).then((files) => {
        if (!files.some(([name]) => name.startsWith(prefix))) throw new Error('it holds no saves for ' + title);
        files = files.map(([name, data]) => [name, name === SETTINGS_FILE ? withThisDevice(data) : data]);
        if (!savesDatabase) throw new Error('this browser is not keeping saves');
        const replaced = files.some(([name]) => name === SETTINGS_FILE) ? 'Saves with the same names, and your settings, are replaced'
                                                                         : 'Saves with the same names are replaced';
        if (!confirm('Import ' + files.length + ' files? ' + replaced + ', and the game starts again.')) {
          status.textContent = '';
          return;
        }
        // The engine reads the records and settings only as it starts
        return keepFiles(files).then(() => {
          window.onbeforeunload = null;
          location.reload();
        });
      }).catch((error) => {
        console.warn('LTSAVES', error);
        status.textContent = 'Could not import ' + file.name + ': ' + error.message + '.';
      });
    });
  }

  // The player's settings (app/engine/config.py), one key=value a line. Those
  // for the device the game runs on stay with it: a zip's settings neither
  // carry them nor replace this device's
  const SETTINGS_FILE = 'config.ini';
  const DEVICE_SETTINGS = ['screen_size', 'fullscreen', 'sound_buffer_size', 'mouse'];
  // The lines of the settings for the device, or the others
  function settings(data, forDevice) {
    const lines = new TextDecoder().decode(data).split('\n').filter((line) => line.includes('='));
    const kept = lines.filter((line) => DEVICE_SETTINGS.includes(line.split('=')[0]) === forDevice);
    return new TextEncoder().encode(kept.map((line) => line + '\n').join(''));
  }
  // A zip's settings, with this device's own in place of any it has
  function withThisDevice(data) {
    const path = savesFolder + '/' + SETTINGS_FILE;
    const device = python.FS.analyzePath(path).exists ? settings(python.FS.readFile(path), true) : new Uint8Array();
    return new Uint8Array([...settings(data, false), ...device]);
  }

  // Into the saves folder and the database at once, so that the next look
  // does not put back what the folder held before
  function keepFiles(files) {
    return new Promise((resolve, reject) => {
      const transaction = savesDatabase.transaction('files', 'readwrite');
      const store = transaction.objectStore('files');
      for (const [name, data] of files) {
        python.FS.writeFile(savesFolder + '/' + name, data);
        store.put(data, name);
      }
      transaction.oncomplete = resolve;
      transaction.onerror = () => reject(transaction.error);
    });
  }

  // On a touch screen, the share sheet, which has Save to Files on an iPhone;
  // a download otherwise
  function offerFile(file) {
    if (matchMedia('(pointer: coarse)').matches && navigator.canShare && navigator.canShare({files: [file]})) {
      navigator.share({files: [file]}).catch((error) => { if (error.name !== 'AbortError') download(file); });
    } else {
      download(file);
    }
  }
  function download(file) {
    const link = document.createElement('a');
    link.href = URL.createObjectURL(file);
    link.download = file.name;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(link.href), 60000);
  }

  const CRC_TABLE = new Uint32Array(256).map((_, n) => {
    for (let k = 0; k < 8; k++) n = n & 1 ? 0xedb88320 ^ (n >>> 1) : n >>> 1;
    return n;
  });
  function crc32(data) {
    let crc = 0xffffffff;
    for (let i = 0; i < data.length; i++) crc = CRC_TABLE[(crc ^ data[i]) & 0xff] ^ (crc >>> 8);
    return (crc ^ 0xffffffff) >>> 0;
  }

  // A zip holding the files as they are, uncompressed, from [name, data, last changed]
  function makeZip(files) {
    const encoder = new TextEncoder();
    const entries = [], directory = [];
    let offset = 0;
    for (const [name, data, changed] of files) {
      const nameBytes = encoder.encode(name);
      const date = new Date(changed);
      const time = (date.getHours() << 11) | (date.getMinutes() << 5) | (date.getSeconds() >> 1);
      const day = ((date.getFullYear() - 1980) << 9) | ((date.getMonth() + 1) << 5) | date.getDate();
      const crc = crc32(data);
      // Each header: signature, version needed, names in UTF-8, stored, time, day, crc, sizes, name length
      const header = new DataView(new ArrayBuffer(30));
      [[0, 0x04034b50, 4], [4, 20, 2], [6, 0x0800, 2], [8, 0, 2], [10, time, 2], [12, day, 2],
       [14, crc, 4], [18, data.length, 4], [22, data.length, 4], [26, nameBytes.length, 2]].forEach(write(header));
      const listing = new DataView(new ArrayBuffer(46));
      [[0, 0x02014b50, 4], [4, 20, 2], [6, 20, 2], [8, 0x0800, 2], [10, 0, 2], [12, time, 2], [14, day, 2],
       [16, crc, 4], [20, data.length, 4], [24, data.length, 4], [28, nameBytes.length, 2], [42, offset, 4]].forEach(write(listing));
      entries.push(header, nameBytes, data);
      directory.push(listing, nameBytes);
      offset += 30 + nameBytes.length + data.length;
    }
    const directorySize = directory.reduce((sum, part) => sum + part.byteLength, 0);
    const end = new DataView(new ArrayBuffer(22));
    [[0, 0x06054b50, 4], [8, files.length, 2], [10, files.length, 2], [12, directorySize, 4], [16, offset, 4]].forEach(write(end));
    return new Blob([...entries, ...directory, end]);
  }
  const write = (view) => ([at, value, size]) => size === 4 ? view.setUint32(at, value, true) : view.setUint16(at, value, true);

  // The files in a zip that wanted takes, by name without the folders the zip
  // has them in, as [name, data]. Stored or deflated, as zips usually are
  function readZip(buffer, wanted) {
    const view = new DataView(buffer);
    const bytes = new Uint8Array(buffer);
    let end = buffer.byteLength - 22;
    while (end >= 0 && view.getUint32(end, true) !== 0x06054b50) end--;
    if (end < 0) return Promise.reject(new Error('it is not a zip file'));
    const decoder = new TextDecoder();
    const reads = [];
    let at = view.getUint32(end + 16, true);
    for (let i = view.getUint16(end + 10, true); i > 0; i--) {
      if (view.getUint32(at, true) !== 0x02014b50) return Promise.reject(new Error('its list of files is damaged'));
      const method = view.getUint16(at + 10, true);
      const crc = view.getUint32(at + 16, true);
      const size = view.getUint32(at + 20, true);
      const nameLength = view.getUint16(at + 28, true);
      const path = decoder.decode(bytes.subarray(at + 46, at + 46 + nameLength));
      const local = view.getUint32(at + 42, true);
      at += 46 + nameLength + view.getUint16(at + 30, true) + view.getUint16(at + 32, true);
      const name = path.split(/[\\/]/).pop();
      if (!name || path.startsWith('__MACOSX/') || !wanted(name)) continue;
      const start = local + 30 + view.getUint16(local + 26, true) + view.getUint16(local + 28, true);
      reads.push(unpack(method, bytes.slice(start, start + size)).then((data) => {
        if (crc32(data) !== crc) throw new Error(name + ' in it is damaged');
        return [name, data];
      }));
    }
    return Promise.all(reads);
  }
  function unpack(method, packed) {
    if (method === 0) return Promise.resolve(packed);
    if (method === 8 && typeof DecompressionStream !== 'undefined') {
      const stream = new Blob([packed]).stream().pipeThrough(new DecompressionStream('deflate-raw'));
      return new Response(stream).arrayBuffer().then((data) => new Uint8Array(data));
    }
    return Promise.reject(new Error('this browser cannot unpack how it is compressed'));
  }

  // The game's screen, drawn from SDL's canvas, at the game's own size, onto
  // one the size of the window. Each game pixel becomes a block of the same
  // whole number of screen pixels, and only the fraction left over is blended
  // at the blocks' edges ("sharp bilinear"), so no pixel comes out wider than
  // its neighbours, as plain scaling to a size not a whole multiple does
  const VERTEX = `
    attribute vec2 corner;
    varying vec2 uv;
    void main() {
      uv = vec2(corner.x + 1.0, 1.0 - corner.y) * 0.5;
      gl_Position = vec4(corner, 0.0, 1.0);
    }`;
  const FRAGMENT = `
    precision highp float;
    uniform sampler2D game;
    uniform vec2 gameSize;
    uniform vec2 screenSize;
    varying vec2 uv;
    void main() {
      vec2 texel = uv * gameSize;
      vec2 scale = max(floor(screenSize / gameSize), vec2(1.0));
      vec2 sharp = 0.5 - 0.5 / scale;
      vec2 off = fract(texel) - 0.5;
      vec2 blend = (off - clamp(off, -sharp, sharp)) * scale + 0.5;
      gl_FragColor = texture2D(game, (floor(texel) + blend) / gameSize);
    }`;

  // Returns the canvas it draws on, or null where the browser has no WebGL or
  // can't build the shaders. The browser may take the canvas's WebGL away
  // while the page runs, as iOS does to a page in the background short of
  // memory; screen.drawing() is false until it gives it back, and changed is
  // called each time that turns, for SDL's own canvas to be shown meanwhile
  function startScreen(source, changed) {
    const screen = document.createElement('canvas');
    screen.id = 'lt-screen';
    const gl = screen.getContext('webgl', {alpha: false, antialias: false});
    if (!gl) return null;
    // The shaders' sizes, once WebGL is set up, or null if it could not be
    const setUp = () => {
      const compile = (type, text) => {
        const shader = gl.createShader(type);
        gl.shaderSource(shader, text);
        gl.compileShader(shader);
        return shader;
      };
      const program = gl.createProgram();
      gl.attachShader(program, compile(gl.VERTEX_SHADER, VERTEX));
      gl.attachShader(program, compile(gl.FRAGMENT_SHADER, FRAGMENT));
      gl.linkProgram(program);
      if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
        console.warn('LTSCREEN could not build the shaders:', gl.getProgramInfoLog(program));
        return null;
      }
      gl.useProgram(program);
      gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
      const corner = gl.getAttribLocation(program, 'corner');
      gl.enableVertexAttribArray(corner);
      gl.vertexAttribPointer(corner, 2, gl.FLOAT, false, 0, 0);
      gl.bindTexture(gl.TEXTURE_2D, gl.createTexture());
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      return {gameSize: gl.getUniformLocation(program, 'gameSize'),
              screenSize: gl.getUniformLocation(program, 'screenSize')};
    };
    let sizes = setUp();
    if (!sizes) return null;
    screen.drawing = () => sizes !== null;
    screen.addEventListener('webglcontextlost', (event) => {
      // Without this the browser never gives it back
      event.preventDefault();
      sizes = null;
      console.warn('LTSCREEN lost WebGL; showing the game unfiltered until it is back');
      changed();
    });
    screen.addEventListener('webglcontextrestored', () => {
      sizes = setUp();
      changed();
    });
    const draw = () => {
      if (sizes && source.width > 1) {
        gl.viewport(0, 0, screen.width, screen.height);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, source);
        gl.uniform2f(sizes.gameSize, source.width, source.height);
        gl.uniform2f(sizes.screenSize, screen.width, screen.height);
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      }
      requestAnimationFrame(draw);
    };
    requestAnimationFrame(draw);
    document.body.appendChild(screen);
    return screen;
  }

  // showPad: whether to draw the buttons. ratio: the game's width over its
  // height. integer: whether to show the game only at whole multiples of its
  // size, leaving a border, rather than filling the window
  window.__ltSetupPage = (showPad, ratio, integer) => {
    keepSoundGoing();
    const canvas = document.getElementById('canvas');
    // pygbag would otherwise size the canvas to half the window
    window.config.user_canvas_managed = 1;
    document.body.style.background = BACKGROUND;
    const style = document.createElement('style');
    style.textContent = STYLE;
    document.head.appendChild(style);
    // Room for one logo in portrait, below the game and its buttons, and one on
    // each side of it in landscape
    const logos = [0, 1].map(() => {
      const logo = document.createElement('img');
      logo.className = 'lt-logo';
      logo.src = 'lt_logo.png';
      document.body.appendChild(logo);
      return logo;
    });
    const pad = showPad ? buildPad() : null;
    // SDL's canvas stays where the screen is, unseen while the screen draws, to take the mouse
    const screen = startScreen(canvas, () => layout());

    // How far in from each edge of the window the phone's notch, status bar
    // and home bar reach (the page draws under them, viewport-fit=cover)
    const safeArea = document.createElement('div');
    safeArea.style.cssText = 'position: fixed; visibility: hidden; pointer-events: none; padding: ' +
      'env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left);';
    document.body.appendChild(safeArea);
    const insets = () => {
      const style = getComputedStyle(safeArea);
      return {top: parseFloat(style.paddingTop) || 0, right: parseFloat(style.paddingRight) || 0,
              bottom: parseFloat(style.paddingBottom) || 0, left: parseFloat(style.paddingLeft) || 0};
    };

    // The game as large as the window allows, keeping its shape, clear of the
    // notch, status bar and home bar. Held to the top in portrait with the
    // buttons below it; centred otherwise, with the buttons either side
    const layout = () => {
      const width = window.innerWidth, height = window.innerHeight, dpr = window.devicePixelRatio || 1;
      const portrait = height > width;
      const inset = insets();
      const room = {width: width - inset.left - inset.right, height: height - inset.top - inset.bottom};
      let w, h;
      if (integer) {
        const scale = Math.max(1, Math.floor(Math.min(room.width * dpr / ratio, room.height * dpr) / (canvas.height || 160)));
        h = Math.round(scale * (canvas.height || 160) / dpr);
        w = Math.round(h * ratio);
      } else {
        // Whole pixels, which the style reads back exactly as written
        w = room.width; h = Math.round(room.width / ratio);
        if (h > room.height) { h = room.height; w = Math.round(room.height * ratio); }
      }
      const left = inset.left + Math.round((room.width - w) / 2);
      const top = inset.top + (pad && portrait ? 0 : Math.round((room.height - h) / 2));
      const drawing = screen !== null && screen.drawing();
      const wanted = {
        position: 'absolute', margin: '0px', right: 'auto', bottom: 'auto',
        width: w + 'px', height: h + 'px', left: left + 'px', top: top + 'px',
        opacity: drawing ? '0' : '1',
      };
      // Only on a change, as a change calls this again (below)
      for (const [property, value] of Object.entries(wanted)) {
        if (canvas.style[property] !== value) canvas.style[property] = value;
      }
      if (screen) {
        Object.assign(screen.style, {width: wanted.width, height: wanted.height, left: wanted.left, top: wanted.top,
                                     visibility: drawing ? 'visible' : 'hidden'});
        // Setting its size clears it, so only on a change
        if (screen.width !== Math.round(w * dpr)) screen.width = Math.round(w * dpr);
        if (screen.height !== Math.round(h * dpr)) screen.height = Math.round(h * dpr);
      }
      if (pad) {
        pad.className = portrait ? 'portrait' : 'landscape';
        pad.style.top = portrait ? (top + h) + 'px' : '0';
      }
      placeLogos(width, height, portrait, w, h, left, top);
    };

    // A logo where there is room for one at least 64 pixels across: under the
    // game and its buttons in portrait, and either side of it in landscape,
    // between L or R and the buttons below them
    const place = (logo, centreX, centreY, size, opacity) => {
      if (size < 64) { logo.style.display = 'none'; return; }
      Object.assign(logo.style, {
        display: 'block', width: size + 'px', height: size + 'px', opacity: String(opacity),
        left: Math.round(centreX - size / 2) + 'px', top: Math.round(centreY - size / 2) + 'px',
      });
    };
    const placeLogos = (width, height, portrait, w, h, left, top) => {
      if (portrait) {
        // The portrait buttons reach 266 pixels below the game
        const below = top + h + (pad ? 280 : 0);
        place(logos[0], width / 2, (below + height) / 2, Math.min(height - below - 24, width * 0.55, 260), 0.9);
        place(logos[1], 0, 0, 0, 0);
      } else {
        const [leftSide, rightSide] = [left, width - left - w];
        // Below L and R (46 pixels down), above the D-pad (178 up from the bottom)
        // and A (158 up), on both sides alike
        const [above, below] = pad ? [46, height - 178] : [0, height];
        const size = Math.min(Math.min(leftSide, rightSide) - 16, below - above - 16, 260);
        const centreY = (above + below) / 2;
        place(logos[0], leftSide / 2, centreY, size, pad ? 0.85 : 0.6);
        place(logos[1], width - rightSide / 2, centreY, size, pad ? 0.85 : 0.6);
      }
    };
    window.addEventListener('resize', layout);
    // On a phone, the window's size and the notch's place settle a moment after a turn
    window.addEventListener('orientationchange', () => setTimeout(layout, 250));
    // pygbag places the canvas itself on timers set before this ran, and the
    // engine sizes it when it opens its display; put it back
    new MutationObserver(layout).observe(canvas, {attributes: true, attributeFilter: ['style', 'width', 'height']});
    layout();
    return showPad;
  };

  // The game's title, for the browser's tab and the name it takes on a home screen
  window.__ltSetTitle = (title) => {
    document.title = title;
    const name = document.createElement('meta');
    name.name = 'apple-mobile-web-app-title';
    name.content = title;
    document.head.appendChild(name);
  };
})();
