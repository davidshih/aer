export interface SheetData {
  name: string;
  columns: string[];
  rows: string[][];
  truncated: boolean;
  truncatedColumns: boolean;
  totalRowsSeen: number;
}

export interface WorkbookData {
  sheets: SheetData[];
  warnings: string[];
}

export interface ParseOptions {
  maxRows: number;
  maxFileSizeBytes: number;
}
