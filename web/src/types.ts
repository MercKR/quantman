export interface IndicatorInfo {
  key: string; label: string; group: string;
  unit?: string;          // 표시 단위 (%, x, 일, 원 등)
  compare_group?: string; // 지표↔지표 비교 호환 그룹 키 (pct/rsi/price/...)
}
export interface SymbolInfo {
  symbol: string;
  name?: string;                    // KIS 마스터의 한글명 (있을 때)
  category: string;
  tradable: boolean;                // KIS 매수 가능 종목 (마스터에 존재)
  has_backtest_data?: boolean;      // 서버 dataset에 OHLC 보유 — 백테스트 가능
  rows: number;
  // per-symbol 지표 배열은 제거됨(22k× 중복 = 43.5MB) — 지표 메타는 전역
  // indicator_catalog(/symbols 응답에 1회)로 받는다.
}

export type Op = ">" | ">=" | "<" | "<=" | "between" | "cross_up" | "cross_down";
export type Logic = "AND" | "OR";
export type OperandKind = "indicator" | "constant" | "history";
export type Stat = "min" | "max" | "mean" | "percentile" | "lag";
export type ModifierKind = "streak" | "within";

/** Phase 41 — Operand.symbol에 이 sentinel을 넣으면 "각 매수 대상 종목" placeholder.
 *  평가 엔진이 current_symbol로 치환. 빌더 좌변 종목 드롭다운 첫 옵션. */
export const SELF_SYMBOL = "__SELF__";

export interface Operand {
  kind: OperandKind;
  symbol?: string;
  indicator?: string;
  value?: number | number[];      // constant — between이면 [min, max]
  stat?: Stat;                    // history
  window?: number;                // history — 롤링 기간(일)
  percentile?: number;            // history — stat="percentile"일 때 0~100
  // G1 — 아핀 변환: 해석된 값에 (× mul + add) 적용. 미지정이면 무변환.
  mul?: number | null;            // 예: MA20 × 1.05 → mul=1.05
  add?: number | null;            // 예: 등락률 + 2 → add=2
}
export interface Modifier { kind: ModifierKind; days: number }
export interface Condition {
  left: Operand;
  op: Op;
  right?: Operand;
  modifier?: Modifier | null;
}
/** G2 — 그룹의 원소는 단일 조건 또는 하위 그룹. (A AND B) OR C 표현 가능. */
export type ConditionNode = Condition | ConditionGroup;
export interface ConditionGroup { conditions: ConditionNode[]; logic: Logic }

/** 노드가 하위 그룹인지 — conditions 배열 보유로 판별 (단일 조건엔 없음). */
export function isGroupNode(n: ConditionNode): n is ConditionGroup {
  return (n as ConditionGroup).conditions !== undefined;
}

export interface ExitRules {
  hold_days?: number | null;
  take_profit?: number | null;
  stop_loss?: number | null;
  trail_atr_mult?: number | null;
  trail_pct?: number | null;
}

/** Phase 32 — 매도 규칙 통합. 익절/손절/트레일링/보유기간/매도 조건이 한 객체.
 *  먼저 트리거되는 규칙으로 매도. */
export interface SellRules {
  take_profit?: number | null;        // %
  stop_loss?: number | null;          // % (음수)
  trail_pct?: number | null;          // %
  trail_atr_mult?: number | null;     // × ATR_14
  hold_days?: number | null;          // 보유 일수
  conditions?: ConditionNode[];       // 자유 매도 조건 (dataset 평가) — G2 중첩 허용
  logic?: Logic;
  sell_amount_pct?: number;           // 100=전량 매도 — 매도조건·미지정 룰의 fallback
  /** Phase 56 — 룰별 매도 비율. keys: "tp"/"sl"/"trail"/"atr"/"hold". 미설정 룰은 sell_amount_pct 적용. */
  rule_sell_pcts?: Record<string, number>;
}

/** 체결 정책 — 모든 필드 optional, null/undefined는 글로벌 default 적용.
 *  Backend: quant_core.exec_defaults.DEFAULT_EXECUTION과 병합. */
