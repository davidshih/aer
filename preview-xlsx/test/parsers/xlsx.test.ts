import * as assert from 'assert';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';
import ExcelJS from 'exceljs';
import { parseXlsx } from '../../src/parsers/xlsx';
import { LimitExceededError } from '../../src/limits';

async function makeWorkbook(rows: number, cols: number): Promise<string> {
  const wb = new ExcelJS.Workbook();
  const ws = wb.addWorksheet('S1');
  for (let r = 0; r < rows; r++) {
    const arr: (string | number)[] = [];
    for (let c = 0; c < cols; c++) arr.push(r === 0 ? `c${c}` : `${r}-${c}`);
    ws.addRow(arr);
  }
  const file = path.join(os.tmpdir(), `pxlsx-${Date.now()}-${Math.random()}.xlsx`);
  await wb.xlsx.writeFile(file);
  return file;
}

describe('parseXlsx', () => {
  it('reads cells as text via streaming', async () => {
    const file = await makeWorkbook(3, 2);
    const data = await parseXlsx(file, { maxRows: 100, maxFileSizeBytes: 5 * 1024 * 1024 });
    assert.strictEqual(data.sheets.length, 1);
    assert.strictEqual(data.sheets[0].rows.length, 3);
    assert.strictEqual(data.sheets[0].rows[1][0], '1-0');
    fs.unlinkSync(file);
  });

  it('truncates beyond maxRows', async () => {
    const file = await makeWorkbook(50, 1);
    const data = await parseXlsx(file, { maxRows: 10, maxFileSizeBytes: 5 * 1024 * 1024 });
    assert.strictEqual(data.sheets[0].rows.length, 10);
    assert.strictEqual(data.sheets[0].truncated, true);
    assert.ok(data.sheets[0].totalRowsSeen >= 50);
    fs.unlinkSync(file);
  });

  it('rejects file exceeding size limit', async () => {
    const file = await makeWorkbook(2, 2);
    await assert.rejects(
      parseXlsx(file, { maxRows: 100, maxFileSizeBytes: 100 }),
      (e: unknown) => e instanceof LimitExceededError && (e as LimitExceededError).limit === 'fileSize'
    );
    fs.unlinkSync(file);
  });
});
