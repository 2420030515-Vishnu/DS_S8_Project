import { CalendarDays, RotateCcw } from 'lucide-react'

export default function Filters({ start, end, min, max, onChange, onReset, label = 'Date range' }) {
  return <div className="date-filters" aria-label={label}>
    <CalendarDays size={15} aria-hidden="true"/>
    <label><span>From</span><input aria-label="Start date" type="date" value={start || ''} min={min || ''} max={end || max || ''} onChange={event => onChange({ start: event.target.value, end })}/></label>
    <label><span>To</span><input aria-label="End date" type="date" value={end || ''} min={start || min || ''} max={max || ''} onChange={event => onChange({ start, end: event.target.value })}/></label>
    <button className="filter-reset" type="button" onClick={onReset} title="Reset date range" aria-label="Reset date range"><RotateCcw size={14}/></button>
  </div>
}
