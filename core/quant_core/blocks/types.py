"""값 타입(6종) + 데이터 형태(5종) — 메타규칙 검증의 근거.

비전 §1.2(값 타입)·§3.1(형태축). 명세 §2.2.

모든 블록은 출력 ValueType과 Shape를 가진다. 이 둘이 있어야
"0.7이 참인 날 진입"(타입 불일치)·"유가에 횡단 순위"(형태 불일치) 같은
무의미한 조립을 메타규칙(validate.py)이 구조적으로 차단할 수 있다.
"""

from __future__ import annotations

from enum import Enum


class ValueType(str, Enum):
    """블록 출력의 값 타입 (비전 §1.2)."""

    SCORE = "score"                # 실수 패널 — 대부분의 신호 출력 (순위·수익률)
    CONDITION = "condition"        # 참/거짓 패널 — 진입·청산 트리거
    SCALAR = "scalar"              # 단일 스칼라 — 성과 지표 결과 (Sharpe 등)
    LABEL = "label"                # 분류 라벨 — 그룹 분할 기준 (업종·국면)
    DISTRIBUTION = "distribution"  # 스칼라 집합 — 그룹 간 비교 (히스토그램)
    RESULTSET = "resultset"        # 백테스트 결과 묶음 — 펼침(sweep) 출력


class Shape(str, Enum):
    """데이터 형태 — 어떤 블록을 걸 수 있는지 결정 (비전 §3.1 형태축)."""

    PANEL = "panel"            # 종목×날짜 행렬 — 모든 블록 적용 가능
    SERIES = "series"          # 시장 단일값(날짜×1) — 횡단·그룹 연산 무의미
    VECTOR = "vector"          # 한 칸 다값(뉴스·옵션체인) — 압축(축5) 선행 강제
    GROUPLABEL = "grouplabel"  # 업종·섹터 분류 — 그룹 연산 기준으로만
    STATIC = "static"          # 거의 불변(상장일·국가) — 대상 종목 선정용
