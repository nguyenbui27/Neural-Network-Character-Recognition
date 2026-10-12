"""Export the trained CNN as float32 weights for dependency-free browser inference."""
import json
from pathlib import Path
import numpy as np
from engine import Engine
from preprocessing import preprocess_batch

root = Path(__file__).resolve().parent
model = Engine().model
if model is None:
    raise SystemExit('Train the model with engine.py first.')
layers, offset, chunks = [], 0, []
for layer in model.layers:
    name = type(layer).__name__
    if name == 'Dropout':
        continue
    entry = {'type': name, 'config': layer.get_config(), 'weights': []}
    for weight in layer.get_weights():
        weight = np.asarray(weight, dtype='<f4')
        entry['weights'].append({'offset': offset, 'size': weight.size, 'shape': list(weight.shape)})
        chunks.append(weight.tobytes())
        offset += weight.size
    layers.append(entry)
(root / 'docs/model.json').write_text(json.dumps({'input': [28, 28, 1], 'layers': layers}))
(root / 'docs/weights.bin').write_bytes(b''.join(chunks))
with np.load(root / 'artifacts/keras-cache/datasets/mnist.npz') as data:
    # One reference image for each digit, preprocessed by the Python pipeline.
    ids = [int(np.flatnonzero(data['y_test'] == digit)[0]) for digit in range(10)]
    images = preprocess_batch(data['x_test'][ids])
expected = np.asarray(model(images, training=False))
(root / 'tests/browser-fixtures.json').write_text(json.dumps([
    {'input': image.ravel().tolist(), 'probabilities': probabilities.tolist()}
    for image, probabilities in zip(images, expected)
]))
print(f'Exported {offset:,} weights for {len(layers)} inference layers.')
