"""quant_core — 백테스트·분석·전략 공유 패키지."""

from .strategy import (Condition, ConditionGroup, ExecutionPolicy, ExitRules,
                       Modifier, Operand, Strategy)
from .dataset import load_dataset
from .data_fetcher import symbol_category
from .engine import run_strategy_backtest, evaluate_buy_signal
from .analysis import run_analysis, run_temporal_stability, build_signal_mask
from .backtest import run_backtest
from .indicators import (compute_all, get_indicator_columns, get_indicator_group,
                         get_indicator_label)
from .exec_defaults import (DEFAULT_EXECUTION, merged_execution, round_to_tick,
                            tick_size)

__all__ = [
    "Condition", "ConditionGroup", "ExecutionPolicy", "ExitRules", "Modifier",
    "Operand", "Strategy",
    "load_dataset", "symbol_category", "run_strategy_backtest", "evaluate_buy_signal",
    "run_analysis", "run_temporal_stability", "build_signal_mask",
    "run_backtest", "compute_all", "get_indicator_columns", "get_indicator_group",
    "get_indicator_label",
    "DEFAULT_EXECUTION", "merged_execution", "round_to_tick", "tick_size",
]
