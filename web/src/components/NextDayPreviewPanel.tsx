/**
 * 내일 매매 미리보기 패널 — 트레이딩 페이지 상단.
 *
 * 서버가 각 데이터 cron 후 자동 평가한 결과를 표시. 사용자 투명성:
 * "내일 자동매매가 무엇을 살/팔 예정인지" 실시간 데이터 기준 미리보기.
 *
 * 실제 발주는 다음날 08:55 로컬앱 사이클에서 — 여기 표시되는 가격·수량은 추정값.
 * 마지막 평가 시각 + 데이터 소스(어떤 cron 직후 갱신됐는지)를 명시해 신뢰성 확보.
 */

import { useEffect, useState } from "react";
import { api } from "../api";
import type { NextDayPreview } from "../types";

const DATA_SOURCE_LABEL: Record<string, string> = {
  kis_master: "KIS 마스터",
  krx: "KRX 일별 시세",
  naver: "NAVER 펀더멘털",
  technical: "기술 지표",
  dataset_global: "글로벌 dataset",
  dataset_kr: "한국 dataset",
  manual: "수동 재계산",
};

function fmtKst(iso: string): string {
  try {
    const d = new Date(iso);
    const parts = new Intl.DateTimeFormat("ko-KR", {
      timeZone: "Asia/Seoul",
      year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit",
      hour12: false,
    }).formatToParts(d);
    const get = (t: string) => parts.find((p) => p.type === t)?.value ?? "";
    return `${get("year")}-${get("month")}-${get("day")} ${get("hour")}:${get("minute")}`;
  } catch { return iso; }
}

function fmtWon(n: number): string {
  if (n >= 100_000_000) return `${(n / 100_000_000).toFixed(2)}억`;
  if (n >= 10_000) return `${Math.round(n / 10_000).toLocaleString()}만`;
  return `${Math.round(n).toLocaleString()}원`;
}

