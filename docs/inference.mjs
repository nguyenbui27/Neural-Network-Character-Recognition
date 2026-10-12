// Float32 CNN inference matching the exported Keras channels-last architecture.
export function predict(input, manifest, weights) {
  let values = new Float32Array(input), height = 28, width = 28, channels = 1;
  for (const layer of manifest.layers) {
    const get = i => { const w = layer.weights[i]; return weights.subarray(w.offset, w.offset + w.size); };
    if (layer.type === 'Conv2D') {
      const kernel = get(0), bias = get(1);
      const [kh, kw, , filters] = layer.weights[0].shape;
      const oh = height - kh + 1, ow = width - kw + 1;
      const output = new Float32Array(oh * ow * filters);
      for (let y = 0; y < oh; y++) for (let x = 0; x < ow; x++) {
        const target = (y * ow + x) * filters;
        const sums = new Float64Array(bias);
        for (let ky = 0; ky < kh; ky++) for (let kx = 0; kx < kw; kx++) for (let c = 0; c < channels; c++) {
          const value = values[((y + ky) * width + x + kx) * channels + c];
          const base = ((ky * kw + kx) * channels + c) * filters;
          for (let f = 0; f < filters; f++) sums[f] += value * kernel[base + f];
        }
        for (let f = 0; f < filters; f++) output[target + f] = Math.max(0, sums[f]);
      }
      values = output; height = oh; width = ow; channels = filters;
    } else if (layer.type === 'MaxPooling2D') {
      const oh = Math.floor(height / 2), ow = Math.floor(width / 2);
      const output = new Float32Array(oh * ow * channels);
      for (let y = 0; y < oh; y++) for (let x = 0; x < ow; x++) for (let c = 0; c < channels; c++) {
        let max = -Infinity;
        for (let dy = 0; dy < 2; dy++) for (let dx = 0; dx < 2; dx++) max = Math.max(max, values[((y * 2 + dy) * width + x * 2 + dx) * channels + c]);
        output[(y * ow + x) * channels + c] = max;
      }
      values = output; height = oh; width = ow;
    } else if (layer.type === 'Dense') {
      const kernel = get(0), bias = get(1), units = bias.length;
      const output = new Float32Array(units);
      for (let j = 0; j < units; j++) {
        let sum = bias[j];
        for (let i = 0; i < values.length; i++) sum += values[i] * kernel[i * units + j];
        output[j] = layer.config.activation === 'relu' ? Math.max(0, sum) : sum;
      }
      if (layer.config.activation === 'softmax') {
        const max = Math.max(...output), exp = Array.from(output, v => Math.exp(v - max)), total = exp.reduce((a, b) => a + b);
        for (let i = 0; i < units; i++) output[i] = exp[i] / total;
      }
      values = output;
    } else if (layer.type !== 'Flatten') throw new Error(`Unsupported layer: ${layer.type}`);
  }
  return Array.from(values);
}
