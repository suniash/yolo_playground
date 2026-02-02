interface PlayerRosterProps {
  metrics: any | null;
}

const PlayerRoster = ({ metrics }: PlayerRosterProps) => {
  if (!metrics) {
    return (
      <div className="panel">
        <div className="panel-header">
          <h3>Players</h3>
        </div>
        <p>Waiting for player metrics...</p>
      </div>
    );
  }

  const players = [...metrics.players].sort(
    (a, b) => b.distance_m - a.distance_m
  );

  return (
    <div className="panel">
      <div className="panel-header">
        <h3>Players</h3>
        <span>{players.length} tracked</span>
      </div>
      <div className="player-cards">
        {players.slice(0, 10).map((player) => (
          <div key={player.id} className="player-card">
            <div>
              <strong>{player.id}</strong>
              <div className="player-meta">Team {player.team}</div>
            </div>
            <div className="player-stats">
              <span>{player.distance_m} m</span>
              <span>{player.avg_speed_mps} m/s</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default PlayerRoster;
