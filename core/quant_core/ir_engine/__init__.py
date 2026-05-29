"""블록 IR 백테스트/분석 엔진.

명세 §7~§9·§12. 1회 백테스트(backtest)·펼침(sweep)·비교검증(compare)을 담는다.
기존 quant_core.backtest(레거시 4-path)와 quant_core.engine(레거시 어댑터)을
단계적으로 대체한다. 전환 완료 후 이 패키지를 engine으로 통합 예정
(현재는 레거시 engine.py와의 이름 충돌을 피해 ir_engine으로 분리).
"""

from .backtest import run_backtest_ir  # noqa: F401
from .compare import (  # noqa: F401
    bootstrap_mean_ci, compare_partition, distribution, excess_distribution,
    two_sample_test, walk_forward_consistency,
)
from .sweep import (  # noqa: F401
    daily_returns, partition_by_label, run_condition_sweep, summarize_returns,
    sweep_condition,
)

__all__ = [
    "run_backtest_ir",
    "run_condition_sweep", "sweep_condition", "partition_by_label",
    "summarize_returns", "daily_returns",
    "two_sample_test", "bootstrap_mean_ci", "walk_forward_consistency",
    "distribution", "compare_partition", "excess_distribution",
]
