/** 공통 수치 포맷 — 모든 수치는 소수점 2자리까지, 정수면 .00 생략.
 *
 * fmt2(123.456) → "123.46"
 * fmt2(10)      → "10"
 * fmt2(0.5)     → "0.5"
 * fmt2(null)    → "-"
 */
export function fmt2(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return "-";
  return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

/** 원 금액 — 만원/억원 단위로 사람이 읽기 쉽게. */
export function wonReadable(n: number): string {
  if (n >= 1e8) return `${fmt2(n / 1e8)}억원`;
  if (n >= 1e4) return `${fmt2(n / 1e4)}만원`;
  return `${fmt2(n)}원`;
}