export interface ExecutionPolicy {
  /** 사이징 모드 (Phase 47 — 4지 통합):
   *  - fixed_amount: 한 종목당 amount_krw 원 (정액)
   *  - pct_cash:    자본의 amount_pct % (정률, default)
   *  - equal_weight: 자본을 screener_limit 종목에 균등 분배
   *  - atr_risk:    트레이드당 atr_risk_pct% 위험, 손절폭 ATR×atr_mult */
  sizing_mode?: "fixed_amount" | "pct_cash" | "equal_weight" | "atr_risk";
  amount_krw?: number;                    // fixed_amount 모드: 한 종목당 원 단위 금액
  atr_risk_pct?: number;                  // atr_risk 모드: 트레이드당 자본의 N% 위험
  atr_mult?: number;                      // ATR × 이 배수 = 1주당 손절폭
  max_position_pct?: number | null;       // 단일 종목 비중 상한 (자본 %). null=한도 없음
  max_drawdown_pct?: number | null;       // 누적 손실 한도 (자본 고점 대비). null=한도 없음
  /** 주문 유형 (Phase 49) — true=지정가(전일 종가 ± tolerance%), false=시장가.
   *  시장가는 시초가 갭에 무방비라 default는 지정가. 변동성 큰 종목·일중 진입에서만 시장가 권장. */
  use_limit?: boolean;
  buy_tolerance_pct?: number;             // 매수 지정가 = 전일 종가 × (1 + N%) — 갭상승 허용 범위 (use_limit=true일 때만 사용)
  sell_tolerance_pct?: number;            // 매도 지정가 = 전일 종가 × (1 - N%) — 갭하락 허용 범위 (Phase 38.9)
  // Phase 39 + C-01 — 백테스트 비용 가정. 실매매(모의/실전) 영향 없음.
  bt_commission_bps?: number;             // 편도 위탁수수료 (bps). 3 = 0.03% (KIS 평균)
  bt_sell_tax_bps?: number;               // 매도 단방향 거래세 (bps). 23 = 0.23% (KOSPI/KOSDAQ 평균)
  bt_slippage_bps?: number;               // 편도 슬리피지 (bps). 10 = 0.10%
}

export interface StrategyDef {
  name: string;
  trade_symbol: string;
  buy: ConditionGroup;
  /** Phase 32 — 매도/청산 통합. 신규 전략은 이 필드만 사용. */
  sell_rules?: SellRules;
  /** [DEPRECATED — backend _migrate_legacy가 sell_rules로 흡수] */
  sell?: ConditionGroup | null;
  /** [DEPRECATED] */
  exit_rules?: ExitRules;
  /** [DEPRECATED — sell_rules.sell_amount_pct로 통합] */
  sell_amount_pct?: number;
  amount_pct: number;              // 자본 대비 매수 비율 (%) — sizing_mode=pct_cash일 때 사용
  screener_limit?: number;         // 자동 선택 시 동시 보유 한도 (기본 5)
  // 커스텀 스크리너 — trade_symbol='screener:custom'일 때 프리셋 대신 사용.
  screener_spec?: ScreenerSpecIO | null;
  rebalance?: RebalanceIO | null;  // 자동 선택 리밸런싱 (라이브 전용)
  execution?: ExecutionPolicy | null;
  fill?: string;
}

export interface RebalanceIO {
  // off: lock-in (재평가·신규 매수 X) / hold: 빈 슬롯만 채움 / replace: 탈락 매도 + 신규
  mode: "off" | "hold" | "replace";
  period: "daily" | "weekly" | "monthly" | "every_n_days";
  every_n_days?: number | null;     // period="every_n_days"일 때만 사용 (영업일)
}

// ── 스크리너 커스터마이징 ─────────────────────────────────────────────────────

export type ScreenerOp = ">" | ">=" | "<" | "<=" | "between";
export interface ScreenerRuleIO {
  field: string;
  op: ScreenerOp;
  value: number | number[];        // between이면 [min, max]
}
export interface ScreenerSpecIO {
  rules: ScreenerRuleIO[];
  sort?: { field: string; order: "asc" | "desc" } | null;
  markets?: string[];
  limit?: number;
  /** 표시용 이름 (커스텀/내 세트). 백엔드 parse_spec은 무시. */
  label?: string;
}
export interface ScreenerField {
  key: string; label: string; unit: string; group: string;
}

