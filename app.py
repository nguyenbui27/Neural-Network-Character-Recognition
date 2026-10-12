"""Local browser interface for the TensorFlow handwriting recognizer."""
import argparse
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import webbrowser
import numpy as np
from PIL import Image
from engine import Engine
from preprocessing import preprocess

ROOT = Path(__file__).resolve().parent


def make_handler(engine):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            if self.path != '/api/status':
                super().log_message(format, *args)

        def send(self, status, value, content_type='application/json'):
            payload = json.dumps(value).encode() if content_type == 'application/json' else value
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(payload)

        def allowed(self):
            host = self.headers.get('Host', '')
            permitted = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            return host in permitted and self.headers.get('Origin', f'http://{host}') == f'http://{host}'

        def do_GET(self):
            if not self.allowed():
                return self.send(403, {'error': 'Use the local app URL.'})
            if self.path == '/api/status':
                return self.send(200, engine.snapshot())
            if self.path == '/api/report':
                return self.send(200, engine.snapshot()['evaluation'])
            files = {'/': ('index.html', 'text/html; charset=utf-8'),
                     '/app.js': ('app.js', 'text/javascript'), '/style.css': ('style.css', 'text/css')}
            if self.path not in files:
                return self.send(404, {'error': 'Not found'})
            name, mime = files[self.path]
            self.send(200, (ROOT / 'static' / name).read_bytes(), mime)

        def do_POST(self):
            if not self.allowed() or self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                return self.send(403, {'error': 'Local JSON requests only.'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 2_000_000:
                    raise ValueError('Request is too large or empty.')
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise ValueError('Expected a JSON object.')
                if self.path == '/api/train':
                    engine.start(body.get('epochs', 5), body.get('samples', 10000))
                    return self.send(202, {'message': 'Training started'})
                if self.path == '/api/stop':
                    engine.stop.set()
                    return self.send(200, {'message': 'Stop requested'})
                if self.path == '/api/predict':
                    encoded = body.get('image', '')
                    if not isinstance(encoded, str) or not encoded.startswith('data:image/png;base64,'):
                        raise ValueError('Expected a PNG canvas image.')
                    data = base64.b64decode(encoded.split(',', 1)[1], validate=True)
                    with Image.open(io.BytesIO(data)) as source:
                        if source.width * source.height > 1_000_000:
                            raise ValueError('Image dimensions are too large.')
                        image = preprocess(source, dark_ink=True)
                    prediction = engine.predict(image)
                    preview = Image.fromarray((image[..., 0] * 255).astype(np.uint8))
                    output = io.BytesIO()
                    preview.save(output, format='PNG')
                    prediction['preview'] = 'data:image/png;base64,' + base64.b64encode(output.getvalue()).decode()
                    return self.send(200, prediction)
                return self.send(404, {'error': 'Not found'})
            except (ValueError, TypeError, KeyError, OSError) as error:
                self.send(400, {'error': str(error)})
            except Exception as error:
                self.send(500, {'error': f'Prediction failed: {error}'})

    return Handler


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5050)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), make_handler(Engine()))
    url = f'http://127.0.0.1:{args.port}'
    print(f'Neural Network Character Recognition: {url}', flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
