"""StrategyIR — 전략 수립 로직의 완전한 통합 구조.

명세 §7(1회 백테스트 5단계)·§3.3(포지션 4부품). 비전의 데이터→신호→포지션→
성과→시뮬을 한 스키마로 통합한다. 핵심: **포지션 레이어가 룰·팩터 전략을 통일**.

  StrategyIR = universe + signal(Node) + position(4부품+오버레이) + simulation + sweep

신호(signal)는 condition(룰 트리거) 또는 score(팩터 알파) — 둘 다 같은 블록 트리.
엔진은 entry.mode × signal 타입으로 디스패치:
  - on_signal + condition        → 이벤트 드리븐(룰) 백테스트
  - scheduled/always + score|cond → 리밸런스/팩터 백테스트(횡단·포트폴리오)

데이터 연동이 아직 얇아도 이 구조 자체는 다양·복잡한 전략을 빠짐없이 표현한다.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from ..blocks.catalog import get, has
from ..blocks.integrity import DatasetMeta, integrity_issues
from ..blocks.node import Node
from ..blocks.validate import (SEV_ERROR, SEV_INTEGRITY_WARN, Issue, has_market_source,
                               meaningfulness_issues, prioritize, validate)

# ── 유니버스 (대상 종목 집합) ─────────────────────────────────────────────────

class Universe(BaseModel):
    kind: Literal["single", "list", "all", "screener"] = "single"
    symbols: list[str] = Field(default_factory=list)   # single(1개)/list(다수)
    screener: Optional[dict] = None                    # kind=screener: {"condition": Node}
    exclude_macro: bool = True                         # all: 매크로/자산 지수 제외


# ── 포지션 4부품 (비전 §3.3) ──────────────────────────────────────────────────

class Sizing(BaseModel):
    """② 크기 — 얼마나."""
    mode: Literal[
        "equal_weight",         # 동일가중 (횡단)
        "signal_proportional",  # 신호(score)비례 (횡단)
        "vol_inverse",          # 변동성 역가중 (횡단)
        "target_vol",           # 목표변동성(per-name 연변동성 타겟 — 레버리지 동반, 횡단)
        "fixed_weight",         # 정적 배분(사용자 지정 per-symbol 비중, 횡단)
        "fixed_amount",         # 종목당 고정 금액 (이벤트 진입 예산)
        "pct_cash",             # 자본 대비 % (이벤트 진입 예산)
    ] = "equal_weight"
    # (제거됨: fixed_risk·kelly — IR 엔진 미구현 모드를 enum에 두지 않는다. ATR위험·켈리는
    #  소비 경로·입력 어휘가 갖춰지고 수요가 생기면 sizer registry에 등록해 부활.)
    amount_pct: float = 10.0           # pct_cash / per-name 기본
    amount_krw: Optional[float] = None  # fixed_amount
    target_vol_pct: Optional[float] = None  # target_vol: 목표 연변동성(%)
    weights: Optional[dict] = None      # fixed_weight: {symbol: 비중}
    vol_window: int = 20                # vol_inverse·target_vol 변동성 창
    # 종목당 상한(%) — opt-in. 기본 100=무제한(집중 사이징 보존). 분산 원하면 낮춤.
    max_position_pct: float = 100.0


class Entry(BaseModel):
    """③ 진입 — 언제 들어가나. 주기(캘린더 규칙) ⊕ 이벤트(+지연) — 명세 §7.6."""
    mode: Literal["on_signal", "scheduled", "always"] = "on_signal"
    rebalance: Literal["daily", "weekly", "monthly", "quarterly", "annual",
                       "every_n_days"] = "weekly"
    every_n_days: Optional[int] = None
    top_n: Optional[int] = None         # scheduled/팩터: score 상위 N 선택
    top_pct: Optional[float] = None     # scheduled/팩터: score 상위 X% 선택(top_n 대안)
    # 임계 선택 — score 신호에서 절대 임계로 집합 선정(횡단 랭킹과 직교한 대안 선택자).
    # 설정 시 top_n/top_pct 대신 사용: 롱={score>threshold}·숏={score<threshold}.
    # 시계열 모멘텀(TSMOM: 자기 추세 부호로 독립 롱/숏)처럼 순위가 아닌 부호·수준 기준 선택에 필수.
    threshold: Optional[float] = None
    # 중간 청산 후 빈 슬롯 처리 — cash: 현금 유지(다음 리밸런스까지) · replace: 차순위 즉시 충원.
    refill: Literal["cash", "replace"] = "cash"


class Exit(BaseModel):
    """④ 청산 — 언제 나오나. 설정한 규칙들은 OR로 결합(가장 먼저 충족되는 것이 청산 발동).

    익절(take_profit)·손절(stop_loss)·보유기간(hold_days)·트레일링(trail_pct·trail_atr_mult)·
    매도조건(condition)을 독립적으로 켠다. 별도 '방식' 선택 없이 채워진 규칙만 활성 —
    예: 보유기간+손절을 함께 설정하면 N일 경과 또는 손절 중 먼저 닿는 쪽에서 청산.
    """
    hold_days: Optional[int] = None
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None
    trail_pct: Optional[float] = None
    trail_atr_mult: Optional[float] = None
    condition: Optional[Node] = None    # 매도 신호(condition Node)


class Overlays(BaseModel):
    """전역 오버레이."""
    vol_target: Optional[float] = None        # 연율화 변동성 타겟(%)
    turnover_damp: Optional[float] = None      # 가중치 변동 억제 임계(hump)
    # 낙폭 제어 — hard: 완전 청산 낙폭(%, kill). soft: 디리스킹 시작 낙폭(%).
    # soft~hard 구간에서 노출을 선형 축소, hard에서 0. soft 미지정(또는 ≥hard)이면 binary kill.
    max_drawdown_stop: Optional[float] = None  # = hard
    max_drawdown_soft: Optional[float] = None  # 부분 디리스킹 시작점(없으면 binary)
    # 그룹 노출 캡 — group_label(섹터·bucket 등)별 |비중| 합이 max_group_pct 초과 시 해당 그룹 축소.
    # per-name 캡(sizing.max_position_pct)의 그룹 일반화. 초과분은 현금 버퍼로(재정규화 안 함).
    max_group_pct: Optional[float] = None
    group_label: Optional[Node] = None         # 그룹 라벨 블록 — out_type=label (§5.4 루트 경계)


class PositionSpec(BaseModel):
    """포지션 레이어 — 신호를 실제 매매로 번역하는 4부품 + 오버레이."""
    direction: Literal["long", "short", "long_short"] = "long"   # ① 방향
    sizing: Sizing = Field(default_factory=Sizing)               # ②
    entry: Entry = Field(default_factory=Entry)                  # ③
    exit: Exit = Field(default_factory=Exit)                     # ④
    overlays: Overlays = Field(default_factory=Overlays)


# ── 시뮬레이션 (비전 §3.5) ────────────────────────────────────────────────────

class SimSpec(BaseModel):
    initial_capital: float = 10_000_000.0
    delay: int = 1                      # 신호→체결 지연(거래일). look-ahead 방지.
    # next_open=익일 시가, close=당일 종가, typical=당일 (고+저+종)/3 일봉 VWAP 근사.
    # (진짜 intraday VWAP·N분 평균은 분봉 데이터 필요 — 현재 데이터 범위 밖, 가짜 폴백 안 함.)
    fill: Literal["next_open", "close", "typical"] = "next_open"
    commission: Optional[float] = None
    slippage: Optional[float] = None
    sell_tax: Optional[float] = None
    currency: str = "KRW"
    leverage: float = 1.0
    # 연율 비용(%) — 숏 차입(short_borrow_pct)·레버리지 펀딩(funding_cost_pct)·현금 무위험수익(rfr_pct).
    # 종목별 차입가능 여부는 데이터 부재로 미모델(정직한 한계 — §7.6).
    short_borrow_pct: Optional[float] = None
    funding_cost_pct: Optional[float] = None
    rfr_pct: Optional[float] = None
    # 유지증거금률(%) — 레버리지 포지션의 자기자본비율(nav/gross)이 이 값 미만이면 마진콜:
    # 목표 레버리지(nav×L)로 강제 복원(nav≤0이면 전량 청산). None=꺼짐.
    # 일봉 종가 기준 체크 — intraday 데이터 없음(가짜 폴백 안 함, §7.6 정직한 한계).
    maintenance_margin_pct: Optional[float] = None
    start: Optional[str] = None
    end: Optional[str] = None
    period_split: Literal["single", "walk_forward", "oos", "kfold"] = "single"


# ── 펼침 (비전 §4) ────────────────────────────────────────────────────────────

class ParamAxis(BaseModel):
    """파라미터 격자의 한 축 — 경로 1개 × 값 목록."""
    path: str                           # "simulation.commission" 등 점경로
    values: list = Field(default_factory=list)


class SweepSpec(BaseModel):
    axis: Literal["none", "condition", "parameter", "asset", "time"] = "none"
    label: Optional[Node] = None        # condition·time축: 라벨 블록(국면 등)
    # parameter축: 격자. 축 1개=1D 펼침, 2개+=데카르트곱(예: commission×slippage 민감도).
    param_grid: list[ParamAxis] = Field(default_factory=list)
    assets: list[str] = Field(default_factory=list)   # asset축: 종목/유니버스 목록
    event: Optional[Node] = None        # time축: 이벤트 조건(미지정 시 signal 사용)
    windows: list[int] = Field(default_factory=lambda: [5, 10, 20])  # time축: forward 윈도우(일)
    # time축 수익 기준: close(종가→종가)·intraday(시가→종가, 당일반등)·excess(시장초과)
    event_basis: Literal["close", "intraday", "excess"] = "close"


# ── 전략 (통합) ───────────────────────────────────────────────────────────────

class StrategyIR(BaseModel):
    name: str = "새 전략"
    universe: Universe = Field(default_factory=Universe)
    signal: Node                        # condition(룰) 또는 score(팩터)
    position: PositionSpec = Field(default_factory=PositionSpec)
    simulation: SimSpec = Field(default_factory=SimSpec)
    sweep: SweepSpec = Field(default_factory=SweepSpec)


# ── 정합성 검증 ───────────────────────────────────────────────────────────────

def signal_out_type(node: Node) -> Optional[str]:
    return get(node.op).out_type.value if has(node.op) else None


def validate_strategy(s: StrategyIR, valid_refs: Optional[set] = None,
                      meta: Optional[DatasetMeta] = None) -> list[Issue]:
    """StrategyIR 정합성 — 블록 메타규칙 + 구조 규칙(신호타입×진입 등) + 무결성."""
    issues: list[Issue] = list(validate(s.signal, valid_refs))
    issues += meaningfulness_issues(s.signal, "signal")   # M2·M3 — 동어반복·모순·퇴화 윈도우
    st = signal_out_type(s.signal)
    ent, pos, u = s.position.entry, s.position, s.universe

    # 최상위 신호는 매매 가능한 타입이어야 — condition(룰 트리거) 또는 score(팩터 알파).
    # label(bucket·calendar)·scalar는 그룹라벨·국면 등 보조 역할일 뿐 신호 자체가 될 수 없다.
    # (엔진은 condition 외 전부를 score로 취급하므로 label 코드가 알파로 오해석되는 silent 결함 차단.)
    if st is not None and st not in ("condition", "score"):
        issues.append(Issue("S-signal", SEV_ERROR,
                            "최상위 신호는 condition(참/거짓) 또는 score(점수) 블록이어야 합니다.", "signal"))

    # M1 — 신호는 시장 데이터를 ≥1회 참조해야 한다. 순수 상수·산술식은 시장에 반응하지
    # 않아(예: const(5)>const(0) → 매일 매수) 백테스트가 무의미하다.
    if st in ("condition", "score") and not has_market_source(s.signal):
        issues.append(Issue("M-const", SEV_ERROR,
                            "신호가 시장 데이터를 참조하지 않습니다 — 상수·산술만으론 시장에 "
                            "반응하지 않아 백테스트가 무의미합니다.", "signal"))

    # 신호 타입 × 진입/방향 호환
    if ent.mode == "on_signal" and st != "condition":
        issues.append(Issue("S-entry", SEV_ERROR,
                            "on_signal 진입은 신호가 condition(참/거짓)이어야 합니다.", "signal"))
    if pos.direction == "long_short" and st != "score":
        issues.append(Issue("S-dir", SEV_ERROR,
                            "long_short는 신호가 score(점수)여야 순위로 롱·숏을 가릅니다.", "signal"))
    if pos.sizing.mode == "signal_proportional" and st != "score":
        issues.append(Issue("S-size", SEV_ERROR,
                            "신호비례 사이징은 신호가 score여야 합니다.", "position.sizing"))
    if ent.threshold is not None and st != "score":
        issues.append(Issue("S-select", SEV_ERROR,
                            "임계 선택(threshold)은 신호가 score(점수)여야 합니다 — "
                            "참/거짓 신호는 그 자체가 임계 선택이므로 condition 신호를 쓰세요.",
                            "position.entry"))

    # M4 — 선택 파라미터 범위 (퇴화 선택 방지: top_n=0/음수, top_pct 범위밖이면 조용한 무거래)
    if ent.top_n is not None and ent.top_n < 1:
        issues.append(Issue("M-select", SEV_ERROR, "top_n은 1 이상이어야 합니다.", "position.entry"))
    if ent.top_pct is not None and not (0 < ent.top_pct <= 100):
        issues.append(Issue("M-select", SEV_ERROR, "top_pct는 0 초과 100 이하여야 합니다.", "position.entry"))

    # M6 — 유니버스/사이징 공허 조합 (경고: 선택이 무의미하거나 매수가 안 됨)
    if u.kind in ("single", "list") and ent.top_n is not None and ent.top_n > len(u.symbols):
        issues.append(Issue("M-vacuous", SEV_INTEGRITY_WARN,
                            f"top_n({ent.top_n})이 유니버스 종목 수({len(u.symbols)})보다 많습니다 — 전체 선택과 동일.",
                            "position.entry"))
    if (pos.sizing.mode == "fixed_weight" and pos.sizing.weights
            and u.kind in ("single", "list") and not (set(pos.sizing.weights) & set(u.symbols))):
        issues.append(Issue("M-vacuous", SEV_INTEGRITY_WARN,
                            "fixed_weight 가중치에 유니버스 종목이 하나도 없습니다 — 매수되지 않습니다.",
                            "position.sizing"))

    # 포지션 짝 제약 (비전 §3.3)
    if ent.mode in ("scheduled", "always") and pos.sizing.mode in ("fixed_amount", "pct_cash"):
        issues.append(Issue("S-pair", SEV_INTEGRITY_WARN,
                            "종목당 예산 사이징(fixed_amount·pct_cash)은 이벤트(on_signal) 진입용 — "
                            "스케줄·상시 진입에선 동일가중으로 처리됩니다.", "position.sizing"))
    if ent.mode == "always" and any((pos.exit.hold_days, pos.exit.take_profit, pos.exit.stop_loss,
                                      pos.exit.trail_pct, pos.exit.trail_atr_mult, pos.exit.condition)):
        issues.append(Issue("S-pair", SEV_INTEGRITY_WARN,
                            "상시 진입은 매일 리밸런싱이라 설정한 청산 규칙이 무시됩니다.", "position.exit"))

    # 유니버스
    if u.kind == "single" and len(u.symbols) != 1:
        issues.append(Issue("S-univ", SEV_ERROR, "단일 유니버스는 종목 1개가 필요합니다.", "universe"))
    if u.kind == "list" and not u.symbols:
        issues.append(Issue("S-univ", SEV_ERROR, "리스트 유니버스는 종목이 1개 이상 필요합니다.", "universe"))
    if ent.mode == "on_signal" and u.kind in ("all", "screener"):
        issues.append(Issue("S-univ", SEV_ERROR,
                            "전체·스크리너 유니버스는 정기리밸런싱(scheduled)·상시(always) 진입과 함께 쓰세요.",
                            "universe"))
    if u.kind == "screener":
        # 스크리너 = 단일 선별 조건(condition). 필터·횡단순위(rank 블록)·그룹 등을
        # AND/OR로 자유 조합 — 별도 rank 특수 struct 없이 프리미티브 조합으로 일반화.
        sc = u.screener or {}
        cond = sc.get("condition")
        if not cond:
            issues.append(Issue("S-univ", SEV_ERROR,
                                "스크리너는 선별 조건(condition)이 필요합니다.", "universe"))
        else:
            try:
                cnode = Node.model_validate(cond)
            except Exception:                       # noqa: BLE001 — 잘못된 트리
                issues.append(Issue("S-univ", SEV_ERROR, "스크리너 조건이 유효한 블록이 아닙니다.", "universe"))
            else:
                issues += list(validate(cnode, valid_refs))
                issues += meaningfulness_issues(cnode, "universe.condition")   # M2·M3
                if signal_out_type(cnode) != "condition":
                    issues.append(Issue("S-univ", SEV_ERROR,
                                        "스크리너 조건은 condition(참/거짓) 블록이어야 합니다 "
                                        "(예: 횡단순위(시총)≤50, 거래대금>임계).", "universe"))
                if not has_market_source(cnode):                              # M1
                    issues.append(Issue("M-const", SEV_ERROR,
                                        "스크리너 조건이 시장 데이터를 참조하지 않습니다.", "universe"))

    # 매도 조건 노드
    if pos.exit.condition is not None:
        issues += list(validate(pos.exit.condition, valid_refs))
        issues += meaningfulness_issues(pos.exit.condition, "exit.condition")   # M2·M3
        if not has_market_source(pos.exit.condition):                          # M1
            issues.append(Issue("M-const", SEV_ERROR,
                                "매도 조건이 시장 데이터를 참조하지 않습니다 — 항상 청산/미청산되어 무의미합니다.",
                                "exit.condition"))
        if signal_out_type(pos.exit.condition) != "condition":
            issues.append(Issue("S-exit", SEV_ERROR, "매도 조건은 condition 블록이어야 합니다.", "exit.condition"))

    # M5 — 청산 규칙 부호·범위 (관례: 익절>0%, 손절<0%, 보유기간≥1, 트레일링>0).
    # 부호가 틀리면 즉시청산/미청산으로 조용히 퇴화한다.
    ex = pos.exit
    if ex.hold_days is not None and ex.hold_days < 1:
        issues.append(Issue("M-exit", SEV_ERROR, "보유기간(hold_days)은 1 이상이어야 합니다.", "position.exit"))
    if ex.take_profit is not None and ex.take_profit <= 0:
        issues.append(Issue("M-exit", SEV_ERROR, "익절(take_profit)은 양수(%)여야 합니다.", "position.exit"))
    if ex.stop_loss is not None and ex.stop_loss >= 0:
        issues.append(Issue("M-exit", SEV_ERROR, "손절(stop_loss)은 음수(%)여야 합니다.", "position.exit"))
    if ex.trail_pct is not None and ex.trail_pct <= 0:
        issues.append(Issue("M-exit", SEV_ERROR, "트레일링(trail_pct)은 양수(%)여야 합니다.", "position.exit"))
    if ex.trail_atr_mult is not None and ex.trail_atr_mult <= 0:
        issues.append(Issue("M-exit", SEV_ERROR, "ATR 트레일링 배수(trail_atr_mult)는 양수여야 합니다.", "position.exit"))

    # 오버레이 (그룹 캡·낙폭 제어)
    ov = pos.overlays
    if ov.group_label is not None:
        issues += list(validate(ov.group_label, valid_refs))
        if signal_out_type(ov.group_label) != "label":
            issues.append(Issue("S-overlay", SEV_ERROR,
                                "그룹 노출 라벨(group_label)은 label 블록(구간분할·달력)이어야 합니다.",
                                "position.overlays"))
    if ov.max_group_pct is not None and ov.group_label is None:
        issues.append(Issue("S-overlay", SEV_ERROR,
                            "그룹 노출 캡(max_group_pct)은 group_label 블록이 필요합니다.", "position.overlays"))
    if (ov.max_drawdown_soft is not None and ov.max_drawdown_stop is not None
            and abs(ov.max_drawdown_soft) >= abs(ov.max_drawdown_stop)):
        issues.append(Issue("S-overlay", SEV_INTEGRITY_WARN,
                            "낙폭 soft가 hard 이상 — 부분 디리스킹 없이 binary kill로 동작합니다.",
                            "position.overlays"))

    # 펼침
    if s.sweep.axis == "condition" and s.sweep.label is None:
        issues.append(Issue("S-sweep", SEV_ERROR, "조건축 펼침은 라벨 블록이 필요합니다.", "sweep"))
    if s.sweep.axis == "parameter" and (not s.sweep.param_grid
                                        or any(not ax.values for ax in s.sweep.param_grid)):
        issues.append(Issue("S-sweep", SEV_ERROR,
                            "파라미터축 펼침은 param_grid(경로·값 목록)가 필요합니다.", "sweep"))
    if s.sweep.axis == "asset" and not s.sweep.assets:
        issues.append(Issue("S-sweep", SEV_ERROR, "자산축 펼침은 assets(종목 목록)가 필요합니다.", "sweep"))
    if s.sweep.axis == "time":
        ev = s.sweep.event or s.signal
        if signal_out_type(ev) != "condition":
            issues.append(Issue("S-event", SEV_ERROR,
                                "이벤트 분석은 이벤트 신호가 condition(발생 여부)이어야 합니다.", "sweep.event"))
        if not s.sweep.windows:
            issues.append(Issue("S-event", SEV_ERROR, "이벤트 분석은 forward 윈도우가 필요합니다.", "sweep.windows"))
        if s.sweep.event_basis == "excess" and u.kind == "single":
            issues.append(Issue("S-event", SEV_ERROR,
                                "초과수익(excess) 기준은 시장 지수 생성을 위해 종목이 2개 이상이어야 합니다.",
                                "sweep.event_basis"))
    if s.sweep.label is not None:
        issues += list(validate(s.sweep.label, valid_refs))
        if signal_out_type(s.sweep.label) != "label":
            issues.append(Issue("S-sweep", SEV_ERROR,
                                "펼침 분할 라벨(sweep.label)은 label 블록(구간분할·국면·달력)이어야 합니다.",
                                "sweep.label"))
    if s.sweep.event is not None:
        issues += list(validate(s.sweep.event, valid_refs))

    # 기간분할 × 펼침 동시 사용 금지 (2D 모호성 차단)
    if s.sweep.axis != "none" and s.simulation.period_split != "single":
        issues.append(Issue("S-split", SEV_ERROR,
                            "기간분할과 펼침은 동시에 쓸 수 없습니다 — 하나만 선택하세요.", "simulation"))

    # 무결성
    if meta is None:
        meta = DatasetMeta(delay=s.simulation.delay)
    issues += list(integrity_issues(s.signal, meta))
    return prioritize(issues)
