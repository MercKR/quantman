import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import BlockTree, { type Catalog } from "../components/BlockTree";
import EquityChart from "../components/EquityChart";
import type {
  IrBlockSpec, IrNode, IrStrategyResult, SymbolInfo,
} from "../types";

/**
 * 전략 연구소 — 노코드 블록트리로 룰·팩터·포트폴리오 전략을 조립·백테스트.
 *
 * 전체 구조(StrategyIR)를 표현: 유니버스 · 신호(condition|score) · 포지션 4부품
 * (방향·사이징·진입·청산) · 펼침(조건/파라미터/자산). /ir/strategy로 실행.
 */

const METRIC_LABELS: [string, string, string][] = [
  ["total_return", "총수익률", "%"], ["cagr", "연수익률(CAGR)", "%"],
  ["mdd", "최대낙폭(MDD)", "%"], ["sharpe", "샤프", ""],
  ["n_trades", "거래수", ""], ["win_rate", "승률", "%"],
];

const SIZING_OPTS: [string, string][] = [
  ["equal_weight", "동일가중"], ["signal_proportional", "신호비례"],
  ["vol_inverse", "변동성 역가중"], ["fixed_risk", "고정위험"],
];
const DIRECTION_OPTS: [string, string][] = [
  ["long", "롱"], ["short", "숏"], ["long_short", "롱숏중립"],
];
const REBALANCE_OPTS: [string, string][] = [
  ["daily", "매일"], ["weekly", "매주"], ["monthly", "매월"],
];
const EXIT_OPTS: [string, string][] = [
  ["stop_target", "손익절"], ["after_n_days", "N일 보유"], ["on_condition", "조건 매도"],
];

function fmt(v: number | null | undefined, suffix: string): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  const n = suffix === "%" ? v.toFixed(2) : (Number.isInteger(v) ? String(v) : v.toFixed(2));
  return `${n}${suffix}`;
}

type Mode = "rule" | "factor";
type SweepAxis = "none" | "condition" | "parameter" | "asset";

