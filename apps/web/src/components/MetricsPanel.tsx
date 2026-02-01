interface MetricsPanelProps {
  metrics: any | null;
}

const MetricsPanel = ({ metrics }: MetricsPanelProps) => {
  if (!metrics) {
    return (
      <div className="panel">
        <div className="panel-header">
          <h3>Metrics</h3>
        </div>
        <p>Waiting for metrics...</p>
      </div>
    );
  }

  const teamA = Math.round(metrics.summary.team_possession.A * 100);
  const teamB = Math.round(metrics.summary.team_possession.B * 100);

  return (
    <div className="panel">
      <div className="panel-header">
        <h3>Metrics</h3>
        <span>Summary</span>
      </div>
      <div className="metrics-grid">
        <div className="metric">
          <span>Players</span>
          <strong>{metrics.summary.player_count}</strong>
        </div>
        <div className="metric">
          <span>Possession</span>
          <strong>{teamA}% / {teamB}%</strong>
        </div>
        <div className="metric">
          <span>Avg speed</span>
          <strong>{metrics.summary.avg_speed_mps} m/s</strong>
        </div>
      </div>
      <div className="panel-sub">
        <h4>Top distance</h4>
        <div className="player-list">
          {metrics.players.slice(0, 5).map((player: any) => (
            <div key={player.id} className="player-row">
              <span>{player.id}</span>
              <span>{player.distance_m} m</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default MetricsPanel;
