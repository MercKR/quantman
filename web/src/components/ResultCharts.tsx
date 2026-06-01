import { useState } from "react";
import {
  Area, Bar, BarChart, CartesianGrid, Cell, ComposedChart, Line, LineChart,
  ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import type { IrDistribution, IrEventStat, IrICStat, IrPartition, IrSweepBucket } from "../types";

/* recharts SVG는 CSS var를 못 받아 토큰값(DESIGN.md)을 직접 인라인한다(EquityChart와 동일 규약).
   변경 시 web/src/index.css :root와 동기화. up=상승/이익(빨강) · down=하락/손실(파랑, 한국 관례). */
const C = {
  accent: "#d97757", strong: "#ad5019", muted: "#6f6a62", grid: "#e8e3db",
  text: "#20201d", up: "#de3033", down: "#1668c4", upSoft: "#fdeceb", downSoft: "#e7f0fa",
};

const num = (v: unknown): number => Number(String(v).split("=").pop());
const f2 = (v: number | null | undefined) =>
  v == null || Number.isNaN(v) ? "—" : (Number.isInteger(v) ? String(v) : v.toFixed(2));

function Box({ title, sub, children }:
  { title: string; sub?: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: C.text, marginBottom: 2 }}>{title}</div>
      {sub ? <div style={{ fontSize: 12, color: C.muted, marginBottom: 6 }}>{sub}</div> : null}
      {children}
    </div>
  );
}

function tip(rows: [string, string][]) {
  return ({ active, payload, label }:
    { active?: boolean; payload?: { payload: Record<string, unknown> }[]; label?: unknown }) => {
    if (!active || !payload?.length) return null;
    return (
      <div style={{ background: "#fff", border: `1px solid ${C.grid}`, borderRadius: 8,
        padding: "8px 10px", fontSize: 12, color: C.muted }}>
        <div style={{ fontWeight: 600, color: C.text, marginBottom: 4 }}>{String(label)}</div>
        {rows.map(([k, key]) => (
          <div key={k}>{k} {f2(payload[0].payload[key] as number)}</div>
        ))}
      </div>
    );
  };
}

// ── 펼침 차트 (파라미터·종목·국면·기간분할) — buckets 동형 ─────────────────────
type SweepMetric = { key: keyof IrSweepBucket; label: string; kind: "signed" | "loss" | "pos" };
const SWEEP_METRICS: SweepMetric[] = [
  { key: "cum_return", label: "누적(%)", kind: "signed" },
  { key: "cagr", label: "CAGR(%)", kind: "signed" },
  { key: "sharpe", label: "샤프", kind: "signed" },
  { key: "sortino", label: "소르티노", kind: "signed" },
  { key: "mdd", label: "MDD(%)", kind: "loss" },
  { key: "win_rate", label: "승률(%)", kind: "pos" },
  { key: "payoff_ratio", label: "손익비", kind: "pos" },
];

const colorFor = (m: SweepMetric, v: number | null | undefined) =>
  m.kind === "loss" ? C.down : m.kind === "pos" ? C.accent
    : (v ?? 0) >= 0 ? C.up : C.down;

