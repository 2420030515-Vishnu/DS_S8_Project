import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { compactNumber, formatNumber } from '../lib/api'
import { EmptyState } from './TrendChart'

export default function RegionChart({ data = [], nameKey = 'State', valueKey = 'Confirmed', title = 'State comparison', subtitle = 'LATEST STATE SNAPSHOT', onExplore }) {
  const chartData = data.slice(0, 10)
  return <article className="panel region-panel"><div className="panel-head"><div><span className="eyebrow">{subtitle}</span><h3>{title}</h3></div>{onExplore && <button className="text-btn" onClick={onExplore}>View all <span>→</span></button>}</div>
    <div className="chart-area region-chart">{chartData.length ? <ResponsiveContainer width="100%" height="100%"><BarChart data={chartData} margin={{ top: 8, right: 9, bottom: 5, left: 0 }}><CartesianGrid vertical={false} stroke="#edf1f4"/><XAxis dataKey={nameKey} interval={0} tickFormatter={value => value.length > 11 ? `${value.slice(0, 10)}…` : value} tickLine={false} axisLine={false} tick={{ fontSize: 9 }}/><YAxis tickFormatter={compactNumber} tickLine={false} axisLine={false} width={45}/><Tooltip formatter={value => [formatNumber(value), valueKey]} labelStyle={{ color: '#34465a' }}/><Bar dataKey={valueKey} radius={[4, 4, 0, 0]}>{chartData.map((_, index) => <Cell key={index} fill={index === 0 ? '#218f9b' : '#8dc4c8'}/>)}</Bar></BarChart></ResponsiveContainer> : <EmptyState text="State comparison is not available."/>}</div>
    <div className="chart-foot">{valueKey} · same unit across regions</div>
  </article>
}
