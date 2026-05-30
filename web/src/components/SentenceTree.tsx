import type { IndicatorInfo, IrBlockSpec, IrNode, IrParamSpec, IrValueType } from "../types";

/**
 * 문장형 빈칸 에디터 — 노코드 전략의 핵심 차별점. BlockTree를 대체.
 *
 * 자기서술 카탈로그(/ir/catalog)의 `phrase` 템플릿({slot}/{param} 토큰)으로 IR Node tree를
 * **문장**으로 재귀 렌더한다. 슬롯=하위문장(인라인 중첩), 빈칸=인라인 드롭다운/입력.
 * 같은 IR을 BlockTree와 동일하게 편집하되, 보여주는 방식만 문장형.
 */

export type Catalog = Map<string, IrBlockSpec>;
type ReqType = IrValueType | IrValueType[];

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
  spec?.params.forEach((p) => { if (p.default !== undefined) params[p.name] = p.default; });
  return { op, inputs: {}, params };
}

interface SymLite {
  symbol: string; name?: string; indicators: IndicatorInfo[]; has_backtest_data?: boolean;
}
interface Props {
  node: IrNode | null;
  catalog: Catalog;
  symbols: SymLite[];
  selfIndicators: IndicatorInfo[];
  requiredType: ReqType;
  onChange: (next: IrNode | null) => void;
  depth?: number;
}

export default function SentenceTree(props: Props) {
  // 루트(depth 0)만 문장 컨테이너로 감싼다 — 줄간격·폰트(.st). 중첩은 인라인.
  if ((props.depth ?? 0) === 0) return <span className="st"><SentenceNode {...props} /></span>;
  return <SentenceNode {...props} />;
}

function SentenceNode(props: Props) {
  const { node, catalog, requiredType, onChange } = props;

  if (!node) {
    return <SlotPicker requiredType={requiredType} catalog={catalog}
                       onCreate={(op) => onChange(makeNode(op, catalog))} />;
  }
  const spec = catalog.get(node.op);
  if (!spec) return <span className="st-unknown">알 수 없는 블록: {node.op}</span>;
  if (node.op === "data") return <DataLeaf {...props} node={node} />;
  if (node.op === "const") return <ConstLeaf node={node} onChange={onChange} />;

  const setSlot = (slot: string, child: IrNode | null) => {
    const inputs = { ...(node.inputs ?? {}) };
    if (child === null) delete inputs[slot]; else inputs[slot] = child;
    onChange({ ...node, inputs });
  };
  const setParam = (name: string, val: unknown) =>
    onChange({ ...node, params: { ...(node.params ?? {}), [name]: val } });

  return (
    <span className="st-block" data-out={spec.out_type}>
      {spec.variadic
        ? <Variadic {...props} node={node} spec={spec} setSlot={setSlot} setParam={setParam} />
        : <Phrase {...props} node={node} spec={spec} setSlot={setSlot} setParam={setParam} />}
      <button type="button" className="st-x" title="삭제" onClick={() => onChange(null)}>✕</button>
    </span>
  );
}

// ── 문장 렌더 (phrase 토큰 치환) ──────────────────────────────────────────────

function Phrase(props: Props & {
  node: IrNode; spec: IrBlockSpec;
  setSlot: (s: string, c: IrNode | null) => void; setParam: (n: string, v: unknown) => void;
}) {
  const { node, spec, setSlot, setParam } = props;
  // phrase 없으면 generic: 라벨 + 슬롯/파라미터 토큰 나열
  const tmpl = spec.phrase
    || `${spec.label} ${[...Object.keys(spec.slots).map((s) => `{${s}}`),
                         ...spec.params.filter((p) => p.kind !== "ref").map((p) => `{${p.name}}`)].join(" ")}`;
  const segs = tmpl.split(/(\{[a-zA-Z_0-9]+\})/);
  return (
    <span className="st-phrase">
      {segs.map((seg, i) => {
        const m = seg.match(/^\{([a-zA-Z_0-9]+)\}$/);
        if (!m) return seg ? <span key={i}>{seg}</span> : null;
        const name = m[1];
        if (name in spec.slots) {
          return (
            <span key={i} className="st-slot">
              <SentenceTree {...props} node={node.inputs?.[name] ?? null}
                            requiredType={spec.slots[name]} depth={(props.depth ?? 0) + 1}
                            onChange={(c) => setSlot(name, c)} />
            </span>
          );
        }
        const p = spec.params.find((pp) => pp.name === name);
        if (p) return <ParamInline key={i} p={p} value={node.params?.[name]}
                                   onChange={(v) => setParam(name, v)} />;
        return <span key={i}>{seg}</span>;
      })}
    </span>
  );
}