export function SweepChart({ axis, buckets, axes }: {
  axis: string;
  buckets: Record<string, IrSweepBucket>;
  axes?: { path: string; values: (number | string)[] }[];
}) {
  const [mi, setMi] = useState(0);
  const m = SWEEP_METRICS[mi];
  const entries = Object.entries(buckets).filter(([, b]) => !b.error);
  if (!entries.length) return null;

  // 파라미터 단일축이고 키가 모두 수치면 라인(민감도 곡선), 아니면 막대(범주 비교).
  const numericX = axis === "parameter" && (axes?.length ?? 1) <= 1
    && entries.every(([k]) => !Number.isNaN(num(k)));
  const data = entries.map(([k, b]) => ({
    label: k, x: numericX ? num(k) : k, value: (b[m.key] as number) ?? null, n: b.n,
  }));
  if (numericX) (data as { x: number }[]).sort((a, z) => a.x - z.x);

  const Tip = tip([[m.label, "value"], ["표본", "n"]]);
  return (
    <Box title="시각화" sub={numericX ? "지표를 바꿔 민감도 곡선의 형태를 보세요 (평평=robust)"
      : "지표를 바꿔 구간별로 비교하세요"}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 8 }}>
        {SWEEP_METRICS.map((mm, i) => (
          <button key={mm.key} type="button" onClick={() => setMi(i)}
            style={{
              fontSize: 12, padding: "3px 9px", borderRadius: 999, cursor: "pointer",
              border: `1px solid ${i === mi ? C.accent : C.grid}`,
              background: i === mi ? C.accent : "#fff", color: i === mi ? "#fff" : C.muted,
            }}>{mm.label}</button>
        ))}
      </div>
      <ResponsiveContainer width="100%" height={260}>
        {numericX ? (
          <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
            <CartesianGrid stroke={C.grid} />
            <XAxis dataKey="x" type="number" domain={["dataMin", "dataMax"]}
              tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} width={48} />
            <Tooltip content={<Tip />} />
            <ReferenceLine y={0} stroke={C.muted} strokeDasharray="3 3" />
            <Line type="monotone" dataKey="value" stroke={C.accent} strokeWidth={2}
              dot={{ r: 2 }} isAnimationActive={false} />
          </LineChart>
        ) : (
          <BarChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
            <CartesianGrid stroke={C.grid} vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} interval={0}
              angle={data.length > 6 ? -30 : 0} textAnchor={data.length > 6 ? "end" : "middle"}
              height={data.length > 6 ? 60 : 30} />
            <YAxis tick={{ fontSize: 11 }} width={48} />
            <Tooltip content={<Tip />} cursor={{ fill: C.accent + "14" }} />
            <ReferenceLine y={0} stroke={C.muted} strokeDasharray="3 3" />
            <Bar dataKey="value" isAnimationActive={false}>
              {data.map((d, i) => <Cell key={i} fill={colorFor(m, d.value)} />)}
            </Bar>
          </BarChart>
        )}
      </ResponsiveContainer>
    </Box>
  );
}

