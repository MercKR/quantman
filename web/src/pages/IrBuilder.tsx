import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import BlockTree, { type Catalog } from "../components/BlockTree";
import EquityChart from "../components/EquityChart";
import type { IrBacktestResult, IrBlockSpec, IrNode, SymbolInfo } from "../types";

/**
 * 전략 연구소 — 노코드 블록트리로 고급 퀀트 전략을 조립하고 백테스트.
 *
 * 자기서술 카탈로그(/ir/catalog)로 빌더를 구동, /ir/backtest로 실행.
 * 기존 "전략 만들기"(문장 빌더)와 병행하는 새 라우트 — 충돌 0.
 */

const METRIC_LABELS: [string, string, string][] = [
  // key, label, suffix
  ["total_return", "총수익률", "%"],
  ["cagr", "연수익률(CAGR)", "%"],
  ["mdd", "최대낙폭(MDD)", "%"],
  ["sharpe", "샤프", ""],
  ["n_trades", "거래수", ""],
  ["win_rate", "승률", "%"],
];

function fmt(v: number | null | undefined, suffix: string): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  const n = suffix === "%" ? v.toFixed(2) : (Number.isInteger(v) ? String(v) : v.toFixed(2));
  return `${n}${suffix}`;
}

export default function IrBuilder() {
  const [catalogList, setCatalogList] = useState<IrBlockSpec[]>([]);
  const [symbols, setSymbols] = useState<SymbolInfo[]>([]);
  const [loadErr, setLoadErr] = useState<string | null>(null);

  const [tradeSymbol, setTradeSymbol] = useState<string>("");
  const [buyNode, setBuyNode] = useState<IrNode | null>(null);
  const [holdDays, setHoldDays] = useState<number | "">(20);
  const [takeProfit, setTakeProfit] = useState<number | "">("");
  const [stopLoss, setStopLoss] = useState<number | "">("");
  const [capital, setCapital] = useState<number>(10_000_000);

  const [result, setResult] = useState<IrBacktestResult | null>(null);
  const [running, setRunning] = useState(false);

  const catalog: Catalog = useMemo(
    () => new Map(catalogList.map((b) => [b.op, b])), [catalogList]);

  useEffect(() => {
    Promise.all([api.irCatalog(), api.symbols()])
      .then(([cat, sym]) => {
        setCatalogList(cat.blocks);
        const tradable = sym.symbols.filter((s) => s.has_backtest_data);
        setSymbols(sym.symbols);
        if (tradable.length && !tradeSymbol) setTradeSymbol(tradable[0].symbol);
      })
      .catch((e) => setLoadErr(e.message ?? String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 카탈로그 로드 후 시작 예시 시드 — "종가가 20일 평균 위" (중첩 시연·항상 유효)
  useEffect(() => {
    if (catalog.size && buyNode === null) {
      setBuyNode({
        op: "compare", params: { op: ">" },
        inputs: {
          left: { op: "data", params: { ref: "__SELF__.Close" } },
          right: { op: "ts_mean", params: { window: 20 },
                   inputs: { signal: { op: "data", params: { ref: "__SELF__.Close" } } } },
        },
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [catalog.size]);

  const selfIndicators = useMemo(
    () => symbols.find((s) => s.symbol === tradeSymbol)?.indicators ?? [],
    [symbols, tradeSymbol]);

  const dataSymbols = symbols.filter((s) => s.has_backtest_data);

  async function run() {
    if (!buyNode || !tradeSymbol) return;
    setRunning(true);
    setResult(null);
    try {
      const res = await api.runIrBacktest({
        trade_symbol: tradeSymbol,
        buy: buyNode,
        hold_days: holdDays === "" ? null : holdDays,
        take_profit: takeProfit === "" ? null : takeProfit,
        stop_loss: stopLoss === "" ? null : stopLoss,
        initial_capital: capital,
      });
      setResult(res);
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
        블록을 조립해 고급 전략을 만들고 백테스트합니다. 슬롯에 또 다른 블록을 끼워
        중첩할 수 있어요 — 예: <b>종가</b>가 <b>20일 평균</b> 위.
      </p>

      <div className="panel">
        <div className="lab-row">
          <label className="lab-field">대상 종목
            <select value={tradeSymbol} onChange={(e) => setTradeSymbol(e.target.value)}>
              {dataSymbols.map((s) => (
                <option key={s.symbol} value={s.symbol}>
                  {s.name ? `${s.symbol} ${s.name}` : s.symbol}
                </option>
              ))}
            </select>
          </label>
          <label className="lab-field">초기자본
            <input type="number" value={capital} step={1_000_000}
                   onChange={(e) => setCapital(Number(e.target.value))} />
          </label>
        </div>
      </div>

      <div className="panel">
        <div className="panel-title">매수 신호</div>
        <p className="muted" style={{ fontSize: 13, marginTop: 0 }}>
          조건(참/거짓) 블록을 만들면 그 신호가 참인 날 매수합니다.</p>
        {catalog.size ? (
          <BlockTree node={buyNode} catalog={catalog} symbols={symbols}
                     selfIndicators={selfIndicators} requiredType="condition"
                     onChange={setBuyNode} />
        ) : <p className="muted">불러오는 중…</p>}
      </div>

      <div className="panel">
        <div className="panel-title">청산 규칙</div>
        <div className="lab-row">
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
      </div>

      <div className="lab-actions">
        <button type="button" onClick={run} disabled={running || !buyNode || !tradeSymbol}>
          {running ? "백테스트 중…" : "백테스트 실행"}
        </button>
      </div>

      {result && <ResultPanel result={result} />}
    </div>
  );
}

function ResultPanel({ result }: { result: IrBacktestResult }) {
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
  const m = result.metrics ?? {};
  return (
    <div className="panel">
      <div className="panel-title">백테스트 결과</div>
      {result.warnings?.length ? (
        <div className="warn-banner">
          ⚠ {result.warnings.map((w) => w.message).join(" · ")}
        </div>
      ) : null}
      <div className="stat-grid">
        {METRIC_LABELS.map(([key, label, suf]) => {
          const v = m[key];
          const pol = (key === "total_return" || key === "cagr")
            ? (typeof v === "number" ? (v >= 0 ? "pos" : "neg") : "")
            : "";
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
