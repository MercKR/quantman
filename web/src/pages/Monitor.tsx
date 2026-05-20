import { useEffect, useState } from "react";
import { api } from "../api";
import type { CommandRow, CommandType, DeviceRow, SyncSnapshot } from "../types";

const REFRESH_MS = 5000;

export default function Monitor() {
  const [snap, setSnap] = useState<SyncSnapshot | null>(null);
  const [devices, setDevices] = useState<DeviceRow[]>([]);
  const [cmds, setCmds] = useState<CommandRow[]>([]);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);

  async function load() {
    try {
      const [s, ds, cs] = await Promise.all([
        api.snapshot(), api.devices(), api.listCommands(undefined, false),
      ]);
      setSnap(s);
      setDevices(ds);
      setCmds(cs);
      setErr("");
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoaded(true);
    }
  }

  useEffect(() => {
    load();
    const t = setInterval(load, REFRESH_MS);
    return () => clearInterval(t);
  }, []);

  async function send(type: CommandType,
                      params: Record<string, string | number> = {}) {
    const dev = devices[0];
    if (!dev) {
      setErr("기기 페어링이 필요합니다.");
      return;
    }
    setBusy(true);
    try {
      await api.createCommand(dev.id, type, params);
      await load();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const p = snap?.payload;
  const ks = p?.kill_switch;
  const summary = p?.cycle_summary;
  const slip = p?.slippage;
  const pending = p?.broker_pending ?? p?.pending_local ?? [];
  const orders = p?.recent_orders ?? [];
  const cycles = p?.recent_cycles ?? [];

  return (
    <div>
      <h1 className="page-title">자동매매 모니터</h1>
      <p className="page-sub">
        로컬앱에서 가져온 최근 사이클·주문·슬리피지를 보고, 웹에서 직접 명령을 보냅니다.
        명령은 평균 1-3초 안에 로컬앱이 받아 실행합니다.
      </p>

      {err && <div className="error">{err}</div>}
      {!loaded && <p className="muted">불러오는 중…</p>}

      {/* Kill switch banner */}
      {ks?.active && (
        <div className="panel" style={{
          borderLeft: "4px solid var(--red)",
          background: "var(--red-soft)", marginBottom: 14,
        }}>
          <div style={{ display: "flex", alignItems: "center",
                          justifyContent: "space-between", gap: 12 }}>
            <div>
              <div style={{ fontWeight: 700, color: "var(--red)" }}>
                ⚠ Kill Switch 활성
              </div>
              <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
                사유: {ks.reason || "(없음)"} ·{" "}
                {ks.since ? new Date(ks.since).toLocaleString() : ""}
              </div>
            </div>
            <button
              className="ghost sm" disabled={busy}
              onClick={() => send("RESET_KILL_SWITCH")}
              style={{ borderColor: "var(--red)", color: "var(--red)" }}
            >
              해제
            </button>
          </div>
        </div>
      )}

      {/* Action bar */}
      <div className="panel" style={{ display: "flex", flexWrap: "wrap",
                                         gap: 8, alignItems: "center" }}>
        <strong style={{ marginRight: 8 }}>액션:</strong>
        <button onClick={() => send("RUN_CYCLE_NOW")} disabled={busy}>
          지금 1회 실행
        </button>
        <button className="ghost sm" onClick={() => send("PAUSE_AUTO")} disabled={busy}>
          일시정지
        </button>
        <button className="ghost sm" onClick={() => send("RESUME_AUTO")} disabled={busy}>
          재개
        </button>
        <button className="ghost sm" onClick={() => {
          if (confirm("정말 모든 보유 종목을 청산하고 신규 진입을 차단하시겠습니까?"))
            send("LIQUIDATE_ALL");
        }} disabled={busy} style={{ color: "var(--red)" }}>
          전량 청산 + 차단
        </button>
        <span className="muted" style={{ marginLeft: "auto", fontSize: 12 }}>
          {devices[0]
            ? `대상 기기: ${devices[0].name} (#${devices[0].id})`
            : "기기 페어링 필요"}
        </span>
      </div>

      {/* Summary stats */}
      {summary && (
        <div className="panel" style={{ marginTop: 14 }}>
          <h3 style={{ marginTop: 0 }}>최근 사이클 요약</h3>
          <div style={{ display: "grid",
                          gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
                          gap: 12 }}>
            <Stat label="평가금액" value={summary.equity_post?.toLocaleString() ?? "—"} />
            <Stat label="매수" value={summary.n_bought ?? 0} />
            <Stat label="매도" value={summary.n_sold ?? 0} />
            <Stat label="갭 스킵" value={summary.n_skip_gap ?? 0} />
            <Stat label="신호 미충족" value={summary.n_skip_signal ?? 0} />
            <Stat label="거부" value={summary.n_rejected ?? 0} />
          </div>
        </div>
      )}

      {/* Slippage */}
      {slip && slip.n > 0 && (
        <div className="panel" style={{ marginTop: 14 }}>
          <h3 style={{ marginTop: 0 }}>슬리피지</h3>
          <p className="muted" style={{ fontSize: 13 }}>
            의도가 vs 체결가의 차이(bps). 양수 = 불리한 체결.
            표본 {slip.n}건 · 평균 {slip.avg_bps} bps · 중앙값 {slip.p50_bps} bps ·
            p95 {slip.p95_bps} bps · 최대 {slip.max_bps} bps
          </p>
        </div>
      )}

      {/* Pending */}
      <div className="panel" style={{ marginTop: 14 }}>
        <h3 style={{ marginTop: 0 }}>미체결 주문 ({pending.length})</h3>
        {pending.length === 0 ? (
          <p className="muted">현재 미체결 주문이 없습니다.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>방향</th><th>종목</th><th>수량</th><th>체결</th>
                <th>잔량</th><th>지정가</th><th>주문번호</th><th></th>
              </tr>
            </thead>
            <tbody>
              {pending.map((o) => (
                <tr key={o.order_no}>
                  <td>{o.side === "buy" ? "매수" : "매도"}</td>
                  <td>{o.symbol}{o.name ? ` · ${o.name}` : ""}</td>
                  <td>{o.qty}</td>
                  <td>{o.filled_qty ?? 0}</td>
                  <td>{o.remain_qty ?? o.qty}</td>
                  <td>{o.limit_price ? o.limit_price.toLocaleString() : "—"}</td>
                  <td style={{ fontFamily: "Consolas", fontSize: 12 }}>{o.order_no}</td>
                  <td>
                    <button
                      className="ghost sm" disabled={busy}
                      onClick={() => send("CANCEL_ORDER", {
                        order_no: o.order_no, symbol: o.symbol,
                        qty: o.remain_qty ?? o.qty,
                      })}
                    >
                      취소
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Recent orders */}
      <div className="panel" style={{ marginTop: 14 }}>
        <h3 style={{ marginTop: 0 }}>주문 내역 (최근 {orders.length}건)</h3>
        {orders.length === 0 ? (
          <p className="muted">아직 주문 이벤트가 없습니다.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>시각</th><th>상태</th><th>방향</th><th>종목</th>
                <th>수량</th><th>지정가</th><th>체결가</th><th>전략</th><th>사유</th>
              </tr>
            </thead>
            <tbody>
              {orders.slice(0, 30).map((o, i) => (
                <tr key={i}>
                  <td style={{ fontSize: 12 }}>
                    {o.ts.replace("T", " ").slice(0, 19)}
                  </td>
                  <td><EventBadge ev={o.event} /></td>
                  <td>{o.side === "buy" ? "매수" : "매도"}</td>
                  <td>{o.symbol}</td>
                  <td>{o.qty}</td>
                  <td>{o.limit_price?.toLocaleString() ?? "—"}</td>
                  <td>{o.fill_price?.toLocaleString() ?? "—"}</td>
                  <td>{o.strategy ?? ""}</td>
                  <td>{o.reason ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Recent cycles */}
      <div className="panel" style={{ marginTop: 14 }}>
        <h3 style={{ marginTop: 0 }}>사이클 로그 (최근 {cycles.length}건)</h3>
        {cycles.length === 0 ? (
          <p className="muted">아직 실행된 사이클이 없습니다.</p>
        ) : (
          cycles.slice(0, 10).map((c, i) => (
            <details key={i} style={{ marginBottom: 6 }}>
              <summary style={{ cursor: "pointer" }}>
                {c.ts.replace("T", " ").slice(0, 19)} —
                {" "}매수 {c.summary.n_bought ?? 0} ·
                {" "}매도 {c.summary.n_sold ?? 0} ·
                {" "}갭 {c.summary.n_skip_gap ?? 0} ·
                {" "}거부 {c.summary.n_rejected ?? 0}
                {c.summary.kill_switch ? " · ⚠ KS" : ""}
              </summary>
              <ul style={{ fontSize: 13, marginTop: 6 }}>
                {c.decisions.map((d, j) => (
                  <li key={j}>
                    <code>{d.action}</code> · {d.symbol || "-"} ·
                    {" "}{d.strategy_name} — {d.reason}
                  </li>
                ))}
              </ul>
            </details>
          ))
        )}
      </div>

      {/* Recent commands */}
      {cmds.length > 0 && (
        <div className="panel" style={{ marginTop: 14 }}>
          <h3 style={{ marginTop: 0 }}>최근 명령</h3>
          <table>
            <thead>
              <tr><th>시각</th><th>타입</th><th>상태</th><th>결과</th></tr>
            </thead>
            <tbody>
              {cmds.slice(0, 10).map((c) => (
                <tr key={c.id}>
                  <td style={{ fontSize: 12 }}>
                    {c.created_at.replace("T", " ").slice(0, 19)}
                  </td>
                  <td><code>{c.type}</code></td>
                  <td>{c.status}</td>
                  <td style={{ fontSize: 12 }}>
                    {Object.keys(c.result).length > 0
                      ? JSON.stringify(c.result).slice(0, 80)
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}

function EventBadge({ ev }: { ev: string }) {
  const colors: Record<string, { bg: string; fg: string }> = {
    filled: { bg: "var(--green-soft)", fg: "var(--green)" },
    partial: { bg: "var(--green-soft)", fg: "var(--green)" },
    submitted: { bg: "var(--accent-soft)", fg: "var(--accent)" },
    cancelled: { bg: "#f3f4f6", fg: "var(--muted)" },
    rejected: { bg: "var(--red-soft)", fg: "var(--red)" },
    timeout: { bg: "var(--amber-soft)", fg: "var(--amber)" },
  };
  const c = colors[ev] ?? colors.cancelled;
  return (
    <span className="badge" style={{ background: c.bg, color: c.fg,
                                       borderColor: "transparent" }}>
      {ev}
    </span>
  );
}
