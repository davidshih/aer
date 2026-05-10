export const LIMITS = {
  fileSizeBytesDefault: 50 * 1024 * 1024,
  fileSizeBytesHardMax: 200 * 1024 * 1024,
  rowsDefault: 100_000,
  rowsHardMax: 250_000,
  columns: 1024,
  cellStringLength: 32 * 1024
} as const;

export class LimitExceededError extends Error {
  constructor(public readonly limit: string, public readonly value: number) {
    super(`limit exceeded: ${limit} reached ${value}`);
    this.name = 'LimitExceededError';
  }
}

export function clampString(s: string): string {
  if (s.length <= LIMITS.cellStringLength) return s;
  return s.slice(0, LIMITS.cellStringLength) + '…';
}
