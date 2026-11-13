import { ArrowDownRight, ArrowUpRight, Database, Sigma } from 'lucide-react'
import { formatDate, formatNumber } from './api'

export function buildInsights(national, states, range) {
  const rows = (national?.trend || []).filter(row => (!range.start || row.Date >= range.start) && (!range.end || row.Date <= range.end))
  const observations = rows.filter(row => row['Daily Confirmed'] != null && row['Daily Confirmed'] !== '' && Number.isFinite(Number(row['Daily Confirmed'])))
  const peak = observations.reduce((best, row) => !best || Number(row['Daily Confirmed']) > Number(best['Daily Confirmed']) ? row : best, null)
  const first = observations[0]
  const last = observations.at(-1)
  const state = [...(states || [])].sort((a, b) => Number(b.Confirmed || 0) - Number(a.Confirmed || 0))[0]
  return [
    peak && { icon: ArrowUpRight, tone: 'blue', title: 'Highest daily count in selected range', text: `${formatNumber(peak['Daily Confirmed'])} reported on ${formatDate(peak.Date)}. Calculated as the maximum Daily Confirmed value in ${observations.length} returned records.` },
    first && last && { icon: ArrowDownRight, tone: 'teal', title: 'Change across returned observations', text: `${formatNumber(first['Daily Confirmed'])} on ${formatDate(first.Date)} to ${formatNumber(last['Daily Confirmed'])} on ${formatDate(last.Date)} (${Number(last['Daily Confirmed']) - Number(first['Daily Confirmed']) >= 0 ? '+' : ''}${formatNumber(Number(last['Daily Confirmed']) - Number(first['Daily Confirmed']))}). Difference of the first and last available values.` },
    state && { icon: Sigma, tone: 'violet', title: 'Largest state snapshot total', text: `${state.State}: ${formatNumber(state.Confirmed)} cumulative confirmed cases in the latest state snapshot. Ranked by Confirmed.` },
    { icon: Database, tone: 'amber', title: 'Coverage of this analysis', text: `${observations.length} dated national observations${rows.length >= 500 ? ' (API returns the latest 500 observations)' : ''}. Figures are historical archive records and may reflect reporting revisions.` },
  ].filter(Boolean)
}
