"""round_to_tick 통화별 라운딩 — KRW(정수 호가단위) / USD($0.01 float)."""

from quant_core import round_to_tick as rt


def test_usd_up_down_nearest():
    assert rt(200.503, "up", "USD") == 200.51
    assert rt(200.507, "down", "USD") == 200.50
    assert rt(200.504, "nearest", "USD") == 200.50
    assert rt(200.50, "up", "USD") == 200.50      # 이미 cent


def test_usd_returns_float():
    assert isinstance(rt(200.5, "up", "USD"), float)


def test_usd_low_price():
    assert rt(3.333, "up", "USD") == 3.34
    assert rt(3.333, "down", "USD") == 3.33


def test_krw_integer_ticks():
    # 5000~20000 구간 틱 10
    assert rt(12345, "up") == 12350
    assert rt(12345, "down") == 12340
    # 2000~5000 구간 틱 5
    assert rt(3001, "up") == 3005
    assert isinstance(rt(12345, "up"), int)


def test_krw_default_currency():
    # currency 미지정 시 KRW 동작 보존
    assert rt(100000, "up") == rt(100000, "up", "KRW")


def test_zero_price():
    assert rt(0, "up", "USD") == 0
    assert rt(-5, "down") == 0
