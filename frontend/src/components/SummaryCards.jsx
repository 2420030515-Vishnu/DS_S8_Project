import { Activity, HeartPulse, TestTubes, TrendingDown } from 'lucide-react'
import { compactNumber, formatDate } from '../lib/api'

const cards = [
  { label: 'CONFIRMED CASES', key: 'Total Confirmed', icon: HeartPulse, tone: 'blue' },
  { label: 'RECOVERED', key: 'Total Recovered', icon: Activity, tone: 'green' },
  { label: 'REPORTED DEATHS', key: 'Total Deceased', icon: TrendingDown, tone: 'rose' },
]

function StatCard({ label, value, note, icon: Icon, tone }) {
  return <article className="stat-card"><div className="stat-top"><span>{label}</span><span className={`stat-icon ${tone}`}><Icon size={17}/></span></div><strong>{compactNumber(value)}</strong><small>{note}</small></article>
}

export default function SummaryCards({ national, testing, range }) {
  const selectRange = (rows, dateKey) => (rows || []).filter(row =>
    (!range?.start || !row[dateKey] || row[dateKey] >= range.start) &&
    (!range?.end || !row[dateKey] || row[dateKey] <= range.end))
  const nationalRows = selectRange(national?.trend, 'Date')
  const latest = nationalRows.at(-1) || {}
  const test = selectRange(testing?.trend, 'Tested As Of').at(-1)
  const selectedDate = latest.Date ? `Cumulative through ${formatDate(latest.Date)}` : 'No observation in selected period'
  return <section className="stats-grid" aria-label="Archive summary metrics">
    {cards.map(card => <StatCard key={card.key} {...card} value={latest[card.key]} note={selectedDate}/>) }
    <StatCard label="SAMPLES TESTED" value={test?.['Total Samples Tested']} note={test ? `Selected period through ${formatDate(test['Tested As Of'])}` : 'No testing observation in selected period'} icon={TestTubes} tone="violet"/>
  </section>
}
