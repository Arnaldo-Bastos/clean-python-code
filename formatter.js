'use strict';
const { spawn } = require('child_process');
const path = require('path');

function runPython(executable, args, request, token) {
  return new Promise((resolve, reject) => {
    if (token && token.isCancellationRequested) return reject(new Error('Formatting cancelled.'));
    const child = spawn(executable, [...args, '-I', path.join(__dirname, 'formatter.py')], {
      shell: false, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe']
    });
    let output = '', errors = '', settled = false;
    let subscription;
    const finish = (error, value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (subscription) subscription.dispose();
      if (error) { child.kill(); reject(error); } else resolve(value);
    };
    const timer = setTimeout(() => finish(new Error('Python formatting exceeded 15 seconds; original code preserved.')), 15000);
    if (token) subscription = token.onCancellationRequested(() => finish(new Error('Formatting cancelled.')));
    child.on('error', error => finish(error));
    child.stdin.on('error', error => finish(error));
    child.stdout.on('data', chunk => {
      output += chunk.toString('utf8');
      if (output.length > 16 * 1024 * 1024) finish(new Error('Formatter response too large.'));
    });
    child.stderr.on('data', chunk => { if (errors.length < 4096) errors += chunk.toString('utf8'); });
    child.on('close', code => {
      if (settled) return;
      if (code !== 0) return finish(new Error(`Python formatter exited with code ${code}. ${errors}`));
      try {
        const response = JSON.parse(output);
        if (!response.ok) return finish(new Error(response.error || 'Python rejected the edit.'));
        finish(null, response);
      } catch (error) { finish(new Error(`Invalid Python formatter response: ${error.message}`)); }
    });
    child.stdin.end(JSON.stringify(request));
  });
}

async function formatSelection(text, options = {}, runtime = {}) {
  if (Buffer.byteLength(text, 'utf8') > 4 * 1024 * 1024) throw new Error('Selection exceeds the 4 MiB limit.');
  const candidates = runtime.pythonPath ? [[runtime.pythonPath, []]] :
    process.platform === 'win32' ? [['py', ['-3']], ['python', []], ['python3', []]] : [['python3', []], ['python', []]];
  const request = { source: text, options };
  if (runtime.document !== undefined) Object.assign(request, { document: runtime.document, start: runtime.start, end: runtime.end });
  for (const [executable, args] of candidates) {
    try {
      return (await runPython(executable, args, request, runtime.token)).formatted;
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;
    }
  }
  throw new Error('Python 3.9+ was not found. Set cleanPythonCode.pythonPath to a Python executable.');
}
module.exports = { formatSelection, runPython };
