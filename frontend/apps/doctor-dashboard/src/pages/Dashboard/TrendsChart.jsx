function clamp(n, min, max) {
  return Math.max(min, Math.min(max, n));
}

function buildLinePath(series, width, height, padding) {
  if (!series?.length) return '';
  const min = Math.min(...series);
  const max = Math.max(...series);
  const span = max - min || 1;

  const innerW = width - padding * 2;
  const innerH = height - padding * 2;
  const step = innerW / Math.max(1, series.length - 1);

  const points = series.map((v, i) => {
    const x = padding + i * step;
    const t = (v - min) / span;
    const y = padding + (1 - clamp(t, 0, 1)) * innerH;
    return { x, y };
  });

  return points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`)
    .join(' ');
}

function buildAreaPath(linePath, width, height, padding) {
  if (!linePath) return '';
  const baselineY = height - padding;
  return `${linePath} L ${(width - padding).toFixed(2)} ${baselineY.toFixed(2)} L ${padding.toFixed(2)} ${baselineY.toFixed(2)} Z`;
}

export default function TrendsChart({
  labels = [],
  seriesA = [],
  seriesB = [],
  legendA = 'Patients',
  legendB = 'Appointments',
}) {
  const width = 720;
  const height = 220;
  const padding = 24;

  const aLine = buildLinePath(seriesA, width, height, padding);
  const bLine = buildLinePath(seriesB, width, height, padding);

  return (
    <div className="dash-panel">
      <div className="dash-panel__head">
        <div className="dash-panel__title">Patient &amp; Appointment Trends</div>
        <div className="dash-panel__legend">
          <span className="dash-legend">
            <span className="dash-legend__dot dash-legend__dot--a" />
            {legendA}
          </span>
          <span className="dash-legend">
            <span className="dash-legend__dot dash-legend__dot--b" />
            {legendB}
          </span>
        </div>
      </div>

      <div className="dash-chart">
        <svg viewBox={`0 0 ${width} ${height}`} width="100%" height="100%" preserveAspectRatio="none" aria-hidden="true">
          <defs>
            <linearGradient id="dash-grad-a" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--dash-a)" stopOpacity="0.15" />
              <stop offset="100%" stopColor="var(--dash-a)" stopOpacity="0" />
            </linearGradient>
            <linearGradient id="dash-grad-b" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--dash-b)" stopOpacity="0.15" />
              <stop offset="100%" stopColor="var(--dash-b)" stopOpacity="0" />
            </linearGradient>
          </defs>

          {/* grid */}
          {Array.from({ length: 6 }).map((_, i) => {
            const y = padding + (i * (height - padding * 2)) / 5;
            return <line key={i} x1={padding} x2={width - padding} y1={y} y2={y} stroke="#eef2f7" strokeWidth="1" />;
          })}

          {/* areas */}
          <path d={buildAreaPath(aLine, width, height, padding)} fill="url(#dash-grad-a)" />
          <path d={buildAreaPath(bLine, width, height, padding)} fill="url(#dash-grad-b)" />

          {/* lines */}
          <path d={aLine} fill="none" stroke="var(--dash-a)" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
          <path d={bLine} fill="none" stroke="var(--dash-b)" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
        </svg>

        {labels?.length ? (
          <div className="dash-chart__x">
            {labels.map((l) => (
              <span key={l}>{l}</span>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}

