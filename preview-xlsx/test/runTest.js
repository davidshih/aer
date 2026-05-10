const path = require('path');
const Mocha = require('mocha');
const fs = require('fs');

async function run() {
  // Compile TS sources for parsers using tsc-less approach: use ts-node-style? We'll require compiled from out/.
  // For simplicity rely on esbuild build of tests via a tiny helper.
  const esbuild = require('esbuild');
  const outDir = path.join(__dirname, '..', 'out-test');
  fs.mkdirSync(outDir, { recursive: true });

  const entries = [
    path.join(__dirname, 'parsers', 'csv.test.ts'),
    path.join(__dirname, 'parsers', 'xlsx.test.ts'),
    path.join(__dirname, 'rendering.test.ts')
  ].filter((p) => fs.existsSync(p));

  await esbuild.build({
    entryPoints: entries,
    outdir: outDir,
    bundle: true,
    platform: 'node',
    target: 'node18',
    format: 'cjs',
    sourcemap: true,
    external: ['mocha', 'exceljs']
  });

  const mocha = new Mocha({ ui: 'bdd', color: true, timeout: 20_000 });
  for (const f of fs.readdirSync(outDir)) {
    if (f.endsWith('.js')) mocha.addFile(path.join(outDir, f));
  }

  await new Promise((resolve, reject) => {
    mocha.run((failures) => (failures > 0 ? reject(new Error(`${failures} failed`)) : resolve()));
  });
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