export interface StrategyRow {
  id: number; name: string; run_mode: string;
  // 표현 엔진 — operand(레거시 row) | ir(전략 연구소). engine으로 분기해 좁혀 읽는다.
  engine?: "operand" | "ir";
  definition: StrategyDef | IrStrategyDef; created_at: string; updated_at: string;
  // Phase 59 — run_mode 전환 시점 기록
  paper_started_at?: string | null;
  live_started_at?: string | null;
}

// Phase 59 — 전략 버전 이력
export interface StrategyVersionRow {
  version_no: number;
  name: string;
  created_at: string;
  created_reason: string;     // "manual_edit" | "restore_from_vN" | "initial"
  definition?: StrategyDef;   // list endpoint에선 omit, single에선 포함
}

// Phase 59 — 전략 현황 (적용 기간 + 누적 손익 요약)
export interface StrategyStats {
  paper_started_at: string | null;
  live_started_at: string | null;
  days_paper: number | null;
  days_live: number | null;
  pnl_total: number | null;
  pnl_pct: number | null;
  win_rate: number | null;
  n_trades: number | null;
  n_positions: number;
  last_snapshot_at: string | null;
}

export interface BacktestResult {
  success: boolean; error?: string;
  metrics?: Record<string, number | null>;
  equity?: { date: string; value: number | null }[];
  benchmark?: { date: string; value: number | null }[];
  trades?: Record<string, string | number | null>[];
  run_id?: number;
  run_created_at?: string;
}

// ── 블록 IR (노코드 빌더) ────────────────────────────────────────────────────
// 자기서술 카탈로그(/ir/catalog)를 소비 — 프론트는 블록 지식을 하드코딩하지 않는다.

export interface IrNode {
  op: string;
  inputs?: Record<string, IrNode>;     // 가지 빈칸 — 슬롯명 → 하위 블록(재귀)
  params?: Record<string, unknown>;    // 잎 빈칸 — window·op·ref·value 등
}

export type IrValueType =
  "score" | "condition" | "scalar" | "label" | "distribution" | "resultset";

export interface IrParamSpec {
  name: string;
  // value_list = 문자열·숫자 혼용 리스트(섹터·버킷 등), bool = 체크박스
  kind: "ref" | "number" | "number_list" | "select" | "value_list" | "bool";
  label?: string;
  options?: string[];
  labels?: Record<string, string> | null;   // 문장형 UI — 옵션값→한글 조각
  default?: unknown;
  required?: boolean;
  min?: number;
  max?: number;
}

export interface IrBlockSpec {
  op: string;
  label: string;
  category: string;
  out_type: IrValueType;
  slots: Record<string, IrValueType>;     // 슬롯명 → 요구 타입
  variadic: boolean;
  variadic_type: IrValueType | null;
  params: IrParamSpec[];
  requires_panel: boolean;
  phrase?: string | null;    // 문장형 UI 템플릿 ({slot}/{param} 토큰; 없으면 generic 렌더)
  doc: string;
}

export interface IrIssue {
  rule: string; severity: number; message: string; path: string;
}

