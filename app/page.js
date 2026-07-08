'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger,
} from '@/components/ui/dialog'
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  Check, RotateCcw, Volume2, VolumeX, Plus, Star, Pencil, LogOut, Delete, Heart,
  PartyPopper, CalendarDays, Flame, ArrowUp, ArrowDown, Sparkles, DoorOpen, Zap, Palette,
} from 'lucide-react'

const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID
const today = () => new Date().toLocaleDateString('en-CA') // YYYY-MM-DD (device local)

const THEMES = {
  animals:   { name: 'Animals',   emoji: '🦁', tiles: ['🦁','🐯','🐘','🦒','🐵','🦓','🐨','🦊'], grad: 'from-amber-100 via-orange-50 to-yellow-100', solid: 'bg-orange-600', text: 'text-orange-700', ring: '#ea580c', confetti: ['🦁','🐾','🐘'] },
  ocean:     { name: 'Ocean',     emoji: '🐠', tiles: ['🐠','🐟','🐙','🐚','🦀','🐬','🌊','🫧'], grad: 'from-cyan-100 via-sky-50 to-blue-100', solid: 'bg-blue-600', text: 'text-blue-700', ring: '#2563eb', confetti: ['🫧','🐠','🌊'] },
  dinosaurs: { name: 'Dinosaurs', emoji: '🦕', tiles: ['🦕','🦖','🌋','🥚','🌿','🦴','🌴'], grad: 'from-lime-100 via-green-50 to-emerald-100', solid: 'bg-green-700', text: 'text-green-800', ring: '#15803d', confetti: ['🦕','🦖','🌋'] },
  space:     { name: 'Space',     emoji: '🚀', tiles: ['🚀','⭐','🪐','🌟','🌙','☄️','👽','🛸'], grad: 'from-indigo-200 via-purple-100 to-slate-200', solid: 'bg-indigo-600', text: 'text-indigo-700', ring: '#4f46e5', confetti: ['🚀','⭐','🪐'] },
  forest:    { name: 'Forest',    emoji: '🌲', tiles: ['🌲','🌳','🍄','🦉','🍁','🌿','🦌'], grad: 'from-emerald-100 via-green-50 to-teal-100', solid: 'bg-emerald-700', text: 'text-emerald-800', ring: '#047857', confetti: ['🌲','🍄','🦉'] },
}
const themeOf = (k) => THEMES[k] || THEMES.animals

function fmtStars(n) { const r = Math.round(n * 10) / 10; return Number.isInteger(r) ? String(r) : r.toFixed(1) }
function fmtSigned(n) { const r = Math.round(n * 10) / 10; const s = r < 0 ? '−' : '+'; const a = Math.abs(r); return s + (Number.isInteger(a) ? String(a) : a.toFixed(1)) }

// ------------------------------- sounds --------------------------------------
function useSound(enabledRef) {
  const ctxRef = useRef(null)
  const getCtx = () => {
    if (typeof window === 'undefined') return null
    if (!ctxRef.current) {
      const AC = window.AudioContext || window.webkitAudioContext
      if (AC) ctxRef.current = new AC()
    }
    return ctxRef.current
  }
  const beep = (freqs, dur = 0.18, gain = 0.11, type = 'sine') => {
    if (!enabledRef.current) return
    const ctx = getCtx(); if (!ctx) return
    if (ctx.state === 'suspended') ctx.resume()
    let t = ctx.currentTime
    freqs.forEach((f) => {
      const osc = ctx.createOscillator(); const g = ctx.createGain()
      osc.type = type; osc.frequency.value = f
      g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(gain, t + 0.02)
      g.gain.exponentialRampToValueAtTime(0.0001, t + dur)
      osc.connect(g); g.connect(ctx.destination)
      osc.start(t); osc.stop(t + dur); t += dur * 0.85
    })
  }
  return {
    correct: () => beep([784, 1047], 0.16, 0.1, 'sine'),
    wrong: () => beep([196, 165], 0.28, 0.09, 'sine'),
    fanfare: () => beep([523, 659, 784, 1047, 1319], 0.22, 0.11, 'triangle'),
  }
}

async function fireConfetti(big, theme, reduced) {
  if (reduced) return
  try {
    const confetti = (await import('canvas-confetti')).default
    const t = themeOf(theme)
    let shapes = []
    try { shapes = t.confetti.map((e) => confetti.shapeFromText({ text: e, scalar: 2 })) } catch (_) {}
    const extra = shapes.length ? { shapes, scalar: 2 } : {}
    if (big) {
      confetti({ particleCount: 60, spread: 100, origin: { y: 0.6 }, ...extra })
      confetti({ particleCount: 50, spread: 75, origin: { y: 0.5 } })
    } else {
      confetti({ particleCount: 18, spread: 50, startVelocity: 22, origin: { y: 0.7 }, ...extra })
    }
  } catch (_) {}
}

