import * as fs from 'fs';
import { LIMITS, clampString, LimitExceededError } from '../limits';
import { SheetData, ParseOptions } from '../types';

export type Delimiter = ',' | '\t';

export async function parseCsvFile(
  filePath: string,
  delimiter: Delimiter,
  opts: ParseOptions
): Promise<SheetData> {
  const stat = await fs.promises.stat(filePath);
  if (stat.size > opts.maxFileSizeBytes) {
    throw new LimitExceededError('fileSize', stat.size);
  }
  const buf = await fs.promises.readFile(filePath);
  return parseCsv(buf, delimiter, opts);
}

export function parseCsv(buf: Buffer, delimiter: Delimiter, opts: ParseOptions): SheetData {
  if (buf.length > opts.maxFileSizeBytes) {
    throw new LimitExceededError('fileSize', buf.length);
  }
  let text = buf.toString('utf8');
  if (text.charCodeAt(0) === 0xfeff) text = text.slice(1); // BOM

  const rows: string[][] = [];
  let field = '';
  let row: string[] = [];
  let inQuotes = false;
  let totalRowsSeen = 0;
  let truncated = false;
  let truncatedColumns = false;
  const maxRows = Math.min(opts.maxRows, LIMITS.rowsHardMax);

  const pushField = () => {
    if (row.length >= LIMITS.columns) {
      truncatedColumns = true;
      field = '';
      return;
    }
    row.push(clampString(field));
    field = '';
  };
  const pushRow = () => {
    pushField();
    totalRowsSeen++;
    if (rows.length < maxRows) {
      rows.push(row);
    } else {
      truncated = true;
    }
    row = [];
  };

  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        field += c;
      }
    } else {
      if (c === '"' && field.length === 0) {
        inQuotes = true;
      } else if (c === delimiter) {
        pushField();
      } else if (c === '\n') {
        pushRow();
      } else if (c === '\r') {
        if (text[i + 1] === '\n') i++;
        pushRow();
      } else {
        field += c;
        if (field.length > LIMITS.cellStringLength * 2) {
          field = clampString(field);
        }
      }
    }
  }
  if (field.length > 0 || row.length > 0) {
    pushRow();
  }

  const colCount = rows.reduce((m, r) => Math.max(m, r.length), 0);
  for (const r of rows) {
    while (r.length < colCount) r.push('');
  }

  const columns: string[] = [];
  for (let i = 0; i < colCount; i++) columns.push(`Column ${i + 1}`);

  return {
    name: delimiter === '\t' ? 'TSV' : 'CSV',
    columns,
    rows,
    truncated,
    truncatedColumns,
    totalRowsSeen
  };
}
