import { useMemo } from 'react';

interface ChartRendererProps {
  content: string;
  className?: string;
}

interface ChartPoint {
  x: string;
  y: number;
}

interface ChartSeries {
  name: string;
  points: ChartPoint[];
}

interface ChartPayload {
  kind: string;
  title?: string;
  chart?: {
    chart_type?: 'bar' | 'line';
    x_label?: string;
    y_label?: string;
    series?: ChartSeries[];
  };
  insights?: string[];
}

const palette = ['#2563eb', '#16a34a', '#f59e0b', '#dc2626', '#7c3aed', '#0d9488'];

function parseChartPayload(content: string): ChartPayload | null {
  try {
    const parsed = JSON.parse(content) as ChartPayload;
    if (!parsed || parsed.kind !== 'chart') return null;
    return parsed;
  } catch {
    return null;
  }
}

function periodSortKey(label: string): [number, number, string] {
  const pieces = label.trim().split(/\s+/);
  if (pieces.length !== 2) return [0, 0, label];
  const year = Number.parseInt(pieces[0], 10);
  const quarter = pieces[1].toUpperCase();
  const quarterOrder = { Q1: 1, Q2: 2, Q3: 3, Q4: 4 }[quarter] || 0;
  return [Number.isFinite(year) ? year : 0, quarterOrder, label];
}

