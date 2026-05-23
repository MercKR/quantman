import {
  CartesianGrid, Legend, Line, LineChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";

interface Point { date: string; value: number | null }

interface Props {
  equity: Point[];
  benchmark?: Point[];
}

/** 자산곡선 차트 — 전략 vs Buy&Hold. */
export default function EquityChart({ equity, benchmark }: Props) {
  // 데이터가 1점뿐이면 recharts가 x축에 같은 날짜를 반복 렌더해 버그처럼 보인다.
  // 곡선이 그려질 만큼 쌓이기 전에는 안내 문구로 대체.
  const distinctDates = new Set(equity.map((p) => p.date)).size;
  if (distinctDates < 2) {
    return (
      <div className="empty" style={{ height: 120 }}>
        데이터가 아직 충분하지 않습니다 — 사이클이 며칠 쌓이면 곡선이 그려집니다.
      </div>
    );
  }

  const merged = equity.map((p, i) => ({
    date: p.date,
    전략: p.value,
    "Buy&Hold": benchmark?.[i]?.value ?? null,
  }));

  const fmt = (v: number) =>
    v >= 1e8 ? `${(v / 1e8).toFixed(1)}억`
      : v >= 1e4 ? `${Math.round(v / 1e4)}만` : `${v}`;

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={merged} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
        {/* recharts SVG는 CSS var를 받지 못해 토큰값(DESIGN.md)을 직접 인라인한다.
            변경 시 두 군데를 동기화: web/src/index.css :root vs 이 파일. */}
        <CartesianGrid stroke="#e8e3db" />
        <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={50} />
        <YAxis tickFormatter={fmt} tick={{ fontSize: 11 }} width={52} />
        <Tooltip
          formatter={(v) => `${Number(v).toLocaleString()}원`}
          labelStyle={{ color: "#6f6a62" }}
        />
        <Legend />
        <Line type="monotone" dataKey="전략" stroke="#d97757"
              dot={false} strokeWidth={2} />
        <Line type="monotone" dataKey="Buy&Hold" stroke="#6f6a62"
              dot={false} strokeWidth={1.5} strokeDasharray="4 3" />
      </LineChart>
    </ResponsiveContainer>
  );
}
