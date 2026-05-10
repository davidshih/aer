// E2E driver: download VS Code, launch Extension Development Host
// pointing at our extension, run the mocha suite from out-e2e/index.js.
const path = require('path');
const fs = require('fs');
const { runTests } = require('@vscode/test-electron');
const esbuild = require('esbuild');

async function main() {
  const repoRoot = path.resolve(__dirname, '..', '..');
  const outDir = path.join(repoRoot, 'out-e2e');
  fs.rmSync(outDir, { recursive: true, force: true });
  fs.mkdirSync(outDir, { recursive: true });

  await esbuild.build({
    entryPoints: [
      path.join(__dirname, 'index.ts'),
      path.join(__dirname, 'smoke.test.ts')
    ],
    outdir: outDir,
    bundle: true,
    platform: 'node',
    target: 'node18',
    format: 'cjs',
    sourcemap: true,
    external: ['vscode', 'mocha']
  });

  const userDataDir = path.join(repoRoot, '.vscode-test-user');
  fs.rmSync(userDataDir, { recursive: true, force: true });

  await runTests({
    extensionDevelopmentPath: repoRoot,
    extensionTestsPath: path.join(outDir, 'index.js'),
    launchArgs: [
      '--disable-extensions',
      '--disable-telemetry',
      `--user-data-dir=${userDataDir}`
    ]
  });
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
