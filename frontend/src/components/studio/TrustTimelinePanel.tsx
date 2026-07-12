export type TrustTimelineItem = {
  step: string;
  title: string;
  detail: string;
  status: "complete" | "warning" | "pending";
};

type TrustTimelinePanelProps = {
  items: TrustTimelineItem[];
};

export function TrustTimelinePanel({ items }: TrustTimelinePanelProps) {
  if (items.length === 0) return null;
  return (
    <section className="panel band trust-timeline-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Trust History</p>
          <h2>Why this artifact is reviewable</h2>
        </div>
        <span className="platform-count">{items.length} signals</span>
      </div>
      <div className="trust-timeline">
        {items.map((item, index) => (
          <article className={`trust-step ${item.status}`} key={`${item.step}-${index}-${item.title}`}>
            <span>{item.step}</span>
            <strong>{item.title}</strong>
            <p>{item.detail}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