export default function NextDayPreviewPanel() {
  const [preview, setPreview] = useState<NextDayPreview | null>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  function load() {
    api.getNextDayPreview()
      .then(setPreview)
      .catch((e) => setErr((e as Error).message));
  }

  useEffect(() => {
    load();
    const t = setInterval(load, 30_000);   // 30초 polling
    return () => clearInterval(t);
  }, []);

  async function regenerate() {
    setErr(""); setBusy(true);
    try {
      const r = await api.regenerateNextDayPreview();
      setPreview(r);
    } catch (e) { setErr((e as Error).message); }
    finally { setBusy(false); }
  }

  if (!preview) {
    return (
      <div className="panel preview-panel preview-empty">
        <h3>📋 내일 매매 미리보기</h3>
        <div className="muted">
          {err ? `불러오기 실패: ${err}` : "불러오는 중…"}
        </div>
      </div>
    );
  }

  if (!preview.available) {
    return (
      <div className="panel preview-panel preview-empty">
        <h3>📋 내일 매매 미리보기</h3>
        <div className="muted">{preview.reason ?? "준비 중"}</div>
      </div>
    );
  }

  const s = preview.summary;
  const buyN = s?.n_buy_candidates ?? 0;
  const exitN = preview.exit_candidates?.length ?? 0;

  return (
    <div className="panel preview-panel">
      <div className="preview-head">
        <h3 style={{ margin: 0 }}>
          📋 내일 매매 미리보기
          <button className="ghost sm" onClick={() => setCollapsed((v) => !v)}
                  style={{ marginLeft: 10 }}>
            {collapsed ? "펼치기" : "접기"}
          </button>
        </h3>
        <div className="preview-meta muted small">
          {DATA_SOURCE_LABEL[preview.data_source] ?? preview.data_source} 기준 ·
          {" "}{fmtKst(preview.generated_at)}
          <button className="ghost sm" onClick={regenerate} disabled={busy}
                  style={{ marginLeft: 8 }}>
            {busy ? "재계산 중…" : "지금 다시 평가"}
          </button>
        </div>
      </div>

      {err && <div className="error small">{err}</div>}

      <div className="preview-summary">
        <div className="preview-stat">
          <div className="preview-stat-label">매수 예정</div>
          <div className="preview-stat-value">
            {buyN}건 · {fmtWon(s?.est_total_buy_amount ?? 0)}
          </div>
        </div>
        <div className="preview-stat">
          <div className="preview-stat-label">청산 후보</div>
          <div className="preview-stat-value">{exitN}건</div>
        </div>
        <div className="preview-stat">
          <div className="preview-stat-label">현 보유</div>
          <div className="preview-stat-value">{s?.n_holding ?? 0}종목</div>
        </div>
        <div className="preview-stat">
          <div className="preview-stat-label">가용 현금</div>
          <div className="preview-stat-value">{fmtWon(s?.cash ?? 0)}</div>
        </div>
      </div>

      {!collapsed && (
        <>
          {/* 매수 후보 — 전략별 */}
          {preview.by_strategy && preview.by_strategy.length > 0 && (
            <div className="preview-section">
              <h4>매수 후보 (전략별)</h4>
              {preview.by_strategy.map((bs) => (
                <div key={bs.strategy_id} className="preview-strategy">
                  <div className="preview-strategy-head">
                    <strong>{bs.strategy_name}</strong>
                    <span className={"sc-badge " + bs.run_mode}
                          style={{ marginLeft: 8 }}>
                      {bs.run_mode === "live" ? "실전" : "모의"}
                    </span>
                    <span className="muted small" style={{ marginLeft: 8 }}>
                      {bs.signal_passed ? "신호 통과 ✓" : "신호 미충족"}
                    </span>
                  </div>
                  {bs.candidates.length > 0 && (
                    <table className="preview-table">
                      <thead>
                        <tr>
                          <th>종목</th><th>수량</th><th>전일종가</th>
                          <th>예상 발주가</th><th>예상 총액</th>
                        </tr>
                      </thead>
                      <tbody>
                        {bs.candidates.map((c) => (
                          <tr key={c.symbol}>
                            <td>
                              <strong>{c.symbol}</strong>
                              {c.name && <span className="muted small"> {c.name}</span>}
                            </td>
                            <td>{c.qty}주</td>
                            <td>{c.prev_close.toLocaleString()}원</td>
                            <td>{c.est_limit_price.toLocaleString()}원</td>
                            <td><strong>{c.est_total.toLocaleString()}원</strong></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                  {/* Phase 41 — 공통 조건 평가 결과 (좌변에 명시 종목인 조건들) */}
                  {bs.signal_summary && (
                    <div className="preview-signal-common muted small">
                      <span>공통 조건: </span>
                      <code>{bs.signal_summary}</code>
                    </div>
                  )}
                  {/* Phase 41 — 종목별 평가 결과 — [이 종목] placeholder 조건 */}
                  {bs.per_symbol_details
                    && Object.keys(bs.per_symbol_details).length > 0
                    && Object.keys(bs.per_symbol_details).length <= 30 && (
                    <details className="preview-per-symbol">
                      <summary className="muted small">
                        종목별 조건 평가 ({Object.keys(bs.per_symbol_details).length}종목)
                      </summary>
                      <div className="preview-per-symbol-list">
                        {Object.entries(bs.per_symbol_details).map(([sym, ev]) => (
                          <div key={sym} className="small">
                            <span className={ev.passed ? "pos" : "muted"}>
                              {ev.passed ? "✓" : "✗"}
                            </span>{" "}
                            <strong>{sym}</strong>{" "}
                            <span className="muted">{ev.summary}</span>
                          </div>
                        ))}
                      </div>
                    </details>
                  )}
                  {bs.skipped.length > 0 && (
                    <div className="preview-skipped">
                      {bs.skipped.map((sk, i) => (
                        <div key={i} className="muted small">
                          ⊘ {sk.symbol ? `${sk.symbol}: ` : ""}{sk.reason}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* 청산 후보 — 보유 종목 추적 */}
          {preview.exit_candidates && preview.exit_candidates.length > 0 && (
            <div className="preview-section">
              <h4>보유 종목 추적 (청산 평가는 다음 사이클의 실시간 가격 기준)</h4>
              <table className="preview-table">
                <thead>
                  <tr>
                    <th>종목</th><th>수량</th><th>진입가</th>
                    <th>전일종가</th><th>수익률</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.exit_candidates.map((e) => (
                    <tr key={e.symbol}>
                      <td>
                        <strong>{e.symbol}</strong>
                        {e.name && <span className="muted small"> {e.name}</span>}
                      </td>
                      <td>{e.qty}주</td>
                      <td>{e.entry_price.toLocaleString()}원</td>
                      <td>{e.prev_close.toLocaleString()}원</td>
                      <td className={e.return_pct >= 0 ? "pos" : "neg"}>
                        {e.return_pct >= 0 ? "+" : ""}{e.return_pct.toFixed(2)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="preview-disclaimer muted small">
            ⓘ 표시 가격·수량은 현재 데이터 기준 추정값. 실제 발주는 다음날 08:55 사이클에서
            최신 데이터로 다시 평가 후 09:00 시초가 동시호가에 체결됩니다.
          </div>
        </>
      )}
    </div>
  );
}
