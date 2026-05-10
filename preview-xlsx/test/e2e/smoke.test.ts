import * as assert from 'assert';
import * as path from 'path';
import * as vscode from 'vscode';

const VIEW_TYPE = 'previewXlsx.viewer';

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
    const repoRoot = path.resolve(__dirname, '..', '..');
    const fixture = vscode.Uri.file(
      path.join(repoRoot, 'test', 'fixtures', 'multi-sheet.xlsx')
    );
    await vscode.commands.executeCommand('vscode.openWith', fixture, VIEW_TYPE);

    const tab = await waitFor(() => {
      const t = vscode.window.tabGroups.activeTabGroup.activeTab;
      const input = t?.input as { viewType?: string } | undefined;
      return input && input.viewType === VIEW_TYPE ? t : undefined;
    });
    assert.ok(tab, 'custom editor tab did not open');

    await vscode.commands.executeCommand('workbench.action.closeActiveEditor');
  });
});
