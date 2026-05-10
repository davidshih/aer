import * as assert from 'assert';
import { buildWebviewHtml } from '../../src/webviewHtml';

describe('security · CSP HTML builder', () => {
  const html = buildWebviewHtml({
    scriptUri: 'vscode-resource://dist/webview.js',
    styleUri: 'vscode-resource://dist/styles.css',
    cspSource: 'vscode-resource:',
    nonce: 'NONCE12345'
  });

  it("declares default-src 'none'", () => {
    assert.ok(html.includes(`default-src 'none'`), 'missing default-src none');
  });

  it('uses the provided nonce in script-src and style-src', () => {
    assert.ok(html.includes(`script-src 'nonce-NONCE12345'`));
    assert.ok(html.includes(`'nonce-NONCE12345'`));
  });

  it("contains no 'unsafe-inline' or 'unsafe-eval'", () => {
    assert.strictEqual(html.includes('unsafe-inline'), false);
    assert.strictEqual(html.includes('unsafe-eval'), false);
  });

  it('does not embed any http(s) origins', () => {
    assert.strictEqual(/https?:\/\//.test(html), false, 'remote origin found');
  });

  it('inline script tag carries the nonce', () => {
    const m = html.match(/<script[^>]*nonce="NONCE12345"/);
    assert.ok(m, 'script tag missing nonce');
  });
});
