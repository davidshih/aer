const esbuild = require('esbuild');
const fs = require('fs');
const path = require('path');

const watch = process.argv.includes('--watch');

function copyStyles() {
  fs.mkdirSync('dist', { recursive: true });
  fs.copyFileSync(path.join('src', 'webview', 'styles.css'), path.join('dist', 'styles.css'));
}

const common = {
  bundle: true,
  sourcemap: true,
  minify: false,
  logLevel: 'info'
};

const extensionBuild = {
  ...common,
  entryPoints: ['src/extension.ts'],
  outfile: 'dist/extension.js',
  platform: 'node',
  target: 'node18',
  format: 'cjs',
  external: ['vscode']
};

const webviewBuild = {
  ...common,
  entryPoints: ['src/webview/main.ts'],
  outfile: 'dist/webview.js',
  platform: 'browser',
  target: 'es2022',
  format: 'iife'
};

async function run() {
  if (watch) {
    const ctxA = await esbuild.context(extensionBuild);
    const ctxB = await esbuild.context(webviewBuild);
    await Promise.all([ctxA.watch(), ctxB.watch()]);
    console.log('watching...');
  } else {
    await Promise.all([esbuild.build(extensionBuild), esbuild.build(webviewBuild)]);
    copyStyles();
  }
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
