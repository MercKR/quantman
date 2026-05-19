import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import EquityChart from "../components/EquityChart";
import type { DeviceRow, StrategyRow, SyncSnapshot } from "../types";

const won = (v: number | undefined) =>
  v == null ? "-" : v.toLocaleString() + "원";

export default function Dashboard() {
  const [snap, setSnap] = useState<SyncSnapshot | null>(null);
  const [devices, setDevices] = useState<DeviceRow[]>([]);
  const [strategies, setStrategies] = useState<StrategyRow[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    Promise.all([
      api.snapshot().catch(() => null),
      api.devices().catch(() => []),
      api.listStrategies().catch(() => []),
    ]).then(([s, d, st]) => {
      setSnap(s); setDevices(d); setStrategies(st); setLoaded(true);
    });
  }, []);

  const connected = devices.length > 0;
  const paper = strategies.filter((s) => s.run_mode === "paper");
  const bal = snap?.payload.balance;
  const positions = snap?.payload.positions ?? [];

  const steps: { name: string; done: boolean; desc: ReactNode }[] = [
    {
      name: "전략 만들기", done: strategies.length > 0,
      desc: <>백테스트로 첫 매매 전략을 만들어 보세요. <Link to="/backtest">백테스트로 이동 →</Link></>,
    },
    {
      name: "모의투자 배정", done: paper.length > 0,
      desc: <>만든 전략을 모의투자 모드로 바꾸면 로컬앱이 가져가 실행합니다. <Link to="/strategies">전략 관리 →</Link></>,
    },
    {
      name: "기기 연결", done: connected,
      desc: <>로컬앱을 설치하고 이 계정과 연결하세요. <Link to="/pair">기기 연결 →</Link></>,
    },
    {
      name: "자동매매 가동", done: !!snap,
      desc: <>로컬앱에서 자동매매를 시작하면 체결·평가 결과가 이 화면에 동기화됩니다.</>,
    },
  ];
  const currentIdx = steps.findIndex((s) => !s.done);
  const allDone = currentIdx === -1;

  return (
    <div>
      <h1 className="page-title">대시보드</h1>
      <p className="page-sub">전략 성과와 모의투자 현황을 한눈에 봅니다.</p>

      {!loaded && <p className="muted">불러오는 중…</p>}

      {loaded && (
        <>
          {allDone ? (
            <div className="panel done-banner">
              <span className="dot on" />
              설정 완료 — 모의투자 자동매매가 가동 중입니다.
            </div>
          ) : (
            <div className="steps">
              {steps.map((s, i) => {
                const state = s.done ? "done"
                  : i === currentIdx ? "current" : "todo";
                return (
                  <div key={i} className={"step " + state}>
                    <div className="step-num">{s.done ? "✓" : i + 1}</div>
                    <div className="step-body">
                      <div className="step-name">{s.name}</div>
                      {state === "current" && (
                        <div className="step-desc">{s.desc}</div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {snap && bal && (
            <>
              <div className="cards">
                <div className="stat">
                  <div className="label">총 평가금액</div>
                  <div className="value">{won(bal.total_eval)}</div>
                </div>
                <div className="stat">
                  <div className="label">예수금</div>
                  <div className="value">{won(bal.cash)}</div>
                </div>
                <div className="stat">
                  <div className="label">보유 종목</div>
                  <div className="value">{positions.length}개</div>
                </div>
              </div>
              <div className="spacer" />

              {snap.payload.equity && snap.payload.equity.length > 1 && (
                <div className="panel">
                  <h3>자산곡선 (모의투자)</h3>
                  <EquityChart equity={snap.payload.equity} />
                </div>
              )}

              {positions.length > 0 && (
                <div className="panel">
                  <h3>보유 종목</h3>
                  <table>
                    <thead>
                      <tr><th>종목</th><th>수량</th><th>평균가</th><th>현재가</th></tr>
                    </thead>
                    <tbody>
                      {positions.map((p) => (
                        <tr key={p.symbol}>
                          <td>{p.name ?? p.symbol}</td>
                          <td>{p.qty}</td>
                          <td>{won(p.avg_price)}</td>
                          <td>{won(p.eval_price)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <p className="muted" style={{ marginTop: 10 }}>
                    마지막 동기화: {snap.received_at.slice(0, 16).replace("T", " ")}
                  </p>
                </div>
              )}
            </>
          )}

          <div className="panel">
            <h3>내 전략</h3>
            {strategies.length === 0 ? (
              <p className="muted">
                아직 전략이 없습니다. <Link to="/backtest">백테스트</Link>로 첫 전략을 만들어 보세요.
              </p>
            ) : (
              <p className="muted">
                전략 {strategies.length}개 · 모의투자 {paper.length}개 가동.{" "}
                <Link to="/strategies">전략 관리 →</Link>
              </p>
            )}
          </div>
        </>
      )}
    </div>
  );
}
