'''
Serves a browser build to a device on the local network, and writes down what
the page reports back (?report in its address, see main.py), for a phone
whose browser can't be inspected from this machine.

    python utilities/build_tools/web/serve.py <build_dir> <address> [port] [--log <file>]

address is the one network address to listen on, such as Windows Mobile
Hotspot's (192.168.137.1), so that nothing else on another network can reach
it. Each report is printed and, with --log, appended to the file
'''
import functools
import re
import sys
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

class Handler(SimpleHTTPRequestHandler):
    log_path: Path = None

    def do_POST(self):
        if self.path != '/report':
            self.send_error(404)
            return
        length = int(self.headers.get('Content-Length', 0))
        text = self.rfile.read(length).decode('utf-8', 'replace')
        stamp = time.strftime('%H:%M:%S')
        lines = ['%s %s' % (stamp, line) for line in text.splitlines()]
        print('\n'.join(lines), flush=True)
        if self.log_path:
            with self.log_path.open('a', encoding='utf-8') as log:
                log.write('\n'.join(lines) + '\n')
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        # The page fetches a file the game wants at once as a range of the
        # bundle holding it (page.js), which SimpleHTTPRequestHandler would
        # answer with the whole bundle
        wanted = re.fullmatch(r'bytes=(\d+)-(\d+)', self.headers.get('Range', ''))
        path = Path(self.translate_path(self.path))
        if not wanted or not path.is_file():
            super().do_GET()
            return
        size = path.stat().st_size
        start, end = int(wanted[1]), min(int(wanted[2]), size - 1)
        if start > end:
            self.send_response(416)
            self.send_header('Content-Range', 'bytes */%d' % size)
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        with path.open('rb') as file:
            file.seek(start)
            data = file.read(end - start + 1)
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(str(path)))
        self.send_header('Content-Range', 'bytes %d-%d/%d' % (start, end, size))
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def end_headers(self):
        # A browser otherwise goes on using what it fetched before for a while,
        # guessing from when the file last changed, and a new build goes unseen
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def log_message(self, format, *args):
        # Only the reports, not every file fetched
        pass

def main(args: list[str]):
    if '--log' in args:
        at = args.index('--log')
        Handler.log_path = Path(args[at + 1])
        args = args[:at] + args[at + 2:]
    build_dir, address = args[0], args[1]
    port = int(args[2]) if len(args) > 2 else 8000
    server = ThreadingHTTPServer((address, port), functools.partial(Handler, directory=build_dir))
    print('Serving %s on http://%s:%d/' % (build_dir, address, port), flush=True)
    server.serve_forever()

if __name__ == '__main__':
    main(sys.argv[1:])
