import * as assert from 'assert';
import * as fs from 'fs';
import * as path from 'path';
import { parseCsv, parseCsvFile } from '../../src/parsers/csv';
import { parseXlsx } from '../../src/parsers/xlsx';
import { LIMITS, LimitExceededError } from '../../src/limits';

const FX = path.join(process.cwd(), 'test', 'fixtures');
const opts = { maxRows: 1000, maxFileSizeBytes: 5 * 1024 * 1024 };

describe('security · parser', () => {
  it('preserves hostile leading characters in CSV (no formula stripping)', () => {
    const buf = fs.readFileSync(path.join(FX, 'malicious-formula.csv'));
    const r = parseCsv(buf, ',', opts);
    const firstCol = r.rows.map((row) => row[0]);
    assert.deepStrictEqual(firstCol, [
      `=cmd|' /C calc'!A0`,
      `@SUM(1)*cmd`,
      `+HYPERLINK("x","y")`,
      `-cmd|fake`,
      ` =SUM(1,1)`,
      `\t=cmd|tabbed`,
      `=2+2`
    ]);
  });

  it('preserves raw HTML strings inside xlsx cells', async () => {
    const data = await parseXlsx(path.join(FX, 'malicious-html.xlsx'), opts);
    const cells = data.sheets[0].rows.map((r) => r[0]);
    assert.ok(cells.includes('<img src=x onerror="alert(1)">'), 'img tag preserved');
    assert.ok(cells.includes('<script>alert(1)</script>'), 'script tag preserved');
    assert.ok(cells.includes('javascript:alert(1)'), 'js scheme string preserved');
  });

  it('does not leak hyperlink target URLs into the parsed payload', async () => {
    const data = await parseXlsx(path.join(FX, 'malicious-link.xlsx'), opts);
    const json = JSON.stringify(data);
    assert.strictEqual(json.includes('javascript:'), false, 'javascript: target leaked');
    assert.strictEqual(json.includes('file://'), false, 'file:// target leaked');
    // display text still surfaces
    const cells = data.sheets[0].rows.flat();
    assert.ok(cells.includes('click me'));
    assert.ok(cells.includes('open file'));
  });

  it('LimitExceededError fires on tiny maxFileSizeBytes via parseCsvFile', async () => {
    const tmp = path.join(FX, '..', 'tmp-limit.csv');
    fs.writeFileSync(tmp, 'a,b\n1,2\n');
    try {
      await assert.rejects(
        parseCsvFile(tmp, ',', { maxRows: 100, maxFileSizeBytes: 1 }),
        (e: unknown) =>
          e instanceof LimitExceededError && (e as LimitExceededError).limit === 'fileSize'
      );
    } finally {
      fs.unlinkSync(tmp);
    }
  });

  it('truncates rows when maxRows is small', () => {
    const buf = Buffer.from('a\nb\nc\nd\ne\nf\n');
    const r = parseCsv(buf, ',', { maxRows: 3, maxFileSizeBytes: 1024 });
    assert.strictEqual(r.rows.length, 3);
    assert.strictEqual(r.truncated, true);
    assert.strictEqual(r.totalRowsSeen, 6);
  });

  it('flags truncatedColumns over the column cap', () => {
    const cols = LIMITS.columns + 10;
    const line = new Array(cols).fill('x').join(',');
    const r = parseCsv(Buffer.from(line + '\n'), ',', opts);
    assert.strictEqual(r.truncatedColumns, true);
    assert.strictEqual(r.rows[0].length, LIMITS.columns);
  });
});
