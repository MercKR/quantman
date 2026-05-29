import type {
  AnalysisResult, BacktestResult, BacktestRunDetail, BacktestRunSummary,
  CommandRow, CommandType, DeviceRow, IrBacktestResult, IrBlockSpec, IrNode,
  MarketContext, NextDayPreview, PortfolioRisk,
  ScreenerField, ScreenerMatch, ScreenerPreset, ScreenerSpecIO, ScreenerUserPreset,
  StrategyDef, StrategyRow, StrategyStats, StrategyVersionRow,
  SymbolInfo, SyncSnapshot, TradingTimeline, UserSettingsIO,
} from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "qp_token";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

// Audit P0-1 — ETag/304 자동 처리. 서버가 ETag 헤더 보내는 endpoint(/sync/snapshot 등)에서
// 동일 응답 시 304 받아 캐시된 데이터 반환. egress·서버 부담 큰 폭 절감.
// GET 요청만 적용 (POST/PUT/DELETE는 캐시 의미 없음).
const etagCache = new Map<string, { etag: string; data: unknown }>();

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(opts.headers as Record<string, string>),
  };
  const t = tokenStore.get();
  if (t) headers["Authorization"] = `Bearer ${t}`;

  const method = (opts.method ?? "GET").toUpperCase();
  const cached = method === "GET" ? etagCache.get(path) : undefined;
  if (cached) headers["If-None-Match"] = cached.etag;

  const res = await fetch(BASE + path, { ...opts, headers });

  if (res.status === 304 && cached) {
    return cached.data as T;
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `${res.status} ${res.statusText}`);
  }
  if (res.status === 204) return null as T;

  const data = await res.json();
  const etag = res.headers.get("ETag");
  if (method === "GET" && etag) {
    etagCache.set(path, { etag, data });
  }
  return data;
}

