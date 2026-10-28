#!/usr/bin/env python3
"""Loopback-only public Chrome fixture and bounded, numeric-only DOM receipts."""
import argparse
import http.server
import json
from pathlib import Path

HTML = Path(__file__).with_name('index.html').read_bytes()
NO_SUGGESTIONS = Path(__file__).with_name('no-suggestions.html').read_bytes()
FIELDS = {'length', 'words', 'corrections', 'lastCorrected', 'firstFive', 'undo',
          'sixth', 'literalFive', 'literalBackspace'}
FLAGS = FIELDS - {'length', 'words', 'corrections'}


class FixtureHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        payload = {'/rune-q8': HTML, '/rune-q8-no-suggestions': NO_SUGGESTIONS}.get(self.path)
        if payload is None:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        profile = {'/rune-q8-metrics/ordinary': 'ordinary',
                   '/rune-q8-metrics/no-suggestions': 'no-suggestions'}.get(self.path)
        if profile is None:
            self.send_error(404)
            return
        self.connection.settimeout(2)
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 512:
                raise ValueError('size')
            value = json.loads(self.rfile.read(size))
            if not isinstance(value, dict) or value.keys() != FIELDS:
                raise ValueError('fields')
            if any(type(v) is not int or not 0 <= v <= 512 for v in value.values()):
                raise ValueError('numbers')
            if any(value[k] not in (0, 1) for k in FLAGS):
                raise ValueError('flags')
        except (ValueError, TimeoutError, OSError):
            self.send_error(400)
            return
        if self.server.records >= 512:
            self.send_error(429)
            return
        self.server.receipt.write(json.dumps({'profile': profile, **value}, sort_keys=True) + '\n')
        self.server.receipt.flush()
        self.server.records += 1
        self.send_response(204)
        self.end_headers()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port-file', required=True, type=Path)
    parser.add_argument('--receipt-file', required=True, type=Path)
    args = parser.parse_args()
    # Exclusive handoffs avoid overwriting an earlier run's evidence.
    with args.receipt_file.open('x') as receipt:
        server = http.server.HTTPServer(('127.0.0.1', 0), FixtureHandler)
        server.receipt = receipt
        server.records = 0
        try:
            with args.port_file.open('x') as handoff:
                handoff.write(str(server.server_port) + '\n')
            server.serve_forever()
        finally:
            server.server_close()


if __name__ == '__main__':
    main()
