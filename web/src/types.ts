export interface IndicatorInfo { key: string; label: string; group: string }
export interface SymbolInfo {
  symbol: string; category: string; tradable: boolean; rows: number;
  indicators: IndicatorInfo[];
}

export type Op = ">" | ">=" | "<" | "<=" | "between" | "cross_up" | "cross_down";
export type Logic = "AND" | "OR";
export type OperandKind = "indicator" | "constant" | "history";
export type Stat = "min" | "max" | "mean" | "percentile" | "lag";
export type ModifierKind = "streak" | "within";

export interface Operand {
  kind: OperandKind;
  symbol?: string;
  indicator?: string;
  value?: number | number[];      // constant — between이면 [min, max]
  stat?: Stat;                    // history
  window?: number;                // history — 롤링 기간(일)
  percentile?: number;            // history — stat="percentile"일 때 0~100
}
export interface Modifier { kind: ModifierKind; days: number }
export interface Condition {
  left: Operand;
  op: Op;
  right?: Operand;
  modifier?: Modifier | null;
}
export interface ConditionGroup { conditions: Condition[]; logic: Logic }

export interface ExitRules {
  hold_days?: number | null;
  take_profit?: number | null;
  stop_loss?: number | null;
  trail_atr_mult?: number | null;
  trail_pct?: number | null;
}

export interface StrategyDef {
  name: string;
  trade_symbol: string;
  buy: ConditionGroup;
  sell?: ConditionGroup | null;
  exit_rules: ExitRules;
  amount_pct: number;
  fill?: string;
}

export interface StrategyRow {
  id: number; name: string; run_mode: string;
  definition: StrategyDef; created_at: string; updated_at: string;
}

export interface BacktestResult {
  success: boolean; error?: string;
  metrics?: Record<string, number | null>;
  equity?: { date: string; value: number | null }[];
  benchmark?: { date: string; value: number | null }[];
  trades?: Record<string, string | number | null>[];
}

export interface AnalysisResult {
  success: boolean; error?: string;
  n_samples?: number; prob_positive?: number | null;
  mean?: number | null; median?: number | null;
  q25?: number | null; q75?: number | null; std?: number | null;
  t_stat?: number | null; p_value?: number | null;
  distribution?: (number | null)[]; condition_dates?: string[];
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
  n_skip_gap?: number; n_skip_signal?: number; n_skip_held?: number;
  n_rejected?: number; n_unfilled?: number; n_errors?: number;
  kill_switch?: boolean;
  equity_pre?: number; equity_post?: number;
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

export interface SyncSnapshot {
  payload: {
    balance?: { cash: number; total_eval: number };
    positions?: { symbol: string; name?: string; qty: number;
                  avg_price?: number; eval_price?: number }[];
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
  };
  received_at: string; device_id: number;
}

export type CommandType =
  | "RUN_CYCLE_NOW" | "PAUSE_AUTO" | "RESUME_AUTO"
  | "LIQUIDATE_ALL" | "CANCEL_ORDER" | "RESET_KILL_SWITCH";

export interface CommandRow {
  id: number; device_id: number; type: CommandType;
  params: Record<string, string | number>;
  status: "pending" | "delivered" | "done" | "failed";
  created_at: string; delivered_at: string | null;
  completed_at: string | null; result: Record<string, unknown>;
}
