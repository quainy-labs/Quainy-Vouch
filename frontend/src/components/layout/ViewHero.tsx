import type { ViewItem } from "../../types";

type ViewHeroProps = {
  view: ViewItem;
};

export function ViewHero({ view }: ViewHeroProps) {
  return (
    <section className="view-hero">
      <div>
        <p className="eyebrow">{view.eyebrow}</p>
        <h2>{view.title}</h2>
        <p>{view.description}</p>
      </div>
      <span>{view.badge}</span>
    </section>
  );
}
