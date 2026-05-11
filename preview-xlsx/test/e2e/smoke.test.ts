import * as assert from 'assert';
import * as path from 'path';
import * as fs from 'fs';
import * as vscode from 'vscode';

const VIEW_TYPE = 'previewXlsx.viewer';
const REPO_ROOT = process.env.PREVIEW_XLSX_REPO_ROOT;

async function waitFor<T>(probe: () => T | undefined, timeoutMs = 10_000, stepMs = 100): Promise<T> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const v = probe();
    if (v !== undefined) return v;
    await new Promise((r) => setTimeout(r, stepMs));
  }
  throw new Error('waitFor timed out');
}

describe('E2E · smoke', () => {
  it('activates the extension', async () => {
    const ext = vscode.extensions.getExtension('local.preview-xlsx');
    assert.ok(ext, 'extension not found');
    await ext.activate();
    assert.strictEqual(ext.isActive, true);
  });

  it('opens an .xlsx via the custom editor', async () => {
    assert.ok(REPO_ROOT, 'PREVIEW_XLSX_REPO_ROOT env not set by driver');
    const fixturePath = path.join(REPO_ROOT, 'test', 'fixtures', 'multi-sheet.xlsx');
    assert.ok(fs.existsSync(fixturePath), `fixture missing: ${fixturePath}`);
    const fixture = vscode.Uri.file(fixturePath);
    await vscode.commands.executeCommand('vscode.openWith', fixture, VIEW_TYPE);

    const tab = await waitFor(() => {
      const t = vscode.window.tabGroups.activeTabGroup.activeTab;
      const input = t?.input as { viewType?: string; uri?: vscode.Uri } | undefined;
      if (!input || input.viewType !== VIEW_TYPE) return undefined;
      if (input.uri?.fsPath !== fixturePath) return undefined;
      return t;
    });
    assert.ok(tab, 'custom editor tab did not open for the expected fixture');

    await vscode.commands.executeCommand('workbench.action.closeActiveEditor');
  });
});
