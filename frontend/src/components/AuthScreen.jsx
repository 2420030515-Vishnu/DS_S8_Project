import { useState } from 'react'
import { Activity, Eye, EyeOff, ShieldCheck } from 'lucide-react'
import { api } from '../lib/api'

const validEmail = value => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)

export default function AuthScreen({ initialMode = 'login', onAuthenticated, onModeChange }) {
  const [mode, setMode] = useState(initialMode)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmation, setShowConfirmation] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [formError, setFormError] = useState('')

  function changeMode(nextMode) {
    setMode(nextMode)
    setError('')
    setFormError('')
    onModeChange(nextMode)
  }

  async function submit(event) {
    event.preventDefault()
    setError('')
    setFormError('')
    const values = Object.fromEntries(new FormData(event.currentTarget))
    if (!validEmail(values.email || '')) return setFormError('Enter a valid email address.')
    if ((values.password || '').length < 8) return setFormError('Use a password with at least 8 characters.')
    if (mode === 'register' && (values.name || '').trim().length < 2) return setFormError('Enter your name (at least 2 characters).')
    if (mode === 'register' && values.password !== values.confirmPassword) return setFormError('The passwords do not match.')
    setBusy(true)
    try {
      const { user } = await api(`/auth/${mode}`, { method: 'POST', body: JSON.stringify({ name: values.name, email: values.email.trim(), password: values.password }) })
      if (!user) throw new Error('The server did not return an authenticated account.')
      onAuthenticated(user)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  return <main className="auth-page"><div className="auth-art"><div className="brand"><span className="brand-mark"><Activity size={20}/></span> Arogya<span className="brand-sub">/ DATA</span></div><div className="art-copy"><span className="eyebrow">INDIA · PUBLIC HEALTH ARCHIVE</span><h1>Read the record.<br/><i>Understand</i> the curve.</h1><p>Explore India's COVID-19 history through a thoughtful, transparent view of the data that was recorded.</p><div className="art-rule" aria-hidden="true">{Array.from({ length: 8 }, (_, index) => <span key={index}/>)}</div><small>ARCHIVE · CONTEXT · CLARITY</small></div><div className="art-foot">A public health research workspace.</div></div><section className="auth-content"><div className="auth-box"><div className="mobile-brand"><span className="brand-mark"><Activity size={19}/></span> Arogya<span className="brand-sub">/ DATA</span></div><span className="eyebrow">YOUR RESEARCH WORKSPACE</span><h2>{mode === 'register' ? 'Create your account' : 'Welcome back'}</h2><p className="muted">{mode === 'register' ? 'Register to save your analysis preferences.' : 'Sign in to continue exploring the archive.'}</p><form className="auth-form" onSubmit={submit} noValidate>
    {mode === 'register' && <label>Full name<input name="name" placeholder="Your name" autoComplete="name" required maxLength={100}/></label>}
    <label>Email address<input name="email" placeholder="you@example.com" type="email" autoComplete="email" required maxLength={254}/></label>
    <label>Password<div className="password-input"><input name="password" placeholder="At least 8 characters" type={showPassword ? 'text' : 'password'} autoComplete={mode === 'register' ? 'new-password' : 'current-password'} required minLength={8}/><button type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword(!showPassword)}>{showPassword ? <EyeOff size={16}/> : <Eye size={16}/>}</button></div></label>
    {mode === 'register' && <><p className="password-hint">Use at least 8 characters. Avoid reusing a password from another account.</p><label>Confirm password<div className="password-input"><input name="confirmPassword" placeholder="Enter your password again" type={showConfirmation ? 'text' : 'password'} autoComplete="new-password" required minLength={8}/><button type="button" aria-label={showConfirmation ? 'Hide confirmation' : 'Show confirmation'} onClick={() => setShowConfirmation(!showConfirmation)}>{showConfirmation ? <EyeOff size={16}/> : <Eye size={16}/>}</button></div></label></>}
    {(formError || error) && <div className="error-box" role="alert">{formError || error}</div>}
    <button className="primary-btn" disabled={busy}>{busy ? <><span className="button-spinner"/> {mode === 'register' ? 'Creating account…' : 'Signing in…'}</> : <>{mode === 'register' ? 'Create account' : 'Sign in'} <span>→</span></>}</button>
  </form><div className="auth-switch">{mode === 'register' ? 'Already registered?' : 'New to Arogya?'} <button onClick={() => changeMode(mode === 'register' ? 'login' : 'register')}>{mode === 'register' ? 'Sign in' : 'Create account'}</button></div><div className="auth-note"><ShieldCheck size={15}/> Passwords are hashed by the authentication service.</div></div></section></main>
}