export function ChartRenderer({ content, className = '' }: ChartRendererProps) {
  const payload = useMemo(() => parseChartPayload(content), [content]);

  const chartModel = useMemo(() => {
    if (!payload?.chart?.series || payload.chart.series.length === 0) return null;

    const categories: string[] = [];
    const categorySet = new Set<string>();
    let maxY = 0;

    const normalizedSeries = payload.chart.series
      .map((series) => {
        const points = (series.points || [])
          .filter((point) => typeof point?.x === 'string' && Number.isFinite(point?.y))
          .map((point) => ({ x: point.x, y: Number(point.y) }))
          .sort((a, b) => {
            const aKey = periodSortKey(a.x);
            const bKey = periodSortKey(b.x);
            if (aKey[0] !== bKey[0]) return aKey[0] - bKey[0];
            if (aKey[1] !== bKey[1]) return aKey[1] - bKey[1];
            return aKey[2].localeCompare(bKey[2]);
          });

        points.forEach((point) => {
          if (!categorySet.has(point.x)) {
            categorySet.add(point.x);
            categories.push(point.x);
          }
          maxY = Math.max(maxY, point.y);
        });

        return {
          name: series.name || 'Series',
          points,
        };
      })
      .filter((series) => series.points.length > 0);

    if (normalizedSeries.length === 0 || categories.length === 0) return null;

    return {
      chartType: payload.chart.chart_type || 'bar',
      xLabel: payload.chart.x_label || 'Category',
      yLabel: payload.chart.y_label || 'Value',
      title: payload.title || 'Chart',
      series: normalizedSeries,
      categories,
      maxY: maxY > 0 ? maxY : 1,
      insights: payload.insights || [],
    };
  }, [payload]);

  if (!payload || !chartModel) {
    return (
      <div className={`rounded-lg border border-zinc-200 bg-zinc-50 p-3 text-xs text-zinc-500 ${className}`}>
        Unable to render chart payload.
      </div>
    );
  }

  const width = 720;
  const height = 300;
  const margin = { top: 20, right: 20, bottom: 65, left: 55 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;

  const categoryIndex = new Map(chartModel.categories.map((label, index) => [label, index]));
  const xForCategory = (label: string) => {
    const index = categoryIndex.get(label) || 0;
    if (chartModel.categories.length === 1) {
      return margin.left + plotWidth / 2;
    }
    return margin.left + (index / (chartModel.categories.length - 1)) * plotWidth;
  };

  const yForValue = (value: number) => margin.top + plotHeight - (value / chartModel.maxY) * plotHeight;

  const linePaths = chartModel.series.map((series, index) => {
    const points = series.points.map((point) => `${xForCategory(point.x)},${yForValue(point.y)}`);
    return {
      name: series.name,
      color: palette[index % palette.length],
      points: series.points,
      polylinePoints: points.join(' '),
    };
  });

  const barGroups = chartModel.series.map((series, index) => {
    const pointMap = new Map(series.points.map((point) => [point.x, point.y]));
    return {
      name: series.name,
      color: palette[index % palette.length],
      values: chartModel.categories.map((label) => pointMap.get(label)),
    };
  });

  const categoryWidth = plotWidth / Math.max(chartModel.categories.length, 1);
  const barWidth = Math.max(categoryWidth / (barGroups.length + 1), 4);

  return (
    <div className={`rounded-lg border border-sky-100 bg-sky-50/40 p-3 ${className}`}>
      <div className="text-sm font-semibold text-sky-900">{chartModel.title}</div>
      <svg viewBox={`0 0 ${width} ${height}`} className="mt-2 w-full h-auto rounded bg-white">
        <line
          x1={margin.left}
          y1={margin.top + plotHeight}
          x2={width - margin.right}
          y2={margin.top + plotHeight}
          stroke="#cbd5e1"
          strokeWidth={1}
        />
        <line
          x1={margin.left}
          y1={margin.top}
          x2={margin.left}
          y2={margin.top + plotHeight}
          stroke="#cbd5e1"
          strokeWidth={1}
        />

        {[0, 0.25, 0.5, 0.75, 1].map((tick) => {
          const y = margin.top + plotHeight - tick * plotHeight;
          const value = (chartModel.maxY * tick).toFixed(1);
          return (
            <g key={tick}>
              <line x1={margin.left} y1={y} x2={width - margin.right} y2={y} stroke="#e2e8f0" strokeWidth={0.8} />
              <text x={margin.left - 8} y={y + 3} textAnchor="end" fontSize="8.5" fill="#64748b">
                {value}
              </text>
            </g>
          );
        })}

        {chartModel.chartType === 'line' && (
          <>
            {linePaths.map((series) => (
              <g key={series.name}>
                {series.points.length >= 2 && (
                  <polyline
                    fill="none"
                    stroke={series.color}
                    strokeWidth={2.2}
                    points={series.polylinePoints}
                  />
                )}
                {series.points.map((point) => (
                  <circle
                    key={`${series.name}-${point.x}`}
                    cx={xForCategory(point.x)}
                    cy={yForValue(point.y)}
                    r={2.6}
                    fill={series.color}
                  />
                ))}
              </g>
            ))}
          </>
        )}

        {chartModel.chartType !== 'line' && (
          <>
            {barGroups.map((series, seriesIndex) => (
              <g key={series.name}>
                {series.values.map((value, categoryIdx) => {
                  if (value === undefined) return null;
                  const barHeight = (value / chartModel.maxY) * plotHeight;
                  const x = margin.left + categoryIdx * categoryWidth + (seriesIndex + 0.5) * barWidth;
                  const y = margin.top + plotHeight - barHeight;
                  return (
                    <rect
                      key={`${series.name}-${categoryIdx}`}
                      x={x}
                      y={y}
                      width={barWidth}
                      height={barHeight}
                      rx={1.5}
                      fill={series.color}
                    />
                  );
                })}
              </g>
            ))}
          </>
        )}

        {chartModel.categories.map((label, idx) => (
          <text
            key={label}
            x={chartModel.categories.length === 1 ? margin.left + plotWidth / 2 : margin.left + (idx / (chartModel.categories.length - 1)) * plotWidth}
            y={height - 43}
            textAnchor="middle"
            fontSize="9"
            fill="#475569"
          >
            {label}
          </text>
        ))}

        <text x={width / 2} y={height - 16} textAnchor="middle" fontSize="10" fill="#475569">
          {chartModel.xLabel}
        </text>
      </svg>

      <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-zinc-600">
        {chartModel.series.map((series, idx) => (
          <div key={series.name} className="flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: palette[idx % palette.length] }} />
            <span>{series.name}</span>
          </div>
        ))}
      </div>

      {chartModel.insights.length > 0 && (
        <ul className="mt-3 list-disc pl-5 text-xs text-zinc-600 space-y-1">
          {chartModel.insights.map((insight, idx) => (
            <li key={`${insight}-${idx}`}>{insight}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
