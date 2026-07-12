import type React from "react";

type InsightListProps = {
  title: string;
  icon: React.ReactNode;
  items: string[];
};

export function InsightList({ title, icon, items }: InsightListProps) {
  return (
    <section className="panel compact">
      <div className="panel-title">
        {icon}
        <h2>{title}</h2>
      </div>
      <ul className="plain-list">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}
