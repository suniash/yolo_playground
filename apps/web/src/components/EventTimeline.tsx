interface EventTimelineProps {
  events: Array<{
    id: string;
    type: string;
    start: number;
    end: number;
    frame: number;
    confidence: number;
    explanation: string;
    involved?: string[];
  }>;
  onSelect: (time: number) => void;
}

const EventTimeline = ({ events, onSelect }: EventTimelineProps) => {
  return (
    <div className="panel">
      <div className="panel-header">
        <h3>Timeline</h3>
        <span>{events.length} events</span>
      </div>
      <div className="timeline">
        {events.map((event) => (
          <button
            key={event.id}
            className="timeline-item"
            type="button"
            onClick={() => onSelect(event.start)}
          >
            <div>
              <strong>{event.type.replace(/_/g, " ")}</strong>
              <div className="timeline-meta">{event.explanation}</div>
            </div>
            <div className="timeline-time">{event.start.toFixed(1)}s</div>
          </button>
        ))}
      </div>
    </div>
  );
};

export default EventTimeline;
