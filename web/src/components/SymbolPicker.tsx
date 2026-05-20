import { useEffect, useRef, useState } from "react";
import type { SymbolInfo } from "../types";

export const SYMBOL_CAT_ORDER = [
  "국내주식 (KOSPI)", "국내주식 (KOSDAQ)",
  "국내ETF/ETN (KOSPI)", "국내ETF/ETN (KOSDAQ)",
  "국내REITs (KOSPI)",
  "미국 NASDAQ 주식", "미국 NYSE 주식", "미국 AMEX 주식",
  "미국 NASDAQ ETF/ETN", "미국 NYSE ETF/ETN", "미국 AMEX ETF/ETN",
  "일본 주식", "일본 ETF/ETN",
  "홍콩 주식", "홍콩 ETF/ETN",
  "자산", "변동성", "금리·환율", "신용", "거시지표", "심리", "개별종목",
];

/** 팝오버를 외부 클릭·Esc로 닫는 훅. 트리거+패널을 감싸는 ref를 반환. */
export function usePopoverDismiss<T extends HTMLElement>(
  open: boolean, setOpen: (v: boolean) => void,
) {
  const ref = useRef<T>(null);
  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, setOpen]);
  return ref;
}

/** 카테고리 헤더로 그룹화된 검색 가능한 선택 목록. */
export function CategoryList({ items, order, selected, search, onPick }: {
  items: { key: string; label: string; cat: string; badge?: string }[];
  order: string[];
  selected?: string;
  search?: string;
  onPick: (key: string) => void;
}) {
  const q = (search ?? "").trim().toLowerCase();
  const filtered = q
    ? items.filter((i) => i.label.toLowerCase().includes(q)
                       || i.key.toLowerCase().includes(q))
    : items;

  const byCat: Record<string, typeof items> = {};
  for (const it of filtered) (byCat[it.cat] ??= []).push(it);
  const cats = order.filter((c) => byCat[c]?.length)
    .concat(Object.keys(byCat).filter((c) => !order.includes(c)));

  // 큰 리스트는 잘라서 표시 (검색이 좁히기 전 4000+개 그대로 렌더 방지)
  const LIMIT_PER_CAT = q ? 200 : 50;

  return (
    <div className="cat-list">
      {cats.length === 0 && <div className="cat-empty">결과 없음</div>}
      {cats.map((cat) => {
        const items = byCat[cat];
        const shown = items.slice(0, LIMIT_PER_CAT);
        const hidden = items.length - shown.length;
        return (
          <div key={cat}>
            <div className="cat-head">{cat} <span className="cat-head-n">{items.length}</span></div>
            {shown.map((it) => (
              <button
                key={it.key} type="button"
                className={"cat-item" + (it.key === selected ? " sel" : "")}
                onClick={() => onPick(it.key)}
              >
                <span>{it.label}</span>
                {it.badge && <span className="cat-item-badge">{it.badge}</span>}
              </button>
            ))}
            {hidden > 0 && (
              <div className="cat-empty" style={{ fontSize: 11 }}>
                +{hidden}개 더 — 검색으로 좁혀주세요
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/** 종목 선택 칩 — 클릭 시 검색·카테고리 팝오버가 열린다. */
export default function SymbolPicker({ symbols, value, tradableOnly, onChange }: {
  symbols: SymbolInfo[];
  value: string;
  tradableOnly?: boolean;
  onChange: (sym: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const ref = usePopoverDismiss<HTMLSpanElement>(open, setOpen);

  // tradableOnly=true: 매수 가능 종목 = KIS 마스터의 모든 종목 (indicators 없어도 OK)
  // tradableOnly=false: 조건 평가용 → indicators 있는 종목만
  const list = symbols.filter((s) =>
    tradableOnly ? s.tradable : s.indicators.length > 0);
  const empty = tradableOnly && list.length === 0 && symbols.length > 0;

  return (
    <span className="chip-wrap" ref={ref}>
      <button type="button" className="chip" onClick={() => setOpen((v) => !v)}>
        {value || "종목 선택"}
        <span className="chip-caret">▾</span>
      </button>
      {open && (
        <div className="popover">
          {empty ? (
            <div className="cat-empty" style={{ padding: 16, lineHeight: 1.6 }}>
              매수 가능 종목 목록을 준비 중입니다.<br/>
              서버가 KIS 공식 마스터를 다운로드 중입니다.
              잠시 후 다시 시도해주세요.
            </div>
          ) : (
            <>
              <input
                className="pop-search" placeholder="종목명 또는 코드 검색…" autoFocus
                value={search} onChange={(e) => setSearch(e.target.value)}
              />
              <div className="op-label">종목</div>
              <CategoryList
                items={list.map((s) => ({
                  key: s.symbol,
                  label: s.name ? `${s.symbol} ${s.name}` : s.symbol,
                  cat: s.category,
                  badge: s.has_backtest_data === false ? "백테스트 불가" : undefined,
                }))}
                order={SYMBOL_CAT_ORDER}
                selected={value}
                search={search}
                onPick={(k) => { onChange(k); setOpen(false); }}
              />
            </>
          )}
        </div>
      )}
    </span>
  );
}
