"""비교·검증층 (비전 §5) — 결과 차이가 유의한지 통계적으로 판정.

명세 §9. 펼침(sweep)이 만든 라벨별 수익률 분포를 받아:
  - 2표본 차이검정(Welch t) — 두 국면 성과가 유의하게 다른가
  - 부트스트랩 평균 신뢰구간 — 성과가 운인가
  - 워크포워드 일관성 — 여러 구간에서 일관되게 유의한가
  - 분포 출력 — 히스토그램·분위수 (distribution 타입)
  - 초과수익(CAR) — 벤치마크 대비 누적 초과

다표본·predictor 비교·몬테카를로·다중검정 보정은 후속(P2).
scipy는 t-test에서만 지연 import (패키징 경량 — analysis.py 패턴).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _clean(r: pd.Series) -> pd.Series:
    return r.dropna() if isinstance(r, pd.Series) else pd.Series(r).dropna()


def one_sample_test(returns: pd.Series) -> dict:
    """1표본 t-검정 — 수익률 평균이 0과 유의하게 다른가(이벤트 스터디용)."""
    arr = _clean(returns).to_numpy(dtype=float)
    if len(arr) < 2:
        return {"n": int(len(arr)), "mean": np.nan, "t_stat": np.nan,
                "p_value": np.nan, "prob_positive": np.nan}
    from scipy import stats
    t, p = stats.ttest_1samp(arr, 0.0)
    return {"n": int(len(arr)), "mean": float(arr.mean() * 100),
            "t_stat": float(t), "p_value": float(p),
            "prob_positive": float((arr > 0).mean() * 100)}


def two_sample_test(a: pd.Series, b: pd.Series) -> dict:
    """Welch 2표본 t-검정 — 두 수익률 분포의 평균이 유의하게 다른가."""
    a, b = _clean(a), _clean(b)
    if len(a) < 2 or len(b) < 2:
        return {"t_stat": np.nan, "p_value": np.nan, "mean_diff": np.nan,
                "n_a": int(len(a)), "n_b": int(len(b))}
    from scipy import stats
    t, p = stats.ttest_ind(a, b, equal_var=False)  # Welch (등분산 가정 안 함)
    return {"t_stat": float(t), "p_value": float(p),
            "mean_a": float(a.mean() * 100), "mean_b": float(b.mean() * 100),
            "mean_diff": float((a.mean() - b.mean()) * 100),
            "n_a": int(len(a)), "n_b": int(len(b))}


def bootstrap_mean_ci(r: pd.Series, n_boot: int = 2000, alpha: float = 0.05,
                      seed: int = 0) -> dict:
    """부트스트랩 평균 신뢰구간 — 성과가 통계적으로 0과 다른가(운/실력)."""
    arr = _clean(r).to_numpy(dtype=float)
    if len(arr) < 2:
        return {"mean": np.nan, "ci_low": np.nan, "ci_high": np.nan, "n": int(len(arr))}
    rng = np.random.default_rng(seed)
    means = np.array([rng.choice(arr, size=len(arr), replace=True).mean()
                      for _ in range(n_boot)])
    lo, hi = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    return {"mean": float(arr.mean() * 100), "ci_low": float(lo * 100),
            "ci_high": float(hi * 100), "n": int(len(arr)), "alpha": alpha}


def walk_forward_consistency(r: pd.Series, n_folds: int = 4) -> dict:
    """시간순 구간 분할 → 구간별 평균 수익률의 부호 일관성(과최적화 탐지)."""
    arr = _clean(r).to_numpy(dtype=float)
    if len(arr) < n_folds:
        return {"n_folds": 0, "fold_means": [], "positive_folds": 0, "consistency": np.nan}
    folds = [f for f in np.array_split(arr, n_folds) if len(f) > 0]
    means = [float(f.mean()) for f in folds]
    pos = sum(1 for m in means if m > 0)
    return {"n_folds": len(means), "fold_means": [m * 100 for m in means],
            "positive_folds": pos, "consistency": pos / len(means) if means else np.nan}


def distribution(r: pd.Series, bins: int = 10) -> dict:
    """수익률 분포(히스토그램·분위수) — distribution 타입 출력."""
    arr = _clean(r).to_numpy(dtype=float)
    if len(arr) == 0:
        return {"n": 0}
    counts, edges = np.histogram(arr, bins=bins)
    q = np.quantile(arr, [0.05, 0.25, 0.5, 0.75, 0.95])
    return {
        "n": int(len(arr)), "mean": float(arr.mean() * 100), "std": float(arr.std() * 100),
        "quantiles": {"q05": float(q[0] * 100), "q25": float(q[1] * 100),
                      "q50": float(q[2] * 100), "q75": float(q[3] * 100),
                      "q95": float(q[4] * 100)},
        "hist_counts": counts.tolist(), "hist_edges": (edges * 100).tolist(),
    }


def compare_partition(parts: dict) -> dict:
    """라벨별 수익률({label: Series})에 분포 요약 + 라벨 쌍별 2표본 검정."""
    labels = sorted(parts.keys())
    by_label = {lab: distribution(parts[lab]) for lab in labels}
    pairwise = {}
    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            li, lj = labels[i], labels[j]
            pairwise[f"{li}_vs_{lj}"] = two_sample_test(parts[li], parts[lj])
    return {"by_label": by_label, "pairwise": pairwise}


def excess_distribution(strat_equity: pd.Series, bench_equity: pd.Series) -> dict:
    """벤치마크 대비 초과수익 분포 + 누적초과(CAR)."""
    sr = strat_equity.pct_change().dropna()
    br = bench_equity.pct_change().dropna()
    idx = sr.index.intersection(br.index)
    ex = sr.reindex(idx) - br.reindex(idx)
    car = float(((1 + sr.reindex(idx)).prod() - (1 + br.reindex(idx)).prod()) * 100)
    return {"mean_excess": float(ex.mean() * 100), "car": car,
            "distribution": distribution(ex)}
