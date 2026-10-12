"""Shared MNIST and drawing preprocessing: white ink on a black 28×28 image."""
import numpy as np
from PIL import Image, ImageOps


def preprocess(image, dark_ink=False):
    image = image.convert('L')
    if dark_ink:
        image = ImageOps.invert(image)
    pixels = np.asarray(image)
    ys, xs = np.nonzero(pixels > 20)
    if not len(xs):
        raise ValueError('Draw a digit before recognizing it.')
    cropped = image.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    scale = 20 / max(cropped.size)
    cropped = cropped.resize(tuple(max(1, round(s * scale)) for s in cropped.size), Image.Resampling.LANCZOS)
    canvas = Image.new('L', (28, 28))
    canvas.paste(cropped, ((28 - cropped.width) // 2, (28 - cropped.height) // 2))
    values = np.asarray(canvas, dtype=np.float32) / 255.0
    yy, xx = np.indices(values.shape)
    mass = values.sum()
    dx = round(13.5 - float((xx * values).sum() / mass))
    dy = round(13.5 - float((yy * values).sum() / mass))
    centered = Image.new('L', (28, 28))
    centered.paste(canvas, (dx, dy))
    return np.asarray(centered, dtype=np.float32)[..., None] / 255.0


def preprocess_batch(images):
    return np.stack([preprocess(Image.fromarray(image)) for image in images])
