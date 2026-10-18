// Sets up the page for the game: shows the game's screen as large as the
// window allows, keeps its sound going, keeps its saves, and on a touch screen
// draws the buttons a keyboard would give. main.py runs this file, then
// __ltSaves.restore, then __ltSetupPage once the engine is imported.
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

  // The files the build left out of the game's download (deferred.json lists
  // them, the soonest wanted first), fetched a few at a time into the game's
  // filesystem beside the rest, under root. The engine fetches any it opens
  // before they arrive itself, with fetchNow (app/engine/deferred_files.py)
  const DOWNLOADS_AT_ONCE = 4;
  window.__ltDeferred = {
    start(root) {
      fetch('deferred.json').then((response) => response.json()).then((paths) => {
        const next = () => {
          const path = paths.shift();
          if (path === undefined) return;
          fetch(url(path)).then((response) => {
            if (!response.ok) throw new Error(response.status + ' for ' + path);
            return response.arrayBuffer();
          }).then((data) => {
            const target = root + '/' + path;
            if (!python.FS.analyzePath(target).exists) python.FS.writeFile(target, new Uint8Array(data));
          }).catch((error) => console.warn('LTDEFERRED', error)).finally(next);
        };
        for (let i = 0; i < DOWNLOADS_AT_ONCE; i++) next();
      }).catch((error) => console.warn('LTDEFERRED no deferred.json', error));
    },
    // Holds the game until the file is in place, at target
    fetchNow(path, target) {
      const request = new XMLHttpRequest();
      request.open('GET', url(path), false);
      // A request that holds the page must take text; this keeps each byte as it is
      request.overrideMimeType('text/plain; charset=x-user-defined');
      request.send();
      if (request.status !== 200) {
        console.warn('LTDEFERRED', request.status, 'for', path);
        return;
      }
      const text = request.responseText;
      const data = new Uint8Array(text.length);
      for (let i = 0; i < text.length; i++) data[i] = text.charCodeAt(i) & 0xff;
      python.FS.writeFile(target, data);
      console.log('LTDEFERRED waited for', path);
    },
  };
  const url = (path) => 'deferred/' + path.split('/').map(encodeURIComponent).join('/');

  // The game's filesystem is only memory, and empties when the page closes.
  // The saves folder (save files, settings, records) is kept in the browser's
  // IndexedDB instead: restore puts it back before the engine starts, and from
  // then on each file written or removed there is written to IndexedDB at the
  // next look, every second and when the page is hidden. A page at another
  // address keeps its own
  const SAVES_LOOK_EVERY = 1000;  // ms
  const SAVES_DATABASE = 'lex-talionis saves ' + location.pathname;
  window.__ltSaves = {
    ready: false,
    restore(folder) {
      const opened = new Promise((resolve, reject) => {
        const request = indexedDB.open(SAVES_DATABASE, 1);
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
        setInterval(look, SAVES_LOOK_EVERY);
        document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') look(); });
        window.addEventListener('pagehide', look);
        // Asks the browser not to clear them when it runs short of space
        if (navigator.storage && navigator.storage.persist) {
          navigator.storage.persist().then((granted) => console.log('LTSAVES kept for good:', granted));
        }
      }).catch((error) => {
        console.warn('LTSAVES no IndexedDB, so saves last only until the page closes:', error);
      }).finally(() => { window.__ltSaves.ready = true; });
    },
  };
  // Each file in the folder, with when it last changed and its size
  function savedFiles(folder) {
    return python.FS.readdir(folder).filter((name) => name !== '.' && name !== '..').map((name) => {
      const stat = python.FS.stat(folder + '/' + name);
      return python.FS.isFile(stat.mode) ? [name, +stat.mtime + ':' + stat.size] : null;
    }).filter(Boolean);
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

  // Returns the canvas it draws on, or null where the browser has no WebGL
  function startScreen(source) {
    const screen = document.createElement('canvas');
    screen.id = 'lt-screen';
    const gl = screen.getContext('webgl', {alpha: false, antialias: false});
    if (!gl) return null;
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
    const gameSize = gl.getUniformLocation(program, 'gameSize');
    const screenSize = gl.getUniformLocation(program, 'screenSize');
    const draw = () => {
      if (source.width > 1) {
        gl.viewport(0, 0, screen.width, screen.height);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, source);
        gl.uniform2f(gameSize, source.width, source.height);
        gl.uniform2f(screenSize, screen.width, screen.height);
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
    const viewport = document.querySelector('meta[name=viewport]');
    viewport.setAttribute('content', 'width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover');
    // Added to the home screen, the page opens without Safari's bars, under this icon
    const statusBar = document.createElement('meta');
    statusBar.name = 'apple-mobile-web-app-status-bar-style';
    statusBar.content = 'black-translucent';
    document.head.appendChild(statusBar);
    const icon = document.createElement('link');
    icon.rel = 'apple-touch-icon';
    icon.href = 'apple-touch-icon.png';
    document.head.appendChild(icon);
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
    // SDL's canvas stays where the screen is, unseen, to take the mouse
    const screen = startScreen(canvas);

    // The game as large as the window allows, keeping its shape. Held to the
    // top in portrait with the buttons below it; centred otherwise, with the
    // buttons either side
    const layout = () => {
      const width = window.innerWidth, height = window.innerHeight, dpr = window.devicePixelRatio || 1;
      const portrait = height > width;
      let w, h;
      if (integer) {
        const scale = Math.max(1, Math.floor(Math.min(width * dpr / ratio, height * dpr) / (canvas.height || 160)));
        h = Math.round(scale * (canvas.height || 160) / dpr);
        w = Math.round(h * ratio);
      } else {
        // Whole pixels, which the style reads back exactly as written
        w = width; h = Math.round(width / ratio);
        if (h > height) { h = height; w = Math.round(height * ratio); }
      }
      const wanted = {
        position: 'absolute', margin: '0px', right: 'auto', bottom: 'auto',
        width: w + 'px', height: h + 'px',
        left: Math.round((width - w) / 2) + 'px', top: (pad && portrait ? 0 : Math.round((height - h) / 2)) + 'px',
        opacity: screen ? '0' : '1',
      };
      // Only on a change, as a change calls this again (below)
      for (const [property, value] of Object.entries(wanted)) {
        if (canvas.style[property] !== value) canvas.style[property] = value;
      }
      if (screen) {
        Object.assign(screen.style, {width: wanted.width, height: wanted.height, left: wanted.left, top: wanted.top});
        // Setting its size clears it, so only on a change
        if (screen.width !== Math.round(w * dpr)) screen.width = Math.round(w * dpr);
        if (screen.height !== Math.round(h * dpr)) screen.height = Math.round(h * dpr);
      }
      if (pad) {
        pad.className = portrait ? 'portrait' : 'landscape';
        pad.style.top = portrait ? h + 'px' : '0';
      }
      placeLogos(width, height, portrait, w, h, parseInt(wanted.top));
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
    const placeLogos = (width, height, portrait, w, h, top) => {
      if (portrait) {
        // The portrait buttons reach 266 pixels below the game
        const below = top + h + (pad ? 280 : 0);
        place(logos[0], width / 2, (below + height) / 2, Math.min(height - below - 24, width * 0.55, 260), 0.9);
        place(logos[1], 0, 0, 0, 0);
      } else {
        const side = (width - w) / 2;
        // Below L and R (46 pixels down), above the D-pad (178 up from the bottom)
        // and A (158 up), on both sides alike
        const [above, below] = pad ? [46, height - 178] : [0, height];
        const size = Math.min(side - 16, below - above - 16, 260);
        const centreY = (above + below) / 2;
        place(logos[0], side / 2, centreY, size, pad ? 0.85 : 0.6);
        place(logos[1], width - side / 2, centreY, size, pad ? 0.85 : 0.6);
      }
    };
    window.addEventListener('resize', layout);
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
