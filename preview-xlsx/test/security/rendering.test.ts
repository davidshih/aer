// jsdom does not enforce VS Code webview CSP. CSP is verified separately
// by csp.test.ts on the HTML string. This file only proves that hostile
// strings end up as text nodes inside #grid, never as elements.

import * as assert from 'assert';
import { JSDOM } from 'jsdom';
import { mountGrid, GridState } from '../../src/webview/grid';

interface SheetData {
  name: string;
  columns: string[];
  rows: string[][];
  truncated: boolean;
  truncatedColumns: boolean;
  totalRowsSeen: number;
}

const HOSTILE = [
  '<img src=x onerror="alert(1)">',
  '<script>alert(1)</script>',
  'javascript:alert(1)',
  '"><iframe src=evil>',
  '&#60;script&#62;'
];

function makeSheet(): SheetData {
  return {
    name: 's',
    columns: ['c1'],
    rows: HOSTILE.map((h) => [h]),
    truncated: false,
    truncatedColumns: false,
    totalRowsSeen: HOSTILE.length
  };
}

function bootstrapDom(): { dom: JSDOM; gridEl: HTMLElement } {
  const dom = new JSDOM(`<!DOCTYPE html><html><body><div id="grid" style="height:200px"></div></body></html>`, {
    pretendToBeVisual: true
  });
  // wire jsdom globals so grid.ts can reach document/Node
  const g = globalThis as Record<string, unknown>;
  g.window = dom.window;
  g.document = dom.window.document;
  g.Node = dom.window.Node;
  g.HTMLElement = dom.window.HTMLElement;
  const gridEl = dom.window.document.getElementById('grid') as unknown as HTMLElement;
  return { dom, gridEl };
}

describe('security · rendering', () => {
  let dom: JSDOM;
  let gridEl: HTMLElement;

  beforeEach(() => {
    ({ dom, gridEl } = bootstrapDom());
  });

  afterEach(() => {
    dom.window.close();
  });

  it('produces no <a>, <img>, <script>, or <iframe> elements inside #grid', () => {
    const state: GridState = { sortColumn: null, sortDir: null, filters: [''] };
    mountGrid(gridEl, makeSheet(), state);
    const offenders = gridEl.querySelectorAll('a, img, script, iframe');
    assert.strictEqual(offenders.length, 0, `found ${offenders.length} offending elements`);
  });

  it('renders each hostile cell as a single text node with raw content', () => {
    const state: GridState = { sortColumn: null, sortDir: null, filters: [''] };
    mountGrid(gridEl, makeSheet(), state);
    const dataTds = Array.from(gridEl.querySelectorAll('tbody tr td')).filter(
      (td) => !(td as HTMLElement).classList.contains('spacer') &&
              !(td as HTMLElement).classList.contains('row-index')
    );
    const seen = dataTds.map((td) => td.textContent ?? '');
    for (const h of HOSTILE) {
      assert.ok(seen.includes(h), `cell missing: ${h}`);
    }
    for (const td of dataTds) {
      if (!td.firstChild) continue;
      assert.strictEqual(
        td.firstChild.nodeType,
        dom.window.Node.TEXT_NODE,
        `cell first child not text node for "${td.textContent}"`
      );
    }
  });

  it('filter input keeps focus across keystrokes (A4 regression sentinel)', async () => {
    const state: GridState = { sortColumn: null, sortDir: null, filters: [''] };
    mountGrid(gridEl, makeSheet(), state);
    const input = gridEl.querySelector('tr.filter-row input') as HTMLInputElement;
    input.focus();
    assert.strictEqual(dom.window.document.activeElement, input);

    input.value = 's';
    input.dispatchEvent(new dom.window.Event('input', { bubbles: true }));
    input.value = 'sc';
    input.dispatchEvent(new dom.window.Event('input', { bubbles: true }));

    await new Promise((r) => setTimeout(r, 120)); // past 80ms debounce

    assert.strictEqual(
      dom.window.document.activeElement,
      input,
      'filter input lost focus after typing'
    );
    // sc filters down hostile rows containing "sc" → 2 (script tag + encoded)
    const rendered = gridEl.querySelectorAll('tbody tr').length;
    assert.ok(rendered >= 1, 'no rows rendered after filter');
  });
});
