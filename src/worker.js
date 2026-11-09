/* Learner Python runs here, never in the host server process. */
importScripts('/vendor/pyodide/pyodide.js');
let runtime;
const ready = (async () => {
  runtime = await loadPyodide({ indexURL: '/vendor/pyodide/' });
  const response = await fetch('/runner.py');
  if (!response.ok) throw new Error('Could not load the exercise runner.');
  runtime.runPython(await response.text());
  postMessage({ type: 'ready' });
})();
ready.catch(error => postMessage({ type: 'error', message: String(error) }));
self.onmessage = async ({ data }) => {
  try {
    await ready;
    postMessage({ type: 'started' });
    runtime.globals.set('_request_json', JSON.stringify(data));
    const result = runtime.runPython('run_request(_request_json)');
    postMessage({ type: 'result', result: JSON.parse(result) });
  } catch (error) {
    postMessage({ type: 'error', message: String(error) });
  }
};
