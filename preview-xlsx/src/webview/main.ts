import { mountGrid, GridState, GridController } from './grid';

interface SheetData {
  name: string;
  columns: string[];
  rows: string[][];
  truncated: boolean;
  truncatedColumns: boolean;
  totalRowsSeen: number;
}
interface WorkbookData {
  sheets: SheetData[];
  warnings: string[];
}

const statusEl = document.getElementById('status') as HTMLElement;
const tabsEl = document.getElementById('tabs') as HTMLElement;
const gridEl = document.getElementById('grid') as HTMLElement;

let workbook: WorkbookData | null = null;
let activeSheet = 0;
let controller: GridController | null = null;
const stateBySheet = new Map<number, GridState>();

function setStatus(text: string, isWarning = false, isError = false): void {
  statusEl.textContent = text;
  statusEl.classList.toggle('warning', isWarning);
  statusEl.classList.toggle('error', isError);
}

function renderTabs(): void {
  tabsEl.replaceChildren();
  if (!workbook) return;
  workbook.sheets.forEach((s, i) => {
    const btn = document.createElement('button');
    btn.className = 'tab';
    btn.type = 'button';
    btn.role = 'tab';
    btn.setAttribute('aria-selected', String(i === activeSheet));
    btn.textContent = s.name;
    btn.addEventListener('click', () => {
      if (i === activeSheet) return;
      activeSheet = i;
      renderTabs();
      mountActive();
    });
    tabsEl.appendChild(btn);
  });
}

function mountActive(): void {
  if (controller) {
    controller.destroy();
    controller = null;
  }
  if (!workbook) return;
  const sheet = workbook.sheets[activeSheet];
  if (!sheet) return;
  let state = stateBySheet.get(activeSheet);
  if (!state) {
    state = { sortColumn: null, sortDir: null, filters: new Array(sheet.columns.length).fill('') };
    stateBySheet.set(activeSheet, state);
  }
  controller = mountGrid(gridEl, sheet, state);

  const parts = [`${sheet.totalRowsSeen} rows`, `${sheet.columns.length} cols`];
  if (sheet.truncated) parts.push(`(rows truncated to ${sheet.rows.length})`);
  if (sheet.truncatedColumns) parts.push('(columns truncated)');
  if (workbook.warnings.length > 0) parts.push(workbook.warnings.join(' '));
  setStatus(parts.join(' · '), sheet.truncated || sheet.truncatedColumns || workbook.warnings.length > 0);
}

window.addEventListener('message', (ev: MessageEvent) => {
  const msg = ev.data as { type: string; payload?: WorkbookData; message?: string };
  if (msg.type === 'data' && msg.payload) {
    workbook = msg.payload;
    activeSheet = 0;
    stateBySheet.clear();
    renderTabs();
    mountActive();
  } else if (msg.type === 'error') {
    workbook = null;
    if (controller) {
      controller.destroy();
      controller = null;
    }
    tabsEl.replaceChildren();
    gridEl.replaceChildren();
    setStatus(msg.message ?? 'Unknown error', false, true);
  }
});