// StrategyIR(통합 IR) 직렬화 형태 — core ir_engine/spec.py StrategyIR과 동기.
// "전략 연구소" 저장/불러오기 라운드트립의 단일 표현. engine='ir' 전략의 definition.
export interface IrStrategyDef {
  name: string;
  universe: {
    kind: "single" | "list" | "all" | "screener";
    symbols?: string[];
    screener?: {
      filter?: IrNode | null;
      rank?: { ref: string; top_n: number; direction: string } | null;
    } | null;
    exclude_macro?: boolean;
  };
  signal: IrNode;
  position: {
    direction: "long" | "short" | "long_short";
    sizing: {
      mode: string;
      amount_pct?: number; amount_krw?: number | null;
      target_vol_pct?: number | null; weights?: Record<string, number> | null;
      vol_window?: number; max_position_pct?: number;
    };
    entry: {
      mode: string; rebalance?: string; every_n_days?: number | null;
      top_n?: number | null; top_pct?: number | null;
      threshold?: number | null; refill?: string;
    };
    exit: {
      hold_days?: number | null; take_profit?: number | null; stop_loss?: number | null;
      trail_pct?: number | null; trail_atr_mult?: number | null; condition?: IrNode | null;
    };
    overlays: {
      vol_target?: number | null; turnover_damp?: number | null;
      max_drawdown_stop?: number | null; max_drawdown_soft?: number | null;
      max_group_pct?: number | null; group_label?: IrNode | null;
    };
  };
  simulation: {
    initial_capital?: number; delay?: number; fill?: string;
    commission?: number | null; slippage?: number | null; sell_tax?: number | null;
    currency?: string; leverage?: number;
    short_borrow_pct?: number | null; funding_cost_pct?: number | null; rfr_pct?: number | null;
    start?: string | null; end?: string | null; period_split?: string;
  };
  sweep: {
    axis: "none" | "condition" | "parameter" | "asset" | "time";
    label?: IrNode | null;
    param_grid?: { path: string; values: (number | string)[] }[];
    assets?: string[];
    event?: IrNode | null;
    windows?: number[];
    event_basis?: string;
  };
}

// 모든 펼침 버킷의 단일 지표 어휘 (engine perf_from_returns와 동기) — 갭 A.
export interface IrSweepBucket {
  n: number;
  mean?: number; std?: number; sharpe?: number; sortino?: number;
  cum_return?: number; cagr?: number; mdd?: number; win_rate?: number;
  payoff_ratio?: number; profit_factor?: number; var_95?: number; cvar_95?: number;
  error?: string;
}

// 이벤트 표본 통계 — 종점 유의성 + 경로지표(MAE/MFE). 갭 C·E.
export interface IrEventStat {
  n: number; mean?: number; t_stat?: number; p_value?: number; prob_positive?: number;
  mean_mae?: number; worst_mae?: number; mean_mfe?: number; payoff_ratio?: number;
}
export interface IrPairTest {
  p_value?: number; mean_diff?: number; mean_a?: number; mean_b?: number;
  n_a?: number; n_b?: number;
}

// StrategyIR 백테스트 결과 — 단일(equity/metrics)·펼침(axis/buckets)·이벤트(time) 통합.
export interface IrStrategyResult extends BacktestResult {
  warnings?: IrIssue[];
  issues?: IrIssue[];
  axis?: "condition" | "parameter" | "asset" | "time" | "period_split";
  buckets?: Record<string, IrSweepBucket>;
  overall?: IrSweepBucket | Record<string, IrEventStat>;
  // parameter축 격자 메타 (다축 Cartesian) — 갭 B
  axes?: { path: string; values: (number | string)[] }[];
  // period_split 일관성
  consistency?: { n_folds: number; positive_folds: number; consistency: number };
  // condition축 유의성 (A1)
  compare?: { pairwise?: Record<string, IrPairTest> };
  // time축 이벤트 스터디 (A2) — basis: close/intraday/excess (갭 C)
  windows?: string[];
  basis?: "close" | "intraday" | "excess";
  n_events?: number;
  by_regime?: Record<string, {
    by_regime: Record<string, IrEventStat>;
    pairwise: Record<string, IrPairTest>;
  }>;
}

export interface BacktestRunSummary {
  id: number;
  name: string;
  created_at: string;
  initial_capital: number;
  metrics: Record<string, number | null>;
  success?: boolean;
  // Phase 59 — 전략 detail의 "백테스트 내역" 응답
  version_no?: number | null;
  start?: string | null;
  end?: string | null;
}

export interface DeviceRow {
  id: number; name: string; created_at: string; last_seen_at: string | null;
}

export interface PendingOrder {
  order_no: string; symbol: string; name?: string;
  side: "buy" | "sell"; qty: number; filled_qty?: number;
  remain_qty?: number; limit_price?: number; submitted_at?: string;
}

export interface OrderEvent {
  ts: string;
  event: "submitted" | "filled" | "partial" | "cancelled" | "rejected" | "timeout";
  side: "buy" | "sell"; symbol: string; qty: number;
  order_no?: string; intended_price?: number | null;
  limit_price?: number | null; fill_price?: number | null;
  strategy?: string; reason?: string; msg?: string;
}

