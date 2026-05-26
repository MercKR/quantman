/**
 * 전략 상세 페이지 (Phase 59).
 *
 * /strategies/:id 경로. 4탭:
 *  1. 설정값 — 모든 정의 조회 (read-only 요약 + 빌더에서 수정 link)
 *  2. 버전 — 자동/수동 스냅샷 이력 + 복원
 *  3. 현황 — 적용 기간 + 누적 P&L + 보유 종목
 *  4. 백테스트 내역 — 이 전략으로 실행된 백테스트 목록
 *
 * 사용자 명세 (요청): "모든 설정값 조회 및 수정 / 버전 관리 / 현황".
 * 인라인 수정은 다음 단계에서 BuildTab 통합으로 추가.
 */

import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { BuildTab } from "./Backtest";
import { HELD_DAYS_KEY } from "../components/ConditionBuilder";
import type {
  AnalysisResult, BacktestResult, BacktestRunSummary, ConditionGroup,
  ConditionNode, ExecutionPolicy, RebalanceIO, ScreenerSpecIO,
  StrategyDef, StrategyRow, StrategyStats, StrategyVersionRow, SymbolInfo,
} from "../types";
import { EXECUTION_DEFAULTS } from "../types";

type SizingMode = "fixed_amount" | "pct_cash" | "equal_weight" | "atr_risk";
type RuleKey = "tp" | "sl" | "trail" | "atr";

type TabKey = "config" | "versions" | "stats" | "backtests";

const TAB_LABEL: Record<TabKey, string> = {
  config: "설정값",
  versions: "버전",
  stats: "현황",
  backtests: "백테스트 내역",
};

const krw = (v: number | null | undefined) =>
  v == null ? "—" : (v >= 0 ? "+" : "") + v.toLocaleString() + "원";
const pct = (v: number | null | undefined, sign = true) =>
  v == null ? "—"
    : (sign && v >= 0 ? "+" : "") + v.toFixed(2) + "%";
const dateOnly = (iso?: string | null) => (iso ?? "").slice(0, 10);

export default function StrategyDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const sid = id ? Number(id) : NaN;

  const [strategy, setStrategy] = useState<StrategyRow | null>(null);
  const [stats, setStats] = useState<StrategyStats | null>(null);
  const [versions, setVersions] = useState<StrategyVersionRow[]>([]);
  const [backtests, setBacktests] = useState<BacktestRunSummary[]>([]);
  const [tab, setTab] = useState<TabKey>("config");
  const [err, setErr] = useState("");
  const [loaded, setLoaded] = useState(false);

  function loadAll() {
    if (isNaN(sid)) return;
    setErr("");
    Promise.all([
      api.getStrategy(sid),
      api.getStrategyStats(sid).catch(() => null),
      api.listStrategyVersions(sid).catch(() => []),
      api.listStrategyBacktests(sid).catch(() => []),
    ])
      .then(([s, st, vs, bs]) => {
        setStrategy(s); setStats(st); setVersions(vs); setBacktests(bs);
      })
      .catch((e) => setErr((e as Error).message))
      .finally(() => setLoaded(true));
  }
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(loadAll, [sid]);

  async function restoreVersion(versionNo: number) {
    if (!confirm(`v${versionNo}으로 복원할까요?\n현재 정의도 자동 새 버전으로 보존됩니다.`)) return;
    try {
      await api.restoreStrategyVersion(sid, versionNo);
      loadAll();
    } catch (e) { setErr((e as Error).message); }
  }

  async function remove() {
    if (!strategy) return;
    if (!confirm("이 전략을 삭제할까요? 모든 버전·백테스트도 함께 삭제됩니다.")) return;
    try {
      await api.deleteStrategy(strategy.id);
      navigate("/strategies");
    } catch (e) { setErr((e as Error).message); }
  }

  if (isNaN(sid)) return <div className="error">잘못된 전략 ID입니다.</div>;
  if (!loaded) return <p className="muted">불러오는 중…</p>;
  if (err) return <div className="error">{err}</div>;
  if (!strategy) return <div className="error">전략을 찾을 수 없습니다.</div>;

  return (
    <div>
      <div className="strategy-detail-head">
        <Link to="/strategies" className="muted small">← 내 전략</Link>
        <h1 className="page-title" style={{ marginBottom: 4 }}>
          {strategy.name}
        </h1>
        <div className="strategy-detail-sub">
          <span className={"sc-badge " + strategy.run_mode}>
            {strategy.run_mode === "live" ? "실전"
              : strategy.run_mode === "paper" ? "모의" : "초안"}
          </span>
          <span className="muted small">
            생성 {dateOnly(strategy.created_at)} · 최근 수정 {dateOnly(strategy.updated_at)}
          </span>
        </div>
      </div>

      <nav className="tabs" style={{ marginTop: 16 }}>
        {(Object.keys(TAB_LABEL) as TabKey[]).map((k) => (
          <button key={k} type="button"
                  className={"tab" + (tab === k ? " active" : "")}
                  onClick={() => setTab(k)}>
            {TAB_LABEL[k]}
            {k === "versions" && versions.length > 0 && (
              <span className="tab-count">{versions.length}</span>
            )}
            {k === "backtests" && backtests.length > 0 && (
              <span className="tab-count">{backtests.length}</span>
            )}
          </button>
        ))}
      </nav>

      {tab === "config" && (
        <ConfigEditTab
          strategy={strategy}
          onSaved={loadAll}
          onRemove={remove}
        />
      )}
      {tab === "versions" && (
        <VersionsTab versions={versions} onRestore={restoreVersion} />
      )}
      {tab === "stats" && <StatsTab stats={stats} strategy={strategy} />}
      {tab === "backtests" && <BacktestsTab backtests={backtests} />}
    </div>
  );
}

