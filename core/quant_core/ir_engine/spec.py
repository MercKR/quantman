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
from ..blocks.validate import SEV_ERROR, SEV_INTEGRITY_WARN, Issue, prioritize, validate

# ── 유니버스 (대상 종목 집합) ─────────────────────────────────────────────────

class Universe(BaseModel):
    kind: Literal["single", "list", "all", "screener"] = "single"
    symbols: list[str] = Field(default_factory=list)   # single(1개)/list(다수)
    screener: Optional[dict] = None                    # kind=screener: screener spec
    exclude_macro: bool = True                         # all: 매크로/자산 지수 제외


# ── 포지션 4부품 (비전 §3.3) ──────────────────────────────────────────────────

class Sizing(BaseModel):
    """② 크기 — 얼마나."""
    mode: Literal[
        "equal_weight",         # 동일가중
        "signal_proportional",  # 신호(score)비례
        "vol_inverse",          # 변동성 역가중
        "fixed_risk",           # 고정위험(ATR 기반)
        "kelly",                # 켈리(승률·손익비)
        "fixed_amount",         # 종목당 고정 금액
        "pct_cash",             # 자본 대비 %
    ] = "equal_weight"
    amount_pct: float = 10.0           # pct_cash / per-name 기본
    amount_krw: Optional[float] = None  # fixed_amount
    risk_pct: Optional[float] = None    # fixed_risk: 거래당 자본 risk %
    atr_mult: Optional[float] = None    # fixed_risk: ATR 배수
    vol_window: int = 20                # vol_inverse 변동성 창
    # 종목당 상한(%) — opt-in. 기본 100=무제한(집중 사이징 보존). 분산 원하면 낮춤.
    max_position_pct: float = 100.0


class Entry(BaseModel):
    """③ 진입 — 언제 들어가나."""
    mode: Literal["on_signal", "scheduled", "always"] = "on_signal"
    rebalance: Literal["daily", "weekly", "monthly", "every_n_days"] = "weekly"
    every_n_days: Optional[int] = None
    top_n: Optional[int] = None         # scheduled/팩터: score 상위 N 선택


class Exit(BaseModel):
    """④ 청산 — 언제 나오나."""
    mode: Literal["on_condition", "after_n_days", "stop_target", "daily"] = "stop_target"
    hold_days: Optional[int] = None
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None
    trail_pct: Optional[float] = None
    trail_atr_mult: Optional[float] = None
    condition: Optional[Node] = None    # on_condition: 매도 신호(condition Node)


class Overlays(BaseModel):
    """전역 오버레이."""
    vol_target: Optional[float] = None        # 연율화 변동성 타겟(%)
    turnover_damp: Optional[float] = None      # 가중치 변동 억제 임계(hump)
    max_drawdown_stop: Optional[float] = None  # 누적 -% 도달 시 청산(kill switch)


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
    fill: Literal["next_open", "close"] = "next_open"
    commission: Optional[float] = None
    slippage: Optional[float] = None
    sell_tax: Optional[float] = None
    currency: str = "KRW"
    leverage: float = 1.0
    start: Optional[str] = None
    end: Optional[str] = None
    period_split: Literal["single", "walk_forward", "oos", "kfold"] = "single"


# ── 펼침 (비전 §4) ────────────────────────────────────────────────────────────

class SweepSpec(BaseModel):
    axis: Literal["none", "condition", "parameter", "asset", "time"] = "none"
    label: Optional[Node] = None        # condition·time축: 라벨 블록(국면 등)
    param_path: Optional[str] = None    # parameter축: "simulation.commission" 등 경로
    param_values: list = Field(default_factory=list)  # parameter축: 값 목록
    assets: list[str] = Field(default_factory=list)   # asset축: 종목/유니버스 목록
    event: Optional[Node] = None        # time축: 이벤트 조건(미지정 시 signal 사용)
    windows: list[int] = Field(default_factory=lambda: [5, 10, 20])  # time축: forward 윈도우(일)


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
    st = signal_out_type(s.signal)
    ent, pos, u = s.position.entry, s.position, s.universe

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

    # 포지션 짝 제약 (비전 §3.3)
    if pos.sizing.mode == "fixed_risk" and pos.sizing.atr_mult is None:
        issues.append(Issue("S-pair", SEV_ERROR,
                            "고정위험 사이징은 atr_mult가 필요합니다.", "position.sizing"))
    if pos.sizing.mode == "kelly":
        issues.append(Issue("S-pair", SEV_INTEGRITY_WARN,
                            "켈리 사이징은 현재 동일가중으로 근사됩니다(입력 미지원).", "position.sizing"))
    if ent.mode == "always" and pos.exit.mode != "daily":
        issues.append(Issue("S-pair", SEV_INTEGRITY_WARN,
                            "상시 진입은 매일 리밸런싱이라 청산 규칙이 무시됩니다.", "position.exit"))

    # 유니버스
    if u.kind == "single" and len(u.symbols) != 1:
        issues.append(Issue("S-univ", SEV_ERROR, "단일 유니버스는 종목 1개가 필요합니다.", "universe"))
    if u.kind == "list" and not u.symbols:
        issues.append(Issue("S-univ", SEV_ERROR, "리스트 유니버스는 종목이 1개 이상 필요합니다.", "universe"))
    if ent.mode == "on_signal" and u.kind == "all":
        issues.append(Issue("S-univ", SEV_ERROR,
                            "전체 유니버스는 정기리밸런싱(scheduled)·상시(always) 진입과 함께 쓰세요.", "universe"))
    if u.kind == "screener":
        issues.append(Issue("S-univ", SEV_ERROR,
                            "screener 유니버스 동적 해결은 데이터 연동 후 지원됩니다 — 현재는 전체/리스트를 쓰세요.",
                            "universe"))

    # 매도 조건 노드
    if pos.exit.condition is not None:
        issues += list(validate(pos.exit.condition, valid_refs))
        if signal_out_type(pos.exit.condition) != "condition":
            issues.append(Issue("S-exit", SEV_ERROR, "매도 조건은 condition 블록이어야 합니다.", "exit.condition"))

    # 펼침
    if s.sweep.axis == "condition" and s.sweep.label is None:
        issues.append(Issue("S-sweep", SEV_ERROR, "조건축 펼침은 라벨 블록이 필요합니다.", "sweep"))
    if s.sweep.axis == "time":
        ev = s.sweep.event or s.signal
        if signal_out_type(ev) != "condition":
            issues.append(Issue("S-event", SEV_ERROR,
                                "이벤트 분석은 이벤트 신호가 condition(발생 여부)이어야 합니다.", "sweep.event"))
        if not s.sweep.windows:
            issues.append(Issue("S-event", SEV_ERROR, "이벤트 분석은 forward 윈도우가 필요합니다.", "sweep.windows"))
    if s.sweep.label is not None:
        issues += list(validate(s.sweep.label, valid_refs))
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