export interface CycleSummary {
  today?: string; n_strategies?: number;
  n_bought?: number; n_sold?: number;
  n_skip_held?: number;
  n_rejected?: number; n_unfilled?: number; n_errors?: number;
  kill_switch?: boolean;
  equity_pre?: number; equity_post?: number;
  // 미국 해외 실시간 시세 미신청 — 장중 실시간 손절 미제공 (P8)
  us_realtime_unavailable?: boolean;
}

export interface CycleRow {
  ts: string;
  decisions: { action: string; strategy_id: string; strategy_name: string;
                symbol: string; reason: string;
                prev_close?: number; cur_price?: number;
                intended?: number; fill?: number }[];
  summary: CycleSummary;
}

export interface SlippageStats {
  n: number;
  avg_bps: number | null; p50_bps: number | null;
  p95_bps: number | null; max_bps: number | null;
  recent: { ts: string; side: string; symbol: string;
             intended: number; fill: number; bps: number }[];
}

export interface KillSwitchState {
  active: boolean; since: string | null; reason: string;
  day_start_equity: number | null; day_start_date: string | null;
}

export interface PositionRich {
  symbol: string; name?: string; qty: number;
  avg_price?: number; eval_price?: number;
  strategy_name?: string; entry_date?: string;
  entry_price?: number; peak_price?: number;
  cur_return_pct?: number; held_days?: number;
  distances?: {
    tp_gap_pct?: number;
    sl_gap_pct?: number;
    trail_gap_pct?: number;
    hold_days_left?: number;
  };
  // Phase 47 Cycle C — 분할매수 진행 상황 (없으면 단일 진입)
  phases_executed?: number[];
  phases_total?: number;
  base_qty?: number;
}

export interface StrategyPnlRow {
  strategy: string; trades: number; win_rate: number;
  pnl: number; today_pnl: number; week_pnl: number; month_pnl: number;
}

export interface StrategyPnlSummary {
  by_strategy: StrategyPnlRow[];
  total: { today: number; week: number; month: number; all: number };
}

export interface SlippageBucket {
  bucket: string; n: number; avg_bps: number; max_bps: number;
}

export interface RejectionReason { label: string; n: number }

export interface DrawdownState {
  high?: number | null; current?: number | null;
  depth_pct: number; days_since_high: number; high_date?: string | null;
}

export interface LocalHealth {
  last_cycle_ts?: string | null;
  kis_token_expires_at?: string | null;
  kis_master_pushed_date?: string | null;
  warnings: string[];
}

export interface MarketIndicator {
  label: string; available: boolean;
  value?: number; change_pct?: number; as_of?: string;
}

export interface MarketContext {
  indicators: MarketIndicator[];
  session: { phase: string; kst_now: string };
}

export interface PortfolioRisk {
  positions: string[];
  matrix: number[][];
  sectors: { label: string; amount: number; share_pct: number }[];
  window: number;
}

export interface UserSettingsIO {
  alert_webhook_url: string;
  alert_on_killswitch: boolean;
  alert_on_daily_loss_pct: number;
  alert_on_unfilled_count: number;
  // Phase 48 P1-C — 슬리피지 임계 초과 알림 (bps, 0=비활성)
  alert_on_slippage_bps: number;
  // Phase 48 P1-D — 일일 거래 한도 (0=비활성)
  daily_turnover_limit_krw: number;
  daily_trade_count_limit: number;
  // Phase 38.7 — kill switch 일일 손실 한도(%). null이면 글로벌 default(3.0).
  kill_switch_daily_loss_pct: number | null;
  // Phase 38.10 — 누적 drawdown 한도(%). null이면 글로벌 default(20.0).
  max_drawdown_pct: number | null;
  // Phase 38.5 — preview 연속 누락 일수 알림 임계 (1+)
  preview_missing_alert_threshold: number;
  // Phase 40 — KIS ↔ ledger 정합성 drift 알림
  alert_on_reconcile_drift: boolean;
  // 미국 매수여력 모드: "integrated"(통합증거금, KRW 담보·FX 노출) |
  // "usd_cash"(USD 예수금 한정, 보수적)
  us_buying_power_mode: "integrated" | "usd_cash";
}

