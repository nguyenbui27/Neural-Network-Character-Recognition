const $ = id => document.getElementById(id);
const canvas = $('drawing'), ctx = canvas.getContext('2d');
let drawing = false, ink = false, model, weights, revision = 0, busy = false;
function clear() {
  revision++; drawing = false; ink = false;
  ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, 280, 280);
  $('drawHint').hidden = false; $('digit').textContent = '—';
  $('message').textContent = model ? '' : 'Loading the recognition model…';
}
function point(event) {
  const r = canvas.getBoundingClientRect();
  return [(event.clientX - r.left) * 280 / r.width, (event.clientY - r.top) * 280 / r.height];
}
canvas.addEventListener('pointerdown', event => {
  if (event.button !== 0) return;
  canvas.setPointerCapture(event.pointerId); drawing = true; ink = true; revision++;
  $('drawHint').hidden = true; $('digit').textContent = '—'; $('message').textContent = '';
  ctx.strokeStyle = '#151515'; ctx.fillStyle = '#151515'; ctx.lineWidth = 17; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  const [x, y] = point(event);
  ctx.beginPath(); ctx.arc(x, y, 8.5, 0, Math.PI * 2); ctx.fill(); ctx.beginPath(); ctx.moveTo(x, y);
});
canvas.addEventListener('pointermove', event => { if (drawing) {ctx.lineTo(...point(event)); ctx.stroke();} });
for (const name of ['pointerup', 'pointercancel', 'lostpointercapture']) canvas.addEventListener(name, () => drawing = false);
$('clear').addEventListener('click', clear);
function normalizedDrawing() {
  const rgba = ctx.getImageData(0, 0, 280, 280).data;
  let minX = 280, minY = 280, maxX = -1, maxY = -1;
  const source = document.createElement('canvas'); source.width = source.height = 280;
  const sourceCtx = source.getContext('2d'), gray = sourceCtx.createImageData(280, 280);
  for (let y = 0; y < 280; y++) for (let x = 0; x < 280; x++) {
    const i = (y * 280 + x) * 4;
    const value = 255 - Math.round(rgba[i] * .299 + rgba[i + 1] * .587 + rgba[i + 2] * .114);
    gray.data[i] = gray.data[i + 1] = gray.data[i + 2] = value; gray.data[i + 3] = 255;
    if (value > 20) { minX = Math.min(minX, x); minY = Math.min(minY, y); maxX = Math.max(maxX, x); maxY = Math.max(maxY, y); }
  }
  if (maxX < 0) throw new Error('Draw a number first.');
  sourceCtx.putImageData(gray, 0, 0);
  const small = document.createElement('canvas'); small.width = small.height = 28;
  const sc = small.getContext('2d'); sc.fillStyle = '#000'; sc.fillRect(0, 0, 28, 28);
  const w = maxX - minX + 1, h = maxY - minY + 1, scale = 20 / Math.max(w, h);
  const dw = Math.max(1, Math.round(w * scale)), dh = Math.max(1, Math.round(h * scale));
  sc.imageSmoothingEnabled = true; sc.imageSmoothingQuality = 'high';
  sc.drawImage(source, minX, minY, w, h, Math.floor((28 - dw) / 2), Math.floor((28 - dh) / 2), dw, dh);
  const data = sc.getImageData(0, 0, 28, 28).data;
  let mass = 0, mx = 0, my = 0;
  for (let y = 0; y < 28; y++) for (let x = 0; x < 28; x++) { const v = data[(y * 28 + x) * 4] / 255; mass += v; mx += x * v; my += y * v; }
  const dx = Math.round(13.5 - mx / mass), dy = Math.round(13.5 - my / mass), output = new Float32Array(784);
  for (let y = 0; y < 28; y++) for (let x = 0; x < 28; x++) if (x + dx >= 0 && x + dx < 28 && y + dy >= 0 && y + dy < 28) output[(y + dy) * 28 + x + dx] = data[(y * 28 + x) * 4] / 255;
  return output;
}
const worker = new Worker(new URL('./worker.mjs', import.meta.url), {type:'module'});
worker.addEventListener('message', event => {
  busy = false; $('recognize').disabled = !model;
  if (event.data.revision !== revision) return;
  if (event.data.error) { $('message').textContent = event.data.error; return; }
  const scores = event.data.scores;
  $('digit').textContent = scores.indexOf(Math.max(...scores)); $('message').textContent = '';
});
worker.addEventListener('error', () => { busy = false; $('recognize').disabled = !model; $('message').textContent = 'Recognition failed. Refresh and try again.'; });
$('recognize').addEventListener('click', () => {
  if (!ink) { $('message').textContent = 'Draw a number first.'; return; }
  if (!model || busy) return;
  try {
    const input = normalizedDrawing(); busy = true; $('recognize').disabled = true; $('message').textContent = 'Recognizing…';
    worker.postMessage({input, revision}, [input.buffer]);
  } catch (error) { $('message').textContent = error.message; }
});
clear();
try {
  const [metadata, binary] = await Promise.all([fetch('./model.json'), fetch('./weights.bin')]);
  if (!metadata.ok || !binary.ok) throw new Error('The model could not be loaded. Refresh to try again.');
  model = await metadata.json(); weights = new Float32Array(await binary.arrayBuffer());
  worker.postMessage({model, weights}, [weights.buffer]);
  $('recognize').disabled = false; $('message').textContent = '';
} catch (error) { $('message').textContent = error.message; }
