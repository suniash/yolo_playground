interface CalibrationPointDraft {
  image_x: string;
  image_y: string;
  field_x: string;
  field_y: string;
}

interface CalibrationEditorProps {
  points: CalibrationPointDraft[];
  onUpdate: (index: number, point: CalibrationPointDraft) => void;
  onAdd: () => void;
  onRemove: (index: number) => void;
  onSave: () => void;
  saving: boolean;
  error: string | null;
}

const CalibrationEditor = ({
  points,
  onUpdate,
  onAdd,
  onRemove,
  onSave,
  saving,
  error,
}: CalibrationEditorProps) => {
  return (
    <div className="panel">
      <div className="panel-header">
        <h3>Calibration</h3>
        <button className="btn-secondary" type="button" onClick={onAdd}>
          Add point
        </button>
      </div>
      <p className="helper">
        Add reference points to map image coordinates to field coordinates.
      </p>
      <div className="calibration-grid">
        {points.map((point, index) => (
          <div className="calibration-row" key={`pt-${index}`}>
            <input
              type="number"
              value={point.image_x}
              placeholder="Image X"
              onChange={(event) =>
                onUpdate(index, { ...point, image_x: event.target.value })
              }
            />
            <input
              type="number"
              value={point.image_y}
              placeholder="Image Y"
              onChange={(event) =>
                onUpdate(index, { ...point, image_y: event.target.value })
              }
            />
            <input
              type="number"
              value={point.field_x}
              placeholder="Field X"
              onChange={(event) =>
                onUpdate(index, { ...point, field_x: event.target.value })
              }
            />
            <input
              type="number"
              value={point.field_y}
              placeholder="Field Y"
              onChange={(event) =>
                onUpdate(index, { ...point, field_y: event.target.value })
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
        {saving ? "Saving..." : "Save calibration"}
      </button>
    </div>
  );
};

export default CalibrationEditor;
export type { CalibrationPointDraft };
