import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

_CORE_DIR = Path(__file__).resolve().parent.parent
if str(_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR))

from quant_core.expression_parser import ExpressionParser


@pytest.fixture
def dummy_data():
    dates = pd.date_range("2026-01-01", periods=10)
    data = {
        "005930": pd.DataFrame({
            "Open": [10.0, 11.0, 12.0, 11.0, 10.0, 10.5, 11.0, 12.0, 13.0, 12.5],
            "Close": [10.5, 11.5, 11.0, 10.5, 9.5, 10.8, 11.2, 12.5, 12.8, 12.2],
            "Volume": [100.0, 120.0, 90.0, 80.0, 110.0, 130.0, 95.0, 85.0, 105.0, 115.0]
        }, index=dates),
        "000660": pd.DataFrame({
            "Open": [20.0, 21.0, 22.0, 21.0, 20.0, 20.5, 21.0, 22.0, 23.0, 22.5],
            "Close": [21.0, 22.0, 21.5, 20.0, 19.0, 20.2, 20.8, 22.2, 22.6, 21.8],
            "Volume": [200.0, 240.0, 180.0, 160.0, 220.0, 260.0, 190.0, 170.0, 210.0, 230.0]
        }, index=dates)
    }
    return data


def test_expression_parser_basic_arithmetic(dummy_data):
    """기본 사칙연산 수식 평가 검증."""
    parser = ExpressionParser(data=dummy_data)
    
    # 1) 가산
    res_add = parser.evaluate("Close + 5")
    assert isinstance(res_add, pd.DataFrame)
    assert res_add.loc["2026-01-01", "005930"] == 15.5
    assert res_add.loc["2026-01-01", "000660"] == 26.0

    # 2) 곱셈
    res_mul = parser.evaluate("Close * 2")
    assert res_mul.loc["2026-01-01", "005930"] == 21.0

    # 3) 복합 연산
    res_complex = parser.evaluate("(Close - Open) * 10")
    assert res_complex.loc["2026-01-01", "005930"] == 5.0  # (10.5 - 10.0) * 10


def test_expression_parser_logical_ops(dummy_data):
    """비교 및 논리 연산 평가 검증."""
    parser = ExpressionParser(data=dummy_data)
    
    # 1) 단순 비교 — numpy>=2.0의 bool 스칼라(np.True_)는 파이썬 True와 identity가
    #    다르므로 `is True`가 아니라 bool()로 값을 비교한다.
    res_cmp = parser.evaluate("Close > Open")
    assert isinstance(res_cmp, pd.DataFrame)
    assert bool(res_cmp.loc["2026-01-01", "005930"]) is True
    assert bool(res_cmp.loc["2026-01-03", "005930"]) is False  # Close=11.0, Open=12.0

    # 2) if_else 삼항 연산
    res_ifelse = parser.evaluate("if_else(Close > Open, 1.0, -1.0)")
    assert res_ifelse.loc["2026-01-01", "005930"] == 1.0
    assert res_ifelse.loc["2026-01-03", "005930"] == -1.0


def test_expression_parser_time_series_functions(dummy_data):
    """시계열 (Rolling) 함수군 평가 검증."""
    parser = ExpressionParser(data=dummy_data)
    
    # 1) ts_mean
    res_mean = parser.evaluate("ts_mean(Close, 3)")
    # '2026-01-03' 005930의 3일 평균 = (10.5 + 11.5 + 11.0) / 3 = 11.0
    assert round(res_mean.loc["2026-01-03", "005930"], 4) == 11.0
    # 앞쪽 데이터 부족 시점은 NaN이어야 함
    assert pd.isna(res_mean.iloc[0, 0])

    # 2) ts_delta
    res_delta = parser.evaluate("ts_delta(Close, 1)")
    assert res_delta.loc["2026-01-02", "005930"] == 1.0  # 11.5 - 10.5


def test_expression_parser_cross_sectional_functions(dummy_data):
    """횡단면 (Cross-Sectional) 함수군 평가 검증."""
    parser = ExpressionParser(data=dummy_data)
    
    # 1) rank
    res_rank = parser.evaluate("rank(Close)")
    # 종목이 2개이므로 큰 값을 가진 종목이 1.0, 작은 종목이 0.5를 차지함
    # 2026-01-01 Close: 005930=10.5, 000660=21.0
    assert res_rank.loc["2026-01-01", "005930"] == 0.5
    assert res_rank.loc["2026-01-01", "000660"] == 1.0


def test_expression_parser_group_neutralization(dummy_data, monkeypatch, tmp_path):
    """그룹 중립화(group_neutralize) 연산 검증."""
    # 분류 사이드카(core/data/_classification.json)가 존재하면 005930·000660이
    # 서로 다른 업종(반도체 vs 통신장비)으로 나뉘어 각자 단일 그룹이 되고 중립화
    # 결과가 0이 된다. 이 테스트는 get_symbol_group의 폴백 휴리스틱(숫자 코드 →
    # 동일 '기타' 그룹)을 검증하므로, 빈 데이터 디렉터리로 사이드카를 격리해
    # 환경(사이드카 적재 여부) 무관하게 폴백 경로를 강제한다.
    monkeypatch.setenv("QP_CORE_DATA_DIR", str(tmp_path))
    parser = ExpressionParser(data=dummy_data)

    # 005930과 000660은 모두 IT 그룹으로 분류됨 (heuristic)
    # IT 그룹의 2026-01-01 Close 평균 = (10.5 + 21.0) / 2 = 15.75
    # 중립화 결과:
    # 005930 = 10.5 - 15.75 = -5.25
    # 000660 = 21.0 - 15.75 = 5.25
    res_neut = parser.evaluate("group_neutralize(Close)")
    assert res_neut.loc["2026-01-01", "005930"] == -5.25
    assert res_neut.loc["2026-01-01", "000660"] == 5.25


def test_expression_parser_case_insensitive_handling(dummy_data):
    """대소문자 미구분 변수 및 수식 바인딩 검증."""
    parser = ExpressionParser(data=dummy_data)
    
    res_lower = parser.evaluate("close * volume")
    res_upper = parser.evaluate("Close * Volume")
    
    pd.testing.assert_frame_equal(res_lower, res_upper)


def test_expression_parser_invalid_expression_raises_error(dummy_data):
    """미지원 수식 및 에러 상황 검증."""
    parser = ExpressionParser(data=dummy_data)
    
    # 미지원 함수
    with pytest.raises(Exception):
        parser.evaluate("non_existent_function(Close)")
        
    # 잘못된 문법
    with pytest.raises(Exception):
        parser.evaluate("Close +++")
