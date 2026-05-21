/**
 * 모의/실전 전역 모드 — 모든 페이지가 이 상태를 구독해 데이터를 필터한다.
 *
 * 시각 경고: 실전 모드일 때 <html data-mode="live"> 가 붙어 CSS가
 * 빨간 stripe·배지를 활성화한다. 사용자가 모의/실전을 헷갈리지 않게
 * 페이지 어디에서나 동일한 시각 신호를 보여준다.
 */

import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";

export type TradingMode = "paper" | "live";

interface ModeContextValue {
  mode: TradingMode;
  setMode: (m: TradingMode) => void;
  isLive: boolean;
}

const ModeContext = createContext<ModeContextValue | null>(null);
const MODE_KEY = "qp_mode";

export function ModeProvider({ children }: { children: ReactNode }) {
  const [mode, _setMode] = useState<TradingMode>(() => {
    const stored = localStorage.getItem(MODE_KEY);
    return stored === "live" ? "live" : "paper";
  });

  const setMode = (m: TradingMode) => {
    _setMode(m);
    localStorage.setItem(MODE_KEY, m);
  };

  useEffect(() => {
    document.documentElement.dataset.mode = mode;
  }, [mode]);

  return (
    <ModeContext.Provider value={{ mode, setMode, isLive: mode === "live" }}>
      {children}
    </ModeContext.Provider>
  );
}

export function useMode() {
  const ctx = useContext(ModeContext);
  if (!ctx) throw new Error("useMode must be used within ModeProvider");
  return ctx;
}
