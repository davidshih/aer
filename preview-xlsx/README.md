# Spreadsheet Preview

`read-only` · `no network` · `no macros` · `no formula execution`

A lightweight, read-only preview for tabular files inside VS Code, with click-to-sort headers
and per-column substring filters. Designed to keep the security surface as small as possible.

## Supported formats

- `.xlsx` — modern Excel workbooks
- `.csv` — comma-separated, RFC 4180-ish
- `.tsv` — tab-separated

`.xls` (legacy BIFF) and `.xlsm` (macro-enabled) are deliberately not supported.

## Usage

1. Right-click a supported file in the Explorer.
2. Choose **Open With…** → **Spreadsheet Preview**.
3. Click a column header to toggle sort (asc → desc → off).
4. Type into the per-column filter row to substring-filter (case-insensitive).

This viewer is not the default editor for any format. Open it explicitly via **Open With…**.

## Limits and behaviour

| Limit | Default | Hard max | Behaviour when exceeded |
|---|---|---|---|
| File size | 50 MB | 200 MB | **Reject** with error before reading body |
| Rows per sheet | 100,000 | 250,000 | Truncate; warning shown in status bar |
| Columns per sheet | 1,024 | 1,024 | Truncate; warning shown in status bar |
| Cell string length | 32 KB | 32 KB | Clamp with trailing ellipsis |

Adjust `previewXlsx.maxRows` and `previewXlsx.maxFileSizeMB` in VS Code settings if you need
different defaults (still capped by the hard maxes).

## Security model

- Strict CSP with a per-render nonce: no inline scripts, no `eval`, no remote origins, no remote images.
- `localResourceRoots` restricted to the extension's `dist/` folder.
- `enableCommandUris` and `enableForms` are disabled.
- All cell values render via `textContent` — never `innerHTML`. Crafted cells containing markup display as plain text.
- Hyperlinks render as plain text (no `<a href>`), defeating `javascript:`, `vbscript:`, and `file://` exfiltration.
- Formulas are not evaluated; only cached values or formula text are read. CSV cells beginning with `=`/`@`/`+` are shown verbatim.
- External images, drawings, OLE objects, charts, conditional formatting, and VBA macros are not rendered and not exposed to the webview. The parser passes `ignoreNodes` to ExcelJS to skip those parts where supported, but a malformed workbook may still touch the underlying lib's parser code paths — the file-size cap remains the primary backstop.
- Runtime makes **no network calls** and emits **no telemetry**.
- `untrustedWorkspaces.supported = true`; safe in Restricted Mode because file content is never executed.

Threat-model honesty: the file-size cap is the primary defence against DoS. This extension
does **not** claim per-shared-string or per-decompression-byte limits beyond that cap.

## What this extension does not do

Editing, formula recalculation, charts, images, pivot tables, conditional formatting, macros,
export. Use Excel for any of those.

## Build and verify

```
npm install
npm run verify
code --extensionDevelopmentPath=$PWD
```

## Origin

Built independently against the public VS Code Custom Editor API and the public ExcelJS API.
No code, CSS, DOM structure, README text, icons, screenshots, or test data was copied from any
other spreadsheet viewer extension.

## License

MIT — see `LICENSE`.