// ── 변동 슬롯 (logic: 그리고/또는으로 조건 결합) ──────────────────────────────

function Variadic(props: Props & {
  node: IrNode; spec: IrBlockSpec;
  setSlot: (s: string, c: IrNode | null) => void; setParam: (n: string, v: unknown) => void;
}) {
  const { node, spec, setSlot, setParam, catalog } = props;
  const inputs = node.inputs ?? {};
  const keys = Object.keys(inputs).sort((a, b) => Number(a) - Number(b));
  const reqType = spec.variadic_type ?? "condition";
  const isOr = node.params?.logic === "OR";
  const conn = isOr ? "또는" : "그리고";
  const nextKey = String(keys.length ? Math.max(...keys.map(Number)) + 1 : 0);
  return (
    <span className="st-variadic">
      {keys.map((k, i) => (
        <span key={k}>
          {i > 0 && (
            <button type="button" className="st-conn" title="그리고/또는 전환"
                    onClick={() => setParam("logic", isOr ? "AND" : "OR")}>{conn}</button>
          )}
          <span className="st-slot">
            <SentenceTree {...props} node={inputs[k]} requiredType={reqType}
                          depth={(props.depth ?? 0) + 1} onChange={(c) => setSlot(k, c)} />
          </span>
        </span>
      ))}
      <SlotPicker requiredType={reqType} catalog={catalog} compact
                  onCreate={(op) => setSlot(nextKey, makeNode(op, catalog))} />
    </span>
  );
}

// ── 인라인 파라미터 컨트롤 ────────────────────────────────────────────────────

function ParamInline({ p, value, onChange }: {
  p: IrParamSpec; value: unknown; onChange: (v: unknown) => void;
}) {
  if (p.kind === "select") {
    const v = String(value ?? p.default ?? p.options?.[0] ?? "");
    return (
      <select className="st-param" value={v} onChange={(e) => onChange(e.target.value)} title={p.label}>
        {p.options?.map((o) => <option key={o} value={o}>{p.labels?.[o] ?? o}</option>)}
      </select>
    );
  }
  if (p.kind === "bool") {
    const b = Boolean(value ?? p.default);
    const lbl = p.labels?.[String(b)] ?? (b ? "예" : "아니오");
    return (
      <button type="button" className="st-param st-toggle" title={p.label}
              onClick={() => onChange(!b)}>{lbl}</button>
    );
  }
  if (p.kind === "value_list") {
    const text = Array.isArray(value) ? value.join(", ") : "";
    return (
      <input className="st-param st-list" type="text" placeholder="금융, 지주" value={text}
             title={p.label}
             onChange={(e) => onChange(e.target.value.split(",").map((x) => x.trim())
               .filter(Boolean).map((x) => (x !== "" && !Number.isNaN(Number(x)) ? Number(x) : x)))} />
    );
  }
  if (p.kind === "number_list") {
    const text = Array.isArray(value) ? value.join(", ") : "";
    return (
      <input className="st-param st-list" type="text" placeholder="20, 30" value={text}
             title={p.label}
             onChange={(e) => onChange(e.target.value.split(",").map((x) => Number(x.trim()))
               .filter((n) => !Number.isNaN(n)))} />
    );
  }
  // number
  return (
    <input className="st-param st-num" type="number" title={p.label}
           value={value === undefined ? "" : Number(value)} min={p.min} max={p.max}
           onChange={(e) => onChange(e.target.value === "" ? undefined : Number(e.target.value))} />
  );
}