// ── 탭 1: 설정값 (인라인 수정 — BuildTab 직접 사용) ─────────────────────────

function ConfigEditTab({ strategy, onSaved, onRemove }: {
  strategy: StrategyRow;
  onSaved: () => void;
  onRemove: () => void;
}) {
  // 빌더와 동일한 모든 useState를 strategy.definition에서 초기화.
  // 매번 strategy가 변하면 (저장 후 refresh) 모든 state 재초기화 — key로 강제.
  // 부모(StrategyDetail)에서 strategy 객체 새로 받으면 이 컴포넌트가 unmount/remount.
  return (
    <ConfigEditInner key={strategy.id + "-" + strategy.updated_at}
                     strategy={strategy} onSaved={onSaved} onRemove={onRemove} />
  );
}

function ConfigEditInner({ strategy, onSaved, onRemove }: {
  strategy: StrategyRow;
  onSaved: () => void;
  onRemove: () => void;
}) {
  const d = strategy.definition;
  const sr = d.sell_rules ?? {};
  const e = d.execution ?? {};

  // 모든 빌더 state — strategy.definition에서 초기화
  const [symbols, setSymbols] = useState<SymbolInfo[]>([]);
  const [hasMaster, setHasMaster] = useState<boolean>(true);
  const [name, setName] = useState(d.name ?? strategy.name);
  const [tradeSymbol, setTradeSymbol] = useState(d.trade_symbol ?? "");
  const [buy, setBuy] = useState<ConditionGroup>(
    d.buy ?? { conditions: [], logic: "AND" });
  // 매도 conditions에 hold_days를 다시 inject (UI에서 보이도록)
  const sellConditions = (sr.conditions ?? []).slice();
  if (sr.hold_days != null && sr.hold_days > 0) {
    sellConditions.unshift({
      left: { kind: "indicator", symbol: "_self", indicator: HELD_DAYS_KEY },
      op: ">=", right: { kind: "constant", value: sr.hold_days },
      modifier: null,
    });
  }
  const [sell, setSell] = useState<ConditionGroup>({
    conditions: sellConditions, logic: sr.logic ?? "AND",
  });
  const [exits, setExits] = useState<Record<RuleKey, { on: boolean; v: number; sell_pct: number }>>({
    tp:    { on: sr.take_profit != null, v: sr.take_profit ?? 10,
             sell_pct: sr.rule_sell_pcts?.tp ?? 100 },
    sl:    { on: sr.stop_loss != null, v: sr.stop_loss ?? -5,
             sell_pct: sr.rule_sell_pcts?.sl ?? 100 },
    trail: { on: sr.trail_pct != null, v: sr.trail_pct ?? 8,
             sell_pct: sr.rule_sell_pcts?.trail ?? 100 },
    atr:   { on: sr.trail_atr_mult != null, v: sr.trail_atr_mult ?? 3,
             sell_pct: sr.rule_sell_pcts?.atr ?? 100 },
  });
  const [sellRealtimeEnabled, setSellRealtimeEnabled] = useState(false);
  const [sellEodEnabled, setSellEodEnabled] = useState(false);
  const [buyAmountPct, setBuyAmountPct] = useState(d.amount_pct ?? 10);
  const [sellAmountPct, setSellAmountPct] = useState(sr.sell_amount_pct ?? 100);
  const [screenerLimit, setScreenerLimit] = useState(d.screener_limit ?? 5);
  const [screenerSpec, setScreenerSpec] = useState<ScreenerSpecIO | null>(
    d.screener_spec ?? null);
  const [rebalance, setRebalance] = useState<RebalanceIO>(
    d.rebalance ?? { mode: "off", period: "weekly" });
  const [sizingMode, setSizingMode] = useState<SizingMode>(
    (e.sizing_mode ?? EXECUTION_DEFAULTS.sizing_mode) as SizingMode);
  const [amountKrw, setAmountKrw] = useState(e.amount_krw ?? EXECUTION_DEFAULTS.amount_krw);
  const [atrRiskPct, setAtrRiskPct] = useState(e.atr_risk_pct ?? EXECUTION_DEFAULTS.atr_risk_pct);
  const [atrMult, setAtrMult] = useState(e.atr_mult ?? EXECUTION_DEFAULTS.atr_mult);
  const [maxPositionPct, setMaxPositionPct] = useState(e.max_position_pct ?? 10);
  const [maxPositionEnabled, setMaxPositionEnabled] = useState<boolean>(e.max_position_pct != null);
  const [maxDrawdownPct, setMaxDrawdownPct] = useState(e.max_drawdown_pct ?? 20);
  const [maxDrawdownEnabled, setMaxDrawdownEnabled] = useState<boolean>(e.max_drawdown_pct != null);
  const [useLimit, setUseLimit] = useState<boolean>(e.use_limit ?? EXECUTION_DEFAULTS.use_limit);
  const [buyTolerancePct, setBuyTolerancePct] = useState(e.buy_tolerance_pct ?? EXECUTION_DEFAULTS.buy_tolerance_pct);
  const [sellTolerancePct, setSellTolerancePct] = useState(e.sell_tolerance_pct ?? EXECUTION_DEFAULTS.sell_tolerance_pct);
  const [btCommissionBps, setBtCommissionBps] = useState(e.bt_commission_bps ?? EXECUTION_DEFAULTS.bt_commission_bps);
  const [btSellTaxBps, setBtSellTaxBps] = useState(e.bt_sell_tax_bps ?? EXECUTION_DEFAULTS.bt_sell_tax_bps);
  const [btSlippageBps, setBtSlippageBps] = useState(e.bt_slippage_bps ?? EXECUTION_DEFAULTS.bt_slippage_bps);
  const [capital, setCapital] = useState(10_000_000);
  const [forwardDays, setForwardDays] = useState(1);

  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [backtest, setBacktest] = useState<BacktestResult | null>(null);
  const [busy, setBusy] = useState<"" | "analysis" | "backtest" | "save">("");
  const [err, setErr] = useState("");
  const [saveMsg, setSaveMsg] = useState("");

  function setRule(key: RuleKey, patch: Partial<{ on: boolean; v: number; sell_pct: number }>) {
    setExits((e) => ({ ...e, [key]: { ...e[key], ...patch } }));
  }

  useEffect(() => {
    api.symbols().then((r) => {
      setSymbols(r.symbols);
      setHasMaster(r.has_master);
    }).catch((e) => setErr((e as Error).message));
  }, []);

  function buildDef(): StrategyDef {
    const execution: ExecutionPolicy = {
      sizing_mode: sizingMode, amount_krw: amountKrw,
      atr_risk_pct: atrRiskPct, atr_mult: atrMult,
      max_position_pct: maxPositionEnabled ? maxPositionPct : null,
      max_drawdown_pct: maxDrawdownEnabled ? maxDrawdownPct : null,
      use_limit: useLimit,
      buy_tolerance_pct: buyTolerancePct,
      sell_tolerance_pct: sellTolerancePct,
      bt_commission_bps: btCommissionBps,
      bt_sell_tax_bps: btSellTaxBps,
      bt_slippage_bps: btSlippageBps,
    };
    const ruleSellPcts: Record<string, number> = {};
    for (const [k, v] of Object.entries(exits)) {
      if (v.on) ruleSellPcts[k] = v.sell_pct;
    }
    let holdDaysFromCond: number | null = null;
    const cleanedConditions = (sell.conditions || []).filter((node: ConditionNode) => {
      if ("left" in node && node.left?.indicator === HELD_DAYS_KEY) {
        const v = node.right && "value" in node.right ? Number(node.right.value) : NaN;
        if (Number.isFinite(v) && v > 0) holdDaysFromCond = Math.floor(v);
        return false;
      }
      return true;
    });
    return {
      name, trade_symbol: tradeSymbol, buy,
      sell_rules: {
        take_profit:    exits.tp.on    ? exits.tp.v    : null,
        stop_loss:      exits.sl.on    ? exits.sl.v    : null,
        trail_pct:      exits.trail.on ? exits.trail.v : null,
        trail_atr_mult: exits.atr.on   ? exits.atr.v   : null,
        hold_days:      holdDaysFromCond,
        conditions:     cleanedConditions,
        logic:          sell.logic,
        sell_amount_pct: sellAmountPct,
        rule_sell_pcts: ruleSellPcts,
      },
      amount_pct: buyAmountPct,
      screener_limit: screenerLimit,
      screener_spec: tradeSymbol === "screener:custom" ? screenerSpec : null,
      rebalance: tradeSymbol.startsWith("screener:") ? rebalance : undefined,
      execution,
    };
  }

  async function saveChanges() {
    setErr(""); setSaveMsg("");
    setBusy("save");
    try {
      await api.updateStrategy(strategy.id, buildDef(), strategy.run_mode);
      setSaveMsg("저장됨 — 변경 전 정의는 자동으로 새 버전으로 보존됐습니다.");
      onSaved();
    } catch (e) { setErr((e as Error).message); }
    finally { setBusy(""); }
  }

  async function runBacktest() {
    setErr("");
    setBusy("backtest"); setBacktest(null);
    try {
      const r = await api.runBacktest(buildDef(), capital, undefined, undefined,
                                       strategy.id);
      setBacktest(r);
    } catch (e) { setErr((e as Error).message); }
    finally { setBusy(""); }
  }

  async function runAnalysis() {
    setErr("");
    setBusy("analysis"); setAnalysis(null);
    try {
      const r = await api.runAnalysis({
        conditions: buy.conditions, logic: buy.logic,
        target_symbol: tradeSymbol,
        target_indicator: symbols.find((s) => s.symbol === tradeSymbol)
          ?.indicators.find((i) => i.key.includes("pct_change"))?.key ?? "",
        forward_days: forwardDays,
      });
      setAnalysis(r);
    } catch (e) { setErr((e as Error).message); }
    finally { setBusy(""); }
  }

  function discardChanges() {
    if (!window.confirm("변경사항을 취소하고 마지막 저장 상태로 되돌릴까요?")) return;
    onSaved();   // 부모가 strategy 다시 fetch → key 변경 → 이 컴포넌트 remount
  }

  return (
    <div className="strategy-detail-body">
      {err && <div className="error">{err}</div>}
      {saveMsg && <div className="ok">{saveMsg}</div>}

      <BuildTab
        symbols={symbols} hasMaster={hasMaster}
        name={name} setName={setName}
        tradeSymbol={tradeSymbol} setTradeSymbol={setTradeSymbol}
        buy={buy} setBuy={setBuy}
        sell={sell} setSell={setSell}
        exits={exits} setRule={setRule}
        sellRealtimeEnabled={sellRealtimeEnabled} setSellRealtimeEnabled={setSellRealtimeEnabled}
        sellEodEnabled={sellEodEnabled} setSellEodEnabled={setSellEodEnabled}
        buyAmountPct={buyAmountPct} setBuyAmountPct={setBuyAmountPct}
        sellAmountPct={sellAmountPct} setSellAmountPct={setSellAmountPct}
        screenerLimit={screenerLimit} setScreenerLimit={setScreenerLimit}
        screenerSpec={screenerSpec} setScreenerSpec={setScreenerSpec}
        rebalance={rebalance} setRebalance={setRebalance}
        sizingMode={sizingMode} setSizingMode={setSizingMode}
        amountKrw={amountKrw} setAmountKrw={setAmountKrw}
        atrRiskPct={atrRiskPct} setAtrRiskPct={setAtrRiskPct}
        atrMult={atrMult} setAtrMult={setAtrMult}
        maxPositionPct={maxPositionPct} setMaxPositionPct={setMaxPositionPct}
        maxPositionEnabled={maxPositionEnabled} setMaxPositionEnabled={setMaxPositionEnabled}
        maxDrawdownPct={maxDrawdownPct} setMaxDrawdownPct={setMaxDrawdownPct}
        maxDrawdownEnabled={maxDrawdownEnabled} setMaxDrawdownEnabled={setMaxDrawdownEnabled}
        useLimit={useLimit} setUseLimit={setUseLimit}
        buyTolerancePct={buyTolerancePct} setBuyTolerancePct={setBuyTolerancePct}
        sellTolerancePct={sellTolerancePct} setSellTolerancePct={setSellTolerancePct}
        btCommissionBps={btCommissionBps} setBtCommissionBps={setBtCommissionBps}
        btSellTaxBps={btSellTaxBps} setBtSellTaxBps={setBtSellTaxBps}
        btSlippageBps={btSlippageBps} setBtSlippageBps={setBtSlippageBps}
        capital={capital} setCapital={setCapital}
        forwardDays={forwardDays} setForwardDays={setForwardDays}
        busy={busy} runAnalysis={runAnalysis} runBacktest={runBacktest}
        analysis={analysis}
        resetStrategy={discardChanges}
      />

      {backtest && backtest.success && (
        <div className="panel" style={{ marginTop: 12 }}>
          <h4>방금 실행한 백테스트 결과</h4>
          <p className="muted small">
            이 결과는 전략의 "백테스트 내역" 탭에 자동 저장됩니다.
          </p>
          {backtest.metrics && (
            <div className="rule-row">
              <span className="rule-label">총수익률</span>
              <span className="rule-val">
                {(backtest.metrics.total_return as number | null)?.toFixed(2) ?? "—"}%
              </span>
            </div>
          )}
        </div>
      )}
      {backtest && !backtest.success && (
        <div className="error">{backtest.error}</div>
      )}

      <div className="strategy-save-bar">
        <button className="apply-btn" disabled={!!busy} onClick={saveChanges}>
          {busy === "save" ? "저장 중…" : "✓ 변경사항 저장 (새 버전)"}
        </button>
        <button className="ghost" disabled={!!busy} onClick={discardChanges}>
          변경 취소
        </button>
        <span style={{ flex: 1 }} />
        <button className="danger-btn" onClick={onRemove}>전략 삭제</button>
      </div>
    </div>
  );
}

