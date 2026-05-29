"""블록별 파라미터(잎 빈칸) UI 스키마 — 자기서술적 카탈로그.

명세 §12·P1-7. 프론트 빌더(와 향후 NL 컴파일러)가 각 블록이 어떤 잎 빈칸을
요구하는지 하드코딩 없이 알 수 있도록, op → 파라미터 스펙 목록을 한곳에 정의한다.
catalog_spec()이 이를 각 블록에 병합한다.

spec kind:
  - "ref"        : 데이터 참조 (종목.지표 / [이 종목].지표 / 매크로) — data 잎
  - "number"     : 숫자 입력
  - "number_list": 숫자 리스트 (bucket 경계, between 범위)
  - "select"     : 열거값 드롭다운 (options 제공)
"""

from __future__ import annotations

_WINDOW = {"name": "window", "kind": "number", "label": "기간(일)", "default": 20, "min": 1}

PARAM_SPECS: dict[str, list[dict]] = {
    # ── 잎 ──
    "data": [{"name": "ref", "kind": "ref", "label": "데이터", "required": True}],
    "const": [{"name": "value", "kind": "number", "label": "값", "required": True}],
    # ── 축1 ──
    "compare": [{"name": "op", "kind": "select", "label": "비교",
                 "options": [">", ">=", "<", "<=", "between"], "required": True}],
    "logic": [{"name": "logic", "kind": "select", "label": "결합",
               "options": ["AND", "OR"], "default": "AND"}],
    "binary": [{"name": "op", "kind": "select", "label": "연산",
                "options": ["+", "-", "*", "/"], "required": True}],
    "unary": [{"name": "func", "kind": "select", "label": "함수",
               "options": ["log", "exp", "abs", "sign", "sqrt"], "required": True}],
    "select": [],
    "cross": [{"name": "direction", "kind": "select", "label": "방향",
               "options": ["up", "down"], "required": True}],
    "bucket": [{"name": "edges", "kind": "number_list", "label": "경계값", "required": True}],
    "modifier": [{"name": "kind", "kind": "select", "label": "수식어",
                  "options": ["streak", "within"], "required": True},
                 {"name": "days", "kind": "number", "label": "일수", "default": 2, "min": 1}],
    # ── 축2a 시계열 ──
    "ts_mean": [_WINDOW], "ts_sum": [_WINDOW], "ts_std": [_WINDOW],
    "ts_delta": [_WINDOW], "ts_delay": [_WINDOW], "ts_rank": [_WINDOW],
    "ts_zscore": [_WINDOW], "ts_decay": [_WINDOW], "ts_max": [_WINDOW],
    "ts_min": [_WINDOW], "ts_argmax": [_WINDOW], "ts_argmin": [_WINDOW],
    "ts_percentile": [_WINDOW, {"name": "percentile", "kind": "number",
                                "label": "백분위(%)", "default": 50, "min": 0, "max": 100}],
    "ts_autocorr": [_WINDOW, {"name": "lag", "kind": "number", "label": "지연(일)", "default": 1, "min": 1}],
    "ts_halflife": [{"name": "window", "kind": "number", "label": "기간(일)", "default": 60, "min": 3}],
    # ── 축2b 관계 ──
    "ts_corr": [_WINDOW],
    "ts_regression": [_WINDOW, {"name": "output", "kind": "select", "label": "출력",
                                "options": ["beta", "residual"], "default": "beta"}],
    "orthogonalize": [],
    # ── 축3 횡단 ──
    "rank": [], "zscore": [], "normalize": [], "scale": [], "cs_dispersion": [],
    # ── 축4 그룹 ──
    "group_rank": [{"name": "group_type", "kind": "select", "label": "그룹",
                    "options": ["Industry", "Sector"], "default": "Industry"}],
    "group_aggregate": [{"name": "stat", "kind": "select", "label": "집계",
                         "options": ["mean", "sum"], "default": "mean"},
                        {"name": "group_type", "kind": "select", "label": "그룹",
                         "options": ["Industry", "Sector"], "default": "Industry"}],
    "group_neutralize": [{"name": "group_type", "kind": "select", "label": "그룹",
                          "options": ["Industry", "Sector"], "default": "Industry"}],
    "hump": [{"name": "threshold", "kind": "number", "label": "임계", "default": 0.0, "min": 0}],
}


def params_for(op: str) -> list[dict]:
    return PARAM_SPECS.get(op, [])


# 빌더 팔레트 그룹핑·표시용 (op → 한글 라벨·카테고리). 잎(data/const)은 팔레트에
# 직접 안 띄우고 슬롯 채우기에서 선택되므로 카테고리 "잎".
BLOCK_META: dict[str, dict] = {
    "data": {"label": "데이터", "category": "잎"},
    "const": {"label": "상수", "category": "잎"},
    "compare": {"label": "비교", "category": "비교·논리"},
    "logic": {"label": "그리고/또는", "category": "비교·논리"},
    "cross": {"label": "돌파", "category": "비교·논리"},
    "select": {"label": "조건선택", "category": "비교·논리"},
    "binary": {"label": "사칙연산", "category": "산술"},
    "unary": {"label": "단항변환", "category": "산술"},
    "ts_mean": {"label": "N일 평균", "category": "시계열"},
    "ts_sum": {"label": "N일 합", "category": "시계열"},
    "ts_std": {"label": "N일 변동성", "category": "시계열"},
    "ts_delta": {"label": "N일 변화량", "category": "시계열"},
    "ts_delay": {"label": "N일 전 값", "category": "시계열"},
    "ts_rank": {"label": "윈도우 내 위치", "category": "시계열"},
    "ts_zscore": {"label": "N일 z-score", "category": "시계열"},
    "ts_decay": {"label": "시간가중 평활", "category": "시계열"},
    "ts_max": {"label": "N일 최댓값", "category": "시계열"},
    "ts_min": {"label": "N일 최솟값", "category": "시계열"},
    "ts_argmax": {"label": "최고 후 경과일", "category": "시계열"},
    "ts_argmin": {"label": "최저 후 경과일", "category": "시계열"},
    "ts_percentile": {"label": "N일 백분위", "category": "시계열"},
    "ts_autocorr": {"label": "자기상관", "category": "시계열"},
    "ts_halflife": {"label": "평균회귀 반감기", "category": "시계열"},
    "ts_corr": {"label": "동행성(상관)", "category": "관계"},
    "ts_regression": {"label": "선형적합(베타)", "category": "관계"},
    "orthogonalize": {"label": "직교화", "category": "관계"},
    "rank": {"label": "횡단 순위", "category": "횡단"},
    "zscore": {"label": "횡단 표준화", "category": "횡단"},
    "normalize": {"label": "횡단 평균차감", "category": "횡단"},
    "scale": {"label": "비중 스케일", "category": "횡단"},
    "cs_dispersion": {"label": "횡단 산포", "category": "횡단"},
    "group_rank": {"label": "그룹 내 순위", "category": "그룹"},
    "group_aggregate": {"label": "그룹 집계", "category": "그룹"},
    "group_neutralize": {"label": "그룹 중립화", "category": "그룹"},
    "bucket": {"label": "구간분할", "category": "라벨"},
    "hump": {"label": "턴오버 억제", "category": "변환"},
    "modifier": {"label": "지속성/최근성", "category": "수식어"},
}


def meta_for(op: str) -> dict:
    return BLOCK_META.get(op, {"label": op, "category": "기타"})