export interface SyncSnapshot {
  payload: {
    balance?: { cash: number; total_eval: number };
    positions?: PositionRich[];
    equity?: { date: string; value: number }[];
    trades?: Record<string, string | number>[];
    decisions?: CycleRow["decisions"];
    broker_pending?: PendingOrder[];
    pending_local?: PendingOrder[];
    recent_orders?: OrderEvent[];
    recent_cycles?: CycleRow[];
    slippage?: SlippageStats;
    kill_switch?: KillSwitchState;
    cycle_summary?: CycleSummary;
    // Phase 13 — Monitor 고도화
    strategy_pnl?: StrategyPnlSummary;
    slippage_by_hour?: { buckets: SlippageBucket[] };
    rejection_reasons?: { reasons: RejectionReason[] };
    drawdown?: DrawdownState;
    health?: LocalHealth;
    // Phase 31 — 내일 매매 미리보기
    next_day_preview?: NextDayPreview;
    // Phase 40 — KIS 잔고 ↔ ledger 정합성
    reconciliation?: ReconciliationResult;
  };
  received_at: string; device_id: number | null;
  // Phase 58 — 5분 주기 heartbeat. snapshot보다 최신이면 "살아있음" 지표로
  // 사용. 정규장 외(새벽 등) cycle 없을 때도 alive 표시 가능.
  last_heartbeat_at?: string | null;
}

/** Phase 40 — KIS 잔고 ↔ ledger drift 점검 결과 */
export interface ReconciliationResult {
  ledger_orphans: {
    symbol: string; ledger_total_qty: number; kis_qty: number;
    shortfall: number;
    ledger_sids: { sid: string; qty: number }[];
  }[];
  external_extras: {
    symbol: string; kis_qty: number; ledger_total_qty: number;
    excess: number; in_ledger: boolean;
  }[];
  in_sync: string[];
  checked_at: string;
  ledger_symbol_count: number;
  kis_symbol_count: number;
  applied?: {
    sid: string; symbol: string; old_qty: number; new_qty: number;
    removed_qty: number; fully_closed: boolean;
  }[];
  external_extras_count?: number;
  has_drift?: boolean;
  error?: string;
}

/** 내일 매매 미리보기 — 각 데이터 cron 후 서버가 평가해 sync snapshot에 merge */
export interface NextDayPreview {
  generated_at: string;
  data_source: string;          // cron 식별자 — 'dataset_global', 'krx_2nd' 등
  available: boolean;
  reason?: string;              // available=false일 때 사유
  summary?: {
    n_buy_candidates: number;
    est_total_buy_amount: number;
    n_holding: number;
    cash: number;
  };
  by_strategy?: PreviewByStrategy[];
  exit_candidates?: PreviewExit[];
}

export interface PreviewSignalDetail {
  label: string;
  passed: boolean | null;
  reason?: string | null;
}
export interface PreviewPerSymbolEval {
  passed: boolean;
  summary: string;
  details: PreviewSignalDetail[];
}
export interface PreviewByStrategy {
  strategy_id: number;
  strategy_name: string;
  trade_symbol: string;
  run_mode: string;
  signal_passed: boolean;
  candidates: PreviewBuyCandidate[];
  skipped: { symbol?: string; reason: string }[];
  // Phase 41 — 공통/종목별 신호 평가 결과
  signal_details?: PreviewSignalDetail[];      // 공통 조건 결과
  signal_summary?: string;                      // 공통 조건 한 줄 요약
  per_symbol_details?: Record<string, PreviewPerSymbolEval>;
}

export interface PreviewBuyCandidate {
  symbol: string;
  name: string;
  // 미국 종목(Phase 60+)은 server에서 사이징 불가 → qty/est_limit_price/est_total
  // 모두 null. trader가 발주 시점에 USD 잔고로 결정. currency="USD" 표시.
  qty: number | null;
  prev_close: number;
  est_limit_price: number | null;
  est_total: number | null;
  sizing_mode: string;
  data_as_of: string | null;
  currency?: "KRW" | "USD";
  note?: string;
}