export default function App() {
  const [booting, setBooting] = useState(true)
  const [user, setUser] = useState(null)
  const [signinError, setSigninError] = useState('')
  const [kids, setKids] = useState([])
  const [activeKid, setActiveKid] = useState(null)
  const [mode, setMode] = useState(null) // null | 'normal' | 'speed'
  const [reducedMotion, setReducedMotion] = useState(false)

  // normal set state
  const [set, setSet] = useState(null)
  const [queue, setQueue] = useState([])
  const [completion, setCompletion] = useState(null)

  // speed state
  const [speed, setSpeed] = useState(null) // {id, problems, startedAt, serverNow, timeLimit}
  const [speedResult, setSpeedResult] = useState(null)
  const [showExplainer, setShowExplainer] = useState(false)

  const [busy, setBusy] = useState(false)
  const soundRef = useRef(true)
  const sound = useSound(soundRef)
  const theme = themeOf(activeKid?.theme)

  useEffect(() => {
    if (typeof window !== 'undefined' && window.matchMedia) {
      setReducedMotion(window.matchMedia('(prefers-reduced-motion: reduce)').matches)
    }
  }, [])
  useEffect(() => { soundRef.current = activeKid ? activeKid.soundOn !== false : true }, [activeKid])

  const api = useCallback(async (path, opts = {}) => {
    const res = await fetch(path, { headers: { 'Content-Type': 'application/json' }, credentials: 'same-origin', ...opts })
    const data = await res.json().catch(() => ({}))
    return { ok: res.ok, status: res.status, data }
  }, [])

  const loadKids = useCallback(async () => {
    const { data } = await api(`/api/kids?date=${today()}`)
    if (data?.kids) setKids(data.kids)
    return data?.kids || []
  }, [api])

  const refreshActiveKid = useCallback(async () => {
    const list = await loadKids()
    setActiveKid((prev) => prev ? (list.find((k) => k.id === prev.id) || prev) : prev)
  }, [loadKids])

  useEffect(() => {
    (async () => {
      const { ok, data } = await api('/api/me')
      if (ok && data?.user) { setUser(data.user); await loadKids() }
      setBooting(false)
    })()
  }, [api, loadKids])

  // Daily rollover: when the tab regains focus and we're on a home/picker screen,
  // re-check the date by reloading kids so allowances reset for the new day.
  useEffect(() => {
    const onFocus = () => { if (user && mode === null) refreshActiveKid() }
    window.addEventListener('focus', onFocus)
    document.addEventListener('visibilitychange', () => { if (!document.hidden) onFocus() })
    return () => { window.removeEventListener('focus', onFocus) }
  }, [user, mode, refreshActiveKid])

  // ------------------------- Google sign-in ---------------------------------
  const onCredential = useCallback(async (resp) => {
    setSigninError('')
    const { ok, status, data } = await api('/api/auth/google', { method: 'POST', body: JSON.stringify({ credential: resp.credential }) })
    if (ok && data?.user) { setUser(data.user); await loadKids() }
    else if (status === 403) setSigninError(data?.error || 'Not on the allowlist.')
    else setSigninError(data?.error || 'Sign-in failed. Please try again.')
  }, [api, loadKids])

  useEffect(() => {
    if (booting || user) return
    let tries = 0
    const t = setInterval(() => {
      tries++
      if (window.google?.accounts?.id) {
        clearInterval(t)
        try {
          window.google.accounts.id.initialize({ client_id: CLIENT_ID, callback: onCredential })
          const el = document.getElementById('gbtn')
          if (el) window.google.accounts.id.renderButton(el, { theme: 'filled_blue', size: 'large', text: 'signin_with', shape: 'pill', width: 300 })
        } catch (e) {}
      }
      if (tries > 50) clearInterval(t)
    }, 200)
    return () => clearInterval(t)
  }, [booting, user, onCredential])

  // ------------------------- navigation helpers -----------------------------
  const selectKid = (kid) => { setActiveKid(kid); setMode(null); setSet(null); setSpeed(null); setCompletion(null); setSpeedResult(null) }
  const goHome = async () => { setMode(null); setSet(null); setSpeed(null); setCompletion(null); setSpeedResult(null); await refreshActiveKid() }

  // ------------------------- NORMAL set --------------------------------------
  const startSet = async () => {
    setBusy(true)
    const { data } = await api(`/api/kids/${activeKid.id}/set`, { method: 'POST', body: JSON.stringify({ date: today() }) })
    setBusy(false)
    if (data?.locked) { await refreshActiveKid(); return }
    if (data?.set) {
      setSet(data.set); setQueue(data.set.problems.filter((p) => !p.solved).map((p) => p.id))
      setCompletion(null); setMode('normal')
    }
  }
  const resetSet = async () => {
    if (!set) return; setBusy(true)
    const { data } = await api(`/api/sets/${set.id}/reset`, { method: 'POST', body: JSON.stringify({ date: today() }) })
    setBusy(false)
    if (data?.set) { setSet(data.set); setQueue(data.set.problems.map((p) => p.id)) }
  }
  const exitSet = async () => { if (set) await api(`/api/sets/${set.id}/exit`, { method: 'POST', body: JSON.stringify({}) }); await goHome() }

  // ------------------------- SPEED session -----------------------------------
  const actuallyStartSpeed = async () => {
    setBusy(true)
    const { data } = await api(`/api/kids/${activeKid.id}/speed`, { method: 'POST', body: JSON.stringify({ date: today() }) })
    setBusy(false)
    if (data?.locked) { await refreshActiveKid(); return }
    if (data?.session) {
      setSpeed({ ...data.session, serverNow: data.serverNow, timeLimit: data.timeLimit })
      setSpeedResult(null); setMode('speed')
    }
  }
  const startSpeed = () => {
    if (activeKid?.speedLocked) return
    if (!activeKid?.speedEver) setShowExplainer(true)
    else actuallyStartSpeed()
  }
  const exitSpeed = async () => { if (speed) await api(`/api/speed/${speed.id}/exit`, { method: 'POST', body: JSON.stringify({}) }); await goHome() }

  // =========================== RENDER =======================================
  if (booting) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-2xl font-bold text-slate-500 animate-pulse font-display">Loading MathCompete…</div>
      </div>
    )
  }
  if (!user) return <SignIn error={signinError} />

  return (
    <div className="min-h-screen">
      <ThemeBg theme={activeKid?.theme} active={mode !== null} reduced={reducedMotion} />

      <header className="sticky top-0 z-20 bg-white/90 backdrop-blur border-b border-slate-200">
        <div className="max-w-3xl mx-auto px-4 h-14 flex items-center justify-between gap-2">
          <button onClick={goHome} className="flex items-center gap-2 font-extrabold text-lg sm:text-xl text-indigo-700 font-display">
            <Sparkles className="w-6 h-6" /> MathCompete
          </button>
          <div className="flex items-center gap-2">
            {activeKid && mode === null && (
              <Button variant="ghost" size="sm" onClick={() => setActiveKid(null)}>Switch player</Button>
            )}
            <Button variant="outline" size="sm" onClick={async () => { await api('/api/auth/logout', { method: 'POST' }); setUser(null); setKids([]); setActiveKid(null); setMode(null) }} className="gap-1">
              <LogOut className="w-4 h-4" /> <span className="hidden sm:inline">Sign out</span>
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-6">
        {!activeKid && <Picker kids={kids} onSelect={selectKid} onAdd={loadKids} api={api} />}

        {activeKid && mode === null && (
          <KidHome
            kid={activeKid} theme={theme} busy={busy}
            onPlay={startSet} onSpeed={startSpeed}
            onToggleSound={async () => {
              const next = !(activeKid.soundOn !== false); soundRef.current = next
              setActiveKid((k) => ({ ...k, soundOn: next }))
              await api(`/api/kids/${activeKid.id}`, { method: 'PUT', body: JSON.stringify({ soundOn: next }) }); refreshActiveKid()
            }}
            onGradeChange={async (grade) => { await api(`/api/kids/${activeKid.id}`, { method: 'PUT', body: JSON.stringify({ grade }) }); refreshActiveKid() }}
            onThemeChange={async (th) => { setActiveKid((k) => ({ ...k, theme: th })); await api(`/api/kids/${activeKid.id}`, { method: 'PUT', body: JSON.stringify({ theme: th }) }); refreshActiveKid() }}
          />
        )}

        {activeKid && mode === 'normal' && set && (
          <NormalGame
            set={set} queue={queue} setQueue={setQueue} setSet={setSet}
            theme={theme} sound={sound} reducedMotion={reducedMotion} busy={busy} setBusy={setBusy} api={api}
            soundOn={activeKid.soundOn !== false}
            onToggleSound={async () => { const next = !(activeKid.soundOn !== false); soundRef.current = next; setActiveKid((k) => ({ ...k, soundOn: next })); await api(`/api/kids/${activeKid.id}`, { method: 'PUT', body: JSON.stringify({ soundOn: next }) }) }}
            onReset={resetSet} onExit={exitSet}
            onComplete={(data) => { sound.fanfare(); fireConfetti(true, activeKid.theme, reducedMotion); setCompletion(data) }}
          />
        )}

        {activeKid && mode === 'speed' && speed && (
          <SpeedGame
            session={speed} theme={theme} sound={sound} reducedMotion={reducedMotion} api={api}
            soundOn={activeKid.soundOn !== false}
            onExit={exitSpeed}
            onFinish={(data) => { if (data.starsEarned > 0) { sound.fanfare(); fireConfetti(true, activeKid.theme, reducedMotion) } setSpeedResult(data) }}
          />
        )}
      </main>

      {completion && (
        <CompletionOverlay data={completion} theme={theme} reducedMotion={reducedMotion} onClose={goHome} />
      )}
      {speedResult && (
        <SpeedResultOverlay data={speedResult} theme={theme} reducedMotion={reducedMotion} onClose={goHome} />
      )}
      {showExplainer && (
        <SpeedExplainer theme={theme} onClose={() => setShowExplainer(false)} onGo={() => { setShowExplainer(false); actuallyStartSpeed() }} />
      )}
    </div>
  )
}

