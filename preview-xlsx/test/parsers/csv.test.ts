import * as assert from 'assert';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { parseCsv, parseCsvFile } from '../../src/parsers/csv';
import { LIMITS, LimitExceededError } from '../../src/limits';

const opts = { maxRows: 1000, maxFileSizeBytes: 10 * 1024 * 1024 };

describe('parseCsv', () => {
  it('parses basic comma rows', () => {
    const r = parseCsv(Buffer.from('a,b,c\n1,2,3\n'), ',', opts);
    assert.deepStrictEqual(r.rows, [['a', 'b', 'c'], ['1', '2', '3']]);
  });

  it('strips UTF-8 BOM', () => {
    const r = parseCsv(Buffer.from('﻿a,b\n1,2\n'), ',', opts);
    assert.strictEqual(r.rows[0][0], 'a');
  });

  it('handles CRLF line endings', () => {
    const r = parseCsv(Buffer.from('a,b\r\n1,2\r\n'), ',', opts);
    assert.deepStrictEqual(r.rows, [['a', 'b'], ['1', '2']]);
  });

  it('handles quoted comma', () => {
    const r = parseCsv(Buffer.from('"a,b",c\n'), ',', opts);
    assert.deepStrictEqual(r.rows, [['a,b', 'c']]);
  });

  it('handles quoted newline', () => {
    const r = parseCsv(Buffer.from('"a\nb",c\n'), ',', opts);
    assert.deepStrictEqual(r.rows, [['a\nb', 'c']]);
  });

  it('handles escaped double quote', () => {
    const r = parseCsv(Buffer.from('"a""b",c\n'), ',', opts);
    assert.deepStrictEqual(r.rows, [['a"b', 'c']]);
  });

  it('preserves leading equals (no formula stripping)', () => {
    const r = parseCsv(Buffer.from('=cmd|x,1\n'), ',', opts);
    assert.strictEqual(r.rows[0][0], '=cmd|x');
  });

  it('truncates beyond maxRows and reports totalRowsSeen', () => {
    let txt = '';
    for (let i = 0; i < 50; i++) txt += `${i}\n`;
    const r = parseCsv(Buffer.from(txt), ',', { maxRows: 10, maxFileSizeBytes: 1024 });
    assert.strictEqual(r.rows.length, 10);
    assert.strictEqual(r.truncated, true);
    assert.strictEqual(r.totalRowsSeen, 50);
  });

  it('clamps oversized cell', () => {
    const big = 'x'.repeat(LIMITS.cellStringLength + 100);
    const r = parseCsv(Buffer.from(`${big}\n`), ',', opts);
    assert.ok(r.rows[0][0].length <= LIMITS.cellStringLength + 1);
  });

  it('parses tab delimiter', () => {
    const r = parseCsv(Buffer.from('a\tb\n1\t2\n'), '\t', opts);
    assert.deepStrictEqual(r.rows, [['a', 'b'], ['1', '2']]);
  });

  it('parseCsvFile rejects oversize without reading body', async () => {
    const file = path.join(os.tmpdir(), `pcsv-${Date.now()}.csv`);
    fs.writeFileSync(file, 'a,b\n1,2\n');
    try {
      await assert.rejects(
        parseCsvFile(file, ',', { maxRows: 100, maxFileSizeBytes: 2 }),
        (e: unknown) => e instanceof LimitExceededError && (e as LimitExceededError).limit === 'fileSize'
      );
    } finally {
      fs.unlinkSync(file);
    }
  });

  it('flags truncatedColumns when row exceeds column cap', () => {
    const cols = LIMITS.columns + 5;
    const header = new Array(cols).fill('x').join(',');
    const r = parseCsv(Buffer.from(header + '\n'), ',', opts);
    assert.strictEqual(r.truncatedColumns, true);
    assert.strictEqual(r.rows[0].length, LIMITS.columns);
  });
});
