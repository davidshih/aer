interface SheetData {
  name: string;
  columns: string[];
  rows: string[][];
  truncated: boolean;
  truncatedColumns: boolean;
  totalRowsSeen: number;
}

export interface GridState {
  sortColumn: number | null;
  sortDir: 'asc' | 'desc' | null;
  filters: string[];
}

export interface GridController {
  applyState(): void;
  destroy(): void;
}

const ROW_HEIGHT = 22;
const OVERSCAN = 8;
const FILTER_DEBOUNCE_MS = 80;

function compareNumeric(a: string, b: string): number {
  const an = Number(a);
  const bn = Number(b);
  if (Number.isFinite(an) && Number.isFinite(bn)) return an - bn;
  return a.localeCompare(b);
}

function recomputeFiltered(sheet: SheetData, state: GridState): number[] {
  const filters = state.filters.map((f) => f.toLowerCase());
  const anyFilter = filters.some((f) => f.length > 0);
  const indices: number[] = [];
  for (let i = 0; i < sheet.rows.length; i++) {
    if (!anyFilter) {
      indices.push(i);
      continue;
    }
    const row = sheet.rows[i];
    let ok = true;
    for (let c = 0; c < filters.length; c++) {
      const f = filters[c];
      if (!f) continue;
      if ((row[c] ?? '').toLowerCase().indexOf(f) === -1) {
        ok = false;
        break;
      }
    }
    if (ok) indices.push(i);
  }
  if (state.sortColumn !== null && state.sortDir !== null) {
    const col = state.sortColumn;
    const dir = state.sortDir === 'asc' ? 1 : -1;
    indices.sort((ia, ib) => dir * compareNumeric(sheet.rows[ia][col] ?? '', sheet.rows[ib][col] ?? ''));
  }
  return indices;
}

export function mountGrid(
  container: HTMLElement,
  sheet: SheetData,
  state: GridState
): GridController {
  if (state.filters.length !== sheet.columns.length) {
    state.filters = new Array(sheet.columns.length).fill('');
  }

  container.replaceChildren();

  const table = document.createElement('table');
  const thead = document.createElement('thead');
  const headerRow = document.createElement('tr');
  const sortArrows: HTMLSpanElement[] = [];

  const idxTh = document.createElement('th');
  idxTh.textContent = '#';
  headerRow.appendChild(idxTh);

  sheet.columns.forEach((col, ci) => {
    const th = document.createElement('th');
    th.textContent = col;
    const arrow = document.createElement('span');
    arrow.className = 'arrow';
    th.appendChild(arrow);
    sortArrows.push(arrow);
    th.addEventListener('click', () => {
      if (state.sortColumn !== ci) {
        state.sortColumn = ci;
        state.sortDir = 'asc';
      } else if (state.sortDir === 'asc') {
        state.sortDir = 'desc';
      } else {
        state.sortColumn = null;
        state.sortDir = null;
      }
      controller.applyState();
    });
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);

  const filterRow = document.createElement('tr');
  filterRow.className = 'filter-row';
  filterRow.appendChild(document.createElement('th'));

  let debounceTimer: ReturnType<typeof setTimeout> | null = null;
  const debouncedApply = () => {
    if (debounceTimer !== null) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      debounceTimer = null;
      controller.applyState();
    }, FILTER_DEBOUNCE_MS);
  };

  sheet.columns.forEach((_, ci) => {
    const th = document.createElement('th');
    const input = document.createElement('input');
    input.type = 'text';
    input.value = state.filters[ci] ?? '';
    input.placeholder = 'filter…';
    input.dataset.filterIndex = String(ci);
    input.addEventListener('input', () => {
      state.filters[ci] = input.value;
      debouncedApply();
    });
    th.appendChild(input);
    filterRow.appendChild(th);
  });
  thead.appendChild(filterRow);
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  const topSpacer = document.createElement('tr');
  const topCell = document.createElement('td');
  topCell.className = 'spacer';
  topCell.colSpan = sheet.columns.length + 1;
  topSpacer.appendChild(topCell);

  const bottomSpacer = document.createElement('tr');
  const bottomCell = document.createElement('td');
  bottomCell.className = 'spacer';
  bottomCell.colSpan = sheet.columns.length + 1;
  bottomSpacer.appendChild(bottomCell);

  tbody.appendChild(topSpacer);
  tbody.appendChild(bottomSpacer);
  table.appendChild(tbody);
  container.appendChild(table);

  let filtered: number[] = [];

  const renderWindow = () => {
    const total = filtered.length;
    const scrollTop = container.scrollTop;
    const viewport = container.clientHeight;
    const first = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
    const last = Math.min(total, Math.ceil((scrollTop + viewport) / ROW_HEIGHT) + OVERSCAN);

    while (tbody.children.length > 2) {
      tbody.removeChild(tbody.children[1]);
    }

    topCell.style.height = `${first * ROW_HEIGHT}px`;
    bottomCell.style.height = `${Math.max(0, (total - last) * ROW_HEIGHT)}px`;

    const frag = document.createDocumentFragment();
    for (let i = first; i < last; i++) {
      const rowIdx = filtered[i];
      const rowData = sheet.rows[rowIdx];
      const tr = document.createElement('tr');
      tr.style.height = `${ROW_HEIGHT}px`;
      const idxTd = document.createElement('td');
      idxTd.className = 'row-index';
      idxTd.textContent = String(rowIdx + 1);
      tr.appendChild(idxTd);
      for (let c = 0; c < sheet.columns.length; c++) {
        const td = document.createElement('td');
        td.textContent = rowData[c] ?? '';
        tr.appendChild(td);
      }
      frag.appendChild(tr);
    }
    tbody.insertBefore(frag, bottomSpacer);
  };

  const updateSortArrows = () => {
    sortArrows.forEach((arrow, ci) => {
      if (state.sortColumn === ci) {
        arrow.textContent = state.sortDir === 'asc' ? ' ▲' : state.sortDir === 'desc' ? ' ▼' : '';
      } else {
        arrow.textContent = '';
      }
    });
  };

  const onScroll = () => renderWindow();
  container.addEventListener('scroll', onScroll, { passive: true });

  const controller: GridController = {
    applyState() {
      filtered = recomputeFiltered(sheet, state);
      updateSortArrows();
      renderWindow();
    },
    destroy() {
      container.removeEventListener('scroll', onScroll);
      if (debounceTimer !== null) clearTimeout(debounceTimer);
      container.replaceChildren();
    }
  };

  controller.applyState();
  return controller;
}