// ------------------------------- Theme background ----------------------------
function ThemeBg({ theme, active, reduced }) {
  const t = themeOf(theme)
  return (
    <div aria-hidden className={`fixed inset-0 -z-10 bg-gradient-to-br ${t.grad}`}>
      <div className={`absolute inset-0 ${active ? 'opacity-[0.07]' : 'opacity-20'}`}>
        <div className="w-full h-full grid grid-cols-4 sm:grid-cols-6 gap-6 p-6 text-5xl md:text-6xl select-none overflow-hidden">
          {Array.from({ length: 30 }).map((_, i) => <span key={i}>{t.tiles[i % t.tiles.length]}</span>)}
        </div>
      </div>
      {active && <div className="absolute inset-0 bg-white/50" />}
    </div>
  )
}

// ------------------------------- Sign In -------------------------------------
function SignIn({ error }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-b from-indigo-100 to-emerald-100 px-4">
      <div className="text-center mb-8">
        <div className="text-6xl mb-3">🧮</div>
        <h1 className="text-4xl md:text-5xl font-extrabold text-indigo-800 font-display">MathCompete</h1>
        <p className="text-lg text-slate-600 mt-2 max-w-md">A daily math game for kids in grades 1–5. Parents sign in to set up players.</p>
      </div>
      <Card className="w-full max-w-sm p-6 flex flex-col items-center gap-4 shadow-xl">
        <h2 className="text-xl font-bold text-slate-800 font-display">Parent Sign-In</h2>
        <p className="text-sm text-slate-500 text-center">Access is limited to families on the allowlist.</p>
        <div id="gbtn" className="flex justify-center min-h-[44px]" />
        {error && <p role="alert" className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md p-3 text-center">{error}</p>}
      </Card>
    </div>
  )
}