export interface PreviewExit {
  symbol: string;
  name: string;
  qty: number;
  entry_price: number;
  prev_close: number;
  return_pct: number;
  peak_price: number;
}

// ── 종목 자동 선택 (Screener) ─────────────────────────────────────────────────

export interface ScreenerPreset {
  key: string;          // "marcap_top" 등
  title: string;        // "시가총액 상위"
  desc: string;
  spec?: ScreenerSpecIO; // 편집 시작점 — 프리셋의 룰 (presets 엔드포인트가 포함)
  // 국내("KR") / 미국("US") — 웹이 컨텍스트별 섹션으로 노출. 통화·단위 표기에도 사용.
  market_group?: "KR" | "US";
}

/** 계정에 저장된 사용자 정의 세트. */
export interface ScreenerUserPreset {
  id: number;
  name: string;
  spec: ScreenerSpecIO;
  created_at: string;
  updated_at: string;
}

export interface ScreenerMatch {
  symbol: string;
  name: string;
  market: string;
  close: number | null;
  pct_change_1d: number | null;
  market_cap: number | null;
  trade_value: number | null;
  volume: number | null;
}

/** 매수 대상이 자동 선택 모드인지 — trade_symbol이 "screener:..."로 시작. */
export function parseScreenerKey(tradeSymbol: string): string | null {
  return tradeSymbol.startsWith("screener:")
    ? tradeSymbol.slice("screener:".length) : null;
}

/** trade_symbol을 모드와 종목 코드 배열로 파싱.
 *  - "screener:marcap_top" → { mode: "screener", symbols: ["marcap_top"] }  (preset key)
 *  - "005930,000660,035420" → { mode: "manual", symbols: [3개] }
 *  자동 선택과 수동 다중은 혼합 불가 — UI에서 모드 토글로 제어. */
export function parseTradeSymbols(tradeSymbol: string): {
  mode: "screener" | "manual";
  symbols: string[];
} {
  const s = (tradeSymbol ?? "").trim();
  if (s.startsWith("screener:")) {
    return { mode: "screener", symbols: [s.slice("screener:".length)] };
  }
  const parts = s.split(",").map((p) => p.trim()).filter(Boolean);
  return { mode: "manual", symbols: parts };
}

export type CommandType =
  | "RUN_CYCLE_NOW" | "PAUSE_AUTO" | "RESUME_AUTO"
  | "LIQUIDATE_ALL" | "CANCEL_ORDER" | "RESET_KILL_SWITCH"
  | "RECONCILE_NOW";   // Phase 40 — 수동 잔고 정합성 점검

export interface CommandRow {
  id: number; device_id: number; type: CommandType;
  params: Record<string, string | number>;
  status: "pending" | "delivered" | "done" | "failed";
  created_at: string; delivered_at: string | null;
  completed_at: string | null; result: Record<string, unknown>;
}

// 자동매매 타임라인 — /trading/timeline 응답.
// 서버 routers/trading.py 와 동기. event kind 추가 시 양쪽 같이 갱신.
// 시작=cycle(주문 발주), 종료=settlement(미체결 정리·잔고 reconcile).
// preview 시장별 분리: krx_preview(07:30 — US 종가 반영), us_preview(18:15 — KRX 종가 반영).
export type TimelineEventKind =
  | "krx_cycle" | "krx_settlement" | "krx_preview"
  | "us_cycle"  | "us_settlement"  | "us_preview";
export type TimelineEventStatus = "done" | "scheduled" | "missed" | "holiday";

export interface TimelineEvent {
  at: string;                 // ISO datetime (KST offset 포함)
  kind: TimelineEventKind;
  status: TimelineEventStatus;
  summary: string;            // 1줄 표시 (e.g. "1건 매수", "US 7건", "")
  detail: string;             // hover 시 자세한 설명 (e.g. missed 이유)
}

export interface TradingTimeline {
  now: string;
  heartbeat_at: string | null;
  heartbeat_status: "normal" | "warning" | "error";
  events: TimelineEvent[];
}