export const api = {
  signup: (email: string, password: string) =>
    req<{ access_token: string }>("/auth/signup", {
      method: "POST", body: JSON.stringify({ email, password }),
    }),
  login: (email: string, password: string) =>
    req<{ access_token: string }>("/auth/login", {
      method: "POST", body: JSON.stringify({ email, password }),
    }),
  googleLogin: (credential: string) =>
    req<{ access_token: string }>("/auth/google", {
      method: "POST", body: JSON.stringify({ credential }),
    }),
  me: () => req<{ id: number; email: string; created_at: string }>("/auth/me"),

  symbols: () => req<{ symbols: SymbolInfo[]; has_master: boolean }>("/symbols"),

  listStrategies: () => req<StrategyRow[]>("/strategies"),
  getStrategy: (id: number) => req<StrategyRow>(`/strategies/${id}`),
  createStrategy: (definition: StrategyDef, run_mode: string) =>
    req<StrategyRow>("/strategies", {
      method: "POST", body: JSON.stringify({ definition, run_mode }),
    }),
  updateStrategy: (id: number, definition: StrategyDef, run_mode: string) =>
    req<StrategyRow>(`/strategies/${id}`, {
      method: "PUT", body: JSON.stringify({ definition, run_mode }),
    }),
  deleteStrategy: (id: number) =>
    req<{ ok: boolean }>(`/strategies/${id}`, { method: "DELETE" }),

  // Phase 59 — 버전·현황·백테스트 내역
  listStrategyVersions: (id: number) =>
    req<StrategyVersionRow[]>(`/strategies/${id}/versions`),
  getStrategyVersion: (id: number, versionNo: number) =>
    req<StrategyVersionRow>(`/strategies/${id}/versions/${versionNo}`),
  restoreStrategyVersion: (id: number, versionNo: number) =>
    req<StrategyRow>(`/strategies/${id}/restore`, {
      method: "POST", body: JSON.stringify({ version_no: versionNo }),
    }),
  getStrategyStats: (id: number) =>
    req<StrategyStats>(`/strategies/${id}/stats`),
  listStrategyBacktests: (id: number) =>
    req<BacktestRunSummary[]>(`/strategies/${id}/backtests`),

  runBacktest: (strategy: StrategyDef, initial_capital: number,
                start?: string, end?: string,
                strategy_id?: number, version_no?: number) =>
    req<BacktestResult>("/backtest/run", {
      method: "POST",
      body: JSON.stringify({
        strategy, initial_capital, start, end, strategy_id, version_no,
      }),
    }),
  runAnalysis: (body: {
    conditions: unknown[]; logic: string; target_symbol: string;
    target_indicator: string; forward_days: number; lookback_years?: number | null;
  }) => req<AnalysisResult>("/analysis/run", {
    method: "POST", body: JSON.stringify(body),
  }),

  listBacktestRuns: () => req<BacktestRunSummary[]>("/backtest/runs"),
  getBacktestRun: (id: number) => req<BacktestRunDetail>(`/backtest/runs/${id}`),
  deleteBacktestRun: (id: number) =>
    req<{ ok: boolean }>(`/backtest/runs/${id}`, { method: "DELETE" }),

  devices: () => req<DeviceRow[]>("/auth/devices"),
  revokeDevice: (id: number) =>
    req<{ ok: boolean }>(`/auth/devices/${id}`, { method: "DELETE" }),
  approveDevice: (user_code: string) =>
    req<{ ok: boolean; device_name: string }>("/auth/device/approve", {
      method: "POST", body: JSON.stringify({ user_code }),
    }),

  snapshot: () => req<SyncSnapshot | null>("/sync/snapshot"),

  // 명령 버스 — 웹에서 발행, 로컬앱이 SSE로 수신·실행
  listCommands: (deviceId?: number, onlyPending = false) => {
    const q = new URLSearchParams();
    if (deviceId !== undefined) q.set("device_id", String(deviceId));
    if (onlyPending) q.set("only_pending", "true");
    return req<CommandRow[]>(`/sync/commands?${q.toString()}`);
  },
  createCommand: (deviceId: number, type: CommandType,
                   params: Record<string, string | number> = {}) =>
    req<CommandRow>("/sync/commands", {
      method: "POST",
      body: JSON.stringify({ device_id: deviceId, type, params }),
    }),

  // Phase 13 — Monitor 고도화
  marketContext: () => req<MarketContext>("/market/context"),
  portfolioRisk: (window = 60) =>
    req<PortfolioRisk>(`/portfolio/risk?window=${window}`),
  getSettings: () => req<UserSettingsIO>("/settings"),
  putSettings: (s: UserSettingsIO) =>
    req<UserSettingsIO>("/settings", { method: "PUT", body: JSON.stringify(s) }),

  // Phase 17~ — 종목 자동 선택 (스크리너)
  listScreenerPresets: () =>
    req<{ presets: ScreenerPreset[]; as_of: string | null }>("/screener/presets"),
  runScreenerPreset: (key: string) =>
    req<{ preset: string; count: number; matches: ScreenerMatch[]; as_of: string | null }>(
      `/screener/preset/${key}/run`, { method: "POST" }),
  screenerFields: () =>
    req<{ fields: ScreenerField[] }>("/screener/fields"),
  runScreenerCustom: (spec: ScreenerSpecIO) =>
    req<{ count: number; matches: ScreenerMatch[]; as_of: string | null }>(
      "/screener/run", { method: "POST", body: JSON.stringify(spec) }),

  // 내 세트 (계정 저장 사용자 정의 세트) CRUD
  listMyScreenerPresets: () =>
    req<{ presets: ScreenerUserPreset[] }>("/screener/my-presets"),
  createMyScreenerPreset: (name: string, spec: ScreenerSpecIO) =>
    req<ScreenerUserPreset>("/screener/my-presets", {
      method: "POST", body: JSON.stringify({ name, spec }),
    }),
  updateMyScreenerPreset: (id: number, name: string, spec: ScreenerSpecIO) =>
    req<ScreenerUserPreset>(`/screener/my-presets/${id}`, {
      method: "PUT", body: JSON.stringify({ name, spec }),
    }),
  deleteMyScreenerPreset: (id: number) =>
    req<{ ok: boolean }>(`/screener/my-presets/${id}`, { method: "DELETE" }),

  // Phase 31 — 내일 매매 미리보기
  getNextDayPreview: () => req<NextDayPreview>("/preview/next-day"),
  regenerateNextDayPreview: () =>
    req<NextDayPreview>("/preview/regenerate", { method: "POST" }),

  // 자동매매 타임라인 — [now-24h, now+24h] 이벤트 + heartbeat 상태
  getTradingTimeline: () => req<TradingTimeline>("/trading/timeline"),

  // 블록 IR 노코드 빌더 (P1-7) — 자기서술 카탈로그 + IR 백테스트
  irCatalog: () => req<{ blocks: IrBlockSpec[] }>("/ir/catalog"),
  runIrBacktest: (body: {
    trade_symbol: string;
    buy: IrNode;
    sell?: IrNode | null;
    hold_days?: number | null;
    take_profit?: number | null;
    stop_loss?: number | null;
    trail_atr_mult?: number | null;
    trail_pct?: number | null;
    initial_capital?: number;
    start?: string;
    end?: string;
  }) => req<IrBacktestResult>("/ir/backtest", {
    method: "POST", body: JSON.stringify(body),
  }),
};

