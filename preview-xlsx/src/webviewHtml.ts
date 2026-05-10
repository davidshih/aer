export interface WebviewHtmlInputs {
  scriptUri: string;
  styleUri: string;
  cspSource: string;
  nonce: string;
}

export function buildWebviewHtml(i: WebviewHtmlInputs): string {
  const csp = [
    `default-src 'none'`,
    `script-src 'nonce-${i.nonce}'`,
    `style-src 'nonce-${i.nonce}' ${i.cspSource}`,
    `img-src ${i.cspSource} data:`,
    `font-src ${i.cspSource}`
  ].join('; ');
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="${csp}">
<link rel="stylesheet" href="${i.styleUri}" nonce="${i.nonce}">
<title>Spreadsheet Preview</title>
</head>
<body>
<div id="status" role="status" aria-live="polite">Loading…</div>
<div id="tabs" role="tablist"></div>
<div id="grid"></div>
<script nonce="${i.nonce}" src="${i.scriptUri}"></script>
</body>
</html>`;
}
