/** 백테스트 지표를 평이한 한국어 평가로 풀어주는 카드.
 *  초중급 사용자가 "이 전략 쓸 만한가?"를 숫자 해석 없이 판단하도록 돕는다. */

type Tone = "good" | "ok" | "warn" | "bad";

const fmt = (v: number, d = 1) =>
  v.toLocaleString(undefined, { maximumFractionDigits: d });

const num = (v: number | null | undefined): number | null =>
  v == null || Number.isNaN(v) ? null : v;

export default function Verdict({ metrics }: {
  metrics: Record<string, number | null>;
}) {
  const ret = num(metrics.total_return);
  const cagr = num(metrics.cagr);
  const mdd = num(metrics.mdd);
  const sharpe = num(metrics.sharpe);
  const nTrades = num(metrics.n_trades);
  const excess = num(metrics.excess_return);

  const points: { cls: string; text: string }[] = [];

  if (excess != null) {
    if (excess >= 0)
      points.push({ cls: "pt-good",
        text: `같은 종목을 그냥 사서 보유했을 때보다 +${fmt(excess)}%p 더 벌었습니다.` });
    else
      points.push({ cls: "pt-warn",
        text: `그냥 사서 보유한 것보다 ${fmt(excess)}%p 뒤처졌습니다. 거래가 오히려 손해였습니다.` });
  }

  if (mdd != null) {
    const d = Math.abs(mdd);
    const cls = d <= 20 ? "pt-good" : d <= 40 ? "pt-warn" : "pt-bad";
    const word = d <= 20 ? "비교적 안정적입니다"
      : d <= 40 ? "꽤 큰 변동을 견딜 각오가 필요합니다"
      : "손실 구간이 매우 깊어 실전에서 버티기 어렵습니다";
    points.push({ cls,
      text: `최대 낙폭(MDD) ${fmt(mdd)}% — 보유 중 한때 자산이 이만큼 줄었습니다. ${word}.` });
  }

  if (sharpe != null) {
    const cls = sharpe >= 1 ? "pt-good" : sharpe >= 0.5 ? "pt-neutral" : "pt-warn";
    const word = sharpe >= 2 ? "매우 우수한"
      : sharpe >= 1 ? "양호한"
      : sharpe >= 0.5 ? "보통"
      : sharpe >= 0 ? "낮은" : "마이너스";
    points.push({ cls,
      text: `위험 대비 수익(샤프 ${fmt(sharpe, 2)})은 ${word} 수준입니다.` });
  }

  const thinSample = nTrades != null && nTrades < 10;
  if (thinSample)
    points.push({ cls: "pt-warn",
      text: `거래가 ${nTrades}회뿐입니다. 표본이 적어 결과를 그대로 믿기엔 이릅니다. `
          + `조건을 넓혀 거래 횟수를 늘려 보세요.` });

  let score = 0;
  if (sharpe != null)
    score += sharpe >= 2 ? 3 : sharpe >= 1 ? 2 : sharpe >= 0.5 ? 1 : sharpe >= 0 ? 0 : -2;
  if (mdd != null) {
    const d = Math.abs(mdd);
    score += d <= 15 ? 2 : d <= 25 ? 1 : d <= 40 ? 0 : -2;
  }
  if (excess != null)
    score += excess >= 50 ? 2 : excess >= 0 ? 1 : excess >= -20 ? 0 : -1;

  let tone: Tone;
  let grade: string;
  let tagline: string;

  if (thinSample) {
    tone = "warn"; grade = "표본 부족";
    tagline = "거래가 너무 적어 평가를 보류합니다";
  } else if (score >= 5) {
    tone = "good"; grade = "우수";
    tagline = "위험 대비 수익이 뛰어난 전략입니다";
  } else if (score >= 3) {
    tone = "good"; grade = "양호";
    tagline = "시장보다 나은, 쓸 만한 전략입니다";
  } else if (score >= 1) {
    tone = "ok"; grade = "보통";
    tagline = "장점과 약점이 섞여 있습니다";
  } else if (score >= -1) {
    tone = "warn"; grade = "주의";
    tagline = "수익보다 위험이 더 커 보입니다";
  } else {
    tone = "bad"; grade = "부족";
    tagline = "지금 형태로는 추천하기 어렵습니다";
  }

  const summary =
    ret != null && cagr != null
      ? `과거 데이터 기준 총 ${fmt(ret)}% (연평균 ${fmt(cagr)}%) 수익을 냈고, `
        + `그 과정에서 한때 자산이 최대 ${mdd != null ? fmt(mdd) : "?"}%까지 줄었습니다.`
      : "백테스트 기간이 짧아 일부 지표를 계산하지 못했습니다.";

  return (
    <div className={"verdict " + tone}>
      <div className="verdict-head">
        <span className="verdict-grade">{grade}</span>
        <span className="verdict-tagline">{tagline}</span>
      </div>
      <p className="verdict-summary">{summary}</p>
      {points.length > 0 && (
        <ul className="verdict-points">
          {points.map((p, i) => (
            <li key={i} className={p.cls}>
              {p.cls === "pt-good" ? "✓ " : "⚠ "}{p.text}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
