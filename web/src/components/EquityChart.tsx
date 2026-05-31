import { useState } from "react";
import {
  CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer,
  Scatter, Tooltip, XAxis, YAxis,
} from "recharts";

interface Point { date: string; value: number | null }
type Trade = Record<string, string | number | null>;

interface Props {
  equity: Point[];
  benchmark?: Point[];
  trades?: Trade[];        // 있으면 진입▲/청산▼ 지점을 자산곡선 위에 마킹
}

/* recharts SVG는 CSS var를 못 받아 토큰값(DESIGN.md)을 직접 인라인한다.
   변경 시 web/src/index.css :root와 동기화. up=매수/상승(빨강), down=매도/하락(파랑). */
const C = {
  accent: "#d97757", muted: "#6f6a62", grid: "#e8e3db",
  up: "#de3033", down: "#1668c4", ink: "#20201d",
};

const won = (v: number | null | undefined) =>
  v == null ? "—" : `${Math.round(v).toLocaleString()}원`;
const px = (v: number | null | undefined) =>
  v == null ? "—" : `@${Number(v).toLocaleString()}`;   // 종목 통화 단위 미상 → @가격 중립표기

// 매수 ▲ (자산곡선 점 위에 위쪽 삼각형)
function BuyMarker({ cx, cy }: { cx?: number; cy?: number }) {
  if (cx == null || cy == null) return null;
  return <path d={`M${cx},${cy - 7} L${cx - 6},${cy + 5} L${cx + 6},${cy + 5} Z`}
    fill={C.up} stroke="#fff" strokeWidth={1} />;
}
// 매도 ▼ (아래쪽 삼각형)
function SellMarker({ cx, cy }: { cx?: number; cy?: number }) {
  if (cx == null || cy == null) return null;
  return <path d={`M${cx},${cy + 7} L${cx - 6},${cy - 5} L${cx + 6},${cy - 5} Z`}
    fill={C.down} stroke="#fff" strokeWidth={1} />;
}

interface Row {
  date: string;
  전략: number | null;
  "Buy&Hold": number | null;
  buy: number | null;
  sell: number | null;
  buyInfo: { sym?: string; price: number | null }[];
  sellInfo: { sym?: string; price: number | null; ret: number | null }[];
}

function ChartTooltip({ active, payload, label }:
  { active?: boolean; payload?: { payload: Row }[]; label?: string }) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div style={{
      background: "#fff", border: `1px solid ${C.grid}`, borderRadius: 8,
      padding: "8px 10px", fontSize: 12, color: C.muted,
    }}>
      <div style={{ fontWeight: 600, color: C.ink, marginBottom: 4 }}>{label}</div>
      <div>전략 {won(row.전략)}</div>
      {row["Buy&Hold"] != null && <div>Buy&Hold {won(row["Buy&Hold"])}</div>}
      {row.buyInfo.map((b, k) => (
        <div key={`b${k}`} style={{ color: C.up, marginTop: 2 }}>
          ▲ 매수 {b.sym ? `${b.sym} ` : ""}{px(b.price)}
        </div>
      ))}
      {row.sellInfo.map((s, k) => (
        <div key={`s${k}`} style={{ color: C.down, marginTop: 2 }}>
          ▼ 매도 {s.sym ? `${s.sym} ` : ""}{px(s.price)}
          {s.ret != null ? ` (${s.ret >= 0 ? "+" : ""}${s.ret.toFixed(1)}%)` : ""}
        </div>
      ))}
    </div>
  );
}

/** 자산곡선 차트 — 전략 vs Buy&Hold. trades가 있으면 진입▲/청산▼ 마킹. */
export default function EquityChart({ equity, benchmark, trades }: Props) {
  const [showTrades, setShowTrades] = useState(true);

  // 데이터가 1점뿐이면 recharts가 x축에 같은 날짜를 반복 렌더해 버그처럼 보인다.
  const distinctDates = new Set(equity.map((p) => p.date)).size;
  if (distinctDates < 2) {
    return (
      <div className="empty" style={{ height: 120 }}>
        데이터가 아직 충분하지 않습니다 — 사이클이 며칠 쌓이면 곡선이 그려집니다.
      </div>
    );
  }

  const idx = new Map<string, number>();
  const merged: Row[] = equity.map((p, i) => {
    idx.set(p.date, i);
    return {
      date: p.date, 전략: p.value, "Buy&Hold": benchmark?.[i]?.value ?? null,
      buy: null, sell: null, buyInfo: [], sellInfo: [],
    };
  });

  const hasTrades = !!(trades && trades.length);
  if (hasTrades && showTrades) {
    for (const t of trades!) {
      const sym = (t["종목"] as string) ?? undefined;
      const bi = idx.get(t["진입일"] as string);
      const si = idx.get(t["청산일"] as string);
      if (bi != null) {
        merged[bi].buy = merged[bi].전략;            // 마커는 그날 자산곡선 값 위에
        merged[bi].buyInfo.push({ sym, price: (t["진입가"] as number) ?? null });
      }
      if (si != null) {
        merged[si].sell = merged[si].전략;
        merged[si].sellInfo.push({
          sym, price: (t["청산가"] as number) ?? null,
          ret: (t["수익률(%)"] as number) ?? null,
        });
      }
    }
  }

  const fmt = (v: number) =>
    v >= 1e8 ? `${(v / 1e8).toFixed(1)}억`
      : v >= 1e4 ? `${Math.round(v / 1e4)}만` : `${v}`;

  return (
    <div>
      {hasTrades && (
        <label style={{
          display: "flex", alignItems: "center", gap: 6, fontSize: 12,
          color: C.muted, marginBottom: 6, cursor: "pointer", userSelect: "none",
        }}>
          <input type="checkbox" checked={showTrades}
                 onChange={(e) => setShowTrades(e.target.checked)} />
          거래 표시 (매수 ▲ · 매도 ▼)
        </label>
      )}
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={merged} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
          <CartesianGrid stroke={C.grid} />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={50} />
          <YAxis tickFormatter={fmt} tick={{ fontSize: 11 }} width={52} />
          <Tooltip content={<ChartTooltip />} />
          <Legend />
          <Line type="monotone" dataKey="전략" stroke={C.accent}
                dot={false} strokeWidth={2} />
          <Line type="monotone" dataKey="Buy&Hold" stroke={C.muted}
                dot={false} strokeWidth={1.5} strokeDasharray="4 3" />
          {hasTrades && showTrades && (
            <Scatter name="매수" dataKey="buy" fill={C.up}
                     shape={<BuyMarker />} legendType="triangle" isAnimationActive={false} />
          )}
          {hasTrades && showTrades && (
            <Scatter name="매도" dataKey="sell" fill={C.down}
                     shape={<SellMarker />} legendType="triangle" isAnimationActive={false} />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
