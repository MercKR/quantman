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


def _moments(arr: np.ndarray) -> dict:
    """왜도(분포 비대칭)·초과첨도(꼬리 두께). 표본<3이면 NaN. scipy 지연 import."""
    if len(arr) < 3:
        return {"skew": np.nan, "kurtosis": np.nan}
    from scipy import stats
    return {"skew": float(stats.skew(arr)), "kurtosis": float(stats.kurtosis(arr))}


def one_sample_test(returns: pd.Series, pct: bool = True) -> dict:
    """1표본 t-검정 — 표본 평균이 0과 유의하게 다른가(이벤트 스터디·IC용).

    pct=True(기본): 평균을 백분율로(수익률 스케일). IC·상관처럼 이미 비율인 값은 pct=False.
    t통계·p값·prob_positive는 스케일 불변이라 그대로.
    """
    arr = _clean(returns).to_numpy(dtype=float)
    if len(arr) < 2:
        return {"n": int(len(arr)), "mean": np.nan, "t_stat": np.nan,
                "p_value": np.nan, "prob_positive": np.nan}
    from scipy import stats
    sc = 100.0 if pct else 1.0
    t, p = stats.ttest_1samp(arr, 0.0)
    return {"n": int(len(arr)), "mean": float(arr.mean() * sc),
            "t_stat": float(t), "p_value": float(p),
            "prob_positive": float((arr > 0).mean() * 100)}


def summarize_events(endpoints, maes, mfes) -> dict:
    """이벤트 표본 집계 — 종점수익 유의성 + 경로지표(MAE·MFE).

    endpoints: 윈도 종점 수익(이벤트별). maes/mfes: 보유 중 최대 불리/유리 편차.
    mean_mae = 평균 최대낙폭(task8 forward-MDD·task9 MAE의 단일 출처),
    payoff = 종점 승/패 평균비. 모두 백분율.
    """
    base = one_sample_test(pd.Series(endpoints, dtype=float))
    m = _clean(pd.Series(maes, dtype=float)).to_numpy(dtype=float)
    f = _clean(pd.Series(mfes, dtype=float)).to_numpy(dtype=float)
    e = _clean(pd.Series(endpoints, dtype=float)).to_numpy(dtype=float)
    base["mean_mae"] = float(m.mean() * 100) if len(m) else np.nan
    base["worst_mae"] = float(m.min() * 100) if len(m) else np.nan
    base["mean_mfe"] = float(f.mean() * 100) if len(f) else np.nan
    wins, losses = e[e > 0], e[e < 0]
    base["payoff_ratio"] = (float(wins.mean()) / abs(float(losses.mean()))
                            if len(wins) and len(losses) and losses.mean() != 0 else np.nan)
    base.update(_moments(e))   # 종점수익 왜도·첨도(비대칭 붕괴·꼬리 — T1)
    return base


def two_sample_test(a: pd.Series, b: pd.Series, pct: bool = True) -> dict:
    """Welch 2표본 t-검정 — 두 분포의 평균이 유의하게 다른가. pct=False면 비율값 스케일."""
    a, b = _clean(a), _clean(b)
    if len(a) < 2 or len(b) < 2:
        return {"t_stat": np.nan, "p_value": np.nan, "mean_diff": np.nan,
                "n_a": int(len(a)), "n_b": int(len(b))}
    from scipy import stats
    sc = 100.0 if pct else 1.0
    t, p = stats.ttest_ind(a, b, equal_var=False)  # Welch (등분산 가정 안 함)
    return {"t_stat": float(t), "p_value": float(p),
            "mean_a": float(a.mean() * sc), "mean_b": float(b.mean() * sc),
            "mean_diff": float((a.mean() - b.mean()) * sc),
            "n_a": int(len(a)), "n_b": int(len(b))}


def bootstrap_mean_ci(r: pd.Series, n_boot: int = 2000, alpha: float = 0.05,
                      seed: int = 0, pct: bool = True) -> dict:
    """IID 부트스트랩 평균 신뢰구간 — 성과가 통계적으로 0과 다른가(운/실력)."""
    arr = _clean(r).to_numpy(dtype=float)
    if len(arr) < 2:
        return {"mean": np.nan, "ci_low": np.nan, "ci_high": np.nan, "n": int(len(arr))}
    sc = 100.0 if pct else 1.0
    rng = np.random.default_rng(seed)
    means = np.array([rng.choice(arr, size=len(arr), replace=True).mean()
                      for _ in range(n_boot)])
    lo, hi = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    return {"mean": float(arr.mean() * sc), "ci_low": float(lo * sc),
            "ci_high": float(hi * sc), "n": int(len(arr)), "alpha": alpha}