// ── 탭 2: 버전 ────────────────────────────────────────────────────────────────

function VersionsTab({ versions, onRestore }: {
  versions: StrategyVersionRow[];
  onRestore: (versionNo: number) => void;
}) {
  if (versions.length === 0) {
    return <p className="muted">아직 저장된 버전이 없습니다.</p>;
  }
  return (
    <div className="strategy-detail-body">
      <p className="muted small">
        매 저장마다 자동 스냅샷. 최대 50건 또는 30일까지 보관 — 그 이전 버전은 자동 회전.
      </p>
      <div className="version-list">
        {versions.map((v) => (
          <div key={v.version_no} className="version-row">
            <div className="version-no">v{v.version_no}</div>
            <div className="version-meta">
              <div className="version-name">{v.name}</div>
              <div className="muted small">
                {dateOnly(v.created_at)} · {labelReason(v.created_reason)}
              </div>
            </div>
            <div className="version-actions">
              <button className="ghost sm" onClick={() => onRestore(v.version_no)}>
                이 버전으로 복원
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function labelReason(reason: string): string {
  if (reason === "initial") return "최초 생성";
  if (reason === "manual_edit") return "수정";
  if (reason.startsWith("restore_from_v"))
    return `v${reason.slice("restore_from_v".length)} 복원 직전`;
  return reason;
}

// ── 탭 3: 현황 ────────────────────────────────────────────────────────────────

function StatsTab({ stats, strategy }: {
  stats: StrategyStats | null;
  strategy: StrategyRow;
}) {
  if (!stats) return <p className="muted">현황 데이터가 없습니다.</p>;
  const days = stats.days_live ?? stats.days_paper;
  const lifecycle = stats.live_started_at
    ? `실전 ${stats.days_live ?? 0}일`
    : stats.paper_started_at
      ? `모의 ${stats.days_paper ?? 0}일`
      : "—";

  return (
    <div className="strategy-detail-body">
      <div className="stats-grid">
        <StatBox label="적용 기간" value={lifecycle}
                 sub={days != null && days > 0
                   ? `시작일 ${dateOnly(stats.live_started_at ?? stats.paper_started_at)}`
                   : ""} />
        <StatBox label="누적 P&L" value={krw(stats.pnl_total)}
                 cls={(stats.pnl_total ?? 0) >= 0 ? "pos" : "neg"}
                 sub={stats.pnl_pct != null ? pct(stats.pnl_pct) : ""} />
        <StatBox label="승률"
                 value={stats.win_rate != null ? pct(stats.win_rate * 100, false) : "—"}
                 sub={stats.n_trades ? `거래 ${stats.n_trades}건` : ""} />
        <StatBox label="현재 보유"
                 value={stats.n_positions > 0 ? `${stats.n_positions}종목` : "없음"} />
      </div>

      <section className="panel" style={{ marginTop: 16 }}>
        <h4>운용 모드</h4>
        <Rule label="현재 모드"
              v={strategy.run_mode === "live" ? "실전"
                : strategy.run_mode === "paper" ? "모의" : "초안"} />
        <Rule label="모의 시작" v={dateOnly(stats.paper_started_at) || "—"} />
        <Rule label="실전 시작" v={dateOnly(stats.live_started_at) || "—"} />
        <Rule label="최근 동기화"
              v={stats.last_snapshot_at
                ? new Date(stats.last_snapshot_at).toLocaleString("ko-KR")
                : "—"} />
      </section>

      <p className="muted small" style={{ marginTop: 12 }}>
        ⓘ 종목별 매매 상세는 로컬앱 "주문 내역" 탭에서 확인하세요 (서버에는 요약만 보관).
      </p>
    </div>
  );
}

function StatBox({ label, value, sub, cls }: {
  label: string; value: string; sub?: string; cls?: string;
}) {
  return (
    <div className="stat-box">
      <div className="stat-label">{label}</div>
      <div className={"stat-value " + (cls ?? "")}>{value}</div>
      {sub && <div className="stat-sub muted small">{sub}</div>}
    </div>
  );
}

// ── 탭 4: 백테스트 내역 ────────────────────────────────────────────────────────

function BacktestsTab({ backtests }: {
  backtests: BacktestRunSummary[];
}) {
  if (backtests.length === 0) {
    return (
      <div className="strategy-detail-body">
        <p className="muted">이 전략으로 실행된 백테스트가 없습니다.</p>
        <Link to="/backtest" className="cta sm">빌더에서 백테스트 실행 →</Link>
      </div>
    );
  }
  return (
    <div className="strategy-detail-body">
      <table className="bt-history-table">
        <thead>
          <tr>
            <th>실행일</th>
            <th>버전</th>
            <th>기간</th>
            <th>초기자본</th>
            <th>총수익률</th>
            <th>MDD</th>
            <th>샤프</th>
          </tr>
        </thead>
        <tbody>
          {backtests.map((b) => {
            const m = b.metrics ?? {};
            const ret = (m.total_return as number | null) ?? null;
            const mdd = (m.max_drawdown as number | null) ?? null;
            const sharpe = (m.sharpe as number | null) ?? null;
            return (
              <tr key={b.id}>
                <td>{new Date(b.created_at).toLocaleString("ko-KR", {
                  year: "2-digit", month: "2-digit", day: "2-digit",
                  hour: "2-digit", minute: "2-digit",
                })}</td>
                <td>{b.version_no != null ? `v${b.version_no}` : "—"}</td>
                <td className="small muted">{b.start ?? "—"} ~ {b.end ?? "—"}</td>
                <td>{b.initial_capital.toLocaleString()}원</td>
                <td className={ret != null && ret >= 0 ? "pos" : ret != null ? "neg" : ""}>
                  {ret != null ? pct(ret * 100) : "—"}
                </td>
                <td>{mdd != null ? pct(mdd * 100, false) : "—"}</td>
                <td>{sharpe != null ? sharpe.toFixed(2) : "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── 공용 ──────────────────────────────────────────────────────────────────────

function Rule({ label, v }: { label: string; v: string }) {
  return (
    <div className="rule-row">
      <span className="rule-label">{label}</span>
      <span className="rule-val">{v}</span>
    </div>
  );
}

