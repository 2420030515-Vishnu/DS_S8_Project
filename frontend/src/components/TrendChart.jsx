import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { compactNumber, formatDate, formatNumber } from '../lib/api'

export default function TrendChart({ data = [], dateKey = 'Date', metricKey = 'Daily Confirmed', title = 'Daily confirmed cases', subtitle = 'NATIONAL TIME SERIES', color = '#218f9b', cumulative = false }) {
  return <article className="panel trend-panel">
    <div className="panel-head"><div><span className="eyebrow">{subtitle}</span><h3>{title}</h3></div><span className="legend-dot teal-dot">{metricKey}</span></div>
    <div className="chart-area">{data.length ? <ResponsiveContainer width="100%" height="100%"><AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}><defs><linearGradient id={`fill-${metricKey.replaceAll(/[^a-z0-9]/gi, '')}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={color} stopOpacity={.2}/><stop offset="100%" stopColor={color} stopOpacity={0}/></linearGradient></defs><CartesianGrid vertical={false} stroke="#edf1f4"/><XAxis dataKey={dateKey} tickFormatter={date => new Date(date).toLocaleDateString('en-IN', { month: 'short', year: '2-digit', timeZone: 'UTC' })} minTickGap={42} tickLine={false} axisLine={false}/><YAxis tickFormatter={compactNumber} tickLine={false} axisLine={false} width={48} label={{ value: cumulative ? 'Cumulative records' : 'Reported count', angle: -90, position: 'insideLeft', style: { fill: '#929eaa', fontSize: 9 } }}/><Tooltip labelFormatter={formatDate} formatter={value => [formatNumber(value), metricKey]} contentStyle={{ borderRadius: 10, border: '1px solid #e8edf0', boxShadow: '0 8px 24px #18325012' }}/><Area type="monotone" dataKey={metricKey} stroke={color} strokeWidth={2.3} fill={`url(#fill-${metricKey.replaceAll(/[^a-z0-9]/gi, '')})`} connectNulls={false}/></AreaChart></ResponsiveContainer> : <EmptyState text="No records are available for this date range."/>}</div>
    <div className="chart-foot"><span>{cumulative ? 'Cumulative source values' : 'Daily reported observations'}</span><span>{data.length ? `${formatDate(data[0][dateKey])} – ${formatDate(data.at(-1)[dateKey])}` : 'No dates in range'}</span></div>
  </article>
}

export function EmptyState({ text }) { return <div className="empty-state"><span>{text}</span></div> }
