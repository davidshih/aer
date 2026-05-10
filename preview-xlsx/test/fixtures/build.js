// Deterministic test fixture generator. Run: `node test/fixtures/build.js`.
// Outputs are committed; this script is the source of truth so reviewers can
// see exactly what each fixture contains. No content is copied from any
// external source.

const fs = require('fs');
const path = require('path');
const ExcelJS = require('exceljs');

const FX = __dirname;

async function malformulaCsv() {
  // Hostile leading characters; whitespace and tab prefixes; quoted formula.
  // Read-only viewer must show all of these verbatim.
  const cells = [
    `=cmd|' /C calc'!A0`,
    `@SUM(1)*cmd`,
    `+HYPERLINK("x","y")`,
    `-cmd|fake`,
    ` =SUM(1,1)`,
    `\t=cmd|tabbed`,
    `=2+2`
  ];
  // CSV-quote each hostile cell so inner commas don't split into fields,
  // and double internal quotes per RFC 4180.
  const quote = (s) => `"${s.replace(/"/g, '""')}"`;
  const lines = cells.map((c) => `${quote(c)},plain`);
  fs.writeFileSync(path.join(FX, 'malicious-formula.csv'), lines.join('\n') + '\n');
}

async function maliciousHtmlXlsx() {
  const wb = new ExcelJS.Workbook();
  const ws = wb.addWorksheet('s');
  ws.getCell('A1').value = '<img src=x onerror="alert(1)">';
  ws.getCell('A2').value = '<script>alert(1)</script>';
  ws.getCell('A3').value = 'javascript:alert(1)';
  await wb.xlsx.writeFile(path.join(FX, 'malicious-html.xlsx'));
}

async function maliciousLinkXlsx() {
  const wb = new ExcelJS.Workbook();
  const ws = wb.addWorksheet('s');
  ws.getCell('A1').value = { text: 'click me', hyperlink: 'javascript:alert(1)' };
  ws.getCell('A2').value = { text: 'open file', hyperlink: 'file:///etc/passwd' };
  await wb.xlsx.writeFile(path.join(FX, 'malicious-link.xlsx'));
}

async function multiSheetXlsx() {
  const wb = new ExcelJS.Workbook();
  const a = wb.addWorksheet('Alpha');
  a.addRow(['name', 'qty']);
  a.addRow(['apple', 3]);
  a.addRow(['banana', 1]);
  const b = wb.addWorksheet('Beta');
  b.addRow(['date', 'amount']);
  b.addRow([new Date('2026-01-01T00:00:00Z'), 12.5]);
  b.addRow([new Date('2026-02-15T00:00:00Z'), 7.25]);
  const c = wb.addWorksheet('Gamma');
  c.addRow(['n']);
  for (let i = 1; i <= 5; i++) c.addRow([i]);
  await wb.xlsx.writeFile(path.join(FX, 'multi-sheet.xlsx'));
}

async function main() {
  await malformulaCsv();
  await maliciousHtmlXlsx();
  await maliciousLinkXlsx();
  await multiSheetXlsx();
  console.log('fixtures generated in', FX);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
