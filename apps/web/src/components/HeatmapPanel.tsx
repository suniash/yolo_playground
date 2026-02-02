interface HeatmapPanelProps {
  metrics: any | null;
}

const colorForValue = (value: number, max: number) => {
  if (max === 0) return "rgba(14, 116, 144, 0.08)";
  const intensity = value / max;
  const alpha = 0.15 + intensity * 0.75;
  return `rgba(14, 116, 144, ${alpha.toFixed(2)})`;
};

const HeatmapGrid = ({ title, grid }: { title: string; grid: number[][] }) => {
  const max = Math.max(...grid.flat());
  return (
    <div className="heatmap-block">
      <div className="heatmap-title">{title}</div>
      <div className="heatmap-grid">
        {grid.flat().map((value, index) => (
          <div
            key={`${title}-${index}`}
            className="heatmap-cell"
            style={{ background: colorForValue(value, max) }}
          />
        ))}
      </div>
    </div>
  );
};

const HeatmapPanel = ({ metrics }: HeatmapPanelProps) => {
  if (!metrics) {
    return (
      <div className="panel">
        <div className="panel-header">
          <h3>Heatmaps</h3>
        </div>
        <p>Waiting for heatmap data...</p>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <h3>Heatmaps</h3>
        <span>Team movement</span>
      </div>
      <div className="heatmap-layout">
        <HeatmapGrid title="Team A" grid={metrics.heatmaps.teams.A} />
        <HeatmapGrid title="Team B" grid={metrics.heatmaps.teams.B} />
      </div>
    </div>
  );
};

export default HeatmapPanel;
