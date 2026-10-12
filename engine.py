"""CNN training, live callback metrics, and held-out model evaluation."""
import copy
import json
import os
from pathlib import Path
import threading
import time
import certifi

ROOT = Path(__file__).resolve().parent
os.environ.setdefault('KERAS_HOME', str(ROOT / 'artifacts' / 'keras-cache'))
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')
os.environ.setdefault('TF_NUM_INTRAOP_THREADS', '2')
os.environ.setdefault('TF_NUM_INTEROP_THREADS', '2')
os.environ.setdefault('SSL_CERT_FILE', certifi.where())
import numpy as np
import tensorflow as tf
from preprocessing import preprocess_batch

ARTIFACTS = ROOT / 'artifacts'
ARTIFACTS.mkdir(exist_ok=True)


class Engine:
    def __init__(self):
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.model = None
        self.state = {'status': 'idle', 'message': 'Ready to train your first model.',
                      'history': [], 'batch_progress': 0, 'epoch': 0,
                      'evaluation': None, 'model_ready': False}
        if (ARTIFACTS / 'model.keras').exists() and (ARTIFACTS / 'report.json').exists():
            self.model = tf.keras.models.load_model(ARTIFACTS / 'model.keras')
            report = json.loads((ARTIFACTS / 'report.json').read_text())
            self.state.update(status='complete', message='Saved model loaded.',
                              model_ready=True, evaluation=report, history=report['history'])

    def snapshot(self):
        with self.lock:
            return copy.deepcopy(self.state)

    def update(self, **values):
        with self.lock:
            self.state.update(values)

    def start(self, epochs=5, samples=10000):
        if isinstance(epochs, bool) or not isinstance(epochs, int) or not 1 <= epochs <= 20:
            raise ValueError('Epochs must be an integer between 1 and 20.')
        if isinstance(samples, bool) or not isinstance(samples, int) or not 8000 <= samples <= 50000:
            raise ValueError('Training samples must be between 8,000 and 50,000.')
        with self.lock:
            if self.state['status'] in ('loading', 'training', 'evaluating'):
                raise ValueError('A training run is already in progress.')
            self.stop.clear()
            self.state.update(status='loading', message='Loading MNIST and normalizing images…',
                              history=[], epoch=0, epochs=epochs, samples=samples, batch_progress=0,
                              batch_accuracy=None, batch_loss=None, run_evaluation=None)
        thread = threading.Thread(target=self.train, args=(epochs, samples), daemon=True)
        thread.start()
        return thread

    def train(self, epochs, samples):
        started = time.monotonic()
        owner = self
        try:
            tf.keras.utils.set_random_seed(42)
            (raw_train, labels), (raw_test, test_labels) = tf.keras.datasets.mnist.load_data()
            order = np.random.default_rng(42).permutation(len(labels))
            train_ids, val_ids = order[:samples], order[50000:52000]
            train_x = preprocess_batch(raw_train[train_ids])
            val_x = preprocess_batch(raw_train[val_ids])
            test_x = preprocess_batch(raw_test)
            model = tf.keras.Sequential([
                tf.keras.layers.Input(shape=(28, 28, 1)),
                tf.keras.layers.Conv2D(32, 3, activation='relu'),
                tf.keras.layers.MaxPooling2D(),
                tf.keras.layers.Conv2D(64, 3, activation='relu'),
                tf.keras.layers.MaxPooling2D(),
                tf.keras.layers.Flatten(),
                tf.keras.layers.Dense(64, activation='relu'),
                tf.keras.layers.Dropout(0.3),
                tf.keras.layers.Dense(10, activation='softmax'),
            ])
            model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])

            class Feedback(tf.keras.callbacks.Callback):
                def on_epoch_begin(self, epoch, logs=None):
                    owner.update(epoch=epoch + 1, batch_progress=0)

                def on_train_batch_end(self, batch, logs=None):
                    owner.update(batch_progress=(batch + 1) / int(np.ceil(samples / 128)),
                                 batch_accuracy=float(logs['accuracy']), batch_loss=float(logs['loss']))
                    if owner.stop.is_set():
                        self.model.stop_training = True

                def on_epoch_end(self, epoch, logs=None):
                    entry = {'epoch': epoch + 1, **{k: float(v) for k, v in logs.items()}}
                    with owner.lock:
                        owner.state['history'].append(entry)

            if self.stop.is_set():
                self.update(status='cancelled', message='Training cancelled. Previous saved model retained.')
                return
            self.update(status='training', message='Training CNN; metrics update after each batch.')
            model.fit(train_x, labels[train_ids], validation_data=(val_x, labels[val_ids]),
                      epochs=epochs, batch_size=128, callbacks=[Feedback()], verbose=0)
            if self.stop.is_set():
                self.update(status='cancelled', message='Training cancelled. Previous saved model retained.')
                return
            self.update(status='evaluating', message='Evaluating 10,000 unseen test images…')
            probabilities = model.predict(test_x, batch_size=256, verbose=0)
            predictions = probabilities.argmax(axis=1)
            matrix = np.zeros((10, 10), dtype=int)
            np.add.at(matrix, (test_labels, predictions), 1)
            report = {'dataset': 'MNIST digits 0–9', 'train_samples': samples,
                      'validation_samples': len(val_ids), 'test_samples': len(test_labels),
                      'test_accuracy': float(np.mean(predictions == test_labels)),
                      'test_loss': float(-np.log(np.maximum(probabilities[np.arange(len(test_labels)), test_labels], 1e-7)).mean()),
                      'target_accuracy': 0.89, 'epochs': epochs, 'seed': 42,
                      'elapsed_seconds': round(time.monotonic() - started, 2),
                      'confusion_matrix': matrix.tolist(),
                      'per_class': [{'digit': i, 'support': int(matrix[i].sum()),
                                     'precision': float(matrix[i, i] / max(1, matrix[:, i].sum())),
                                     'recall': float(matrix[i, i] / max(1, matrix[i].sum()))} for i in range(10)],
                      'history': self.snapshot()['history'], 'tensorflow_version': tf.__version__,
                      'preprocessing': 'crop ink, fit 20×20, center of mass, normalize 0–1'}
            model.save(ARTIFACTS / 'model.pending.keras')
            (ARTIFACTS / 'report.pending.json').write_text(json.dumps(report, indent=2))
            with self.lock:
                (ARTIFACTS / 'model.pending.keras').replace(ARTIFACTS / 'model.keras')
                (ARTIFACTS / 'report.pending.json').replace(ARTIFACTS / 'report.json')
                self.model = model
                self.state.update(status='complete', message='Training complete. Model saved and evaluated.',
                                  model_ready=True, evaluation=report, run_evaluation=report)
        except Exception as error:
            self.update(status='error', message=f'{type(error).__name__}: {error}')

    def predict(self, image):
        with self.lock:
            if self.model is None:
                raise ValueError('Train a model before recognizing digits.')
            scores = np.asarray(self.model(image[None, ...], training=False))[0]
        return {'digit': int(scores.argmax()), 'confidence': float(scores.max()),
                'probabilities': [float(value) for value in scores]}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--epochs', type=int, default=5)
    parser.add_argument('--samples', type=int, default=10000)
    args = parser.parse_args()
    engine = Engine()
    worker = engine.start(args.epochs, args.samples)
    last = None
    while worker.is_alive():
        state = engine.snapshot()
        progress = (state['status'], state['epoch'], len(state['history']))
        if progress != last:
            print(state['message'], 'Epoch', state['epoch'], flush=True)
            last = progress
        worker.join(1)
    state = engine.snapshot()
    print(json.dumps(state['run_evaluation'] if state.get('run_evaluation') else state, indent=2))
    if state['status'] != 'complete':
        raise SystemExit(1)
