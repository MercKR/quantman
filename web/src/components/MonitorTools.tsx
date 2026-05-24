/* Phase 13.4/13.9 — 알림 설정 + CSV export */

import { useEffect, useState } from "react";
import { api } from "../api";
import type { OrderEvent, UserSettingsIO } from "../types";

// ── 알림 설정 ─────────────────────────────────────────────────────────────────

export function AlertSettings() {
  const [s, setS] = useState<UserSettingsIO | null>(null);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  // W-03 — 로드 실패와 "설정 없음"이 같은 null로 합쳐지면 폼이 안내 없이 사라져
  // "기능 없음"으로 오인된다. 상태를 분리해 실패 시 재시도 UI를 보여준다.
  const [loadState, setLoadState] = useState<"loading" | "error" | "loaded">("loading");
  const [reloadKey, setReloadKey] = useState(0);

  // 데이터 패칭 효과 — 의도적. eslint set-state-in-effect 비활성 (W-05 정책).
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    let cancelled = false;
    setLoadState("loading");
    api.getSettings()
      .then((v) => { if (!cancelled) { setS(v); setLoadState("loaded"); } })
      .catch(() => { if (!cancelled) setLoadState("error"); });
    return () => { cancelled = true; };
  }, [reloadKey]);
  /* eslint-enable react-hooks/set-state-in-effect */

  function update<K extends keyof UserSettingsIO>(k: K, v: UserSettingsIO[K]) {
    if (s) setS({ ...s, [k]: v });
  }

  async function save() {
    if (!s) return;
    setBusy(true); setMsg("");
    try {
      await api.putSettings(s);
      setMsg("저장됐습니다.");
    } catch (e) {
      setMsg("저장 실패: " + (e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (loadState === "loading") {
    return (
      <div className="panel">
        <h3 style={{ marginTop: 0 }}>위험 한도 + 알림</h3>
        <p className="muted">불러오는 중…</p>
      </div>
    );
  }
  if (loadState === "error" || !s) {
    return (
      <div className="panel">
        <h3 style={{ marginTop: 0 }}>위험 한도 + 알림</h3>
        <p className="muted">설정을 불러오지 못했습니다 (네트워크·서버 일시 장애).</p>
        <button className="ghost" onClick={() => setReloadKey((k) => k + 1)}>다시 시도</button>
      </div>
    );
  }

  return (
    <div className="panel">
      <h3 style={{ marginTop: 0 }}>위험 한도 + 알림</h3>

      <h4 style={{ marginTop: 16, marginBottom: 8 }}>
        위험 한도 <span className="muted" style={{ fontWeight: 400, fontSize: 13 }}>
          (비워두면 글로벌 default 사용)
        </span>
      </h4>
      <div className="alert-form">
        <div>
          <label>Kill Switch — 일일 손실 한도 (%)</label>
          <input
            type="number" step="0.5" min={0.5} max={20}
            placeholder="예: 3 (default 3.0)"
            value={s.kill_switch_daily_loss_pct ?? ""}
            onChange={(e) => update("kill_switch_daily_loss_pct",
              e.target.value === "" ? null : Number(e.target.value))}
          />
          <span className="muted" style={{ fontSize: 12, marginLeft: 8 }}>
            자본 대비 이 % 손실 시 신규 진입 차단 (청산은 계속)
          </span>
        </div>
        <div>
          <label>누적 Drawdown 한도 (%)</label>
          <input
            type="number" step="1" min={1} max={80}
            placeholder="예: 20 (default 20.0)"
            value={s.max_drawdown_pct ?? ""}
            onChange={(e) => update("max_drawdown_pct",
              e.target.value === "" ? null : Number(e.target.value))}
          />
          <span className="muted" style={{ fontSize: 12, marginLeft: 8 }}>
            자본 고점 대비 이 % 하락 시 신규 진입 차단 (peak 회복 시 자동 해제)
          </span>
        </div>
      </div>

      <h4 style={{ marginTop: 20, marginBottom: 8 }}>미국 주식 거래</h4>
      <div className="alert-form">
        <div>
          <label>매수여력 기준</label>
          <select
            value={s.us_buying_power_mode}
            onChange={(e) => update("us_buying_power_mode",
              e.target.value as UserSettingsIO["us_buying_power_mode"])}
          >
            <option value="integrated">통합증거금 (원화 담보로 미국 주문)</option>
            <option value="usd_cash">USD 예수금 한정 (보수적)</option>
          </select>
          <span className="muted" style={{ fontSize: 12, marginLeft: 8 }}>
            통합증거금: 달러 예수금이 없어도 원화를 담보로 미국 주식을 매수합니다
            (환율 변동 노출 발생). USD 예수금 한정: 보유한 달러 범위 내에서만 매수.
          </span>
        </div>
        <div className="warn-box" style={{
          /* W-07 — amber 토큰만 사용 (이전: rgba(240,180,0,...) 하드코딩) */
          marginTop: 4, padding: "10px 12px", borderRadius: 8,
          background: "var(--amber-soft)", border: "1px solid var(--amber)",
          fontSize: 13, lineHeight: 1.6,
        }}>
          <strong>⚠ 미국 실시간 손절 안내</strong><br/>
          미국 종목의 <b>장중 실시간 손절·익절·트레일링</b>은 KIS <b>해외 실시간 시세
          신청</b>이 있어야 동작합니다. 신청 방법: HTS(eFriend Plus/Force)
          <b> [7781] 시세신청(실시간)</b> 또는 MTS 고객센터 &gt; 거래신청 &gt; 해외주식 &gt;
          해외 실시간 시세 신청.<br/>
          <b>신청하지 않으면</b> 미국 종목은 장 마감 후 사이클에서만 청산이 평가되어,
          <b> 장중 실시간 매도가 제공되지 않습니다.</b> (국내 주식은 별도 신청 불필요)
        </div>
      </div>

      <h4 style={{ marginTop: 20, marginBottom: 8 }}>알림 (Discord / Slack webhook)</h4>
      <div className="alert-form">
        <div>
          <label>Webhook URL</label>
          <input
            type="url"
            placeholder="https://discord.com/api/webhooks/... 또는 https://hooks.slack.com/..."
            value={s.alert_webhook_url}
            onChange={(e) => update("alert_webhook_url", e.target.value)}
            style={{ width: "100%" }}
          />
        </div>
        <label className="alert-toggle">
          <input type="checkbox" checked={s.alert_on_killswitch}
                 onChange={(e) => update("alert_on_killswitch", e.target.checked)} />
          Kill Switch 활성/해제 시 알림
        </label>
        <label className="alert-toggle">
          <input type="checkbox" checked={s.alert_on_reconcile_drift}
                 onChange={(e) => update("alert_on_reconcile_drift", e.target.checked)} />
          잔고 정합성 drift 알림 (HTS/MTS 수동 매매 감지)
        </label>
        <div>
          <label>일일 손실 알림 임계 (%)</label>
          <input type="number" step="0.5" min={0.5} max={10}
                 value={s.alert_on_daily_loss_pct}
                 onChange={(e) => update("alert_on_daily_loss_pct",
                                          Number(e.target.value))} />
        </div>
        <div>
          <label>미체결 누적 알림 (건)</label>
          <input type="number" min={1} value={s.alert_on_unfilled_count}
                 onChange={(e) => update("alert_on_unfilled_count",
                                          Number(e.target.value))} />
        </div>
        <div>
          <label>Preview 연속 누락 알림 (일)</label>
          <input type="number" min={1} max={14}
                 value={s.preview_missing_alert_threshold}
                 onChange={(e) => update("preview_missing_alert_threshold",
                                          Math.max(1, Number(e.target.value)))} />
          <span className="muted" style={{ fontSize: 12, marginLeft: 8 }}>
            서버 cron이 N일 연속 preview 생성 실패 시 webhook
          </span>
        </div>
        {/* Phase 48 P1-C — 슬리피지 임계 초과 알림 */}
        <div>
          <label>슬리피지 알림 임계 (bps)</label>
          <input type="number" min={0} max={500} step={5}
                 value={s.alert_on_slippage_bps}
                 onChange={(e) => update("alert_on_slippage_bps",
                                          Math.max(0, Number(e.target.value)))} />
          <span className="muted" style={{ fontSize: 12, marginLeft: 8 }}>
            평균 슬리피지가 이 bps 초과 시 webhook (0=비활성, 1bp=0.01%)
          </span>
        </div>
      </div>

      <h4 style={{ marginTop: 20, marginBottom: 8 }}>
        일일 거래 한도 <span className="muted" style={{ fontWeight: 400, fontSize: 13 }}>
          (0이면 비활성, 도달 시 신규 진입 차단)
        </span>
      </h4>
      <div className="alert-form">
        <div>
          <label>일일 거래 대금 한도 (원)</label>
          <input type="number" min={0} step={1000000}
                 value={s.daily_turnover_limit_krw}
                 onChange={(e) => update("daily_turnover_limit_krw",
                                          Math.max(0, Number(e.target.value)))} />
          <span className="muted" style={{ fontSize: 12, marginLeft: 8 }}>
            예: 10000000 = 1천만원. 0이면 비활성
          </span>
        </div>
        <div>
          <label>일일 거래 횟수 한도</label>
          <input type="number" min={0} max={1000}
                 value={s.daily_trade_count_limit}
                 onChange={(e) => update("daily_trade_count_limit",
                                          Math.max(0, Number(e.target.value)))} />
          <span className="muted" style={{ fontSize: 12, marginLeft: 8 }}>
            0이면 비활성
          </span>
        </div>
        <button disabled={busy} onClick={save}>
          {busy ? "저장 중…" : "설정 저장"}
        </button>
        {msg && <span className="muted">{msg}</span>}
      </div>
    </div>
  );
}

// ── CSV export ─────────────────────────────────────────────────────────────────

export function CsvExportBar({ orders }: { orders: OrderEvent[] }) {
  function exportOrders() {
    if (!orders || orders.length === 0) return;
    const headers = ["ts", "event", "side", "symbol", "qty",
                      "intended_price", "limit_price", "fill_price",
                      "strategy", "reason", "order_no"];
    const rows = orders.map((o) =>
      headers.map((h) => {
        const v = (o as unknown as Record<string, unknown>)[h];
        if (v == null) return "";
        const s = String(v);
        return s.includes(",") || s.includes("\"")
          ? `"${s.replace(/"/g, '""')}"` : s;
      }).join(","));
    const csv = [headers.join(","), ...rows].join("\n");
    const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `orders_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <button className="ghost sm" onClick={exportOrders}
            disabled={!orders || orders.length === 0}>
      주문 내역 CSV 내보내기
    </button>
  );
}
