import * as fs from 'fs';
import ExcelJS from 'exceljs';
import { LIMITS, clampString, LimitExceededError } from '../limits';
import { WorkbookData, SheetData, ParseOptions } from '../types';

function cellToText(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (value instanceof Date) return value.toISOString();
  if (typeof value === 'object') {
    const v = value as Record<string, unknown>;
    if ('text' in v && typeof v.text === 'string') return v.text;
    if ('result' in v) return cellToText(v.result);
    if ('richText' in v && Array.isArray(v.richText)) {
      return (v.richText as Array<{ text?: string }>).map((r) => r.text ?? '').join('');
    }
    if ('hyperlink' in v && typeof v.text === 'string') return v.text;
    if ('formula' in v) return '';
    if ('error' in v && typeof v.error === 'string') return v.error;
  }
  return String(value);
}

export async function parseXlsx(filePath: string, opts: ParseOptions): Promise<WorkbookData> {
  const stat = await fs.promises.stat(filePath);
  if (stat.size > opts.maxFileSizeBytes) {
    throw new LimitExceededError('fileSize', stat.size);
  }

  const wb = new ExcelJS.Workbook();
  // Reduce parse surface: skip parts we never render. This does not magically
  // bound memory (ExcelJS still loads the workbook), but it shrinks the
  // attack surface from external resources we do not consume.
  await wb.xlsx.readFile(filePath, {
    ignoreNodes: [
      'styles',
      'themes',
      'hyperlinks',
      'media',
      'drawings',
      'comments',
      'tables',
      'pivotTables',
      'conditionalFormatting',
      'dataValidations'
    ]
  } as unknown as Parameters<typeof wb.xlsx.readFile>[1]);

  const sheets: SheetData[] = [];
  const warnings: string[] = [];
  const maxRows = Math.min(opts.maxRows, LIMITS.rowsHardMax);

  wb.eachSheet((ws) => {
    const rows: string[][] = [];
    let truncated = false;
    let truncatedColumns = false;
    let totalRowsSeen = 0;
    let maxCols = 0;

    ws.eachRow({ includeEmpty: false }, (row) => {
      totalRowsSeen++;
      if (rows.length >= maxRows) {
        truncated = true;
        return;
      }
      const values = row.values as unknown[];
      // exceljs row.values is 1-indexed; index 0 is null
      const sourceCount = Math.max(0, values.length - 1);
      if (sourceCount > LIMITS.columns) truncatedColumns = true;
      const limit = Math.min(sourceCount, LIMITS.columns);
      const out: string[] = [];
      for (let c = 1; c <= limit; c++) {
        out.push(clampString(cellToText(values[c])));
      }
      if (out.length > maxCols) maxCols = out.length;
      rows.push(out);
    });

    for (const r of rows) {
      while (r.length < maxCols) r.push('');
    }
    const columns: string[] = [];
    for (let i = 0; i < maxCols; i++) columns.push(`Column ${i + 1}`);

    const sheetName = ws.name || `Sheet${ws.id}`;
    sheets.push({
      name: sheetName,
      columns,
      rows,
      truncated,
      truncatedColumns,
      totalRowsSeen
    });
    if (truncated) {
      warnings.push(`Sheet "${sheetName}" truncated to ${maxRows} rows (file has at least ${totalRowsSeen}).`);
    }
    if (truncatedColumns) {
      warnings.push(`Sheet "${sheetName}" had >${LIMITS.columns} columns; extras dropped.`);
    }
  });

  if (sheets.length === 0) {
    warnings.push('No worksheets found.');
  }

  return { sheets, warnings };
}
