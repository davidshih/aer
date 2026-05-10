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
    path.join(__dirname, 'security', 'parser.test.ts'),
    path.join(__dirname, 'security', 'csp.test.ts'),
    path.join(__dirname, 'security', 'rendering.test.ts')
  ].filter((p) => fs.existsSync(p));

  await esbuild.build({
    entryPoints: entries,
    outdir: outDir,
    bundle: true,
    platform: 'node',
    target: 'node18',
    format: 'cjs',
    sourcemap: true,
    external: ['mocha', 'exceljs', 'jsdom', 'vscode']
  });

  const mocha = new Mocha({ ui: 'bdd', color: true, timeout: 20_000 });
  const walk = (dir) => {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, e.name);
      if (e.isDirectory()) walk(p);
      else if (e.name.endsWith('.js')) mocha.addFile(p);
    }
  };
  walk(outDir);

  await new Promise((resolve, reject) => {
    mocha.run((failures) => (failures > 0 ? reject(new Error(`${failures} failed`)) : resolve()));
  });
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
