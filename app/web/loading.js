// Shows how far the game has loaded, from the moment the page opens until the
// title screen, over a screen of its own. It also fetches the game's archive
// as the page opens, alongside pygbag's Python rather than after it.
// web_export.py puts this file in the page's head, after
// window.__ltLoadingConfig = {archive: 'game.apk', size: <its bytes>}.
// Once Python runs, the page's template waits for the archive (archiveReady),
// takes it (putArchive) and unpacks it (progress, unpacked), and main.py names each step
// of loading it finishes (step), and any error that stops the game (failed)
(() => {
  const {archive, size} = window.__ltLoadingConfig;
  const BACKGROUND = 'radial-gradient(ellipse at center, #1d2856 0%, #151d40 55%, #0d1230 100%)';
  // Each step of loading in order: the step that ends it, what the page says
  // meanwhile, its share of the bar, and about how long it takes on a phone,
  // in seconds. 'downloaded' is this file's own, 'unpacking' and 'unpacked'
  // the template's, and the rest main.py's. Python starts while the archive
  // downloads, and on a phone takes most of the time (10 to 12 seconds on an
  // iPhone, nearly all of it compiling and starting Python, not fetching it),
  // so a slow download leaves no time to its step. The two steps that can say
  // how far along they are take no time here
  const STEPS = [
    ['downloaded', 'Downloading', 0.25, 0],
    ['unpacking', 'Starting Python', 0.5, 6],
    ['unpacked', 'Unpacking', 0.05, 0],
    ['engine imported', 'Starting the engine', 0.07, 0.5],
    ['database loaded', 'Loading the game', 0.07, 0.6],
    ['game started', 'Starting the game', 0.06, 0.6],
  ];
  // Above all of pygbag's page, its own "Loading, please wait" too. While
  // Python holds the page, nothing here can move but the shine across the bar,
  // which the browser draws apart from the page, to show it hasn't stopped
  const STYLE = `
    #lt-loading { position: fixed; left: 0; top: 0; right: 0; bottom: 0; z-index: 1000000; background: ${BACKGROUND};
                  display: flex; flex-direction: column; align-items: center; justify-content: center;
                  gap: 22px; font-family: sans-serif; color: #fff07a; transition: opacity 0.4s; }
    #lt-loading img { max-width: 60vw; max-height: 32vh; }
    #lt-loading .bar { position: relative; overflow: hidden; width: min(70vw, 420px); height: 14px; padding: 2px;
                       border: 2px solid rgba(255, 236, 110, 0.6); border-radius: 9px; box-sizing: content-box; }
    #lt-loading .bar::after { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 30%;
                              background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
                              will-change: transform; animation: lt-shine 1.6s linear infinite; }
    @keyframes lt-shine { from { transform: translateX(-100%); } to { transform: translateX(340%); } }
    #lt-loading .fill { width: 0; height: 100%; border-radius: 7px; background: #fff07a; transition: width 0.25s; }
    #lt-loading .label { font-size: 15px; min-height: 1.2em; text-align: center; max-width: 90vw; }
    #lt-loading.failed .bar::after { display: none; }
    #lt-loading.failed .label { color: #ff9b8a; white-space: pre-wrap; }`;

  let current = 0;  // Index in STEPS of the step under way
  let began = performance.now();  // When it started
  let partial = null;  // How far along it is, from 0 to 1, when it can say
  let received = 0;
  let data = null;
  let error = '';
  let screen = null;
  // When this file's steps happened, as main.py notes its own (LTLOAD), for
  // main.py's ?report to send on, as it starts only once main.py runs
  const noted = [];
  const note = (step) => {
    noted.push('LTLOAD ' + step.padEnd(20) + ' ' + performance.now().toFixed(0).padStart(6) + ' ms');
    console.log(noted[noted.length - 1]);
  };

  function build() {
    const style = document.createElement('style');
    style.textContent = STYLE;
    document.head.appendChild(style);
    screen = document.createElement('div');
    screen.id = 'lt-loading';
    screen.innerHTML = '<img src="lt_logo.png" alt=""><div class="bar"><div class="fill"></div></div><div class="label"></div>';
    document.body.appendChild(screen);
    note('loading screen up');
    draw();
  }

  function draw() {
    if (!screen || error) return;
    if (current >= STEPS.length) return;
    const total = STEPS.reduce((sum, step) => sum + step[2], 0);
    let done = STEPS.slice(0, current).reduce((sum, step) => sum + step[2], 0);
    const seconds = (performance.now() - began) / 1000;
    // A step that can't say how far along it is fills its share of the bar
    // ever more slowly, about two thirds of it in the time it takes
    const takes = STEPS[current][3];
    let along = partial;
    if (along === null) along = takes ? 1 - Math.exp(-seconds / takes) : 0;
    done += STEPS[current][2] * Math.min(along, 1);
    screen.querySelector('.fill').style.width = (100 * done / total).toFixed(1) + '%';
    let label = STEPS[current][1];
    if (STEPS[current][0] === 'downloaded') label += ' ' + megabytes(received) + ' / ' + megabytes(size) + ' MB';
    screen.querySelector('.label').textContent = label;
  }

  const megabytes = (bytes) => (bytes / 2 ** 20).toFixed(1);

  // Moves on to the step after the one named, when it is one of STEPS'
  function reach(name) {
    const index = STEPS.findIndex((step) => step[0] === name);
    if (index < current) return;
    current = index + 1;
    began = performance.now();
    partial = null;
    if (current === STEPS.length && screen) {
      screen.style.opacity = '0';
      setTimeout(() => { screen.remove(); screen = null; }, 400);
    }
    draw();
  }

  function failed(message) {
    error = message;
    if (!screen) build();
    screen.style.opacity = '1';
    screen.classList.add('failed');
    screen.querySelector('.label').textContent = 'The game could not go on:\n' + message;
  }

  // Fetches the archive into one array, as large as the build said it is
  fetch(archive).then(async (response) => {
    if (!response.ok) throw new Error('the server answered ' + response.status + ' for ' + archive);
    const reader = response.body.getReader();
    const bytes = new Uint8Array(size);
    for (;;) {
      const {done, value} = await reader.read();
      if (done) break;
      if (received + value.length > size) throw new Error(archive + ' is larger than the page was built for');
      bytes.set(value, received);
      received += value.length;
      partial = received / size;
    }
    if (received !== size) throw new Error(archive + ' is smaller than the page was built for');
    data = bytes;
    note('archive downloaded');
    reach('downloaded');
  }).catch((reason) => failed('could not download the game: ' + reason.message));

  if (document.body) build();
  else document.addEventListener('DOMContentLoaded', build);
  setInterval(draw, 100);

  window.__ltLoading = {
    archiveReady: () => data !== null || error !== '',
    // Writes the archive into Python's filesystem at path, and lets go of it.
    // Returns why it could not, or '' once it has
    putArchive(path) {
      if (data === null) return error;
      note('python running');
      reach('unpacking');
      python.FS.writeFile(path, data);
      data = null;
      return '';
    },
    // How far along the step under way is, from 0 to 1
    progress(fraction) {
      partial = fraction;
      draw();
    },
    unpacked() {
      note('unpacked');
      reach('unpacked');
    },
    step: reach,
    failed: failed,
    noted: noted,
  };
})();
