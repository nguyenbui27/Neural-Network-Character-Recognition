import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {predict} from '../docs/inference.mjs';
const manifest = JSON.parse(await readFile(new URL('../docs/model.json', import.meta.url)));
const buffer = await readFile(new URL('../docs/weights.bin', import.meta.url));
const weights = new Float32Array(buffer.buffer.slice(buffer.byteOffset, buffer.byteOffset + buffer.byteLength));
const fixtures = JSON.parse(await readFile(new URL('./browser-fixtures.json', import.meta.url)));
let maxError = 0;
for (const fixture of fixtures) {
  const actual = predict(fixture.input, manifest, weights);
  for (let i = 0; i < 10; i++) { const error = Math.abs(actual[i] - fixture.probabilities[i]); maxError = Math.max(maxError, error); assert.ok(error < 1e-5, `Probability mismatch: ${error}`); }
  assert.equal(actual.indexOf(Math.max(...actual)), fixture.probabilities.indexOf(Math.max(...fixture.probabilities)));
}
console.log(`Browser CNN matches TensorFlow for all ${fixtures.length} reference digits; max probability error ${maxError}.`);
