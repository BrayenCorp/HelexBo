import { nf } from "../format";

export interface Series { name: string; color: string; values: number[] }
const COLORS = { orange: "#ff6a00", black: "#111111", soft: "#ffb98a", gray: "#9a9a94" };
export const palette = COLORS;

const dd = (iso: string) => `${iso.slice(8, 10)}.${iso.slice(5, 7)}`;

function Legend({ series }: { series: Series[] }) {
  return <div className="legend">{series.map((s) => <span key={s.name}><i style={{ background: s.color }} />{s.name}</span>)}</div>;
}

function frame(days: string[], max: number) {
  const W = 640, H = 200, L = 40, R = 8, T = 10, B = 24;
  const x = (i: number) => L + (days.length <= 1 ? (W - L - R) / 2 : (i * (W - L - R)) / (days.length - 1));
  const y = (v: number) => T + (1 - v / max) * (H - T - B);
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => Math.round(max * f));
  const step = Math.max(1, Math.ceil(days.length / 7));
  return { W, H, L, R, T, B, x, y, ticks, step };
}

/** Линейный график по дням. Если за период нет данных — честно пишет «Нет данных». */
export function LineChart({ days, series, height = 200 }: { days: string[]; series: Series[]; height?: number }) {
  const max = Math.max(1, ...series.flatMap((s) => s.values));
  const f = frame(days, max);
  const empty = series.every((s) => s.values.every((v) => !v));
  return (
    <div className="chart">
      <svg viewBox={`0 0 ${f.W} ${f.H}`} role="img" style={{ maxHeight: height }}>
        {f.ticks.map((t) => (<g key={t}><line x1={f.L} x2={f.W - f.R} y1={f.y(t)} y2={f.y(t)} stroke="#e6e4e0" /><text x={f.L - 6} y={f.y(t) + 3} textAnchor="end">{nf(t)}</text></g>))}
        {days.map((d, i) => (i % f.step === 0 ? <text key={d} x={f.x(i)} y={f.H - 6} textAnchor="middle">{dd(d)}</text> : null))}
        {series.map((s) => (
          <g key={s.name}>
            <polyline fill="none" stroke={s.color} strokeWidth={2.2} strokeLinejoin="round" points={s.values.map((v, i) => `${f.x(i)},${f.y(v)}`).join(" ")} />
            {days.length <= 31 && s.values.map((v, i) => <circle key={i} cx={f.x(i)} cy={f.y(v)} r={2.6} fill={s.color}><title>{`${s.name}, ${dd(days[i])}: ${nf(v)}`}</title></circle>)}
          </g>
        ))}
        {empty && <text x={f.W / 2} y={f.H / 2} textAnchor="middle" style={{ fontSize: 13 }}>Нет данных за период</text>}
      </svg>
      <Legend series={series} />
    </div>
  );
}

export function BarChart({ days, series, height = 200 }: { days: string[]; series: Series; height?: number }) {
  const max = Math.max(1, ...series.values);
  const f = frame(days, max);
  const bw = Math.max(2, ((f.W - f.L - f.R) / Math.max(days.length, 1)) * 0.7);
  const empty = series.values.every((v) => !v);
  return (
    <div className="chart">
      <svg viewBox={`0 0 ${f.W} ${f.H}`} role="img" style={{ maxHeight: height }}>
        {f.ticks.map((t) => (<g key={t}><line x1={f.L} x2={f.W - f.R} y1={f.y(t)} y2={f.y(t)} stroke="#e6e4e0" /><text x={f.L - 6} y={f.y(t) + 3} textAnchor="end">{nf(t)}</text></g>))}
        {days.map((d, i) => (i % f.step === 0 ? <text key={d} x={f.x(i)} y={f.H - 6} textAnchor="middle">{dd(d)}</text> : null))}
        {series.values.map((v, i) => <rect key={i} x={f.x(i) - bw / 2} y={f.y(v)} width={bw} height={Math.max(0, f.H - f.B - f.y(v))} rx={2} fill={series.color}><title>{`${dd(days[i])}: ${nf(v)}`}</title></rect>)}
        {empty && <text x={f.W / 2} y={f.H / 2} textAnchor="middle" style={{ fontSize: 13 }}>Нет данных за период</text>}
      </svg>
      <Legend series={[series]} />
    </div>
  );
}
