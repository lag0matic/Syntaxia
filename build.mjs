import { build } from 'esbuild';
import { mkdir, copyFile, writeFile, readFile } from 'node:fs/promises';
await mkdir('dist/vendor/pyodide', { recursive: true });
for (const name of ['pyodide.js', 'pyodide.asm.js', 'pyodide.asm.wasm', 'python_stdlib.zip', 'pyodide-lock.json']) {
  await copyFile(`node_modules/pyodide/${name}`, `dist/vendor/pyodide/${name}`);
}
await build({ entryPoints: ['src/app.js'], bundle: true, format: 'esm', outfile: 'dist/app.js', minify: true, legalComments: 'linked' });
await copyFile('src/runner.py', 'dist/runner.py');
await copyFile('src/worker.js', 'dist/worker.js');
const manifest = JSON.parse(await readFile('node_modules/pyodide/package.json', 'utf8'));
await writeFile('dist/vendor/README.txt', `Pyodide ${manifest.version}; https://pyodide.org/ — Mozilla Public License 2.0.\nEditor dependencies: see app.js.LEGAL.txt.\nThese files are copied by npm run build.\n`);
console.log('Built classroom and copied local Python runtime.');
