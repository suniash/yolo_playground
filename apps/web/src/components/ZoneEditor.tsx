interface ZoneDraft {
  id: string;
  name: string;
  points: string;
}

interface ZoneEditorProps {
  zones: ZoneDraft[];
  onUpdate: (index: number, zone: ZoneDraft) => void;
  onAdd: () => void;
  onRemove: (index: number) => void;
  onSave: () => void;
  saving: boolean;
  error: string | null;
}

const ZoneEditor = ({
  zones,
  onUpdate,
  onAdd,
  onRemove,
  onSave,
  saving,
  error,
}: ZoneEditorProps) => {
  return (
    <div className="panel">
      <div className="panel-header">
        <h3>Zones</h3>
        <button className="btn-secondary" type="button" onClick={onAdd}>
          Add zone
        </button>
      </div>
      <p className="helper">
        Define zones as image coordinates like 120,80; 320,80; 320,220; 120,220.
      </p>
      <div className="zone-list">
        {zones.map((zone, index) => (
          <div className="zone-row" key={zone.id}>
            <input
              type="text"
              value={zone.name}
              placeholder="Zone name"
              onChange={(event) =>
                onUpdate(index, { ...zone, name: event.target.value })
              }
            />
            <input
              type="text"
              value={zone.points}
              placeholder="x,y; x,y; x,y"
              onChange={(event) =>
                onUpdate(index, { ...zone, points: event.target.value })
              }
            />
            <button
              className="btn-secondary"
              type="button"
              onClick={() => onRemove(index)}
            >
              Remove
            </button>
          </div>
        ))}
      </div>
      {error && <div className="alert">{error}</div>}
      <button className="btn-primary" type="button" onClick={onSave} disabled={saving}>
        {saving ? "Saving..." : "Save zones"}
      </button>
    </div>
  );
};

export default ZoneEditor;
export type { ZoneDraft };
