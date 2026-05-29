import type { IndicatorInfo, IrBlockSpec, IrNode, IrParamSpec, IrValueType } from "../types";

/**
 * 재귀 블록트리 에디터 — 노코드 전략 조립의 핵심.
 *
 * 자기서술 카탈로그(/ir/catalog)로 구동: 블록 종류·슬롯 타입·파라미터 UI를 전부
 * 서버 명세에서 받아 렌더하므로 프론트는 블록 지식을 하드코딩하지 않는다.
 * 슬롯(가지 빈칸)에 또 다른 블록을 끼워 중첩 — rank(ts_corr(Close, Volume)) 등.
 */

export type Catalog = Map<string, IrBlockSpec>;

const PRICE_COLS: IndicatorInfo[] = [
  { key: "Close", label: "종가", group: "가격" },
  { key: "Open", label: "시가", group: "가격" },
  { key: "High", label: "고가", group: "가격" },
  { key: "Low", label: "저가", group: "가격" },
  { key: "Volume", label: "거래량", group: "가격" },
];

export function makeNode(op: string, catalog: Catalog): IrNode {
  const spec = catalog.get(op);
  const params: Record<string, unknown> = {};
  spec?.params.forEach((p) => {
    if (p.default !== undefined) params[p.name] = p.default;
  });
  return { op, inputs: {}, params };
}

interface SymLite {
  symbol: string;
  name?: string;
  indicators: IndicatorInfo[];
  has_backtest_data?: boolean;
}

interface TreeProps {
  node: IrNode | null;
  catalog: Catalog;
  symbols: SymLite[];
  selfIndicators: IndicatorInfo[];   // [이 종목] = 백테스트 대상 종목의 지표
  requiredType: IrValueType;
  onChange: (next: IrNode | null) => void;
  depth?: number;
}

export default function BlockTree(props: TreeProps) {
  const { node, catalog, requiredType, onChange } = props;

  if (!node) {
    return <SlotPicker requiredType={requiredType} catalog={catalog}
                       onCreate={(op) => onChange(makeNode(op, catalog))} />;
  }

  const spec = catalog.get(node.op);
  if (!spec) return <div className="block block-unknown">알 수 없는 블록: {node.op}</div>;

  if (node.op === "data") {
    return <DataLeaf {...props} node={node} />;
  }
  if (node.op === "const") {
    return <ConstLeaf node={node} onChange={onChange} />;
  }

  const setParams = (params: Record<string, unknown>) => onChange({ ...node, params });
  const setSlot = (slot: string, child: IrNode | null) => {
    const inputs = { ...(node.inputs ?? {}) };
    if (child === null) delete inputs[slot];
    else inputs[slot] = child;
    onChange({ ...node, inputs });
  };

  return (
    <div className="block" data-out={spec.out_type}>
      <div className="block-head">
        <span className="block-label">{spec.label}</span>
        <span className="block-type">{spec.out_type === "condition" ? "조건"
          : spec.out_type === "label" ? "라벨" : "점수"}</span>
        <button type="button" className="block-x" title="삭제"
                onClick={() => onChange(null)}>✕</button>
      </div>

      <ParamRow spec={spec} params={node.params ?? {}} onChange={setParams} />

      {spec.variadic
        ? <VariadicSlots {...props} node={node} spec={spec} setSlot={setSlot} />
        : Object.entries(spec.slots).map(([slot, type]) => (
            <div className="block-slot" key={slot}>
              <span className="slot-label">{slotLabel(slot)}</span>
              <div className="slot-body">
                <BlockTree {...props} node={node.inputs?.[slot] ?? null}
                           requiredType={type} depth={(props.depth ?? 0) + 1}
                           onChange={(c) => setSlot(slot, c)} />
              </div>
            </div>
          ))}
    </div>
  );
}

// ── 가변 슬롯 (logic: AND/OR로 여러 조건 결합) ────────────────────────────────

function VariadicSlots(props: TreeProps & {
  node: IrNode; spec: IrBlockSpec; setSlot: (s: string, c: IrNode | null) => void;
}) {
  const { node, spec, setSlot } = props;
  const inputs = node.inputs ?? {};
  const keys = Object.keys(inputs).sort((a, b) => Number(a) - Number(b));
  const reqType = spec.variadic_type ?? "condition";
  const nextKey = String(keys.length ? Math.max(...keys.map(Number)) + 1 : 0);
  return (
    <>
      {keys.map((k) => (
        <div className="block-slot" key={k}>
          <span className="slot-label">조건</span>
          <div className="slot-body">
            <BlockTree {...props} node={inputs[k]} requiredType={reqType}
                       depth={(props.depth ?? 0) + 1}
                       onChange={(c) => setSlot(k, c)} />
          </div>
        </div>
      ))}
      <div className="block-slot">
        <span className="slot-label" />
        <div className="slot-body">
          <SlotPicker requiredType={reqType} catalog={props.catalog}
                      onCreate={(op) => setSlot(nextKey, makeNode(op, props.catalog))} />
        </div>
      </div>
    </>
  );
}

// ── 슬롯 채우기 picker (요구 타입에 맞는 블록만 제공) ─────────────────────────

