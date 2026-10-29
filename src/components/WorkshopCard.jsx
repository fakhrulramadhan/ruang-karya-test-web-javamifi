import { dateLabel, money } from '../lib/api';

export function WorkshopCard({ workshop, index, onSelect }) {
  return (
    <article className="workshop-card" onClick={() => onSelect(workshop)}>
      <div className="workshop-image">
        <img src={workshop.image} alt={workshop.title} />
        <span className="stamp">0{index + 1} / {workshop.category}</span>
      </div>
      <div className="workshop-copy">
        <div className="meta-row"><span>{workshop.location}</span><span>{dateLabel(workshop.date)}</span></div>
        <h3>{workshop.title}</h3>
        <p>{workshop.description}</p>
        <div className="card-bottom"><strong>{money(workshop.price)}</strong><span>{workshop.available} kursi <b>↗</b></span></div>
      </div>
    </article>
  );
}