def block_bootstrap_ci(r: pd.Series, block_len: int = 21, n_boot: int = 2000,
                       alpha: float = 0.05, seed: int = 0, pct: bool = True) -> dict:
    """블록 부트스트랩 평균 CI — 자기상관 보존(IID보다 정직).

    연속 블록(기본 21일≈1개월, 연도블록은 ~252)을 복원추출해 표본을 채운다. 시계열
    의존을 살려 캘린더·추세 효과의 유의성을 과대평가하지 않는다(SEA1 핵심).
    """
    arr = _clean(r).to_numpy(dtype=float)
    n = len(arr)
    if n < block_len or block_len < 1:
        return {"mean": float(arr.mean() * (100.0 if pct else 1.0)) if n else np.nan,
                "ci_low": np.nan, "ci_high": np.nan, "n": n, "block_len": block_len}
    sc = 100.0 if pct else 1.0
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n / block_len))
    means = np.empty(n_boot)
    for i in range(n_boot):
        starts = rng.integers(0, n - block_len + 1, size=n_blocks)
        means[i] = np.concatenate([arr[s:s + block_len] for s in starts])[:n].mean()
    lo, hi = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    return {"mean": float(arr.mean() * sc), "ci_low": float(lo * sc),
            "ci_high": float(hi * sc), "n": n, "block_len": block_len, "alpha": alpha}


def jackknife_by_year(r: pd.Series, pct: bool = True) -> dict:
    """연도별 leave-one-out 평균 — 소수 위기연도 의존성 탐지(SEA3).

    각 연도를 하나씩 빼고 평균을 재계산. 전체 평균을 가장 크게 바꾸는 연도로
    '몇 개 꼬리연도가 만든 효과'인지 식별한다.
    """
    r = _clean(r)
    sc = 100.0 if pct else 1.0
    if not isinstance(r.index, pd.DatetimeIndex) or len(r) < 2:
        return {"full_mean": float(r.mean() * sc) if len(r) else np.nan,
                "by_year": {}, "most_influential": None}
    full = float(r.mean())
    years = r.index.year
    out: dict = {}
    for y in sorted(set(years)):
        loo = r[years != y]
        out[int(y)] = {"mean_without": float(loo.mean() * sc) if len(loo) else np.nan,
                       "delta": float((loo.mean() - full) * sc) if len(loo) else np.nan}
    valid = {y: v for y, v in out.items() if v["delta"] == v["delta"]}
    most = max(valid, key=lambda y: abs(valid[y]["delta"]), default=None)
    return {"full_mean": float(full * sc), "by_year": out, "most_influential": most}


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


def distribution(r: pd.Series, bins: int = 10, pct: bool = True) -> dict:
    """분포(분위수 q05~q95·왜도/첨도·부트스트랩 평균CI·히스토그램).

    pct=True(기본): 수익률처럼 백분율 스케일. 신호값(상관·반감기 등 비율·일수)은 pct=False.
    """
    arr = _clean(r).to_numpy(dtype=float)
    if len(arr) == 0:
        return {"n": 0}
    sc = 100.0 if pct else 1.0
    counts, edges = np.histogram(arr, bins=bins)
    q = np.quantile(arr, [0.05, 0.10, 0.25, 0.5, 0.75, 0.90, 0.95])
    ci = bootstrap_mean_ci(pd.Series(arr), n_boot=1000, pct=pct)
    out = {
        "n": int(len(arr)), "mean": float(arr.mean() * sc), "std": float(arr.std() * sc),
        "quantiles": {"q05": float(q[0] * sc), "q10": float(q[1] * sc), "q25": float(q[2] * sc),
                      "q50": float(q[3] * sc), "q75": float(q[4] * sc), "q90": float(q[5] * sc),
                      "q95": float(q[6] * sc)},
        "bootstrap_ci": {"low": ci["ci_low"], "high": ci["ci_high"]},
        "hist_counts": counts.tolist(), "hist_edges": (edges * sc).tolist(),
    }
    out.update(_moments(arr))   # skew·kurtosis (꼬리·비대칭)
    return out


def compare_partition(parts: dict, pct: bool = True) -> dict:
    """라벨별 표본({label: Series})에 분포 요약 + 라벨 쌍별 2표본 검정. pct=False면 비율값."""
    labels = sorted(parts.keys())
    by_label = {lab: distribution(parts[lab], pct=pct) for lab in labels}
    pairwise = {}
    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            li, lj = labels[i], labels[j]
            pairwise[f"{li}_vs_{lj}"] = two_sample_test(parts[li], parts[lj], pct=pct)
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
