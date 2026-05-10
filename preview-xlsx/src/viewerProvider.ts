import * as vscode from 'vscode';
import * as path from 'path';
import * as crypto from 'crypto';
import { parseXlsx } from './parsers/xlsx';
import { parseCsvFile } from './parsers/csv';
import { LIMITS, LimitExceededError } from './limits';
import { WorkbookData, ParseOptions } from './types';

const VIEW_TYPE = 'previewXlsx.viewer';

class ReadonlyDocument implements vscode.CustomDocument {
  constructor(public readonly uri: vscode.Uri) {}
  dispose(): void {
    /* noop */
  }
}

export class SpreadsheetViewerProvider implements vscode.CustomReadonlyEditorProvider<ReadonlyDocument> {
  static register(context: vscode.ExtensionContext): vscode.Disposable {
    const provider = new SpreadsheetViewerProvider(context);
    return vscode.window.registerCustomEditorProvider(VIEW_TYPE, provider, {
      supportsMultipleEditorsPerDocument: false,
      webviewOptions: { retainContextWhenHidden: false }
    });
  }

  constructor(private readonly context: vscode.ExtensionContext) {}

  openCustomDocument(uri: vscode.Uri): ReadonlyDocument {
    return new ReadonlyDocument(uri);
  }

  async resolveCustomEditor(
    document: ReadonlyDocument,
    webviewPanel: vscode.WebviewPanel
  ): Promise<void> {
    const distRoot = vscode.Uri.joinPath(this.context.extensionUri, 'dist');
    webviewPanel.webview.options = {
      enableScripts: true,
      enableCommandUris: false,
      enableForms: false,
      localResourceRoots: [distRoot]
    };

    webviewPanel.webview.html = this.buildHtml(webviewPanel.webview);

    const post = (msg: unknown) => webviewPanel.webview.postMessage(msg);

    const load = async () => {
      try {
        const data = await this.parseFile(document.uri);
        post({ type: 'data', payload: data });
      } catch (err) {
        const message =
          err instanceof LimitExceededError
            ? `File rejected: ${err.limit} limit exceeded (${err.value}). See settings previewXlsx.* to adjust.`
            : err instanceof Error
              ? err.message
              : 'Failed to read file.';
        post({ type: 'error', message });
      }
    };

    const watcher = vscode.workspace.createFileSystemWatcher(
      new vscode.RelativePattern(
        vscode.Uri.file(path.dirname(document.uri.fsPath)),
        path.basename(document.uri.fsPath)
      )
    );
    watcher.onDidChange(load);
    webviewPanel.onDidDispose(() => watcher.dispose());

    await load();
  }

  private getOptions(): ParseOptions {
    const cfg = vscode.workspace.getConfiguration('previewXlsx');
    const maxRows = Math.min(cfg.get<number>('maxRows', 100_000), LIMITS.rowsHardMax);
    const maxFileMB = Math.min(cfg.get<number>('maxFileSizeMB', 50), 200);
    return {
      maxRows,
      maxFileSizeBytes: maxFileMB * 1024 * 1024
    };
  }

  private async parseFile(uri: vscode.Uri): Promise<WorkbookData> {
    const ext = path.extname(uri.fsPath).toLowerCase();
    const opts = this.getOptions();
    if (ext === '.xlsx') {
      return parseXlsx(uri.fsPath, opts);
    }
    if (ext === '.csv' || ext === '.tsv') {
      const sheet = await parseCsvFile(uri.fsPath, ext === '.tsv' ? '\t' : ',', opts);
      const warnings: string[] = [];
      if (sheet.truncated) {
        warnings.push(
          `File truncated to ${opts.maxRows} rows (file has at least ${sheet.totalRowsSeen}).`
        );
      }
      if (sheet.truncatedColumns) {
        warnings.push(`File had >${1024} columns; extras dropped.`);
      }
      return { sheets: [sheet], warnings };
    }
    throw new Error(`Unsupported file extension: ${ext}`);
  }

  private buildHtml(webview: vscode.Webview): string {
    const nonce = crypto.randomBytes(16).toString('base64');
    const scriptUri = webview.asWebviewUri(
      vscode.Uri.joinPath(this.context.extensionUri, 'dist', 'webview.js')
    );
    const styleUri = webview.asWebviewUri(
      vscode.Uri.joinPath(this.context.extensionUri, 'dist', 'styles.css')
    );
    const csp = [
      `default-src 'none'`,
      `script-src 'nonce-${nonce}'`,
      `style-src 'nonce-${nonce}' ${webview.cspSource}`,
      `img-src ${webview.cspSource} data:`,
      `font-src ${webview.cspSource}`
    ].join('; ');
    return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="${csp}">
<link rel="stylesheet" href="${styleUri}" nonce="${nonce}">
<title>Spreadsheet Preview</title>
</head>
<body>
<div id="status" role="status" aria-live="polite">Loading…</div>
<div id="tabs" role="tablist"></div>
<div id="grid"></div>
<script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
  }
}
