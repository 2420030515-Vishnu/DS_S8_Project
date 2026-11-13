# India COVID-19 Dashboard frontend

React and Vite client for the Flask API. The API uses an HttpOnly cookie and CSRF header; the client does not save credentials or session tokens in local storage. Set `VITE_API_URL` if the Flask API is not at `http://localhost:5000/api`.

## Run (PowerShell)

In a second terminal from the repository root:

```powershell
Set-Location frontend
npm ci
npm run dev -- --host 127.0.0.1
```

Open **http://localhost:5173**. Start the Flask service first; setup and run commands are in `backend/README.md`. The data is historical and the UI displays the date coverage returned by the metadata endpoint.

## End-to-end checklist

1. Register with a new email and password; verify the account is created and the dashboard opens.
2. Sign out, then log in with the same credentials; an incorrect password should show an error.
3. Confirm the summary values, archive coverage, and source label load from the API.
4. Change the dashboard date range; confirm summary cards, national chart, state ranking, testing snapshots, and insights use that range.
5. Open State analytics, select two states, change the measure and dates, and verify both the trend and date-aligned comparison update.
6. Open Data explorer; search, sort, paginate, filter, and export the filtered rows to CSV.
7. Refresh while authenticated; the session should remain active through the HttpOnly cookie.
8. Sign out; the backend revokes the SQLite session record and clears the cookie.
9. Open a protected hash route after sign-out; the app should redirect to login. Replay of a revoked signed cookie should fail `/api/auth/me`.
10. To test an expired session, expire/delete its `auth_sessions` row and make a protected account request; the app should return to login with no authenticated profile.

The automated Flask tests exercise registration, login, session-cookie revocation, real CSV endpoint contracts, filtering, comparison, insights, and explorer pagination. They do not automate a real browser; run this checklist manually in the browser.
