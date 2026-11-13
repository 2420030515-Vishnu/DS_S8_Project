export default function Insights({ items }) {
  return <section className="insight-grid">{items.length ? items.map((item, index) => { const Icon = item.icon; return <article className="insight-card" key={`${item.title}-${index}`}><span className={`insight-symbol ${item.tone}`}><Icon size={16}/></span><div><b>{item.title}</b><p>{item.text}</p></div></article> }) : <p className="muted">No insights can be calculated for this date range.</p>}</section>
}