// ------------------------------- Theme picker tiles --------------------------
function ThemeTiles({ value, onChange }) {
  return (
    <div className="grid grid-cols-3 gap-2">
      {Object.entries(THEMES).map(([key, t]) => (
        <button key={key} type="button" onClick={() => onChange(key)}
          className={`rounded-xl p-3 flex flex-col items-center gap-1 border-2 min-h-[64px] bg-gradient-to-br ${t.grad} ${value === key ? 'border-slate-800 ring-2 ring-slate-800' : 'border-transparent'}`}>
          <span className="text-3xl">{t.emoji}</span>
          <span className="text-xs font-bold text-slate-700 font-display">{t.name}</span>
        </button>
      ))}
    </div>
  )
}

// ------------------------------- Picker --------------------------------------
function Picker({ kids, onSelect, onAdd, api }) {
  const [open, setOpen] = useState(false)
  const [firstName, setFirstName] = useState('')
  const [grade, setGrade] = useState('1')
  const [themeKey, setThemeKey] = useState('animals')
  const [err, setErr] = useState('')
  const [saving, setSaving] = useState(false)

  const addKid = async () => {
    setErr(''); setSaving(true)
    const res = await api('/api/kids', { method: 'POST', body: JSON.stringify({ firstName, grade: Number(grade), theme: themeKey }) })
    setSaving(false)
    if (!res.ok) { setErr(res.data?.error || 'Could not add player.'); return }
    setFirstName(''); setGrade('1'); setThemeKey('animals'); setOpen(false); onAdd()
  }

  return (
    <div>
      <h2 className="text-3xl font-extrabold text-slate-800 mb-1 font-display">Choose your player</h2>
      <p className="text-slate-600 mb-6">Tap a card to start playing.</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {kids.map((kid) => {
          const t = themeOf(kid.theme)
          return (
            <button key={kid.id} onClick={() => onSelect(kid)}
              className={`${t.solid} text-white rounded-2xl p-6 text-left shadow-lg hover:opacity-95 active:scale-95 transition min-h-[44px] relative overflow-hidden`}>
              <div className="absolute right-2 top-2 text-6xl opacity-30">{t.emoji}</div>
              <div className="relative">
                <span className="text-3xl font-extrabold font-display">{kid.firstName}</span>
                <div className="mt-1 text-white/90 font-semibold">Grade {kid.grade} · {t.name}</div>
                <div className="mt-4 flex items-center gap-2 bg-white/25 rounded-full px-3 py-1 w-fit">
                  <Star className="w-5 h-5 fill-white" />
                  <span className="font-bold text-lg">{fmtStars(kid.totalStars)}</span>
                </div>
              </div>
            </button>
          )
        })}

        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <button className="border-2 border-dashed border-slate-300 rounded-2xl p-6 flex flex-col items-center justify-center gap-2 text-slate-500 hover:border-indigo-400 hover:text-indigo-600 transition min-h-[120px] bg-white/70">
              <Plus className="w-8 h-8" /> <span className="font-bold text-lg font-display">New player</span>
            </button>
          </DialogTrigger>
          <DialogContent className="max-h-[90vh] overflow-y-auto">
            <DialogHeader><DialogTitle className="font-display">Add a new player</DialogTitle></DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label htmlFor="fn">First name</Label>
                <Input id="fn" value={firstName} onChange={(e) => setFirstName(e.target.value)} placeholder="e.g. Aarav" />
              </div>
              <div className="space-y-2">
                <Label>Grade</Label>
                <Select value={grade} onValueChange={setGrade}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{[1, 2, 3, 4, 5].map((g) => <SelectItem key={g} value={String(g)}>Grade {g}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Theme</Label>
                <ThemeTiles value={themeKey} onChange={setThemeKey} />
              </div>
              {err && <p className="text-sm text-red-600">{err}</p>}
            </div>
            <DialogFooter>
              <Button onClick={addKid} disabled={saving || !firstName.trim()}>{saving ? 'Adding…' : 'Add player'}</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  )
}

// ------------------------------- KidHome -------------------------------------
function KidHome({ kid, theme, busy, onPlay, onSpeed, onToggleSound, onGradeChange, onThemeChange }) {
  const [editOpen, setEditOpen] = useState(false)
  const [themeOpen, setThemeOpen] = useState(false)
  const [grade, setGrade] = useState(String(kid.grade))

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-3xl font-extrabold text-slate-800 font-display">Hi {kid.firstName}! 👋</h2>
          <div className={`flex items-center gap-2 mt-1 font-bold ${theme.text}`}>
            <Star className="w-5 h-5 fill-amber-400 text-amber-400" /> {kid.levelLabel}
          </div>
        </div>
        <button onClick={onToggleSound} aria-label={kid.soundOn !== false ? 'Turn sound off' : 'Turn sound on'}
          className="w-12 h-12 rounded-full bg-white border border-slate-200 flex items-center justify-center shadow-sm shrink-0">
          {kid.soundOn !== false ? <Volume2 className="w-6 h-6 text-indigo-600" /> : <VolumeX className="w-6 h-6 text-slate-400" />}
        </button>
      </div>

      {/* Total stars — white panel for guaranteed AA contrast, themed accent icon */}
      <Card className={`p-6 bg-white shadow-lg border-t-4`} style={{ borderTopColor: theme.ring }}>
        <div className="flex items-center justify-between">
          <div>
            <div className="text-slate-500 font-semibold">Total stars</div>
            <div className="text-5xl font-extrabold flex items-center gap-2 text-slate-800 font-display">
              <Star className="w-10 h-10 fill-amber-400 text-amber-400" /> {fmtStars(kid.totalStars)}
            </div>
          </div>
          <div className="text-6xl">{theme.emoji}</div>
        </div>
      </Card>

      <div className="grid grid-cols-3 gap-3">
        <StatBox icon={<CalendarDays className="w-5 h-5" />} label="Days played" value={kid.daysPlayed} />
        <StatBox icon={<Flame className="w-5 h-5" />} label="Day streak" value={kid.streak} />
        <StatBox icon={<Star className="w-5 h-5" />} label="Today" value={fmtStars(kid.todayStars)} />
      </div>

      {/* Normal mode */}
      {kid.locked ? (
        <Card className="p-6 text-center bg-white/90 border-emerald-200">
          <div className="text-4xl mb-2">🌙</div>
          <h3 className="text-xl font-extrabold text-emerald-800 font-display">Great work today!</h3>
          <p className="text-emerald-700 mt-1">You finished both practice sets. Come back tomorrow!</p>
        </Card>
      ) : (
        <Button onClick={onPlay} disabled={busy} className={`w-full h-20 text-2xl sm:text-3xl font-extrabold rounded-2xl shadow-lg text-white ${theme.solid} font-display`}>
          {busy ? 'Getting ready…' : `▶ Practice (${2 - kid.todayCompleted} left)`}
        </Button>
      )}

      {/* Speed mode */}
      {kid.speedLocked ? (
        <Card className="p-5 text-center bg-white/90 border-amber-200">
          <div className="text-3xl mb-1">⚡🌙</div>
          <p className="font-bold text-amber-800 font-display">More speed math tomorrow!</p>
        </Card>
      ) : (
        <Button onClick={onSpeed} disabled={busy} variant="outline"
          className="w-full h-16 text-xl font-extrabold rounded-2xl border-2 border-slate-300 bg-white/95 text-slate-800 hover:bg-white gap-2 font-display">
          <Zap className="w-6 h-6 text-amber-500 fill-amber-400" /> Speed Math ({kid.speedRemaining} left)
        </Button>
      )}

      {kid.history?.length > 0 && (
        <Card className="p-4 bg-white/95">
          <h3 className="font-bold text-slate-700 mb-1 font-display">Your history</h3>
          <p className="text-sm text-slate-500 mb-3">{kid.daysPlayed} days played, {fmtStars(kid.totalStars)} stars earned</p>
          <div className="flex flex-wrap gap-2">
            {kid.history.slice(-14).map((h) => (
              <div key={h.date} className="flex items-center gap-1 bg-indigo-50 text-indigo-700 rounded-full px-3 py-1 text-sm font-semibold">
                <span>{h.date.slice(5)}</span><Star className="w-3 h-3 fill-amber-400 text-amber-400" /><span>{fmtStars(h.stars)}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      <div className="flex flex-wrap justify-center gap-2 pt-2">
        <Dialog open={themeOpen} onOpenChange={setThemeOpen}>
          <DialogTrigger asChild>
            <Button variant="ghost" size="sm" className="gap-1 text-slate-600"><Palette className="w-4 h-4" /> Change theme</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle className="font-display">Pick {kid.firstName}'s world</DialogTitle></DialogHeader>
            <ThemeTiles value={kid.theme} onChange={(th) => { onThemeChange(th); setThemeOpen(false) }} />
          </DialogContent>
        </Dialog>

        <Dialog open={editOpen} onOpenChange={setEditOpen}>
          <DialogTrigger asChild>
            <Button variant="ghost" size="sm" className="gap-1 text-slate-600"><Pencil className="w-4 h-4" /> Change grade (parent)</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle className="font-display">Change {kid.firstName}'s grade</DialogTitle></DialogHeader>
            <p className="text-sm text-slate-500">This resets the difficulty level for the new grade. Stars and history are kept.</p>
            <Select value={grade} onValueChange={setGrade}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>{[1, 2, 3, 4, 5].map((g) => <SelectItem key={g} value={String(g)}>Grade {g}</SelectItem>)}</SelectContent>
            </Select>
            <DialogFooter><Button onClick={() => { onGradeChange(Number(grade)); setEditOpen(false) }}>Save</Button></DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  )
}

function StatBox({ icon, label, value }) {
  return (
    <Card className="p-3 text-center bg-white/95">
      <div className="flex justify-center text-indigo-500 mb-1">{icon}</div>
      <div className="text-2xl font-extrabold text-slate-800 font-display">{value}</div>
      <div className="text-xs text-slate-500 font-medium">{label}</div>
    </Card>
  )
}

// ------------------------------- Exit button + confirm -----------------------
function ExitButton({ onExit }) {
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <button aria-label="Exit" className="flex items-center gap-1 h-11 px-3 rounded-full bg-white border border-slate-200 text-slate-600 font-bold shadow-sm shrink-0">
          <DoorOpen className="w-5 h-5" /> Exit
        </button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="font-display">Leave the game?</AlertDialogTitle>
          <AlertDialogDescription>You won't get any stars for this one.</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel autoFocus className="h-12 text-base">Keep playing</AlertDialogCancel>
          <AlertDialogAction onClick={onExit} className="h-12 text-base">Leave</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}

// ------------------------------- Number pad (shared) -------------------------
// PadKey is defined at module scope (stable identity) so the pad NEVER remounts
// on re-render — that previously caused flickering and dropped taps.
const PAD_KEY_BASE = 'h-16 md:h-20 rounded-xl text-3xl font-extrabold flex items-center justify-center active:scale-90 transition-transform shadow-sm select-none touch-manipulation'
function PadKey({ children, onClick, variant, ariaLabel }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={ariaLabel}
      className={`${PAD_KEY_BASE} ${variant === 'muted' ? 'bg-slate-200 text-slate-700 hover:bg-slate-300' : 'bg-white text-slate-800 border border-slate-200 hover:bg-slate-50'}`}
    >
      {children}
    </button>
  )
}

const PAD_DIGITS = ['1', '2', '3', '4', '5', '6', '7', '8', '9']
function NumberPad({ onDigit, onClear, onBack, onSubmit, submitDisabled, submitClass }) {
  return (
    <div className="pb-4">
      <div className="grid grid-cols-3 gap-2 max-w-sm mx-auto">
        {PAD_DIGITS.map((d) => <PadKey key={d} onClick={() => onDigit(d)}>{d}</PadKey>)}
        <PadKey onClick={onClear} variant="muted" ariaLabel="Clear">C</PadKey>
        <PadKey onClick={() => onDigit('0')}>0</PadKey>
        <PadKey onClick={onBack} variant="muted" ariaLabel="Delete"><Delete className="w-7 h-7" /></PadKey>
      </div>
      <div className="max-w-sm mx-auto mt-2">
        <Button onClick={onSubmit} disabled={submitDisabled} className={`w-full h-16 text-2xl font-extrabold rounded-xl text-white ${submitClass} font-display`}>
          <Check className="w-7 h-7 mr-2" /> Submit
        </Button>

      </div>
    </div>
  )
}

// ------------------------------- Normal Game ---------------------------------
function NormalGame({ set, queue, setQueue, setSet, theme, sound, reducedMotion, busy, setBusy, api, soundOn, onToggleSound, onReset, onExit, onComplete }) {
  const [typed, setTyped] = useState('')
  const [feedback, setFeedback] = useState(null)
  const currentId = queue[0]
  const problem = set.problems.find((p) => p.id === currentId)
  const solvedCount = set.problems.filter((p) => p.solved).length
  const pct = Math.round((solvedCount / 30) * 100)

  const submit = useCallback(async () => {
    if (!currentId || typed === '' || busy) return
    setBusy(true)
    const { data } = await api(`/api/sets/${set.id}/answer`, { method: 'POST', body: JSON.stringify({ problemId: currentId, answer: Number(typed) }) })
    setBusy(false)
    if (!data) return
    if (data.correct) {
      sound.correct(); fireConfetti(false, theme.name, reducedMotion)
      setFeedback({ type: 'correct', text: data.encouragement || 'Great!' })
      setSet((prev) => ({ ...prev, problems: prev.problems.map((p) => p.id === currentId ? { ...p, solved: true } : p) }))
      setTyped('')
      if (data.setComplete) { setQueue([]); onComplete({ starsEarned: data.starsEarned, starsToday: data.starsToday, totalStars: data.totalStars, locked: data.locked, levelChanged: data.levelChanged, levelDirection: data.levelDirection, levelLabel: data.levelLabel }) }
      else setQueue((q) => q.slice(1))
    } else {
      sound.wrong(); setFeedback({ type: 'wrong', text: data.message || 'Almost! Try again' }); setTyped('')
      setQueue((q) => q.length > 1 ? [...q.slice(1), q[0]] : q)
    }
    setTimeout(() => setFeedback(null), 1200)
  }, [currentId, typed, busy, api, set.id, sound, theme, reducedMotion, setBusy, setSet, setQueue, onComplete])

  useEffect(() => {
    const onKey = (e) => {
      if (e.key >= '0' && e.key <= '9') setTyped((t) => (t + e.key).slice(0, 7))
      else if (e.key === 'Backspace') setTyped((t) => t.slice(0, -1))
      else if (e.key === 'Enter') submit()
      else if (e.key === 'Escape') setTyped('')
    }
    window.addEventListener('keydown', onKey); return () => window.removeEventListener('keydown', onKey)
  }, [submit])

  return (
    <div className="flex flex-col min-h-[calc(100vh-8rem)]">
      <div className="flex items-center gap-2 mb-3">
        <ExitButton onExit={onExit} />
        <Progress value={pct} className="h-4 flex-1" />
        <span className="text-sm font-bold text-slate-600 whitespace-nowrap">{solvedCount}/30</span>
      </div>
      <div className="flex justify-end gap-2 mb-2">
        <button onClick={onToggleSound} aria-label={soundOn ? 'Turn sound off' : 'Turn sound on'} className="w-11 h-11 rounded-full bg-white border border-slate-200 flex items-center justify-center">
          {soundOn ? <Volume2 className="w-5 h-5 text-indigo-600" /> : <VolumeX className="w-5 h-5 text-slate-400" />}
        </button>
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <button aria-label="Start fresh" className="w-11 h-11 rounded-full bg-white border border-slate-200 flex items-center justify-center"><RotateCcw className="w-5 h-5 text-slate-500" /></button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle className="font-display">Start fresh?</AlertDialogTitle>
              <AlertDialogDescription>Your current 30 questions will go away and you'll get 30 new ones. This earns nothing.</AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Keep playing</AlertDialogCancel>
              <AlertDialogAction onClick={onReset}>Start fresh</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center py-4">
        <div className="text-slate-400 font-semibold mb-2 font-display">Solve it!</div>
        <Card className="px-6 py-4 bg-white/95 shadow-md">
          <div className="text-6xl md:text-8xl font-extrabold text-slate-800 tracking-tight text-center" style={{ minHeight: '1.2em' }}>{problem?.display}</div>
        </Card>
        <div className={`mt-6 min-w-[200px] h-24 md:h-28 rounded-2xl border-4 flex items-center justify-center text-5xl md:text-6xl font-extrabold px-6 bg-white ${feedback?.type === 'correct' ? 'border-emerald-500 text-emerald-700' : feedback?.type === 'wrong' ? 'border-amber-500 text-amber-700' : 'border-slate-300 text-slate-800'}`}>
          {typed || <span className="text-slate-300">?</span>}
        </div>
        <div className="h-12 mt-3 flex items-center" role="status" aria-live="polite">
          {feedback?.type === 'correct' && <div className="flex items-center gap-2 text-emerald-600 font-extrabold text-2xl font-display"><Check className="w-7 h-7" /> {feedback.text}</div>}
          {feedback?.type === 'wrong' && <div className="flex items-center gap-2 text-amber-600 font-extrabold text-2xl font-display"><Heart className="w-7 h-7" /> {feedback.text}</div>}
        </div>
      </div>

      <NumberPad typed={typed} onDigit={(d) => setTyped((t) => (t + d).slice(0, 7))} onClear={() => setTyped('')} onBack={() => setTyped((t) => t.slice(0, -1))} onSubmit={submit} submitDisabled={busy || typed === ''} submitClass={theme.solid} />
    </div>
  )
}

// ------------------------------- Speed Game ----------------------------------
function SpeedGame({ session, theme, sound, reducedMotion, api, soundOn, onExit, onFinish }) {
  const [typed, setTyped] = useState('')
  const [answered, setAnswered] = useState(session.problems.filter((p) => p.answered).length)
  const [feedback, setFeedback] = useState(null)
  const [remaining, setRemaining] = useState(session.timeLimit)
  const [busy, setBusy] = useState(false)
  const finishedRef = useRef(false)
  const offsetRef = useRef(Date.now() - (session.serverNow || Date.now()))

  const problem = session.problems[answered]

  const doFinish = useCallback(async () => {
    if (finishedRef.current) return; finishedRef.current = true
    const { data } = await api(`/api/speed/${session.id}/finish`, { method: 'POST', body: JSON.stringify({}) })
    if (data) onFinish(data)
  }, [api, session.id, onFinish])

  // timer ring
  useEffect(() => {
    const id = setInterval(() => {
      const elapsed = (Date.now() - offsetRef.current - session.startedAt) / 1000
      const rem = Math.max(0, session.timeLimit - elapsed)
      setRemaining(rem)
      if (rem <= 0) { clearInterval(id); doFinish() }
    }, 250)
    return () => clearInterval(id)
  }, [session.startedAt, session.timeLimit, doFinish])

  const submit = useCallback(async () => {
    if (!problem || typed === '' || busy || finishedRef.current) return
    setBusy(true)
    const { data } = await api(`/api/speed/${session.id}/answer`, { method: 'POST', body: JSON.stringify({ problemId: problem.id, answer: Number(typed) }) })
    setBusy(false)
    if (!data) return
    setTyped('')
    if (data.timeUp) { finishedRef.current = true; onFinish(data); return }
    if (data.correct) { sound.correct(); setFeedback({ type: 'correct' }) }
    else { sound.wrong(); setFeedback({ type: 'wrong' }) }
    setTimeout(() => setFeedback(null), 700)
    if (data.sessionComplete) { finishedRef.current = true; onFinish(data) }
    else setAnswered((a) => a + 1)
  }, [problem, typed, busy, api, session.id, sound, onFinish])

  useEffect(() => {
    const onKey = (e) => {
      if (e.key >= '0' && e.key <= '9') setTyped((t) => (t + e.key).slice(0, 7))
      else if (e.key === 'Backspace') setTyped((t) => t.slice(0, -1))
      else if (e.key === 'Enter') submit()
      else if (e.key === 'Escape') setTyped('')
    }
    window.addEventListener('keydown', onKey); return () => window.removeEventListener('keydown', onKey)
  }, [submit])

  const R = 42, C = 2 * Math.PI * R
  const frac = Math.max(0, Math.min(1, remaining / session.timeLimit))
  const mins = Math.floor(remaining / 60), secs = Math.floor(remaining % 60)

  return (
    <div className="flex flex-col min-h-[calc(100vh-8rem)]">
      <div className="flex items-center gap-2 mb-3">
        <ExitButton onExit={onExit} />
        <div className="flex-1 flex items-center justify-center gap-3">
          <div className="flex items-center gap-1 font-extrabold text-amber-600 font-display"><Zap className="w-5 h-5 fill-amber-400" /> Speed Math</div>
        </div>
        <button onClick={() => { /* sound toggle noop visual */ }} aria-hidden className="w-11 h-11 opacity-0 pointer-events-none" />
      </div>

      <div className="flex items-center justify-center gap-6 mb-2">
        {/* calm shrinking ring (no red, no ticking) */}
        <div className="relative w-24 h-24">
          <svg viewBox="0 0 100 100" className="w-24 h-24 -rotate-90">
            <circle cx="50" cy="50" r={R} fill="none" stroke="#e2e8f0" strokeWidth="8" />
            <circle cx="50" cy="50" r={R} fill="none" stroke={theme.ring} strokeWidth="8" strokeLinecap="round"
              strokeDasharray={C} strokeDashoffset={C * (1 - frac)} style={{ transition: 'stroke-dashoffset 0.25s linear' }} />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center font-extrabold text-slate-700 font-display">
            {mins}:{String(secs).padStart(2, '0')}
          </div>
        </div>
        <div className="text-center">
          <div className="text-sm text-slate-500 font-semibold">Question</div>
          <div className="text-3xl font-extrabold text-slate-800 font-display">{Math.min(answered + 1, 10)}<span className="text-slate-400 text-xl"> / 10</span></div>
        </div>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center py-2">
        <Card className="px-6 py-4 bg-white/95 shadow-md">
          <div className="text-6xl md:text-7xl font-extrabold text-slate-800 tracking-tight text-center" style={{ minHeight: '1.2em' }}>{problem?.display}</div>
        </Card>
        <div className={`mt-4 min-w-[200px] h-20 md:h-24 rounded-2xl border-4 flex items-center justify-center text-4xl md:text-5xl font-extrabold px-6 bg-white ${feedback?.type === 'correct' ? 'border-emerald-500 text-emerald-700' : feedback?.type === 'wrong' ? 'border-amber-500 text-amber-700' : 'border-slate-300 text-slate-800'}`}>
          {typed || <span className="text-slate-300">?</span>}
        </div>
        <div className="h-8 mt-2 flex items-center" role="status" aria-live="polite">
          {feedback?.type === 'correct' && <div className="flex items-center gap-1 text-emerald-600 font-extrabold"><Check className="w-6 h-6" /> Yes!</div>}
          {feedback?.type === 'wrong' && <div className="flex items-center gap-1 text-amber-600 font-extrabold"><Heart className="w-6 h-6" /> Keep going!</div>}
        </div>
      </div>

      <NumberPad typed={typed} onDigit={(d) => setTyped((t) => (t + d).slice(0, 7))} onClear={() => setTyped('')} onBack={() => setTyped((t) => t.slice(0, -1))} onSubmit={submit} submitDisabled={busy || typed === ''} submitClass={theme.solid} />
    </div>
  )
}

// ------------------------------- Speed explainer -----------------------------
function SpeedExplainer({ theme, onClose, onGo }) {
  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <Card className="w-full max-w-md p-8 text-center bg-white shadow-2xl">
        <div className="text-6xl mb-2">⚡</div>
        <h2 className="text-3xl font-extrabold text-slate-800 font-display">Speed Math!</h2>
        <div className="mt-4 space-y-2 text-lg text-slate-700 text-left mx-auto max-w-xs">
          <p>🔟 10 questions</p>
          <p>⏱️ 3 minutes</p>
          <p>⭐ All right = 4 stars</p>
          <p>💫 Wrong ones cost half a star!</p>
        </div>
        <div className="mt-6 flex gap-2">
          <Button variant="outline" onClick={onClose} className="flex-1 h-14 text-lg">Not now</Button>
          <Button onClick={onGo} className={`flex-1 h-14 text-lg font-extrabold text-white ${theme.solid} font-display`}>Let's go!</Button>
        </div>
      </Card>
    </div>
  )
}

// --------------------------- Completion (normal) -----------------------------
function CompletionOverlay({ data, theme, onClose, reducedMotion }) {
  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <Card className="w-full max-w-md p-8 text-center bg-white shadow-2xl">
        {reducedMotion ? <div className="text-7xl mb-2">🌟</div> : <div className="text-7xl mb-2 animate-bounce">🎉</div>}
        <h2 className="text-3xl font-extrabold text-emerald-700 flex items-center justify-center gap-2 font-display"><PartyPopper className="w-8 h-8" /> Set complete!</h2>
        <div className="mt-4 text-6xl font-extrabold text-amber-500 flex items-center justify-center gap-2 font-display"><Star className="w-12 h-12 fill-amber-400" /> +{fmtStars(data.starsEarned)}</div>
        <p className="text-slate-600 mt-2 font-semibold">Total: {fmtStars(data.totalStars)} ⭐ · Today: {fmtStars(data.starsToday)} ⭐</p>
        {data.levelChanged && data.levelDirection === 'up' && <div className="mt-4 flex items-center justify-center gap-2 text-indigo-700 font-bold bg-indigo-100 rounded-full py-2 px-4"><ArrowUp className="w-5 h-5" /> Level up! Now {data.levelLabel}</div>}
        {data.levelChanged && data.levelDirection === 'down' && <div className="mt-4 flex items-center justify-center gap-2 text-sky-700 font-bold bg-sky-100 rounded-full py-2 px-4"><ArrowDown className="w-5 h-5" /> Let's practice more · {data.levelLabel}</div>}
        {data.locked ? (
          <div className="mt-5"><div className="text-2xl mb-2">🌙</div><p className="font-bold text-slate-700">That's 2 sets today — come back tomorrow!</p><Button onClick={onClose} className="mt-4 w-full h-14 text-xl font-bold">Done</Button></div>
        ) : (
          <Button onClick={onClose} className={`mt-6 w-full h-14 text-xl font-bold text-white ${theme.solid} font-display`}>Keep going</Button>
        )}
      </Card>
    </div>
  )
}

// --------------------------- Speed result ------------------------------------
function SpeedResultOverlay({ data, theme, onClose, reducedMotion }) {
  const positive = data.starsEarned > 0
  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <Card className="w-full max-w-md p-8 text-center bg-white shadow-2xl">
        {positive ? (reducedMotion ? <div className="text-7xl mb-2">🌟</div> : <div className="text-7xl mb-2 animate-bounce">⚡</div>) : <div className="text-7xl mb-2">🌱</div>}
        <h2 className="text-3xl font-extrabold text-slate-800 font-display">{positive ? 'Nice speed!' : 'Good try!'}</h2>
        <div className={`mt-4 text-6xl font-extrabold flex items-center justify-center gap-2 font-display ${positive ? 'text-amber-500' : 'text-slate-500'}`}>
          <Star className={`w-12 h-12 ${positive ? 'fill-amber-400' : 'fill-slate-300'}`} /> {fmtSigned(data.starsEarned)}
        </div>
        <p className="text-slate-600 mt-3 font-semibold">
          {positive ? `${10 - data.wrong} of 10 right!` : 'Slow and steady next time!'}
        </p>
        <p className="text-slate-500 mt-1">Total: {fmtStars(data.totalStars)} ⭐ · {data.speedRemaining} speed left today</p>
        <Button onClick={onClose} className={`mt-6 w-full h-14 text-xl font-bold text-white ${theme.solid} font-display`}>Done</Button>
      </Card>
    </div>
  )
}
