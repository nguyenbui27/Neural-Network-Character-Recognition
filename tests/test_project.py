import base64
from http.server import ThreadingHTTPServer
import io
import json
from pathlib import Path
import sys
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import numpy as np
from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from preprocessing import preprocess
from engine import Engine, ARTIFACTS
from app import make_handler


class PreprocessingTests(unittest.TestCase):
    def make_image(self):
        image = Image.new('L', (280, 280))
        ImageDraw.Draw(image).line([(60, 20), (70, 180), (110, 220)], fill=255, width=15)
        return image

    def test_range_shape_center_and_polarity(self):
        image = self.make_image()
        output = preprocess(image)
        self.assertEqual(output.shape, (28, 28, 1))
        self.assertEqual(output.dtype, np.float32)
        self.assertGreater(output.max(), .9)
        self.assertGreaterEqual(output.min(), 0)
        self.assertLessEqual(output.max(), 1)
        yy, xx = np.indices((28, 28))
        mass = output[..., 0].sum()
        self.assertAlmostEqual(float((xx * output[..., 0]).sum() / mass), 13.5, delta=.6)
        self.assertAlmostEqual(float((yy * output[..., 0]).sum() / mass), 13.5, delta=.6)
        np.testing.assert_array_equal(output, preprocess(ImageOps.invert(image), dark_ink=True))

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            preprocess(Image.new('L', (280, 280)))

    def test_vertical_stroke_not_stretched(self):
        image = Image.new('L', (100, 100))
        ImageDraw.Draw(image).rectangle((40, 10, 43, 90), fill=255)
        y, x = np.nonzero(preprocess(image)[..., 0] > .2)
        self.assertLessEqual(x.max() - x.min(), 2)
        self.assertGreater(y.max() - y.min(), 15)


class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = Engine()
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(cls.engine))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def post(self, path, data, headers=None):
        request = Request(self.url + path, data=json.dumps(data).encode(),
                          headers={'Content-Type': 'application/json', **(headers or {})})
        return urlopen(request)

    def test_status_and_static_ui(self):
        with urlopen(self.url + '/api/status') as response:
            self.assertIn('history', json.load(response))
        with urlopen(self.url + '/') as response:
            self.assertIn(b'Recognized number', response.read())

    def test_invalid_training_does_not_start(self):
        for body in ({'epochs': 0}, {'epochs': True}, {'samples': 7999}):
            with self.assertRaises(HTTPError) as error:
                self.post('/api/train', body)
            self.assertEqual(error.exception.code, 400)

    def test_cross_origin_rejected(self):
        with self.assertRaises(HTTPError) as error:
            self.post('/api/train', {}, {'Origin': 'http://example.com'})
        self.assertEqual(error.exception.code, 403)

    def test_blank_image_rejected(self):
        stream = io.BytesIO()
        Image.new('RGB', (280, 280), 'white').save(stream, format='PNG')
        with self.assertRaises(HTTPError) as error:
            self.post('/api/predict', {'image': 'data:image/png;base64,' + base64.b64encode(stream.getvalue()).decode()})
        self.assertEqual(error.exception.code, 400)

    def test_saved_model_prediction_and_report(self):
        if not (ARTIFACTS / 'model.keras').exists():
            self.skipTest('Train a model first to exercise saved-model inference.')
        with np.load(ARTIFACTS / 'keras-cache/datasets/mnist.npz') as data:
            image = Image.fromarray(data['x_test'][0])
            label = int(data['y_test'][0])
        stream = io.BytesIO()
        ImageOps.invert(image).save(stream, format='PNG')
        with self.post('/api/predict', {'image': 'data:image/png;base64,' + base64.b64encode(stream.getvalue()).decode()}) as response:
            result = json.load(response)
        self.assertEqual(result['digit'], label)
        self.assertEqual(len(result['probabilities']), 10)
        self.assertAlmostEqual(sum(result['probabilities']), 1, places=5)
        report = self.engine.snapshot()['evaluation']
        self.assertEqual(report['test_samples'], 10000)
        self.assertGreaterEqual(report['train_samples'], 8000)
        self.assertEqual(sum(map(sum, report['confusion_matrix'])), 10000)


if __name__ == '__main__':
    unittest.main()
