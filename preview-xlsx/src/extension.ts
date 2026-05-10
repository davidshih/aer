import * as vscode from 'vscode';
import { SpreadsheetViewerProvider } from './viewerProvider';

export function activate(context: vscode.ExtensionContext): void {
  context.subscriptions.push(SpreadsheetViewerProvider.register(context));
}

export function deactivate(): void {
  /* noop */
}