export default function IrBuilder() {
  const [catalogList, setCatalogList] = useState<IrBlockSpec[]>([]);
  const [symbols, setSymbols] = useState<SymbolInfo[]>([]);
  const [loadErr, setLoadErr] = useState<string | null>(null);

  const [mode, setMode] = useState<Mode>("rule");
  const [universeSymbols, setUniverseSymbols] = useState<string>("005930");  // rule/list
  const [signal, setSignal] = useState<IrNode | null>(null);

  // 포지션 — 팩터
  const [direction, setDirection] = useState("long");
  const [sizingMode, setSizingMode] = useState("equal_weight");
  const [topN, setTopN] = useState<number | "">(20);
  const [rebalance, setRebalance] = useState("monthly");
  // 포지션 — 룰
  const [exitMode, setExitMode] = useState("stop_target");
  const [holdDays, setHoldDays] = useState<number | "">(20);
  const [takeProfit, setTakeProfit] = useState<number | "">("");
  const [stopLoss, setStopLoss] = useState<number | "">("");
  const [exitCond, setExitCond] = useState<IrNode | null>(null);

  // 펼침
  const [sweepAxis, setSweepAxis] = useState<SweepAxis>("none");
  const [sweepParamPath, setSweepParamPath] = useState("position.entry.top_n");
  const [sweepParamValues, setSweepParamValues] = useState("10, 20, 30");
  const [sweepAssets, setSweepAssets] = useState("");
  const [sweepLabel, setSweepLabel] = useState<IrNode | null>(null);

  const [capital, setCapital] = useState(10_000_000);
  const [result, setResult] = useState<IrStrategyResult | null>(null);
  const [running, setRunning] = useState(false);

  const catalog: Catalog = useMemo(
    () => new Map(catalogList.map((b) => [b.op, b])), [catalogList]);

  useEffect(() => {
    Promise.all([api.irCatalog(), api.symbols()])
      .then(([cat, sym]) => { setCatalogList(cat.blocks); setSymbols(sym.symbols); })
      .catch((e) => setLoadErr(e.message ?? String(e)));
  }, []);

  // 모드 전환/카탈로그 로드 시 시작 신호 시드
  useEffect(() => {
    if (!catalog.size) return;
    if (mode === "rule") {
      setSignal({
        op: "compare", params: { op: ">" },
        inputs: {
          left: { op: "data", params: { ref: "__SELF__.Close" } },
          right: { op: "ts_mean", params: { window: 20 },
                   inputs: { signal: { op: "data", params: { ref: "__SELF__.Close" } } } },
        },
      });
    } else {
      setSignal({ op: "rank", inputs: { signal: { op: "data", params: { ref: "momentum_12_1m" } } } });
    }
    setResult(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, catalog.size]);

  const dataSymbols = useMemo(() => symbols.filter((s) => s.has_backtest_data), [symbols]);
  const selfIndicators = useMemo(() => {
    const first = universeSymbols.split(",")[0]?.trim();
    return (symbols.find((s) => s.symbol === first)?.indicators
      ?? dataSymbols[0]?.indicators ?? []);
  }, [symbols, dataSymbols, universeSymbols]);

  const signalType = mode === "rule" ? "condition" : "score";

  function buildStrategy(): Record<string, unknown> {
    const syms = universeSymbols.split(",").map((s) => s.trim()).filter(Boolean);
    const sweep = buildSweep();
    if (mode === "rule") {
      return {
        name: "연구소 전략",
        universe: { kind: syms.length > 1 ? "list" : "single", symbols: syms },
        signal,
        position: {
          direction: "long",
          sizing: { mode: "equal_weight" },
          entry: { mode: "on_signal" },
          exit: {
            mode: exitMode,
            hold_days: holdDays === "" ? null : holdDays,
            take_profit: takeProfit === "" ? null : takeProfit,
            stop_loss: stopLoss === "" ? null : stopLoss,
            condition: exitMode === "on_condition" ? exitCond : null,
          },
        },
        simulation: { initial_capital: capital },
        sweep,
      };
    }
    return {
      name: "연구소 팩터",
      universe: syms.length ? { kind: "list", symbols: syms } : { kind: "all" },
      signal,
      position: {
        direction,
        sizing: { mode: sizingMode },
        entry: { mode: "scheduled", rebalance, top_n: topN === "" ? null : topN },
      },
      simulation: { initial_capital: capital },
      sweep,
    };
  }

  function buildSweep(): Record<string, unknown> {
    if (sweepAxis === "parameter") {
      return {
        axis: "parameter", param_path: sweepParamPath,
        param_values: sweepParamValues.split(",").map((x) => Number(x.trim()))
          .filter((n) => !Number.isNaN(n)),
      };
    }
    if (sweepAxis === "asset") {
      return { axis: "asset", assets: sweepAssets.split(",").map((s) => s.trim()).filter(Boolean) };
    }
    if (sweepAxis === "condition") return { axis: "condition", label: sweepLabel };
    return { axis: "none" };
  }

  async function run() {
    if (!signal) return;
    setRunning(true); setResult(null);
    try {
      setResult(await api.runIrStrategy(buildStrategy()));
    } catch (e) {
      setResult({ success: false, error: (e as Error).message });
    } finally {
      setRunning(false);
    }
  }

  if (loadErr) {
    return <div className="panel"><div className="page-title">전략 연구소</div>
      <p className="muted">카탈로그를 불러오지 못했습니다: {loadErr}</p></div>;
  }

  return (
    <div>
      <div className="page-title">전략 연구소</div>
      <p className="page-sub">
        블록을 조립해 룰·팩터·포트폴리오 전략을 만들고 백테스트합니다.
        슬롯에 블록을 끼워 중첩할 수 있어요.
      </p>

      {/* 모드 + 유니버스 + 자본 */}
      <div className="panel">
        <div className="seg">
          <button type="button" className={"seg-btn" + (mode === "rule" ? " on" : "")}
                  onClick={() => setMode("rule")}>룰 기반 (조건)</button>
          <button type="button" className={"seg-btn" + (mode === "factor" ? " on" : "")}
                  onClick={() => setMode("factor")}>팩터 (점수·횡단)</button>
        </div>
        <div className="lab-row" style={{ marginTop: 12 }}>
          <label className="lab-field">
            {mode === "rule" ? "대상 종목 (쉼표 구분)" : "유니버스 (비우면 전체)"}
            <input type="text" value={universeSymbols} placeholder={mode === "rule" ? "005930" : "비우면 전체 종목"}
                   onChange={(e) => setUniverseSymbols(e.target.value)} style={{ minWidth: 240 }} />
          </label>
          <label className="lab-field">초기자본
            <input type="number" value={capital} step={1_000_000}
                   onChange={(e) => setCapital(Number(e.target.value))} />
          </label>
        </div>
        {dataSymbols.length > 0 && (
          <p className="muted" style={{ fontSize: 12, marginTop: 6 }}>
            백테스트 데이터 보유 종목 {dataSymbols.length.toLocaleString()}개 · 예: {dataSymbols.slice(0, 4).map((s) => s.symbol).join(", ")}
          </p>
        )}
      </div>

      {/* 신호 */}
      <div className="panel">
        <div className="panel-title">{mode === "rule" ? "매수 신호 (조건)" : "팩터 점수 (알파)"}</div>
        <p className="muted" style={{ fontSize: 13, marginTop: 0 }}>
          {mode === "rule"
            ? "조건(참/거짓) 블록 — 참인 날 매수합니다."
            : "점수 블록 — 종목을 줄 세워 상위 N을 보유합니다 (예: 모멘텀 순위)."}
        </p>
        {catalog.size ? (
          <BlockTree node={signal} catalog={catalog} symbols={symbols}
                     selfIndicators={selfIndicators} requiredType={signalType}
                     onChange={setSignal} />
        ) : <p className="muted">불러오는 중…</p>}
      </div>

      {/* 포지션 */}
      <div className="panel">
        <div className="panel-title">포지션</div>
        {mode === "factor" ? (
          <div className="lab-row">
            <label className="lab-field">방향
              <select value={direction} onChange={(e) => setDirection(e.target.value)}>
                {DIRECTION_OPTS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </label>
            <label className="lab-field">사이징
              <select value={sizingMode} onChange={(e) => setSizingMode(e.target.value)}>
                {SIZING_OPTS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </label>
            <label className="lab-field">상위 N
              <input type="number" value={topN}
                     onChange={(e) => setTopN(e.target.value === "" ? "" : Number(e.target.value))} />
            </label>
            <label className="lab-field">리밸런싱
              <select value={rebalance} onChange={(e) => setRebalance(e.target.value)}>
                {REBALANCE_OPTS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </label>
          </div>
        ) : (
          <>
            <div className="lab-row">
              <label className="lab-field">청산 방식
                <select value={exitMode} onChange={(e) => setExitMode(e.target.value)}>
                  {EXIT_OPTS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </label>
              <label className="lab-field">보유일수
                <input type="number" value={holdDays}
                       onChange={(e) => setHoldDays(e.target.value === "" ? "" : Number(e.target.value))} />
              </label>
              <label className="lab-field">익절(%)
                <input type="number" value={takeProfit} placeholder="없음"
                       onChange={(e) => setTakeProfit(e.target.value === "" ? "" : Number(e.target.value))} />
              </label>
              <label className="lab-field">손절(%)
                <input type="number" value={stopLoss} placeholder="없음"
                       onChange={(e) => setStopLoss(e.target.value === "" ? "" : Number(e.target.value))} />
              </label>
            </div>
            {exitMode === "on_condition" && (
              <div style={{ marginTop: 10 }}>
                <div className="muted" style={{ fontSize: 13, marginBottom: 4 }}>매도 조건</div>
                <BlockTree node={exitCond} catalog={catalog} symbols={symbols}
                           selfIndicators={selfIndicators} requiredType="condition"
                           onChange={setExitCond} />
              </div>
            )}
          </>
        )}
      </div>

      {/* 펼침 */}
      <div className="panel">
        <div className="panel-title">펼침 (비교 분석)</div>
        <div className="lab-row">
          <label className="lab-field">축
            <select value={sweepAxis} onChange={(e) => setSweepAxis(e.target.value as SweepAxis)}>
              <option value="none">없음 (1회)</option>
              <option value="parameter">파라미터 그리드</option>
              <option value="asset">종목별</option>
              <option value="condition">국면별</option>
            </select>
          </label>
          {sweepAxis === "parameter" && (
            <>
              <label className="lab-field">파라미터 경로
                <input type="text" value={sweepParamPath} style={{ minWidth: 200 }}
                       onChange={(e) => setSweepParamPath(e.target.value)} />
              </label>
              <label className="lab-field">값들
                <input type="text" value={sweepParamValues}
                       onChange={(e) => setSweepParamValues(e.target.value)} />
              </label>
            </>
          )}
          {sweepAxis === "asset" && (
            <label className="lab-field">종목들 (쉼표)
              <input type="text" value={sweepAssets} placeholder="005930, 000660" style={{ minWidth: 220 }}
                     onChange={(e) => setSweepAssets(e.target.value)} />
            </label>
          )}
        </div>
        {sweepAxis === "condition" && (
          <div style={{ marginTop: 10 }}>
            <div className="muted" style={{ fontSize: 13, marginBottom: 4 }}>국면 라벨 블록 (예: VIX 구간분할)</div>
            <BlockTree node={sweepLabel} catalog={catalog} symbols={symbols}
                       selfIndicators={selfIndicators} requiredType="label"
                       onChange={setSweepLabel} />
          </div>
        )}
      </div>

      <div className="lab-actions">
        <button type="button" onClick={run} disabled={running || !signal}>
          {running ? "백테스트 중…" : "백테스트 실행"}
        </button>
      </div>

      {result && <ResultPanel result={result} />}
    </div>
  );
}

function ResultPanel({ result }: { result: IrStrategyResult }) {
  if (!result.success) {
    return (
      <div className="panel result-fail">
        <div className="panel-title">실행 실패</div>
        <p className="neg">{result.error}</p>
        {result.issues?.length ? (
          <ul className="issue-list">
            {result.issues.map((i, k) => (
              <li key={k}><code>{i.rule}</code> {i.message}{i.path !== "root" ? ` (${i.path})` : ""}</li>
            ))}
          </ul>
        ) : null}
      </div>
    );
  }

  // 펼침 결과 — 버킷 표
  if (result.axis && result.buckets) {
    const rows = Object.entries(result.buckets);
    return (
      <div className="panel">
        <div className="panel-title">펼침 결과 — {result.axis === "parameter" ? "파라미터"
          : result.axis === "asset" ? "종목별" : "국면별"}</div>
        {result.warnings?.length ? (
          <div className="warn-banner">⚠ {result.warnings.map((w) => w.message).join(" · ")}</div>
        ) : null}
        <table className="sweep-table">
          <thead><tr><th>{result.param ?? "구분"}</th><th>표본</th><th>누적수익(%)</th>
            <th>샤프</th><th>승률(%)</th></tr></thead>
          <tbody>
            {rows.map(([k, b]) => (
              <tr key={k}>
                <td>{k}</td>
                <td>{b.n ?? "—"}</td>
                <td className={(b.cum_return ?? 0) >= 0 ? "pos" : "neg"}>{fmt(b.cum_return, "")}</td>
                <td>{fmt(b.sharpe, "")}</td>
                <td>{fmt(b.win_rate, "")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  // 단일 백테스트
  const m = result.metrics ?? {};
  return (
    <div className="panel">
      <div className="panel-title">백테스트 결과</div>
      {result.warnings?.length ? (
        <div className="warn-banner">⚠ {result.warnings.map((w) => w.message).join(" · ")}</div>
      ) : null}
      <div className="stat-grid">
        {METRIC_LABELS.map(([key, label, suf]) => {
          const v = m[key];
          const pol = (key === "total_return" || key === "cagr")
            ? (typeof v === "number" ? (v >= 0 ? "pos" : "neg") : "") : "";
          return (
            <div className="stat" key={key}>
              <div className="label">{label}</div>
              <div className={"value " + pol}>{fmt(v, suf)}</div>
            </div>
          );
        })}
      </div>
      {result.equity?.length ? (
        <div style={{ marginTop: 16 }}>
          <EquityChart equity={result.equity} benchmark={result.benchmark} />
        </div>
      ) : null}
    </div>
  );
}