// 로컬앱 다운로드 — 플랫폼별 zip URL 조회.
//
// 매 release마다 asset 이름이 버전·플랫폼 포함으로 바뀌므로
// (QuantPlatformLocal-v{ver}-{platform}.zip) 정적 URL 불가. GitHub releases API로
// 최신 release의 asset 목록을 받아 plat suffix 매칭으로 선택. 실패 시 release
// 페이지 URL fallback.
//
// 컨벤션 (v0.9.0-beta+):
//   - Windows: '...-windows.zip'
//   - macOS arm64: '...-macos-arm64.zip'
// 하위 호환 (v0.8.x): suffix 없는 단일 zip은 windows 가정.
const RELEASES_API =
  "https://api.github.com/repos/MercKR/quantman-releases/releases/latest";
const RELEASES_PAGE =
  "https://github.com/MercKR/quantman-releases/releases/latest";

export type LocalAppDownloads = {
  /** Windows zip URL. null이면 release에 windows asset 없음 (publish 전 등). */
  windows: string | null;
  /** macOS Apple Silicon zip URL. null이면 release에 mac asset 없음. */
  macos: string | null;
  /** 둘 다 못 받으면 사용자가 직접 release 페이지 가서 선택. */
  fallback: string;
  /** release tag (예: 'v0.9.0-beta'). 표시·debug용 + release notes 링크 생성. */
  tag: string | null;
};

// 옛 단일-URL 헬퍼 (fetchLocalAppDownloadUrl)는 fetchLocalAppDownloads로 대체됨.
// 호출자 0개라 제거. mac 지원 이전 v0.8.x 사용 흐름.

export async function fetchLocalAppDownloads(): Promise<LocalAppDownloads> {
  // 개발 환경 override — Windows 단일 URL만 (mac dev override는 안 씀).
  if (import.meta.env.VITE_LOCAL_APP_URL) {
    return {
      windows: import.meta.env.VITE_LOCAL_APP_URL as string,
      macos: null,
      fallback: RELEASES_PAGE,
      tag: null,
    };
  }
  try {
    const r = await fetch(RELEASES_API);
    if (!r.ok) {
      return { windows: null, macos: null, fallback: RELEASES_PAGE, tag: null };
    }
    const data = await r.json();
    const tag = (data?.tag_name ?? null) as string | null;
    const assets = (data?.assets ?? []) as { name?: string; browser_download_url?: string }[];
    const zips = assets.filter(a => (a.name ?? "").toLowerCase().endsWith(".zip"));

    const macAsset = zips.find(a =>
      (a.name ?? "").toLowerCase().includes("-macos"));
    const winAsset = zips.find(a =>
      (a.name ?? "").toLowerCase().includes("-windows"));

    // 하위 호환 — v0.8.x release는 suffix 없는 단일 zip. mac도 아니면 windows 가정.
    const winFallback = !winAsset
      ? zips.find(a => !((a.name ?? "").toLowerCase().includes("-macos")))
      : undefined;

    return {
      windows: winAsset?.browser_download_url ?? winFallback?.browser_download_url ?? null,
      macos: macAsset?.browser_download_url ?? null,
      fallback: RELEASES_PAGE,
      tag,
    };
  } catch {
    return { windows: null, macos: null, fallback: RELEASES_PAGE, tag: null };
  }
}

/** 사용자 OS 감지 — 다운로드 페이지에서 자기 OS용 버튼을 primary로 표시. */
export function detectOS(): "mac" | "windows" | "other" {
  if (typeof navigator === "undefined") return "other";
  const ua = navigator.userAgent;
  if (/Macintosh|Mac OS X/.test(ua)) return "mac";
  if (/Windows/.test(ua)) return "windows";
  return "other";
}