function SlotPicker({ requiredType, catalog, onCreate }: {
  requiredType: IrValueType; catalog: Catalog; onCreate: (op: string) => void;
}) {
  const candidates = [...catalog.values()].filter((b) => b.out_type === requiredType);
  const byCat = new Map<string, IrBlockSpec[]>();
  for (const b of candidates) {
    if (!byCat.has(b.category)) byCat.set(b.category, []);
    byCat.get(b.category)!.push(b);
  }
  // 잎(데이터·상수) 카테고리를 맨 앞으로
  const cats = [...byCat.keys()].sort((a, b) =>
    (a === "잎" ? -1 : 0) - (b === "잎" ? -1 : 0) || a.localeCompare(b));
  return (
    <select className="slot-picker" value=""
            onChange={(e) => { if (e.target.value) onCreate(e.target.value); }}>
      <option value="">+ {requiredType === "condition" ? "조건" : "값"} 블록 선택…</option>
      {cats.map((cat) => (
        <optgroup key={cat} label={cat}>
          {byCat.get(cat)!.map((b) => (
            <option key={b.op} value={b.op}>{b.label}</option>
          ))}
        </optgroup>
      ))}
    </select>
  );
}

// ── 데이터 잎 (종목.지표) ─────────────────────────────────────────────────────

function DataLeaf({ node, symbols, selfIndicators, onChange }: TreeProps & { node: IrNode }) {
  const ref = String(node.params?.ref ?? "__SELF__.Close");
  const [symPart, indPart] = ref.includes(".") ? splitRef(ref) : ["__SELF__", ref];

  const indicatorsFor = (sym: string): IndicatorInfo[] => {
    if (sym === "__SELF__") return [...PRICE_COLS, ...selfIndicators];
    const s = symbols.find((x) => x.symbol === sym);
    return [...PRICE_COLS, ...(s?.indicators ?? [])];
  };
  const setRef = (sym: string, ind: string) =>
    onChange({ ...node, params: { ...node.params, ref: `${sym}.${ind}` } });

  const dataSyms = symbols.filter((s) => s.has_backtest_data);
  const inds = indicatorsFor(symPart);

  return (
    <div className="block block-leaf" data-out="score">
      <div className="leaf-row">
        <select value={symPart} onChange={(e) => setRef(e.target.value, indPart)}>
          <option value="__SELF__">[이 종목]</option>
          {dataSyms.map((s) => (
            <option key={s.symbol} value={s.symbol}>
              {s.name ? `${s.symbol} ${s.name}` : s.symbol}
            </option>
          ))}
        </select>
        <select value={indPart} onChange={(e) => setRef(symPart, e.target.value)}>
          {inds.map((i) => <option key={i.key} value={i.key}>{i.label}</option>)}
        </select>
        <button type="button" className="block-x" title="삭제"
                onClick={() => onChange(null)}>✕</button>
      </div>
    </div>
  );
}

function splitRef(ref: string): [string, string] {
  const i = ref.indexOf(".");
  return [ref.slice(0, i), ref.slice(i + 1)];
}

// ── 상수 잎 ───────────────────────────────────────────────────────────────────

function ConstLeaf({ node, onChange }: { node: IrNode; onChange: (n: IrNode | null) => void }) {
  const v = node.params?.value;
  const text = Array.isArray(v) ? v.join(", ") : v === undefined ? "" : String(v);
  return (
    <div className="block block-leaf" data-out="score">
      <div className="leaf-row">
        <input type="text" className="const-input" placeholder="값 (범위는 10, 90)"
               value={text}
               onChange={(e) => onChange({ ...node, params: { ...node.params, value: parseConst(e.target.value) } })} />
        <button type="button" className="block-x" title="삭제"
                onClick={() => onChange(null)}>✕</button>
      </div>
    </div>
  );
}

function parseConst(s: string): number | number[] {
  const parts = s.split(",").map((x) => x.trim()).filter(Boolean).map(Number);
  if (parts.length >= 2) return parts.filter((n) => !Number.isNaN(n));
  return Number.isNaN(parts[0]) ? 0 : parts[0];
}

// ── 파라미터 컨트롤 ───────────────────────────────────────────────────────────

function ParamRow({ spec, params, onChange }: {
  spec: IrBlockSpec; params: Record<string, unknown>; onChange: (p: Record<string, unknown>) => void;
}) {
  const visible = spec.params.filter((p) => p.kind !== "ref");  // ref는 data 잎에서 처리
  if (!visible.length) return null;
  return (
    <div className="block-params">
      {visible.map((p) => (
        <ParamControl key={p.name} p={p} value={params[p.name]}
                      onChange={(val) => onChange({ ...params, [p.name]: val })} />
      ))}
    </div>
  );
}

function ParamControl({ p, value, onChange }: {
  p: IrParamSpec; value: unknown; onChange: (v: unknown) => void;
}) {
  if (p.kind === "select") {
    return (
      <label>{p.label ?? p.name}
        <select value={String(value ?? p.default ?? p.options?.[0] ?? "")}
                onChange={(e) => onChange(e.target.value)}>
          {p.options?.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      </label>
    );
  }
  if (p.kind === "number_list") {
    const text = Array.isArray(value) ? value.join(", ") : "";
    return (
      <label>{p.label ?? p.name}
        <input type="text" placeholder="예: 20, 30" value={text}
               onChange={(e) => onChange(e.target.value.split(",").map((x) => Number(x.trim()))
                 .filter((n) => !Number.isNaN(n)))} />
      </label>
    );
  }
  // number
  return (
    <label>{p.label ?? p.name}
      <input type="number" value={value === undefined ? "" : Number(value)}
             min={p.min} max={p.max}
             onChange={(e) => onChange(e.target.value === "" ? undefined : Number(e.target.value))} />
    </label>
  );
}

// 슬롯 라벨 — 한글화 (없으면 슬롯명).
function slotLabel(slot: string): string {
  const M: Record<string, string> = {
    left: "왼쪽", right: "오른쪽", signal: "대상", cond: "조건",
    a: "A", b: "B", x: "X", y: "Y",
  };
  return M[slot] ?? slot;
}
