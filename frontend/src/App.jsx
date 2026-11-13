import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Activity, ArrowDownRight, ArrowUpRight, BarChart3, BookOpen, ChevronDown, Clock3, Database, Download, FileSearch, FlaskConical, HeartPulse, LayoutDashboard, LogOut, Menu, Search, Settings2, ShieldCheck, TestTubes, Users, X } from 'lucide-react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import AuthScreen from './components/AuthScreen'
import Filters from './components/Filters'
import Insights from './components/Insights'
import RegionChart from './components/RegionChart'
import SummaryCards from './components/SummaryCards'
import TrendChart, { EmptyState } from './components/TrendChart'
import { api, compactNumber, downloadCsv, formatDate, formatNumber, loadDataset } from './lib/api'
import './App.css'
import './design.css'

const pages = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'national', label: 'National analytics', icon: Activity },
  { id: 'states', label: 'State analytics', icon: BarChart3 },
  { id: 'districts', label: 'District analytics', icon: Users },
  { id: 'testing', label: 'Testing analytics', icon: TestTubes },
  { id: 'explorer', label: 'Data explorer', icon: FileSearch },
  { id: 'insights', label: 'Insights & reports', icon: FlaskConical },
  { id: 'methodology', label: 'Methodology', icon: BookOpen },
  { id: 'profile', label: 'Profile & settings', icon: Settings2 },
]
const metricFields = ['Confirmed', 'Recovered', 'Deceased']
const asNumber = value => value == null || value === '' ? null : Number(String(value).replaceAll(',', '').replace('%', ''))
const filterDates = (rows, range, key = 'Date') => (rows || []).filter(row => (!range.start || !row[key] || row[key] >= range.start) && (!range.end || !row[key] || row[key] <= range.end))
const pathPage = () => window.location.hash.replace(/^#\/?/, '').split('/')[0] || 'overview'
const datasetOptions = [
  { id: 'national', label: 'National daily' }, { id: 'states', label: 'State daily' },
  { id: 'districts', label: 'District latest' }, { id: 'testing', label: 'Testing daily' }, { id: 'testing_states', label: 'Testing by state' },
]

function Loading({ text = 'Loading archive records…' }) { return <div className="loading-panel"><span className="spinner"/>{text}</div> }
function ErrorNotice({ error, retry }) { return error && <div className="error-banner" role="alert"><b>Unable to load this data.</b><span>{error}</span>{retry && <button type="button" onClick={retry}>Retry</button>}</div> }
function PanelTitle({ eyebrow, title, aside }) { return <div className="panel-head"><div><span className="eyebrow">{eyebrow}</span><h3>{title}</h3></div>{aside}</div> }
function MetricTable({ columns, rows, empty = 'No records match these filters.', onSort, sortKey, direction = 'asc', maxHeight }) {
  return <div className="table-panel panel"><div className="table-scroll" style={maxHeight ? { maxHeight } : undefined}><table><thead><tr>{columns.map(col => <th key={col.key} aria-sort={sortKey === col.key ? (direction === 'asc' ? 'ascending' : 'descending') : 'none'}>{onSort ? <button type="button" className="sort-head" aria-label={`Sort by ${col.label}${sortKey === col.key ? `, ${direction === 'asc' ? 'ascending' : 'descending'}` : ''}`} onClick={() => onSort(col.key)}>{col.label}{sortKey === col.key && <span aria-hidden="true">{direction === 'asc' ? '↑' : '↓'}</span>}</button> : col.label}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={row.id ?? `${row.State || row.State_Name || ''}-${row.District || ''}-${row.Date || ''}-${index}`}>{columns.map(col => <td key={col.key}>{col.render ? col.render(row[col.key], row) : row[col.key] == null || row[col.key] === '' ? '—' : typeof row[col.key] === 'number' ? formatNumber(row[col.key]) : String(row[col.key])}</td>)}</tr>)}</tbody></table>{!rows.length && <EmptyState text={empty}/>}</div></div>
}

function NationalPage({ data, range, setRange, meta, loading }) {
  const trend = useMemo(() => filterDates(data?.trend, range), [data, range])
  const metrics = [
    ['Daily Confirmed', 'Daily confirmed'], ['Daily Recovered', 'Daily recovered'], ['Daily Deceased', 'Daily deceased'],
    ['Total Confirmed', 'Cumulative confirmed'], ['Total Recovered', 'Cumulative recovered'], ['Total Deceased', 'Cumulative deceased'],
  ]
  const [metric, setMetric] = useState(metrics[0][0])
  const selected = metrics.find(item => item[0] === metric) || metrics[0]
  const cumulative = metric.startsWith('Total')
  const days = trend.length
  const latestRow = trend.at(-1)
  const previousRow = trend.at(-2)
  const delta = latestRow && previousRow ? asNumber(latestRow[metric]) - asNumber(previousRow[metric]) : null
  return <>
    <div className="filter-row"><Filters start={range.start} end={range.end} min={data?.trend?.[0]?.Date} max={data?.trend?.at(-1)?.Date} onChange={setRange} onReset={() => setRange({ start: data?.trend?.[0]?.Date || '', end: data?.trend?.at(-1)?.Date || '' })}/><span className="range-note">Showing {days} of the latest {data?.trend?.length || 0} returned observations</span></div>
    {loading ? <Loading/> : <>
      <article className="panel national-chart-panel"><div className="panel-head"><div><span className="eyebrow">NATIONAL TIME SERIES</span><h3>{selected[1]}</h3></div><label className="compact-select">Metric<select value={metric} onChange={event => setMetric(event.target.value)}>{metrics.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select><ChevronDown size={14}/></label></div>
        <div className="chart-area tall">{trend.length ? <ResponsiveContainer width="100%" height="100%"><AreaChart data={trend}><defs><linearGradient id="national-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#218f9b" stopOpacity={.23}/><stop offset="100%" stopColor="#218f9b" stopOpacity={0}/></linearGradient></defs><CartesianGrid vertical={false} stroke="#edf1f4"/><XAxis dataKey="Date" tickFormatter={date => new Date(date).toLocaleDateString('en-IN', { month: 'short', year: '2-digit', timeZone: 'UTC' })} minTickGap={38} tickLine={false} axisLine={false}/><YAxis tickFormatter={compactNumber} tickLine={false} axisLine={false} width={53} label={{ value: cumulative ? 'Cumulative records' : 'Daily reported cases', angle: -90, position: 'insideLeft', style: { fill: '#929eaa', fontSize: 9 } }}/><Tooltip labelFormatter={formatDate} formatter={value => [formatNumber(value), selected[1]]}/><Legend/><Area name={selected[1]} type="monotone" dataKey={metric} stroke="#218f9b" strokeWidth={2.2} fill="url(#national-fill)"/></AreaChart></ResponsiveContainer> : <EmptyState text="No national observations in this date range. The API provides the latest 500 rows."/>}</div>
        <div className="chart-foot"><span>{cumulative ? 'Cumulative values as recorded in source' : 'Daily values as reported in source'}</span><span>{trend.length ? `${formatDate(trend[0].Date)} – ${formatDate(trend.at(-1).Date)}` : 'No dates in selected range'}</span></div>
      </article>
      <div className="two-column-grid"><article className="panel"><PanelTitle eyebrow="RECENT RECORDS" title="Latest observations"/><MetricTable columns={[{ key: 'Date', label: 'DATE', render: value => formatDate(value) }, { key: 'Daily Confirmed', label: 'DAILY CONFIRMED' }, { key: 'Daily Recovered', label: 'DAILY RECOVERED' }, { key: 'Daily Deceased', label: 'DAILY DECEASED' }]} rows={[...trend].slice(-8).reverse()} empty="No national records available." maxHeight="330px"/></article><article className="panel note-panel"><PanelTitle eyebrow="INTERPRETATION" title="How to read this series"/><p>Daily measures are reported values from the national archive. Cumulative measures are displayed only when the source provides them. They are not recalculated from state snapshots.</p><p><b>Coverage:</b> {formatDate(meta?.date_range?.start)} – {formatDate(meta?.date_range?.end)}.</p><p><b>Returned window:</b> {days} observations. The endpoint currently supplies up to 500 rows; dates outside that returned window cannot be charted by this frontend.</p>{delta != null && <div className="small-stat"><span>Latest one-record change in {selected[1]}</span><b>{delta >= 0 ? '+' : ''}{formatNumber(delta)}</b></div>}</article></div>
    </>}
  </>
}

function StatePage({ latest, dateRange, range, setRange, history, historyLoading, historyError, onRetry }) {
  const states = useMemo(() => latest?.regions || [], [latest])
  const [selected, setSelected] = useState([])
  const [metric, setMetric] = useState('Confirmed')
  const [search, setSearch] = useState('')
  const [stateQuery, setStateQuery] = useState('')
  const [comparisonData, setComparisonData] = useState(null)
  const [comparisonError, setComparisonError] = useState('')
  const columns = history?.columns || []
  const stateColumn = columns.includes('State_Name') ? 'State_Name' : 'State'
  const dateColumn = columns.includes('Date') ? 'Date' : null
  const historyDates = (history?.rows || []).map(row => row[dateColumn]).filter(Boolean).sort()
  const coverage = dateRange || { start: historyDates[0], end: historyDates.at(-1) }
  const stateNames = useMemo(() => states.map(row => row.State).filter(Boolean), [states])
  const visibleStateNames = stateNames.filter(name => name.toLowerCase().includes(stateQuery.trim().toLowerCase()))
  const comparisonLimit = 10
  const historyRows = useMemo(() => {
    const chosen = history?.rows || []
    return chosen.filter(row => selected.includes(row[stateColumn]) && (!range.start || !row[dateColumn] || row[dateColumn] >= range.start) && (!range.end || !row[dateColumn] || row[dateColumn] <= range.end))
      .map(row => ({ ...row, __label: row[stateColumn], __date: row[dateColumn], __value: asNumber(row[metric]) }))
      .filter(row => row.__date && row.__value != null)
  }, [history, selected, stateColumn, dateColumn, range, metric])
  const chartRows = useMemo(() => {
    const byDate = new Map()
    historyRows.forEach(row => { const current = byDate.get(row.__date) || { Date: row.__date }; current[row.__label] = row.__value; byDate.set(row.__date, current) })
    return [...byDate.values()].sort((a, b) => a.Date.localeCompare(b.Date))
  }, [historyRows])
  useEffect(() => {
    if (!selected.length) return
    const controller = new AbortController()
    const params = new URLSearchParams({ states: selected.join(','), metric })
    if (range.start) params.set('start', range.start)
    if (range.end) params.set('end', range.end)
    const comparisonKey = `${selected.join('|')}|${metric}|${range.start}|${range.end}`
    api(`/analytics/state-comparison?${params}`, { signal: controller.signal })
      .then(result => { if (!controller.signal.aborted) setComparisonData({ key: comparisonKey, rows: result.rows || [] }) })
      .catch(error => { if (error.name !== 'AbortError' && !controller.signal.aborted) setComparisonError({ key: comparisonKey, message: error.message }) })
    return () => controller.abort()
  }, [selected, metric, range.start, range.end])
  const filteredStates = states.filter(row => row.State?.toLowerCase().includes(search.toLowerCase()))
  return <>
    <div className="filter-row"><Filters start={range.start} end={range.end} min={coverage?.start} max={coverage?.end} onChange={setRange} onReset={() => setRange({ start: coverage?.start || '', end: coverage?.end || '' })}/><span className="range-note">State history: {formatDate(coverage?.start)} – {formatDate(coverage?.end)}</span></div>
    <div className="panel state-controls"><div className="state-control-heading"><div><span className="eyebrow">COMPARE REGIONS</span><h3>Select states and a shared measure</h3></div><div className="state-control-actions"><span className="selection-count" aria-live="polite">{selected.length} of {comparisonLimit} selected</span><button className="outline-btn" type="button" onClick={() => setSelected([])} disabled={!selected.length}>Clear selection</button><label className="compact-select">Measure<select aria-label="State comparison measure" value={metric} onChange={event => setMetric(event.target.value)}>{metricFields.map(value => <option key={value}>{value}</option>)}</select><ChevronDown size={14}/></label></div></div>
      <div className="state-picker-toolbar"><div className="search-field"><Search size={16} aria-hidden="true"/><input aria-label="Search states to compare" placeholder="Find a state or union territory" value={stateQuery} onChange={event => setStateQuery(event.target.value)}/></div><span className="micro-note">Choose up to {comparisonLimit} regions.</span></div>
      <div className="state-select-grid" role="group" aria-label="States to compare">{visibleStateNames.map(name => { const checked = selected.includes(name); return <label className={`check-pill ${checked ? 'selected' : ''}`} key={name}><input type="checkbox" aria-label={`Compare ${name}`} checked={checked} disabled={!checked && selected.length >= comparisonLimit} onChange={event => setSelected(previous => event.target.checked ? [...previous, name] : previous.filter(item => item !== name))}/><span>{name}</span></label> })}{!visibleStateNames.length && <p className="empty-inline">No states match that search.</p>}</div><p className="micro-note">Comparisons use the same source field ({metric}) and selected date range. Values are cumulative source observations; state testing totals are not part of this cases dataset.</p>
    </div>
    {historyLoading ? <Loading text="Loading state history from the archive…"/> : <ErrorNotice error={historyError} retry={onRetry}/>}
    <article className="panel national-chart-panel"><PanelTitle eyebrow="STATE HISTORY" title={`${metric} over time`}/><div className="chart-area tall">{historyRows.length && selected.length ? <ResponsiveContainer width="100%" height="100%"><LineChart data={chartRows}><CartesianGrid vertical={false} stroke="#edf1f4"/><XAxis dataKey="Date" tickFormatter={value => new Date(value).toLocaleDateString('en-IN', { month: 'short', year: '2-digit', timeZone: 'UTC' })} minTickGap={40} tickLine={false} axisLine={false}/><YAxis tickFormatter={compactNumber} tickLine={false} axisLine={false}/><Tooltip labelFormatter={formatDate} formatter={(value, name) => [formatNumber(value), name]}/><Legend/>{selected.map((name, index) => <Line key={name} type="monotone" dataKey={name} dot={false} strokeWidth={2} stroke={['#218f9b', '#4873d1', '#c27c46', '#9172bb', '#64a27e'][index % 5]} connectNulls/> )}</LineChart></ResponsiveContainer> : <EmptyState text={selected.length ? 'No state records in this range.' : 'Select one or more states to compare their time series.'}/>}</div><div className="chart-foot"><span>Source: state_level_daily.csv · cumulative source observations</span><span>{historyRows.length} matching observations</span></div></article>
    {!!selected.length && <><ErrorNotice error={comparisonError?.key === `${selected.join('|')}|${metric}|${range.start}|${range.end}` ? comparisonError.message : ''}/><article className="panel"><PanelTitle eyebrow="DATE-ALIGNED COMPARISON" title={`${metric} at each state's latest observation in the selected period`}/>{comparisonData?.key !== `${selected.join('|')}|${metric}|${range.start}|${range.end}` && comparisonError?.key !== `${selected.join('|')}|${metric}|${range.start}|${range.end}` ? <Loading text="Aligning state observations to the selected dates…"/> : <MetricTable columns={[{ key: 'State', label: 'STATE / UT' }, { key: 'value', label: metric.toUpperCase() }, { key: 'observation_date', label: 'OBSERVATION DATE', render: formatDate }]} rows={comparisonData?.key === `${selected.join('|')}|${metric}|${range.start}|${range.end}` ? comparisonData.rows : []} empty="No selected state has an observation in this period."/>}</article></>}
    <div className="toolbar"><div className="search-field"><Search size={15} aria-hidden="true"/><input aria-label="Search state snapshots" placeholder="Search state / UT" value={search} onChange={event => setSearch(event.target.value)}/></div><span className="result-count">{filteredStates.length} latest state snapshots</span></div>
    <MetricTable columns={[{ key: 'State', label: 'STATE / UT' }, { key: 'Confirmed', label: 'CONFIRMED' }, { key: 'Active', label: 'ACTIVE' }, { key: 'Recovered', label: 'RECOVERED' }, { key: 'Deaths', label: 'DEATHS' }, { key: 'Last_Updated_Time', label: 'LAST UPDATED' }]} rows={filteredStates} empty="No states match the search."/>
  </>
}

function DistrictPage({ districts }) {
  const [state, setState] = useState('')
  const [district, setDistrict] = useState('')
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState({ key: 'Confirmed', direction: 'desc' })
  const all = useMemo(() => districts?.regions || [], [districts])
  const stateNames = districts?.states || []
  const districtOptions = [...new Map(all.filter(row => !state || row.State === state).map(row => [`${row.District}|${row.State}`, row])).values()].sort((a, b) => `${a.District} ${a.State}`.localeCompare(`${b.District} ${b.State}`))
  const selectedDistrict = districtOptions.find(row => `${row.District}|${row.State}` === district)
  const results = useMemo(() => all.filter(row => (!state || row.State === state) && (!district || `${row.District}|${row.State}` === district) && `${row.District || ''} ${row.State || ''}`.toLowerCase().includes(query.toLowerCase()))
    .sort((a, b) => { const av = a[sort.key], bv = b[sort.key]; const compare = Number.isFinite(Number(av)) && Number.isFinite(Number(bv)) ? Number(av) - Number(bv) : String(av || '').localeCompare(String(bv || '')); return compare * (sort.direction === 'asc' ? 1 : -1) }), [all, state, district, query, sort])
  const onSort = key => setSort(current => ({ key, direction: current.key === key && current.direction === 'desc' ? 'asc' : 'desc' }))
  return <><div className="toolbar"><label className="select-field"><span>State</span><select aria-label="Filter districts by state" value={state} onChange={event => { setState(event.target.value); setDistrict('') }}><option value="">All states / UTs</option>{stateNames.map(name => <option key={name}>{name}</option>)}</select><ChevronDown size={15}/></label><label className="select-field"><span>District</span><select aria-label="Select a district" value={district} onChange={event => setDistrict(event.target.value)}><option value="">All districts</option>{districtOptions.map(row => <option key={`${row.District}|${row.State}`} value={`${row.District}|${row.State}`}>{row.District} · {row.State}</option>)}</select><ChevronDown size={15}/></label><div className="search-field"><Search size={15} aria-hidden="true"/><input aria-label="Search district or state" placeholder="Search district or state" value={query} onChange={event => setQuery(event.target.value)}/></div><span className="result-count" aria-live="polite">{results.length} districts</span></div>{selectedDistrict && <section className="district-selected"><div className="district-selected-title"><span className="eyebrow">SELECTED DISTRICT · LATEST SNAPSHOT</span><b>{selectedDistrict.District}, {selectedDistrict.State}</b></div>{['Confirmed', 'Active', 'Recovered', 'Deceased'].map(key => <div className="district-kpi" key={key}><span>{key}</span><b>{formatNumber(selectedDistrict[key])}</b></div>)}</section>}<MetricTable columns={[{ key: 'District', label: 'DISTRICT' }, { key: 'State', label: 'STATE / UT' }, ...['Confirmed', 'Active', 'Recovered', 'Deceased'].map(key => ({ key, label: key.toUpperCase() }))]} rows={results} onSort={onSort} sortKey={sort.key} direction={sort.direction}/><p className="explorer-note"><Database size={14} aria-hidden="true"/> This source is a latest snapshot only. District-level historical trends and date filters are not available in this dataset.</p></>
}

function TestingPage({ data, stateData, range, setRange, loading, stateLoading, onRetry }) {
  const [stateMetric, setStateMetric] = useState('Total Tested')
  const available = useMemo(() => data?.trend || [], [data])
  const filtered = useMemo(() => filterDates(available, range, 'Tested As Of'), [available, range])
  const latest = filtered.at(-1)
  const chartRows = filtered.filter(row => asNumber(row['Total Samples Tested']) != null)
  const byState = stateData?.regions || []
  const stateMetricOptions = [
    ['Total Tested', 'Total tested'], ['Positive', 'Positive tests'], ['Test positivity rate', 'Reported positivity (%)'], ['Tests per million', 'Tests per million'],
  ].filter(([key]) => byState.some(row => row[key] != null))
  const rankedTesting = [...byState].filter(row => asNumber(row[stateMetric]) != null).sort((a, b) => asNumber(b[stateMetric]) - asNumber(a[stateMetric])).slice(0, 12)
  return <><div className="filter-row"><Filters start={range.start} end={range.end} min={available[0]?.['Tested As Of']} max={available.at(-1)?.['Tested As Of']} onChange={setRange} onReset={() => setRange({ start: available[0]?.['Tested As Of'] || '', end: available.at(-1)?.['Tested As Of'] || '' })}/><span className="range-note">Testing series available: {formatDate(data?.date_range?.start)} – {formatDate(data?.date_range?.end)}</span></div>
    {loading ? <Loading/> : <><div className="stats-grid"><article className="stat-card"><div className="stat-top"><span>SAMPLES TESTED</span><span className="stat-icon violet"><TestTubes size={17}/></span></div><strong>{compactNumber(latest?.['Total Samples Tested'])}</strong><small>Last available record · {formatDate(latest?.['Tested As Of'])}</small></article><article className="stat-card"><div className="stat-top"><span>INDIVIDUALS TESTED</span><span className="stat-icon blue"><Users size={17}/></span></div><strong>{compactNumber(latest?.['Total Individuals Tested'])}</strong><small>Cumulative, as recorded</small></article><article className="stat-card"><div className="stat-top"><span>POSITIVE CASES</span><span className="stat-icon rose"><HeartPulse size={17}/></span></div><strong>{compactNumber(latest?.['Total Positive Cases'])}</strong><small>From testing dataset</small></article><article className="stat-card"><div className="stat-top"><span>TEST POSITIVITY</span><span className="stat-icon green"><Activity size={17}/></span></div><strong>{latest?.['Test positivity rate'] == null ? '—' : `${latest['Test positivity rate']}%`}</strong><small>Reported rate; no cross-file calculation</small></article></div><article className="panel full-chart"><TrendChart data={chartRows} dateKey="Tested As Of" metricKey="Total Samples Tested" title="Cumulative samples tested" subtitle="NATIONAL TESTING TIMELINE" color="#7379bf" cumulative/></article></>}
    {stateLoading ? <Loading text="Loading state testing snapshots…"/> : <ErrorNotice error={stateData?.error} retry={onRetry}/>}
    <article className="panel state-testing-panel"><div className="panel-head"><div><span className="eyebrow">STATE TESTING SNAPSHOT</span><h3>Compare latest reported testing</h3></div><label className="compact-select">Measure<select value={stateMetric} onChange={event => setStateMetric(event.target.value)}>{stateMetricOptions.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select><ChevronDown size={14}/></label></div><p className="micro-note">Testing updates were reported on different dates by state. Positivity below is the source-reported rate; it is not recalculated or compared with case counts from another reporting date.</p><div className="chart-area regional-testing-chart">{rankedTesting.length ? <ResponsiveContainer width="100%" height="100%"><BarChart data={rankedTesting} margin={{ top: 10, right: 10, bottom: 6, left: 3 }}><CartesianGrid vertical={false} stroke="#edf1f4"/><XAxis dataKey="State" interval={0} tickFormatter={value => value.length > 10 ? `${value.slice(0, 9)}…` : value} tick={{ fontSize: 9 }} tickLine={false} axisLine={false}/><YAxis tickFormatter={compactNumber} tickLine={false} axisLine={false}/><Tooltip formatter={value => [formatNumber(value), stateMetricOptions.find(([key]) => key === stateMetric)?.[1] || stateMetric]}/><Bar dataKey={stateMetric} radius={[4, 4, 0, 0]}>{rankedTesting.map((row, index) => <Cell key={row.State} fill={index === 0 ? '#218f9b' : '#8dc4c8'}/>)}</Bar></BarChart></ResponsiveContainer> : <EmptyState text="No state testing measure is available from the API."/>}</div><MetricTable columns={[{ key: 'State', label: 'STATE / UT' }, { key: 'Updated On', label: 'UPDATED', render: value => formatDate(value) }, { key: 'Total Tested', label: 'TOTAL TESTED' }, { key: 'Positive', label: 'POSITIVE' }, { key: 'Test positivity rate', label: 'REPORTED POSITIVITY', render: value => value == null ? '—' : `${value}%` }, { key: 'Tests per million', label: 'TESTS / MILLION' }]} rows={byState.slice(0, 20)} empty="The API does not currently return state testing snapshots." maxHeight="400px"/></article>
  </>
}

function ExplorerPage({ dataset, setDataset, data, metadata, loading, progress, error, onRetry }) {
  const [query, setQuery] = useState('')
  const [stateFilter, setStateFilter] = useState('')
  const [districtFilter, setDistrictFilter] = useState('')
  const [dateFilter, setDateFilter] = useState('')
  const [metricFilter, setMetricFilter] = useState('')
  const [minimum, setMinimum] = useState('')
  const [sort, setSort] = useState({ key: '', direction: 'asc' })
  const [page, setPage] = useState(0)
  const [pageSize, setPageSize] = useState(25)

  const columns = useMemo(() => data?.columns || [], [data])
  const states = useMemo(() => [...new Set((data?.rows || []).map(row => row.State_Name || row.State || row['Name of State / UT']).filter(Boolean))].sort(), [data])
  const districts = useMemo(() => [...new Set((data?.rows || []).map(row => row.District).filter(Boolean))].sort(), [data])
  const dates = useMemo(() => ['Date', 'Tested As Of', 'Updated On', 'Last_Updated'].filter(key => columns.includes(key) && data?.rows?.some(row => row[key])), [columns, data])
  const metrics = useMemo(() => columns.filter(key => data?.rows?.some(row => asNumber(row[key]) != null) && !dates.includes(key) && !['SlNo', 'State_Code', 'District_Key'].includes(key)), [columns, data, dates])

  const filteredRows = useMemo(() => {
    const needle = query.toLowerCase().trim()
    const matches = (data?.rows || []).filter(row => {
      if (needle && !columns.some(column => String(row[column] ?? '').toLowerCase().includes(needle))) return false
      if (stateFilter && (row.State_Name || row.State || row['Name of State / UT']) !== stateFilter) return false
      if (districtFilter && row.District !== districtFilter) return false
      const rowDate = dates.map(key => row[key]).find(Boolean)
      if (dateFilter && rowDate && rowDate.slice(0, 10) !== dateFilter) return false
      if (metricFilter && minimum !== '' && (asNumber(row[metricFilter]) ?? -Infinity) < Number(minimum)) return false
      return true
    })
    if (sort.key) matches.sort((a, b) => {
      const av = asNumber(a[sort.key]), bv = asNumber(b[sort.key])
      const compare = av != null && bv != null
        ? av - bv
        : String(a[sort.key] ?? '').localeCompare(String(b[sort.key] ?? ''), undefined, { numeric: true })
      return compare * (sort.direction === 'asc' ? 1 : -1)
    })
    return matches
  }, [data, columns, query, stateFilter, districtFilter, dateFilter, dates, metricFilter, minimum, sort])

  const pageRows = useMemo(() => filteredRows.slice(page * pageSize, (page + 1) * pageSize), [filteredRows, page, pageSize])
  const tableColumns = useMemo(() => columns.map(key => ({ key, label: key, render: value => value == null || value === '' ? '—' : typeof value === 'number' ? formatNumber(value) : String(value) })), [columns])
  const changeDataset = value => {
    setPage(0); setQuery(''); setStateFilter(''); setDistrictFilter(''); setDateFilter('')
    setMetricFilter(''); setMinimum(''); setSort({ key: '', direction: 'asc' }); setDataset(value)
  }
  const toggleSort = key => {
    setSort(current => ({ key, direction: current.key === key && current.direction === 'asc' ? 'desc' : 'asc' }))
    setPage(0)
  }
  const exportRows = () => downloadCsv(filteredRows, columns, `arogya-${dataset}-filtered.csv`)

  return <>
    <div className="explorer-controls">
      <label className="select-field"><span>Dataset</span><select aria-label="Choose a source dataset" value={dataset} onChange={event => changeDataset(event.target.value)}>{datasetOptions.map(option => <option value={option.id} key={option.id}>{option.label}</option>)}</select><ChevronDown size={15}/></label>
      <div className="search-field"><Search size={16} aria-hidden="true"/><input aria-label="Search all dataset columns" placeholder="Search records" value={query} onChange={event => { setQuery(event.target.value); setPage(0) }}/></div>
      <button type="button" className="outline-btn" disabled={!filteredRows.length} onClick={exportRows}><Download size={15} aria-hidden="true"/> Export filtered ({filteredRows.length.toLocaleString('en-IN')})</button>
    </div>
    <div className="explorer-filter-row">
      {columns.some(key => ['State', 'State_Name', 'Name of State / UT'].includes(key)) && <label className="select-field"><span>State</span><select aria-label="Filter by state" value={stateFilter} onChange={event => { setStateFilter(event.target.value); setPage(0) }}><option value="">All states</option>{states.map(value => <option key={value}>{value}</option>)}</select><ChevronDown size={15}/></label>}
      {columns.includes('District') && <label className="select-field"><span>District</span><select aria-label="Filter by district" value={districtFilter} onChange={event => { setDistrictFilter(event.target.value); setPage(0) }}><option value="">All districts</option>{districts.map(value => <option key={value}>{value}</option>)}</select><ChevronDown size={15}/></label>}
      {dates.length > 0 && <label className="date-filter-field"><span>Date</span><input aria-label="Filter records by date" type="date" value={dateFilter} onChange={event => { setDateFilter(event.target.value); setPage(0) }}/></label>}
      {metrics.length > 0 && <><label className="select-field"><span>Metric</span><select aria-label="Choose a metric threshold" value={metricFilter} onChange={event => { setMetricFilter(event.target.value); setPage(0) }}><option value="">No threshold</option>{metrics.map(value => <option key={value}>{value}</option>)}</select><ChevronDown size={15}/></label><input className="minimum-filter" aria-label="Minimum metric value; negative values include corrections" type="number" placeholder="Minimum value" value={minimum} onChange={event => { setMinimum(event.target.value); setPage(0) }} disabled={!metricFilter}/></>}
    </div>
    {error || data?.error ? <ErrorNotice error={error || data?.error} retry={onRetry}/> : loading ? <Loading text={progress ? `Loading ${progress.loaded.toLocaleString('en-IN')} of ${progress.total.toLocaleString('en-IN')} records?` : 'Loading source records?'}/> : !data ? <div className="empty-state" role="status">Select a source dataset to load its archive records.</div> : <>
      <div className="data-meta"><b>{datasetOptions.find(option => option.id === dataset)?.label} archive</b><span>{metadata?.source || data?.source || 'Source attribution unavailable'} ? {metadata?.date_range?.start ? `${formatDate(metadata.date_range.start)} to ${formatDate(metadata.date_range.end)}` : 'Coverage dates unavailable'}</span><span aria-live="polite">{filteredRows.length.toLocaleString('en-IN')} matching of {(data?.total_rows || 0).toLocaleString('en-IN')} records ? {columns.length} columns</span></div>
      <MetricTable columns={tableColumns} rows={pageRows} onSort={toggleSort} sortKey={sort.key} direction={sort.direction} empty="No source records match these filters." maxHeight="calc(100vh - 390px)"/>
      <div className="pager" aria-label="Data explorer pagination"><span aria-live="polite">Showing {filteredRows.length ? (page * pageSize + 1).toLocaleString('en-IN') : 0}?{Math.min((page + 1) * pageSize, filteredRows.length).toLocaleString('en-IN')} of {filteredRows.length.toLocaleString('en-IN')}</span><div className="page-actions"><label>Rows per page <select aria-label="Rows per page" value={pageSize} onChange={event => { setPageSize(Number(event.target.value)); setPage(0) }}><option value={25}>25</option><option value={50}>50</option><option value={100}>100</option></select></label><button type="button" className="outline-btn" disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</button><button type="button" className="outline-btn" disabled={(page + 1) * pageSize >= filteredRows.length} onClick={() => setPage(page + 1)}>Next</button></div></div>
      {data?.truncated && <p className="micro-note">The API limits this source to 100,000 rows; the explorer loaded the available subset.</p>}
    </>}
  </>
}

function MethodologyPage({ meta }) {
  const sources = meta?.datasets || {}
  const details = [
    ['National daily', sources.national, 'Daily and cumulative confirmed, recovered, and deceased counts. The source dates omit the year; the API reconstructs sequential years beginning from the archive’s 2020 start.'],
    ['State daily', sources.states, 'Cumulative confirmed, deceased, and recovered source values by state. Daily changes can be derived by differencing adjacent cumulative observations; this may show negative revisions.'],
    ['District latest', sources.districts, 'Latest available district snapshot with confirmed, active, recovered, and deceased measures. This source does not support historical district trends.'],
    ['National testing', sources.testing, 'Reported testing counts and reported positivity over time. The positivity shown is provided by the source and is not recalculated against an unmatched case date.'],
    ['State testing', 'tests_state_wise.csv', 'State totals and reported positivity on state-specific update dates. Reporting dates differ, so values are not treated as synchronized comparisons.'],
  ]
  return <><section className="method-callout"><span className="method-icon"><ShieldCheck size={19}/></span><div><b>Historical archive, clearly labeled</b><p>Figures describe records in the source files. They are not live statistics and may include revisions, missing fields, or reporting delays.</p></div></section><div className="method-grid">{details.map(([title, file, text]) => <article className="panel method-card" key={title}><span className="eyebrow">SOURCE DATASET</span><h3>{title}</h3><code>{typeof file === 'string' ? file : file?.file || 'Not reported by API'}</code><p>{text}</p></article>)}</div><article className="panel method-detail"><PanelTitle eyebrow="PROCESSING NOTES" title="How dashboard values are prepared"/><ul><li>CSV sources are read with pandas; recognized date fields are parsed and malformed values remain unavailable.</li><li>Count measures are converted to numeric values after removing commas. Blank values are retained as missing and rendered as “—”.</li><li>National and testing charts use the observations returned by the API. The current national endpoint returns up to 500 rows.</li><li>State comparisons use one selected source column for every selected region and the same user-selected date range.</li><li>Insights calculate maxima and first-to-last differences from rows returned by the API and show the metric, dates, and record count.</li><li>No population-normalized rate, cross-file positivity estimate, or missing value is invented by the interface.</li></ul></article><div className="source-footer">Source attribution: {meta?.source || 'Awaiting source metadata'} · Archive coverage: {formatDate(meta?.date_range?.start)} – {formatDate(meta?.date_range?.end)}.</div></>
}

function ProfilePage({ user, preferences, range, onSavePreferences, saving, onLogout }) {
  return <><article className="panel profile-card"><span className="profile-avatar">{user?.name?.[0]?.toUpperCase() || '?'}</span><div className="profile-copy"><span className="eyebrow">AUTHENTICATED ACCOUNT</span><h3>{user?.name || 'Account name unavailable'}</h3><p>{user?.email || 'Email unavailable'}</p><small>Account details loaded from the current authenticated session.</small></div></article><article className="panel preferences-card"><PanelTitle eyebrow="SAVED PREFERENCES" title="Remember this analysis range"/><p>Save the date range currently selected in the dashboard. Preferences are stored for this authenticated account.</p><div className="preference-values"><span>Current range</span><b>{range.start ? `${formatDate(range.start)} – ${formatDate(range.end)}` : 'No date range selected'}</b></div><div className="preference-values"><span>Previously saved</span><b>{preferences?.dateRange?.start ? `${formatDate(preferences.dateRange.start)} – ${formatDate(preferences.dateRange.end)}` : 'No saved date range'}</b></div><button className="primary-btn inline-btn" onClick={() => onSavePreferences({ ...preferences, dateRange: range })} disabled={saving}>{saving ? 'Saving…' : 'Save current range'}</button></article><article className="panel signout-card"><div><b>Sign out of Arogya Data</b><p>This ends the current server session on this browser.</p></div><button className="outline-btn danger-btn" onClick={onLogout}><LogOut size={15}/> Sign out</button></article></>
}

export default function App() {
  const [user, setUser] = useState(null)
  const [authChecked, setAuthChecked] = useState(false)
  const [page, setPage] = useState(pathPage)
  const [mobileMenu, setMobileMenu] = useState(false)
  const menuButtonRef = useRef(null)
  const closeMenuRef = useRef(null)
  const sidebarRef = useRef(null)
  const menuWasOpenRef = useRef(false)
  const [meta, setMeta] = useState(null)
  const [national, setNational] = useState(null)
  const [states, setStates] = useState(null)
  const [periodStates, setPeriodStates] = useState(null)
  const [periodStatesError, setPeriodStatesError] = useState('')
  const [districts, setDistricts] = useState(null)
  const [testing, setTesting] = useState(null)
  const [testingStates, setTestingStates] = useState(null)
  const [baseLoading, setBaseLoading] = useState(false)
  const [baseError, setBaseError] = useState('')
  const [stateHistory, setStateHistory] = useState(null)
  const [stateHistoryLoading, setStateHistoryLoading] = useState(false)
  const [stateHistoryError, setStateHistoryError] = useState('')
  const [testStatesLoading, setTestStatesLoading] = useState(false)
  const [testStatesError, setTestStatesError] = useState('')
  const [exploreDataset, setExploreDataset] = useState('national')
  const [exploreData, setExploreData] = useState(null)
  const [exploreLoading, setExploreLoading] = useState(false)
  const [exploreProgress, setExploreProgress] = useState(null)
  const [exploreError, setExploreError] = useState('')
  const exploreRequestId = useRef(0)
  const [range, setRange] = useState({ start: '', end: '' })
  const [preferences, setPreferences] = useState({})
  const [preferenceError, setPreferenceError] = useState('')
  const [savingPreferences, setSavingPreferences] = useState(false)

  const navigate = useCallback(next => {
    const valid = ['login', 'register', ...pages.map(item => item.id)]
    const destination = valid.includes(next) ? next : 'overview'
    if (pathPage() !== destination) window.location.hash = `/${destination}`
    setPage(destination)
    setMobileMenu(false)
  }, [])

  useEffect(() => {
    if (!mobileMenu) {
      if (menuWasOpenRef.current) menuButtonRef.current?.focus()
      menuWasOpenRef.current = false
      return undefined
    }
    menuWasOpenRef.current = true
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    closeMenuRef.current?.focus()
    const onKeyDown = event => {
      if (event.key === 'Escape') {
        event.preventDefault()
        setMobileMenu(false)
        return
      }
      if (event.key !== 'Tab') return
      const controls = [...(sidebarRef.current?.querySelectorAll('button:not([disabled]), a[href], input:not([disabled]), select:not([disabled])') || [])]
      if (!controls.length) return
      const first = controls[0]
      const last = controls.at(-1)
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
    }
    const onResize = () => { if (window.innerWidth > 800) setMobileMenu(false) }
    document.addEventListener('keydown', onKeyDown)
    window.addEventListener('resize', onResize)
    return () => {
      document.body.style.overflow = previousOverflow
      document.removeEventListener('keydown', onKeyDown)
      window.removeEventListener('resize', onResize)
    }
  }, [mobileMenu])

  useEffect(() => {
    const controller = new AbortController()
    const syncHash = () => setPage(pathPage())
    window.addEventListener('hashchange', syncHash)
    if (!window.location.hash) window.location.hash = '/overview'
    api('/auth/me', { signal: controller.signal }).then(result => {
      if (!controller.signal.aborted) setUser(result.user)
    }).catch(() => {
      if (!controller.signal.aborted) setUser(null)
    }).finally(() => {
      if (!controller.signal.aborted) setAuthChecked(true)
    })
    return () => { controller.abort(); window.removeEventListener('hashchange', syncHash) }
  }, [])

  useEffect(() => {
    if (!authChecked) return
    if (!user && !['login', 'register'].includes(page)) window.location.hash = '/login'
    else if (user && ['login', 'register'].includes(page)) window.location.hash = '/overview'
  }, [authChecked, user, page])

  useEffect(() => {
    const expireSession = () => {
      setUser(null)
      setStateHistory(null)
      setTestingStates(null)
      setExploreData(null)
      navigate('login')
    }
    window.addEventListener('dashboard:session-expired', expireSession)
    return () => window.removeEventListener('dashboard:session-expired', expireSession)
  }, [navigate])

  const loadBaseData = useCallback(async (signal) => {
    setBaseLoading(true)
    setBaseError('')
    const [metaResult, nationalResult, stateResult, districtResult, testingResult] = await Promise.allSettled([
      api('/metadata', { signal }), api('/national', { signal }), api('/states', { signal }), api('/districts', { signal }), api('/testing', { signal }),
    ])
    if (signal?.aborted) return
    const problems = []
    if (metaResult.status === 'fulfilled') setMeta(metaResult.value); else problems.push(metaResult.reason.message)
    if (nationalResult.status === 'fulfilled') {
      const value = nationalResult.value
      setNational(value)
      const observations = value.trend || []
      setRange(previous => previous.start ? previous : { start: observations[0]?.Date || '', end: observations.at(-1)?.Date || '' })
    } else problems.push(nationalResult.reason.message)
    if (stateResult.status === 'fulfilled') setStates(stateResult.value); else problems.push(stateResult.reason.message)
    if (districtResult.status === 'fulfilled') setDistricts(districtResult.value); else problems.push(districtResult.reason.message)
    if (testingResult.status === 'fulfilled') setTesting(testingResult.value); else problems.push(testingResult.reason.message)
    if (problems.length) setBaseError(problems.join(' '))
    setBaseLoading(false)
  }, [])

  useEffect(() => {
    if (!user) return
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      loadBaseData(controller.signal)
      api('/auth/preferences', { signal: controller.signal }).then(value => {
        if (controller.signal.aborted) return
        setPreferences(value || {})
        if (value?.dateRange?.start) setRange(value.dateRange)
      }).catch(() => {})
    }, 0)
    return () => { window.clearTimeout(timer); controller.abort(); setBaseLoading(false) }
  }, [user, loadBaseData])

  const loadStateHistory = useCallback(async (signal) => {
    setStateHistoryLoading(true)
    setStateHistoryError('')
    try { setStateHistory(await loadDataset('states', undefined, { signal })) }
    catch (error) { if (error.name !== 'AbortError' && !signal?.aborted) setStateHistoryError(error.message) }
    finally { if (!signal?.aborted) setStateHistoryLoading(false) }
  }, [])
  useEffect(() => {
    if (!user || page !== 'states' || stateHistory) return
    const controller = new AbortController()
    const timer = window.setTimeout(() => loadStateHistory(controller.signal), 0)
    return () => { window.clearTimeout(timer); controller.abort() }
  }, [user, page, stateHistory, loadStateHistory])

  const loadTestingStates = useCallback(async (selectedRange, signal) => {
    setTestStatesLoading(true); setTestStatesError('')
    const params = new URLSearchParams({ level: 'state' })
    if (selectedRange.start) params.set('start', selectedRange.start)
    if (selectedRange.end) params.set('end', selectedRange.end)
    try {
      const result = await api(`/analytics/testing?${params}`, { signal })
      if (!signal?.aborted) setTestingStates({ rangeKey: `${selectedRange.start}|${selectedRange.end}`, result })
    } catch (error) {
      if (error.name !== 'AbortError' && !signal?.aborted) setTestStatesError(error.message)
    } finally { if (!signal?.aborted) setTestStatesLoading(false) }
  }, [])
  useEffect(() => {
    if (!user || page !== 'testing') return
    const controller = new AbortController()
    const selectedRange = { start: range.start, end: range.end }
    const timer = window.setTimeout(() => loadTestingStates(selectedRange, controller.signal), 0)
    return () => { window.clearTimeout(timer); controller.abort(); setTestStatesLoading(false) }
  }, [user, page, range.start, range.end, loadTestingStates])

  const loadExplore = useCallback(async (dataset, signal) => {
    const requestId = ++exploreRequestId.current
    setExploreLoading(true); setExploreData(null); setExploreError(''); setExploreProgress(null)
    try {
      const value = await loadDataset(dataset, (loaded, total) => {
        if (!signal?.aborted && requestId === exploreRequestId.current) setExploreProgress({ loaded, total })
      }, { signal })
      if (!signal?.aborted && requestId === exploreRequestId.current) setExploreData(value)
    } catch (error) {
      if (error.name !== 'AbortError' && !signal?.aborted && requestId === exploreRequestId.current) setExploreError(error.message)
    } finally {
      if (!signal?.aborted && requestId === exploreRequestId.current) { setExploreLoading(false); setExploreProgress(null) }
    }
  }, [])

useEffect(() => {
  if (!user || page !== 'explorer') return

  const controller = new AbortController()
  const timer = window.setTimeout(() => loadExplore(exploreDataset, controller.signal), 0)

  return () => {
    window.clearTimeout(timer)
    controller.abort()
  }
}, [user, page, exploreDataset, loadExplore])


  const [insightResult, setInsightResult] = useState(null)
  const [insightError, setInsightError] = useState('')
  useEffect(() => {
    if (!user) return
    const controller = new AbortController()
    const rangeKey = `${range.start}|${range.end}`
    const params = new URLSearchParams()
    if (range.start) params.set('start', range.start)
    if (range.end) params.set('end', range.end)
    api(`/insights?${params}`, { signal: controller.signal })
      .then(result => { if (!controller.signal.aborted) setInsightResult({ rangeKey, result }) })
      .catch(error => { if (error.name !== 'AbortError' && !controller.signal.aborted) setInsightError({ rangeKey, message: error.message }) })
    return () => controller.abort()
  }, [user, range.start, range.end])

  useEffect(() => {
    if (!user || page !== 'overview') return
    const controller = new AbortController()
    const rangeKey = `${range.start}|${range.end}`
    const params = new URLSearchParams({ metric: 'Confirmed' })
    if (range.start) params.set('start', range.start)
    if (range.end) params.set('end', range.end)
    api(`/analytics/states?${params}`, { signal: controller.signal })
      .then(result => { if (!controller.signal.aborted) setPeriodStates({ rangeKey, result }) })
      .catch(error => { if (error.name !== 'AbortError' && !controller.signal.aborted) setPeriodStatesError({ rangeKey, message: error.message }) })
    return () => controller.abort()
  }, [user, page, range.start, range.end])

  async function savePreferences(next) {
    setSavingPreferences(true); setPreferenceError('')
    try { const saved = await api('/auth/preferences', { method: 'PUT', body: JSON.stringify(next) }); setPreferences(saved) }
    catch (error) { setPreferenceError(error.message) }
    finally { setSavingPreferences(false) }
  }
  async function logout() {
    setPreferenceError('')
    try {
      await api('/auth/logout', { method: 'POST' })
      setUser(null); setStateHistory(null); setTestingStates(null); navigate('login')
    } catch (error) {
      setPreferenceError(`Could not confirm server sign-out: ${error.message}`)
    }
  }

  const filteredNational = useMemo(() => filterDates(national?.trend, range), [national, range])
  const rangeKey = `${range.start}|${range.end}`
  const currentInsightResult = insightResult?.rangeKey === rangeKey ? insightResult.result : null
  const currentInsightError = insightError?.rangeKey === rangeKey ? insightError.message : ''
  const currentInsightLoading = !currentInsightResult && !currentInsightError
  const currentPeriodStates = periodStates?.rangeKey === rangeKey ? periodStates.result : null
  const currentPeriodStatesError = periodStatesError?.rangeKey === rangeKey ? periodStatesError.message : ''
  const currentTestingStates = testingStates?.rangeKey === rangeKey ? testingStates.result : null
  const insights = useMemo(() => (currentInsightResult?.insights || []).map(item => ({
    icon: item.type === 'peak' ? ArrowUpRight : item.type === 'first_to_last_difference' ? ArrowDownRight : Database,
    tone: item.type === 'peak' ? 'blue' : item.type === 'first_to_last_difference' ? 'teal' : item.type === 'largest_state_snapshot' ? 'violet' : 'amber',
    title: item.type === 'peak' ? 'Highest daily count in selected period' : item.type === 'first_to_last_difference' ? 'Change across selected observations' : item.type === 'largest_state_snapshot' ? 'Largest state snapshot total' : 'Analysis coverage',
    text: [item.state, item.value == null ? null : formatNumber(item.value), item.date ? formatDate(item.date) : null, item.period ? `${formatDate(item.period.start)} to ${formatDate(item.period.end)}` : null, item.calculation].filter(Boolean).join(' · '),
  })), [currentInsightResult])
  if (!authChecked || (user && ['login', 'register'].includes(page))) return <div className="loading-screen"><span className="spinner"/>Checking your secure session…</div>
  if (!user) return <AuthScreen key={page} initialMode={page === 'register' ? 'register' : 'login'} onAuthenticated={account => { setUser(account); navigate('overview') }} onModeChange={navigate}/>

  const current = pages.find(item => item.id === page) || pages[0]
  const lastAvailable = national?.latest?.Date || meta?.date_range?.end
  const sidebar = <aside ref={sidebarRef} id="primary-navigation" aria-label="Primary navigation" className={`sidebar ${mobileMenu ? 'open' : ''}`}>
    <div className="brand"><span className="brand-mark"><Activity size={20}/></span> Arogya<span className="brand-sub">/ DATA</span><button ref={closeMenuRef} type="button" className="close-menu" onClick={() => setMobileMenu(false)} aria-label="Close navigation"><X size={18}/></button></div>
    <div className="side-label">ANALYTICS WORKSPACE</div>
    <nav aria-label="Analytics pages">{pages.map(({ id, label, icon: Icon }) => <button type="button" key={id} className={`nav-item ${page === id ? 'active' : ''}`} aria-current={page === id ? 'page' : undefined} onClick={() => navigate(id)}><Icon size={17} aria-hidden="true"/><span>{label}</span></button>)}</nav>
    <div className="sidebar-bottom"><div className="archive-card"><span className="archive-icon"><Database size={15}/></span><div><b>Historical archive</b><small>{meta?.date_range?.start ? `${formatDate(meta.date_range.start)} – ${formatDate(meta.date_range.end)}` : 'Date range unavailable'}</small></div></div><button type="button" className="user-row user-button" onClick={() => navigate('profile')}><span className="avatar" aria-hidden="true">{user.name?.[0]?.toUpperCase() || '?'}</span><span className="user-info"><b>{user.name || 'Account'}</b><small>{user.email}</small></span><ChevronDown size={15} aria-hidden="true"/></button></div>
  </aside>

  return <div className="app-shell">{sidebar}{mobileMenu && <button type="button" className="mobile-scrim" aria-label="Close navigation" onClick={() => setMobileMenu(false)}/>}<main className="main-area"><header className="topbar"><button ref={menuButtonRef} type="button" className="menu-btn" aria-controls="primary-navigation" aria-expanded={mobileMenu} onClick={() => setMobileMenu(true)} aria-label="Open navigation"><Menu size={20}/></button><div className="breadcrumb">Arogya Data <span>/</span> <b>{current.label}</b></div><div className="top-right"><span className="archive-badge"><i/> HISTORICAL ARCHIVE</span><button type="button" className="help-btn" title="Open methodology" aria-label="Open methodology" onClick={() => navigate('methodology')}><BookOpen size={16}/></button></div></header><div className="content-wrap">
    <div className="page-heading"><div><div className="eyebrow">INDIA · PUBLIC HEALTH DATA</div><h1>{page === 'overview' ? 'The archive, at a glance.' : current.label}</h1><p className="muted">{page === 'overview' ? 'Explore the reported record with clear dates, sources, and context.' : page === 'profile' ? 'Account details and saved analysis preferences.' : `Historical ${current.label.toLowerCase()} from the source archive.`}</p></div><div className="heading-meta"><div className="date-chip"><Clock3 size={15}/><span><small>ARCHIVE COVERAGE</small><b>{meta?.date_range?.start ? `${formatDate(meta.date_range.start)} — ${formatDate(meta.date_range.end)}` : 'Loading source dates'}</b></span></div><div className="last-date-chip"><span>LAST AVAILABLE DATA</span><b>{formatDate(lastAvailable)}</b></div></div></div>
    {page !== 'profile' && page !== 'methodology' && <div className="notice"><Clock3 size={15}/><span><b>Historical data</b> · This dashboard presents archived records, not live statistics. Source: {meta?.source || 'source metadata unavailable'}.</span></div>}
    {page === 'overview' && <>
      <ErrorNotice error={baseError} retry={loadBaseData}/>
      {baseLoading && !national ? <Loading/> : <><SummaryCards national={national} testing={testing} range={range}/><div className="filter-row"><Filters start={range.start} end={range.end} min={national?.trend?.[0]?.Date} max={national?.trend?.at(-1)?.Date} onChange={setRange} onReset={() => setRange({ start: national?.trend?.[0]?.Date || '', end: national?.trend?.at(-1)?.Date || '' })}/><span className="range-note">National chart: {filteredNational.length} returned observations</span></div><div className="chart-grid"><TrendChart data={filteredNational} title="Daily confirmed cases"/><RegionChart data={currentPeriodStates?.regions || []} title="Confirmed cases by state in selected period" onExplore={() => navigate('states')}/></div><ErrorNotice error={currentPeriodStatesError}/><div className="section-heading"><div><span className="eyebrow">DATA-DRIVEN NOTES</span><h2>What the returned records show</h2></div><button className="text-btn" onClick={() => navigate('insights')}>All insights →</button></div><ErrorNotice error={currentInsightError}/>{currentInsightLoading ? <Loading text="Calculating insights from the selected dates…"/> : <Insights items={insights}/>}<div className="source-footer">Source: {meta?.source || 'archive metadata unavailable'} <span>·</span> Values are reproduced from CSV records. <button onClick={() => navigate('methodology')}>Methodology and limitations</button></div></>}
    </>}
    {page === 'national' && <><ErrorNotice error={baseError} retry={loadBaseData}/><NationalPage data={national} range={range} setRange={setRange} meta={meta} loading={baseLoading && !national}/></>}
    {page === 'states' && <><ErrorNotice error={baseError} retry={loadBaseData}/><StatePage latest={states} dateRange={stateHistory?.date_range} range={range} setRange={setRange} history={stateHistory} historyLoading={stateHistoryLoading} historyError={stateHistoryError} onRetry={loadStateHistory}/></>}
    {page === 'districts' && <><ErrorNotice error={baseError} retry={loadBaseData}/>{baseLoading && !districts ? <Loading/> : <DistrictPage districts={districts}/>}</>}
    {page === 'testing' && <><ErrorNotice error={baseError} retry={loadBaseData}/><TestingPage data={testing} stateData={currentTestingStates ? { ...currentTestingStates, error: testStatesError } : testStatesError ? { error: testStatesError } : null} range={range} setRange={setRange} loading={baseLoading && !testing} stateLoading={testStatesLoading} onRetry={() => loadTestingStates(range)}/></>}
    {page === 'explorer' && <ExplorerPage dataset={exploreDataset} setDataset={dataset => { exploreRequestId.current += 1; setExploreData(null); setExploreError(''); setExploreDataset(dataset) }} data={exploreData} metadata={meta?.datasets?.[exploreDataset]} loading={exploreLoading} progress={exploreProgress} error={exploreError} onRetry={() => loadExplore(exploreDataset)}/>}
    {page === 'insights' && <><div className="report-toolbar"><div><span className="eyebrow">CALCULATED BY THE INSIGHTS API</span><p>Each item includes its field, period, and calculation from the selected dates.</p></div><button className="outline-btn" onClick={() => downloadCsv(insights.map(item => ({ insight: item.title, calculation: item.text })), ['insight', 'calculation'], 'arogya-insights.csv')} disabled={!insights.length}><Download size={15}/> Export report</button></div><div className="filter-row"><Filters start={range.start} end={range.end} min={national?.trend?.[0]?.Date} max={national?.trend?.at(-1)?.Date} onChange={setRange} onReset={() => setRange({ start: national?.trend?.[0]?.Date || '', end: national?.trend?.at(-1)?.Date || '' })}/></div><ErrorNotice error={currentInsightError}/>{currentInsightLoading ? <Loading text="Calculating insights from the selected dates…"/> : <Insights items={insights}/>}<article className="panel insight-caveat"><b>Calculation window</b><p>The insights endpoint uses the selected national date range and reports the returned observation count. State snapshot comparisons are labeled separately because their reporting dates may not align with national records.</p></article></>}
    {page === 'methodology' && <MethodologyPage meta={meta}/>}
    {page === 'profile' && <><ErrorNotice error={preferenceError}/><ProfilePage user={user} preferences={preferences} range={range} onSavePreferences={savePreferences} saving={savingPreferences} onLogout={logout}/></>}
    </div></main></div>
}