// ── 데이터 잎 ([이 종목]의 [지표]) ────────────────────────────────────────────

function DataLeaf({ node, symbols, selfIndicators, onChange }: Props & { node: IrNode }) {
  const ref = String(node.params?.ref ?? "__SELF__.Close");
  const [symPart, indPart] = ref.includes(".")
    ? [ref.slice(0, ref.indexOf(".")), ref.slice(ref.indexOf(".") + 1)] : ["__SELF__", ref];
  const indicatorsFor = (sym: string): IndicatorInfo[] => {
    if (sym === "__SELF__") return [...PRICE_COLS, ...selfIndicators];
    return [...PRICE_COLS, ...(symbols.find((x) => x.symbol === sym)?.indicators ?? [])];
  };
  const setRef = (sym: string, ind: string) =>
    onChange({ ...node, params: { ...node.params, ref: `${sym}.${ind}` } });
  const dataSyms = symbols.filter((s) => s.has_backtest_data);
  return (
    <span className="st-leaf" data-out="score">
      <select className="st-param" value={symPart} onChange={(e) => setRef(e.target.value, indPart)}>
        <option value="__SELF__">이 종목</option>
        {dataSyms.map((s) => <option key={s.symbol} value={s.symbol}>{s.name ? `${s.symbol} ${s.name}` : s.symbol}</option>)}
      </select>
      <span className="st-of">의</span>
      <select className="st-param" value={indPart} onChange={(e) => setRef(symPart, e.target.value)}>
        {indicatorsFor(symPart).map((i) => <option key={i.key} value={i.key}>{i.label}</option>)}
      </select>
      <button type="button" className="st-x" title="삭제" onClick={() => onChange(null)}>✕</button>
    </span>
  );
}

function ConstLeaf({ node, onChange }: { node: IrNode; onChange: (n: IrNode | null) => void }) {
  const v = node.params?.value;
  const text = Array.isArray(v) ? v.join(", ") : v === undefined ? "" : String(v);
  const parse = (s: string): number | number[] => {
    const parts = s.split(",").map((x) => x.trim()).filter(Boolean).map(Number);
    return parts.length >= 2 ? parts.filter((n) => !Number.isNaN(n)) : (Number.isNaN(parts[0]) ? 0 : parts[0]);
  };
  return (
    <span className="st-leaf" data-out="score">
      <input className="st-param st-num" type="text" placeholder="값" value={text}
             onChange={(e) => onChange({ ...node, params: { ...node.params, value: parse(e.target.value) } })} />
      <button type="button" className="st-x" title="삭제" onClick={() => onChange(null)}>✕</button>
    </span>
  );
}

// ── 빈칸 picker (요구 타입에 맞는 블록 선택) ──────────────────────────────────

function SlotPicker({ requiredType, catalog, onCreate, compact }: {
  requiredType: ReqType; catalog: Catalog; onCreate: (op: string) => void; compact?: boolean;
}) {
  const types = Array.isArray(requiredType) ? requiredType : [requiredType];
  const candidates = [...catalog.values()].filter((b) => types.includes(b.out_type));
  const byCat = new Map<string, IrBlockSpec[]>();
  for (const b of candidates) {
    if (!byCat.has(b.category)) byCat.set(b.category, []);
    byCat.get(b.category)!.push(b);
  }
  const cats = [...byCat.keys()].sort((a, b) =>
    (a === "잎" ? -1 : 0) - (b === "잎" ? -1 : 0) || a.localeCompare(b));
  const word = types.includes("condition") && types.includes("score") ? "신호"
    : types.includes("condition") ? "조건" : types.includes("label") ? "라벨" : "값";
  return (
    <select className={"st-blank" + (compact ? " st-blank-compact" : "")} value=""
            onChange={(e) => { if (e.target.value) onCreate(e.target.value); }}>
      <option value="">{compact ? "＋" : `＋ ${word} 채우기`}</option>
      {cats.map((cat) => (
        <optgroup key={cat} label={cat}>
          {byCat.get(cat)!.map((b) => <option key={b.op} value={b.op}>{b.label}</option>)}
        </optgroup>
      ))}
    </select>
  );
}
