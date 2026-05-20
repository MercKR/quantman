/** 백테스트 지표를 객관적으로 풀어주는 카드.
 *  주관적 평가("우수/추천" 등)는 투자자문으로 해석될 수 있어 배제.
 *  지표가 무엇을 뜻하는지 평이한 한국어로만 해설한다.
 */

import { fmt2 } from "../format";

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
  const winRate = num(metrics.win_rate);
  const excess = num(metrics.excess_return);

  const lines: string[] = [];

  if (ret != null && cagr != null) {
    lines.push(
      `백테스트 기간 누적 수익률은 ${fmt2(ret)}%, 연평균 환산(CAGR)은 ${fmt2(cagr)}%입니다.`,
    );
  }
  if (mdd != null) {
    lines.push(
      `보유 중 한때 자산이 최대 ${fmt2(mdd)}%까지 감소했습니다(MDD). `
      + `값이 클수록 변동성이 크다는 뜻입니다.`,
    );
  }
  if (sharpe != null) {
    lines.push(
      `샤프 비율 ${fmt2(sharpe)} — 변동성 한 단위당 거둔 수익을 보여주는 위험조정 수익 지표입니다.`,
    );
  }
  if (winRate != null && nTrades != null) {
    lines.push(
      `총 ${nTrades}건의 매매 중 ${fmt2(winRate)}%가 이익으로 마감되었습니다.`,
    );
  }
  if (excess != null) {
    lines.push(
      `같은 종목을 단순 매수·보유했을 때 대비 ${fmt2(excess)}%p 차이입니다.`,
    );
  }
  if (nTrades != null && nTrades < 10) {
    lines.push(
      `매매 횟수가 ${nTrades}건으로 적은 편입니다. 표본이 작을수록 통계의 안정성이 낮아집니다.`,
    );
  }

  if (lines.length === 0) return null;

  return (
    <div className="verdict ok">
      <div className="verdict-head">
        <span className="verdict-tagline">결과 해설</span>
      </div>
      <ul className="verdict-points">
        {lines.map((t, i) => (
          <li key={i} className="pt-neutral">• {t}</li>
        ))}
      </ul>
      <p className="verdict-summary muted" style={{ fontSize: 12, marginTop: 12 }}>
        과거 데이터에 기반한 시뮬레이션 결과로, 미래 수익을 보장하지 않습니다.
        본 화면은 정보 제공 목적이며 투자 자문이 아닙니다.
      </p>
    </div>
  );
}
