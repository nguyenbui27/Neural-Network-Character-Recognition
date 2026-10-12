import {predict} from './inference.mjs';
let model, weights;
self.onmessage = ({data}) => {
  if (data.model) { model = data.model; weights = data.weights; return; }
  try { self.postMessage({revision:data.revision, scores:predict(data.input, model, weights)}); }
  catch (error) { self.postMessage({revision:data.revision, error:error.message}); }
};
