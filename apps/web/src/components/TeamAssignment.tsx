interface PlayerItem {
  id: string;
  team?: string | null;
}

interface TeamAssignmentProps {
  players: PlayerItem[];
  overrides: Record<string, string>;
  onChange: (playerId: string, team: string | null) => void;
  onSave: () => void;
  saving: boolean;
  error: string | null;
}

const TeamAssignment = ({
  players,
  overrides,
  onChange,
  onSave,
  saving,
  error,
}: TeamAssignmentProps) => {
  return (
    <div className="panel">
      <div className="panel-header">
        <h3>Team assignment</h3>
      </div>
      <p className="helper">
        Override auto clustering for specific players. Save will re-run analytics.
      </p>
      <div className="team-list">
        {players.map((player) => {
          const override = overrides[player.id];
          return (
            <div key={player.id} className="team-row">
              <div>
                <strong>{player.id}</strong>
                <div className="team-meta">Auto: {player.team ?? "A"}</div>
              </div>
              <select
                value={override ?? "auto"}
                onChange={(event) => {
                  const value = event.target.value;
                  onChange(player.id, value === "auto" ? null : value);
                }}
              >
                <option value="auto">Auto</option>
                <option value="A">Team A</option>
                <option value="B">Team B</option>
              </select>
            </div>
          );
        })}
      </div>
      {error && <div className="alert">{error}</div>}
      <button className="btn-primary" type="button" onClick={onSave} disabled={saving}>
        {saving ? "Saving..." : "Save team overrides"}
      </button>
    </div>
  );
};

export default TeamAssignment;
