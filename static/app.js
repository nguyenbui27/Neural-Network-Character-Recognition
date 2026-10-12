const $ = id => document.getElementById(id);
const canvas = $('drawing'), ctx = canvas.getContext('2d');
let drawing = false, ink = false, ready = false, predicting = false, revision = 0;
function updateButton() { $('recognize').disabled = !ready || predicting; }
function clear() {
  revision++; drawing = false; ink = false;
  ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, 280, 280);
  $('drawHint').hidden = false; $('digit').textContent = '—';
  $('message').textContent = ready ? '' : 'Connecting…';
}
function point(event) {
  const rect = canvas.getBoundingClientRect();
  return [(event.clientX - rect.left) * 280 / rect.width, (event.clientY - rect.top) * 280 / rect.height];
}
canvas.addEventListener('pointerdown', event => {
  if (event.button !== 0) return;
  canvas.setPointerCapture(event.pointerId); drawing = true; ink = true; revision++;
  $('drawHint').hidden = true; $('digit').textContent = '—'; $('message').textContent = '';
  ctx.strokeStyle = '#151515'; ctx.fillStyle = '#151515'; ctx.lineWidth = 17; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  const [x, y] = point(event);
  ctx.beginPath(); ctx.arc(x, y, 8.5, 0, Math.PI * 2); ctx.fill(); ctx.beginPath(); ctx.moveTo(x, y);
});
canvas.addEventListener('pointermove', event => {
  if (drawing) { ctx.lineTo(...point(event)); ctx.stroke(); }
});
for (const name of ['pointerup', 'pointercancel', 'lostpointercapture']) canvas.addEventListener(name, () => drawing = false);
$('clear').addEventListener('click', clear);
$('recognize').addEventListener('click', async () => {
  if (!ink) { $('message').textContent = 'Draw a number first.'; return; }
  const requestRevision = revision;
  predicting = true; updateButton(); $('message').textContent = 'Recognizing…';
  try {
    const response = await fetch('/api/predict', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: canvas.toDataURL('image/png') })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Please try again.');
    if (revision === requestRevision) { $('digit').textContent = result.digit; $('message').textContent = ''; }
  } catch (error) {
    if (revision === requestRevision) $('message').textContent = error.message;
  } finally { predicting = false; updateButton(); }
});
async function connect() {
  try {
    const response = await fetch('/api/status');
    if (!response.ok) throw new Error('Connection failed');
    const state = await response.json(); ready = state.model_ready; updateButton();
    $('message').textContent = ready ? '' : 'No saved model is available. Train one with engine.py, then reopen this page.';
    if (!ready) setTimeout(connect, 3000);
  } catch (error) {
    ready = false; updateButton(); $('message').textContent = 'The app isn’t connected. Please keep the launcher running.';
    setTimeout(connect, 3000);
  }
}
clear(); connect();