// ── 신호값 분포 — 분위수 박스/휘스커 (q05–q95 · q25–q75 · q50 · 평균) ───────────
function QuantileBox({ rows }: {
  rows: { label: string; d: IrDistribution }[];
}) {
  const vals = rows.flatMap(({ d }) => [d.quantiles?.q05, d.quantiles?.q95, d.mean])
    .filter((v): v is number => v != null && !Number.isNaN(v));
  if (!vals.length) return null;
  let lo = Math.min(...vals), hi = Math.max(...vals);
  if (lo === hi) { lo -= 1; hi += 1; }
  const pad = (hi - lo) * 0.08; lo -= pad; hi += pad;
  const X = (v: number) => ((v - lo) / (hi - lo)) * 100;
  const W = 100, H = 30;
  return (
    <div>
      {rows.map(({ label, d }) => {
        const q = d.quantiles ?? {};
        return (
          <div key={label} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
            <div style={{ width: 90, fontSize: 12, color: C.muted, textAlign: "right",
              overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{label}</div>
            <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
              style={{ flex: 1, height: 30 }}>
              {q.q05 != null && q.q95 != null && (
                <line x1={X(q.q05)} x2={X(q.q95)} y1={H / 2} y2={H / 2}
                  stroke={C.muted} strokeWidth={1} vectorEffect="non-scaling-stroke" />
              )}
              {q.q25 != null && q.q75 != null && (
                <rect x={X(q.q25)} y={H / 2 - 7} width={Math.max(0.4, X(q.q75) - X(q.q25))} height={14}
                  fill={C.accent} fillOpacity={0.25} stroke={C.accent} vectorEffect="non-scaling-stroke" />
              )}
              {q.q50 != null && (
                <line x1={X(q.q50)} x2={X(q.q50)} y1={H / 2 - 8} y2={H / 2 + 8}
                  stroke={C.strong} strokeWidth={2} vectorEffect="non-scaling-stroke" />
              )}
              {d.mean != null && (
                <circle cx={X(d.mean)} cy={H / 2} r={2.5} fill={C.text} />
              )}
            </svg>
            <div style={{ width: 120, fontSize: 11, color: C.muted, fontVariantNumeric: "tabular-nums" }}>
              중앙 {f2(q.q50)} · 평균 {f2(d.mean)}
            </div>
          </div>
        );
      })}
      <div style={{ fontSize: 11, color: C.muted, marginTop: 2 }}>
        막대 q25–q75 · 가는선 q05–q95 · 진한선 중앙값 · 점 평균
      </div>
    </div>
  );
}

export function SignalDistChart({ overall, byRegime }: {
  overall: IrDistribution; byRegime?: IrPartition | null;
}) {
  const rows: { label: string; d: IrDistribution }[] = [{ label: "전체", d: overall }];
  if (byRegime?.by_label) {
    for (const [k, d] of Object.entries(byRegime.by_label)) rows.push({ label: k, d });
  }
  return <Box title="시각화" sub="신호값의 분포 폭과 치우침(skew)을 봅니다 — 손익 아님">
    <QuantileBox rows={rows} />
  </Box>;
}

// ── 팩터 IC — horizon별 평균 IC 막대 (유의 p<0.05 강조) ────────────────────────
export function ICChart({ windows, byWindow }: {
  windows: string[];
  byWindow: Record<string, { overall: IrICStat }>;
}) {
  const data = windows.map((w) => {
    const o = byWindow[w]?.overall ?? ({} as IrICStat);
    return { label: `${w}일`, value: o.mean ?? null, sig: o.p_value != null && o.p_value < 0.05,
      ir: o.ir, t: o.t_stat, p: o.p_value, n: o.n };
  });
  if (!data.length) return null;
  const Tip = tip([["평균 IC", "value"], ["IR", "ir"], ["t", "t"], ["p", "p"], ["표본", "n"]]);
  return (
    <Box title="시각화" sub="예측 horizon별 평균 IC. 0에서 멀고 유의(진한 막대)할수록 예측력 ↑">
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
          <CartesianGrid stroke={C.grid} vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} width={48} />
          <Tooltip content={<Tip />} cursor={{ fill: C.accent + "14" }} />
          <ReferenceLine y={0} stroke={C.muted} />
          <Bar dataKey="value" isAnimationActive={false}>
            {data.map((d, i) => (
              <Cell key={i} fill={(d.value ?? 0) >= 0 ? C.up : C.down}
                fillOpacity={d.sig ? 1 : 0.35} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Box>
  );
}

// ── 이벤트 스터디 — forward 수익 곡선 + MAE/MFE 밴드 ──────────────────────────
export function EventStudyChart({ windows, overall }: {
  windows: string[];
  overall: Record<string, IrEventStat>;
}) {
  const data = [...windows]
    .sort((a, z) => (Number(a) || 0) - (Number(z) || 0))
    .map((w) => {
      const o = overall[w] ?? ({} as IrEventStat);
      return { label: `${w}일`, mean: o.mean ?? null,
        mae: o.mean_mae ?? null, mfe: o.mean_mfe ?? null,
        band: [o.mean_mae ?? null, o.mean_mfe ?? null] as [number | null, number | null],
        prob: o.prob_positive, p: o.p_value, n: o.n };
    });
  if (!data.length) return null;
  const Tip = tip([["평균수익", "mean"], ["MAE", "mae"], ["MFE", "mfe"],
    ["양(+)확률", "prob"], ["p", "p"], ["표본", "n"]]);
  return (
    <Box title="시각화"
      sub="진입 후 경과일별 평균 forward 수익(선) · 평균 최대낙폭~최대상승 범위(음영)">
      <ResponsiveContainer width="100%" height={260}>
        <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
          <CartesianGrid stroke={C.grid} />
          <XAxis dataKey="label" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} width={48} />
          <Tooltip content={<Tip />} />
          <ReferenceLine y={0} stroke={C.muted} strokeDasharray="3 3" />
          <Area dataKey="band" stroke="none" fill={C.accent} fillOpacity={0.12}
            isAnimationActive={false} />
          <Line type="monotone" dataKey="mean" stroke={C.accent} strokeWidth={2}
            dot={{ r: 2 }} isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </Box>
  );
}
