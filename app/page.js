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
  Divide, Minus, X as XIcon, ArrowLeft, Puzzle, Dumbbell, ChevronRight, Lock,
  BarChart3, ShieldCheck,
} from 'lucide-react'
import { useId } from 'react'

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
  const [avatarOpen, setAvatarOpen] = useState(false)
  const [funSub, setFunSub] = useState(null) // null | 'read' | 'ordershapes'
  const [parentView, setParentView] = useState(null) // V1.5: null | 'gate' | 'dash'

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
  const goHome = async () => { setMode(null); setSet(null); setSpeed(null); setCompletion(null); setSpeedResult(null); setFunSub(null); await refreshActiveKid() }

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
      <ThemeBg theme={activeKid?.theme} active={mode !== null} reduced={reducedMotion} brand={!activeKid} />

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
        {!activeKid && <Picker kids={kids} onSelect={selectKid} onAdd={loadKids} api={api} onParent={() => setParentView('gate')} />}

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
            onPractice={() => setMode('practice')} onFunMath={() => { setFunSub(null); setMode('funmath') }}
            onOpenAvatar={() => setAvatarOpen(true)}
          />
        )}

        {activeKid && mode === 'practice' && (
          <PracticeSection grade={activeKid.grade} theme={theme} sound={sound} onExit={goHome} />
        )}

        {activeKid && mode === 'funmath' && !funSub && (
          <FunMathPicker theme={theme} onPick={setFunSub} onExit={goHome} />
        )}

        {activeKid && mode === 'funmath' && funSub === 'read' && (
          <FunMath kid={activeKid} theme={theme} sound={sound} reducedMotion={reducedMotion} api={api}
            onDone={refreshActiveKid}
            onExit={async (goAvatar) => { await goHome(); if (goAvatar === 'avatar') setAvatarOpen(true) }} />
        )}

        {activeKid && mode === 'funmath' && funSub === 'ordershapes' && (
          <OrderShapes kid={activeKid} theme={theme} sound={sound} api={api} onExit={goHome} />
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
      {parentView === 'gate' && (
        <ParentGate onCancel={() => setParentView(null)} onPass={() => setParentView('dash')} />
      )}
      {parentView === 'dash' && (
        <ParentDashboard kids={kids} api={api} onClose={() => { setParentView(null); refreshActiveKid() }} />
      )}
      <Dialog open={avatarOpen} onOpenChange={setAvatarOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle className="font-display">My Avatar</DialogTitle></DialogHeader>
          {activeKid && (
            <AvatarPicker kid={activeKid}
              onClose={() => setAvatarOpen(false)}
              onSave={async (avatarId) => {
                setActiveKid((k) => ({ ...k, avatarId }))
                await api(`/api/kids/${activeKid.id}`, { method: 'PUT', body: JSON.stringify({ avatarId }) })
                refreshActiveKid(); setAvatarOpen(false)
              }} />
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

// ------------------------------- Theme background ----------------------------
function ThemeBg({ theme, active, reduced, brand }) {
  if (brand) {
    // Brand (indigo/blue) background for pre-theme screens like the player picker.
    return (
      <div aria-hidden className="fixed inset-0 -z-10 bg-gradient-to-br from-indigo-600 via-indigo-500 to-blue-600">
        <div className="absolute inset-0 opacity-[0.12]">
          <div className="w-full h-full grid grid-cols-4 sm:grid-cols-6 gap-8 p-6 text-white select-none overflow-hidden">
            {Array.from({ length: 30 }).map((_, i) => <Sparkles key={i} className="w-10 h-10 md:w-12 md:h-12" />)}
          </div>
        </div>
        <div className="absolute inset-0 bg-white/70" />
      </div>
    )
  }
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
        <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-indigo-600 text-white shadow-lg mb-3">
          <Sparkles className="w-11 h-11" />
        </div>
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
function Picker({ kids, onSelect, onAdd, api, onParent }) {
  const [open, setOpen] = useState(false)
  const [firstName, setFirstName] = useState('')
  const [grade, setGrade] = useState('1')
  const [themeKey, setThemeKey] = useState('animals')
  const [avatarKey, setAvatarKey] = useState('astronaut_boy')
  const [err, setErr] = useState('')
  const [saving, setSaving] = useState(false)

  const addKid = async () => {
    setErr(''); setSaving(true)
    const res = await api('/api/kids', { method: 'POST', body: JSON.stringify({ firstName, grade: Number(grade), theme: themeKey, avatarId: avatarKey }) })
    setSaving(false)
    if (!res.ok) { setErr(res.data?.error || 'Could not add player.'); return }
    setFirstName(''); setGrade('1'); setThemeKey('animals'); setAvatarKey('astronaut_boy'); setOpen(false); onAdd()
  }

  return (
    <div>
      <h2 className="text-3xl font-extrabold text-slate-800 mb-1 font-display">Choose your player</h2>
      <p className="text-slate-600 mb-1">Tap a card to start playing.</p>
      <p className="mb-6 flex flex-wrap items-center gap-x-4 gap-y-2">
        <a href="/coppa-notice" target="_blank" rel="noopener noreferrer" className="text-sm font-semibold text-indigo-600 underline underline-offset-2 hover:text-indigo-700">Privacy &amp; COPPA Notice</a>
        {kids.length > 0 && onParent && (
          <button data-testid="open-parent-dashboard" onClick={onParent} className="inline-flex items-center gap-1.5 text-sm font-semibold text-slate-700 bg-white/90 border border-slate-200 rounded-full px-3 py-1.5 shadow-sm hover:bg-white">
            <BarChart3 className="w-4 h-4 text-indigo-600" /> Parent Dashboard <Lock className="w-3.5 h-3.5 text-slate-400" />
          </button>
        )}
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {kids.map((kid) => {
          const t = themeOf(kid.theme)
          return (
            <button key={kid.id} onClick={() => onSelect(kid)}
              className={`${t.solid} text-white rounded-2xl p-6 text-left shadow-lg hover:opacity-95 active:scale-95 transition min-h-[44px] relative overflow-hidden`}>
              <div className="absolute right-2 top-2 text-6xl opacity-30">{t.emoji}</div>
              <div className="relative flex items-start gap-3">
                <div className="bg-white/25 rounded-2xl p-1 shrink-0"><AvatarImg id={kid.avatarId} size={52} /></div>
                <div>
                  <span className="text-3xl font-extrabold font-display">{kid.firstName}</span>
                  <div className="mt-1 text-white/90 font-semibold">Grade {kid.grade} · {t.name}</div>
                  <div className="mt-3 flex items-center gap-2 bg-white/25 rounded-full px-3 py-1 w-fit">
                    <Star className="w-5 h-5 fill-white" />
                    <span className="font-bold text-lg">{fmtStars(kid.totalStars)}</span>
                  </div>
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
              <div className="space-y-2">
                <Label>Avatar</Label>
                <div className="grid grid-cols-2 gap-2">
                  {START_AVATARS.map((a) => (
                    <button key={a} type="button" onClick={() => setAvatarKey(a)} className={`rounded-xl p-2 border-2 flex flex-col items-center gap-1 ${avatarKey === a ? 'border-slate-800 ring-2 ring-slate-800' : 'border-slate-200'}`}>
                      <AvatarImg id={a} size={64} /><span className="text-xs font-bold font-display">{AVATAR_LABELS[a]}</span>
                    </button>
                  ))}
                </div>
                <p className="text-xs text-slate-500">Unlock {AVATAR_IDS.length - START_AVATARS.length} more characters with perfect Read and Think runs!</p>
              </div>
              {err && <p className="text-sm text-red-600">{err}</p>}
              <p className="pt-1">
                <a href="/coppa-notice" target="_blank" rel="noopener noreferrer" className="text-sm font-semibold text-indigo-600 underline underline-offset-2 hover:text-indigo-700">Privacy &amp; COPPA Notice</a>
              </p>
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
function KidHome({ kid, theme, busy, onPlay, onSpeed, onToggleSound, onGradeChange, onThemeChange, onPractice, onFunMath, onOpenAvatar }) {
  const [editOpen, setEditOpen] = useState(false)
  const [themeOpen, setThemeOpen] = useState(false)
  const [grade, setGrade] = useState(String(kid.grade))

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <button onClick={onOpenAvatar} aria-label="My Avatar" className="rounded-full bg-white border border-slate-200 shadow-sm p-1 shrink-0 active:scale-95">
            <AvatarImg id={kid.avatarId} size={56} />
          </button>
          <div>
            <h2 className="text-3xl font-extrabold text-slate-800 font-display">Hi {kid.firstName}! 👋</h2>
            <div className={`flex items-center gap-1.5 mt-1 font-bold ${theme.text}`}>
              <Star className="w-5 h-5 fill-amber-400 text-amber-400" /> {String(kid.levelLabel).replace(/[^A-Za-z ].*$/, '').trim()}
            </div>
          </div>
        </div>
        <button onClick={onToggleSound} aria-label={kid.soundOn !== false ? 'Turn sound off' : 'Turn sound on'}
          className="w-12 h-12 rounded-full bg-white border border-slate-200 flex items-center justify-center shadow-sm shrink-0">
          {kid.soundOn !== false ? <Volume2 className="w-6 h-6 text-indigo-600" /> : <VolumeX className="w-6 h-6 text-slate-400" />}
        </button>
      </div>

      {/* Total stars — flat white panel for guaranteed AA contrast, themed accent icon */}
      <Card className="p-6 bg-white shadow-lg">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-slate-600 font-semibold">Total stars</div>
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

      {/* V1.2 sections */}
      <div className="grid grid-cols-2 gap-3">
        <button onClick={onPractice} className="rounded-2xl p-5 bg-white/95 border-2 border-slate-200 hover:border-indigo-400 flex flex-col items-center gap-2 shadow-sm active:scale-95 min-h-[100px]">
          <Dumbbell className="w-8 h-8 text-indigo-600" />
          <span className="text-lg font-extrabold text-slate-800 font-display">Just Practice</span>
          <span className="text-xs text-slate-500">No stars, no timer</span>
        </button>
        <button onClick={onFunMath} className="rounded-2xl p-5 bg-white/95 border-2 border-slate-200 hover:border-fuchsia-400 flex flex-col items-center gap-2 shadow-sm active:scale-95 min-h-[100px]">
          <Puzzle className="w-8 h-8 text-fuchsia-600" />
          <span className="text-lg font-extrabold text-slate-800 font-display">Fun Math</span>
          <span className="text-xs text-slate-500">Word problems · win a character</span>
        </button>
      </div>

      {(kid.history?.length > 0 || kid.funMathCompleted > 0) && (
        <Card className="p-4 bg-white/95">
          <h3 className="font-bold text-slate-700 mb-1 font-display">Your history</h3>
          <p className="text-sm text-slate-500 mb-1">{kid.daysPlayed} days played, {fmtStars(kid.totalStars)} stars earned</p>
          <p data-testid="funmath-completed" className="text-sm font-semibold text-fuchsia-700 mb-3 flex items-center gap-1">
            <Puzzle className="w-4 h-4" /> Fun Math completed: {kid.funMathCompleted || 0} {kid.funMathCompleted === 1 ? 'time' : 'times'}
          </p>
          <div className="flex flex-wrap gap-2">
            {(kid.history || []).slice(-14).map((h) => (
              <div key={h.date} className="flex items-center gap-1 bg-indigo-50 text-indigo-700 rounded-full px-3 py-1 text-sm font-semibold">
                <span>{h.date.slice(5)}</span><Star className="w-3 h-3 fill-amber-400 text-amber-400" /><span>{fmtStars(h.stars)}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      <div className="flex flex-wrap justify-center gap-2 pt-2">
        <Button variant="ghost" size="sm" className="gap-1 text-slate-600" onClick={onOpenAvatar}><Palette className="w-4 h-4" /> My Avatar</Button>
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
const PAD_KEY_BASE = 'rounded-xl font-extrabold flex items-center justify-center active:scale-90 transition-transform shadow-sm select-none touch-manipulation'
function PadKey({ children, onClick, variant, ariaLabel, compact }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={ariaLabel}
      className={`${PAD_KEY_BASE} ${compact ? 'h-12 md:h-14 text-2xl' : 'h-16 md:h-20 text-3xl'} ${variant === 'muted' ? 'bg-slate-200 text-slate-700 hover:bg-slate-300' : 'bg-white text-slate-800 border border-slate-200 hover:bg-slate-50'}`}
    >
      {children}
    </button>
  )
}

const PAD_DIGITS = ['1', '2', '3', '4', '5', '6', '7', '8', '9']
function NumberPad({ onDigit, onClear, onBack, onSubmit, submitDisabled, submitClass, compact, submitLabel }) {
  return (
    <div className={compact ? 'pb-1' : 'pb-4'}>
      <div className={`grid grid-cols-3 ${compact ? 'gap-1.5' : 'gap-2'} max-w-sm mx-auto`}>
        {PAD_DIGITS.map((d) => <PadKey key={d} compact={compact} onClick={() => onDigit(d)}>{d}</PadKey>)}
        <PadKey compact={compact} onClick={onClear} variant="muted" ariaLabel="Clear">C</PadKey>
        <PadKey compact={compact} onClick={() => onDigit('0')}>0</PadKey>
        <PadKey compact={compact} onClick={onBack} variant="muted" ariaLabel="Delete"><Delete className="w-7 h-7" /></PadKey>
      </div>
      <div className={`max-w-sm mx-auto ${compact ? 'mt-1.5' : 'mt-2'}`}>
        <Button onClick={onSubmit} disabled={submitDisabled} className={`w-full ${compact ? 'h-12 text-xl' : 'h-16 text-2xl'} font-extrabold rounded-xl text-white ${submitClass} font-display`}>
          {submitLabel ? submitLabel : <><Check className="w-7 h-7 mr-2" /> Submit</>}
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
          <div className="text-3xl font-extrabold text-slate-800 font-display">{Math.min(answered + 1, session.problems.length)}<span className="text-slate-400 text-xl"> / {session.problems.length}</span></div>
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
          <p>🔢 15 questions</p>
          <p>⏱️ 3 minutes</p>
          <p>⭐ All right = 4 stars</p>
          <p>💫 Each wrong one costs a little bit of a star!</p>
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
          {positive ? `${(data.total || 15) - data.wrong} of ${data.total || 15} right!` : 'Slow and steady next time!'}
        </p>
        <p className="text-slate-500 mt-1">Total: {fmtStars(data.totalStars)} ⭐ · {data.speedRemaining} speed left today</p>
        <Button onClick={onClose} className={`mt-6 w-full h-14 text-xl font-bold text-white ${theme.solid} font-display`}>Done</Button>
      </Card>
    </div>
  )
}

// ============================ V1.2: Avatars ==================================
const AV_COLORS = { sunset: '#f97316', sky: '#3b82f6', grape: '#8b5cf6', mint: '#10b981', bubblegum: '#ec4899', gold: '#eab308' }
const AV_COLOR_ORDER = ['sunset', 'sky', 'grape', 'mint', 'bubblegum', 'gold']
const AVATAR_LIST = ['bear', 'dog', 'dinosaur']
const AVATAR_LABEL = { bear: 'Bear', dog: 'Dog', dinosaur: 'Dinosaur' }

// V1.4 — illustrated avatar gallery (fixed unlock order; images in /public/avatars/)
const AVATAR_IDS = ['astronaut_boy', 'astronaut_girl', 'golden_retriever', 'baby_dinosaur', 'airplane', 'unicorn', 'girl_pilot', 'boy_pilot',
  'superhero_boy', 'doctor_girl', 'doctor_boy', 'scientist_boy', 'scientist_girl',
  'fire_truck', 'submarine', 'race_car', 'robot', 'wizard',
  'mermaid', 'rocket', 'baby_dragon', 'koala', 'bunny',
  'kitten', 'lion_cub', 'tiger_cub', 'panda', 'fox'] // V1.5 additions appended (order = unlock order)
const START_AVATARS = ['astronaut_boy', 'astronaut_girl']
const AVATAR_LABELS = {
  astronaut_boy: 'Astronaut Boy', astronaut_girl: 'Astronaut Girl', golden_retriever: 'Golden Retriever',
  baby_dinosaur: 'Baby Dino', airplane: 'Airplane', unicorn: 'Unicorn', girl_pilot: 'Girl Pilot', boy_pilot: 'Boy Pilot',
  superhero_boy: 'Super Hero', doctor_girl: 'Doctor Girl', doctor_boy: 'Doctor Boy', scientist_boy: 'Scientist Boy', scientist_girl: 'Scientist Girl',
  fire_truck: 'Fire Truck', submarine: 'Submarine', race_car: 'Race Car', robot: 'Robot', wizard: 'Little Wizard',
  mermaid: 'Mermaid', rocket: 'Rocket', baby_dragon: 'Baby Dragon', koala: 'Koala', bunny: 'Bunny',
  kitten: 'Kitten', lion_cub: 'Lion Cub', tiger_cub: 'Tiger Cub', panda: 'Panda', fox: 'Fox',
}
const avatarSrc = (id) => `/avatars/${AVATAR_IDS.includes(id) ? id : 'astronaut_boy'}.webp`
function AvatarImg({ id = 'astronaut_boy', size = 96, className = '' }) {
  return (
    <img src={avatarSrc(id)} alt={AVATAR_LABELS[id] || 'Avatar'} draggable={false}
      className={`rounded-full object-cover ${className}`} style={{ width: size, height: size }} />
  )
}

function Avatar({ type = 'bear', color = 'sunset', size = 96 }) {
  const uid = useId().replace(/:/g, '')
  const base = AV_COLORS[color] || AV_COLORS.sunset
  const gid = `av-${uid}`
  const eyes = (
    <>
      <circle cx="38" cy="52" r="5" fill="#1f2937" />
      <circle cx="62" cy="52" r="5" fill="#1f2937" />
      <circle cx="40" cy="50" r="1.6" fill="#fff" />
      <circle cx="64" cy="50" r="1.6" fill="#fff" />
    </>
  )
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" role="img" aria-label={`${AVATAR_LABEL[type]} avatar`}>
      <defs>
        <radialGradient id={gid} cx="38%" cy="32%" r="75%">
          <stop offset="0%" stopColor="#ffffff" stopOpacity="0.55" />
          <stop offset="45%" stopColor={base} />
          <stop offset="100%" stopColor="#00000055" />
        </radialGradient>
      </defs>
      {type === 'bear' && (<g>
        <circle cx="26" cy="26" r="13" fill={`url(#${gid})`} /><circle cx="74" cy="26" r="13" fill={`url(#${gid})`} />
        <circle cx="26" cy="26" r="6" fill="#00000022" /><circle cx="74" cy="26" r="6" fill="#00000022" />
        <circle cx="50" cy="55" r="38" fill={`url(#${gid})`} />
        <ellipse cx="50" cy="66" rx="16" ry="13" fill="#ffffffcc" />
        {eyes}<ellipse cx="50" cy="62" rx="4.5" ry="3.5" fill="#1f2937" /><path d="M50 65 q7 6 12 1" stroke="#1f2937" strokeWidth="2.5" fill="none" strokeLinecap="round" />
      </g>)}
      {type === 'dog' && (<g>
        <ellipse cx="18" cy="42" rx="11" ry="22" fill={`url(#${gid})`} /><ellipse cx="82" cy="42" rx="11" ry="22" fill={`url(#${gid})`} />
        <circle cx="50" cy="52" r="38" fill={`url(#${gid})`} />
        <ellipse cx="50" cy="66" rx="18" ry="14" fill="#ffffffcc" />
        {eyes}<ellipse cx="50" cy="63" rx="5" ry="4" fill="#1f2937" /><path d="M50 67 v6" stroke="#1f2937" strokeWidth="2.5" strokeLinecap="round" /><path d="M44 74 q6 5 12 0" stroke="#1f2937" strokeWidth="2.5" fill="none" strokeLinecap="round" />
      </g>)}
      {type === 'dinosaur' && (<g>
        <path d="M30 20 l6 12 l-12 0 z" fill="#00000033" /><path d="M50 12 l7 14 l-14 0 z" fill="#00000033" /><path d="M70 20 l6 12 l-12 0 z" fill="#00000033" />
        <circle cx="50" cy="56" r="38" fill={`url(#${gid})`} />
        <ellipse cx="52" cy="70" rx="20" ry="14" fill="#ffffffbb" />
        {eyes}<circle cx="60" cy="70" r="2" fill="#1f2937" /><circle cx="46" cy="70" r="2" fill="#1f2937" /><path d="M42 78 q10 6 20 0" stroke="#1f2937" strokeWidth="2.5" fill="none" strokeLinecap="round" />
      </g>)}
    </svg>
  )
}

function AvatarPicker({ kid, onSave, onClose }) {
  const owned = Array.isArray(kid.unlockedAvatars) && kid.unlockedAvatars.length ? kid.unlockedAvatars : START_AVATARS
  const initial = AVATAR_IDS.includes(kid.avatarId) && owned.includes(kid.avatarId) ? kid.avatarId : owned[0]
  const [sel, setSel] = useState(initial)
  return (
    <div className="space-y-4">
      <div className="flex justify-center py-2"><AvatarImg id={sel} size={120} /></div>
      <div>
        <Label className="mb-2 block">Choose your character</Label>
        <div className="grid grid-cols-4 gap-2">
          {AVATAR_IDS.map((a) => {
            const isOwned = owned.includes(a)
            return (
              <button key={a} type="button" disabled={!isOwned} onClick={() => isOwned && setSel(a)}
                aria-label={AVATAR_LABELS[a]}
                className={`relative rounded-xl p-1 border-2 flex items-center justify-center ${sel === a ? 'border-slate-800 ring-2 ring-slate-800' : 'border-slate-200'} ${!isOwned ? 'opacity-40 cursor-not-allowed' : ''}`}>
                <AvatarImg id={a} size={60} />
                {!isOwned && <div className="absolute inset-0 flex items-center justify-center"><Lock className="w-5 h-5 text-slate-800" /></div>}
              </button>
            )
          })}
        </div>
        <p className="text-xs text-slate-500 mt-2">Earn locked characters with a perfect Read and Think run!</p>
      </div>
      <div className="flex gap-2 pt-2">
        <Button variant="outline" onClick={onClose} className="flex-1 h-12">Cancel</Button>
        <Button onClick={() => onSave(sel)} className="flex-1 h-12">Save</Button>
      </div>
    </div>
  )
}

// ============================ V1.2: Just Practice ============================
const P_MAX = { 1: { s: 9, dv: 5 }, 2: { s: 50, dv: 10 }, 3: { s: 99, dv: 12 }, 4: { s: 400, dv: 12 }, 5: { s: 999, dv: 20 } }
const PRACTICE_PAGE_SIZE = 50 // V1.5: Addition / Subtraction / Division pages (Multiplication stays a 10-row table)
const pri = (a, b) => Math.floor(Math.random() * (b - a + 1)) + a
function genPractice(op, grade) {
  const c = P_MAX[grade] || P_MAX[1]
  if (op === 'add') { const a = pri(1, c.s), b = pri(1, c.s); return { display: `${a} + ${b} =`, answer: a + b } }
  if (op === 'sub') { const a = pri(2, c.s), b = pri(1, a); return { display: `${a} - ${b} =`, answer: a - b } }
  // division (whole-number only): divisor 2-5 for grade 1, 2-10 for grades 2-5
  const dMax = grade === 1 ? 5 : 10
  const qMax = grade === 1 ? 9 : grade === 2 ? 12 : grade === 3 ? 15 : 20
  const b = pri(2, dMax), q = pri(2, qMax); const a = b * q
  return { display: `${a} \u00f7 ${b} =`, answer: q }
}
function genPage(op, grade, prevSet, count = PRACTICE_PAGE_SIZE) {
  const out = []; const seen = new Set(); let g = 0
  const push = (p) => { seen.add(p.display); out.push({ id: 'p' + out.length + '-' + Math.random().toString(36).slice(2, 6), ...p }) }
  // 1) unique on this page AND not on the previous page
  while (out.length < count && g < 6000) { g++; const p = genPractice(op, grade); if (seen.has(p.display) || (prevSet && prevSet.has(p.display))) continue; push(p) }
  // 2) small grades have few possible problems — allow repeats from the previous page, still unique on this page
  g = 0; while (out.length < count && g < 6000) { g++; const p = genPractice(op, grade); if (seen.has(p.display)) continue; push(p) }
  // 3) last resort: allow repeats so the page is always full
  while (out.length < count) push(genPractice(op, grade))
  return out
}
function genTable(table) {
  return Array.from({ length: 10 }, (_, i) => ({ id: 't' + (i + 1), display: `${table} \u00d7 ${i + 1} =`, answer: table * (i + 1) }))
}

function PracticeSection({ grade, theme, sound, onExit }) {
  const [op, setOp] = useState(null)     // add|sub|div|mul
  const [table, setTable] = useState(null)
  const [items, setItems] = useState([]) // {id, display, answer, value, locked}
  const [prevSet, setPrevSet] = useState(null)
  const [checked, setChecked] = useState(false)
  const [active, setActive] = useState(null) // id currently typing
  const [done, setDone] = useState(false)

  const startOp = (o) => { setOp(o); setTable(null); if (o === 'mul') { setItems([]) } else { const pg = genPage(o, grade, null); setItems(pg.map((x) => ({ ...x, value: '', locked: false }))); setPrevSet(new Set(pg.map((x) => x.display))); setActive(pg[0].id) } setChecked(false); setDone(false) }
  const startTable = (t) => { setTable(t); const tb = genTable(t); setItems(tb.map((x) => ({ ...x, value: '', locked: false }))); setActive(tb[0].id); setChecked(false); setDone(false) }
  const nextPage = () => { const pg = genPage(op, grade, prevSet); setItems(pg.map((x) => ({ ...x, value: '', locked: false }))); setPrevSet(new Set(pg.map((x) => x.display))); setActive(pg[0].id); setChecked(false); setDone(false) }

  const submit = () => {
    let allRight = true
    const upd = items.map((it) => {
      if (it.locked) return it
      const ok = it.value !== '' && Number(it.value) === it.answer
      if (!ok) allRight = false
      return { ...it, locked: ok, value: ok ? it.value : '' }
    })
    setItems(upd); setChecked(true)
    if (allRight) { sound.fanfare(); setDone(true) }
    else { sound.wrong(); const firstOpen = upd.find((x) => !x.locked); setActive(firstOpen ? firstOpen.id : null) }
  }
  const allFilled = items.length > 0 && items.every((it) => it.locked || it.value !== '')
  const type = (d) => { if (!active) return; setItems((arr) => arr.map((it) => it.id === active && !it.locked ? { ...it, value: (String(it.value) + d).slice(0, 6) } : it)) }
  const back = () => { if (!active) return; setItems((arr) => arr.map((it) => it.id === active ? { ...it, value: String(it.value).slice(0, -1) } : it)) }
  const clear = () => { if (!active) return; setItems((arr) => arr.map((it) => it.id === active ? { ...it, value: '' } : it)) }
  // keep the box being typed into visible above the sticky number pad (50-problem pages)
  useEffect(() => {
    if (!active || typeof document === 'undefined') return
    const el = document.querySelector(`[data-practice-id="${active}"]`)
    if (!el) return
    const pad = document.querySelector('[data-practice-pad]')
    const r = el.getBoundingClientRect()
    const bottomLimit = window.innerHeight - (pad ? pad.getBoundingClientRect().height : 0) - 12
    const topLimit = 72 // below the sticky header
    if (r.bottom > bottomLimit) window.scrollBy({ top: r.bottom - bottomLimit, behavior: 'smooth' })
    else if (r.top < topLimit) window.scrollBy({ top: r.top - topLimit, behavior: 'smooth' })
  }, [active])


  const Header = ({ title }) => (
    <div className="flex items-center gap-2 mb-4">
      <button onClick={onExit} aria-label="Exit" className="flex items-center gap-1 h-11 px-3 rounded-full bg-white border border-slate-200 text-slate-600 font-bold shadow-sm"><DoorOpen className="w-5 h-5" /> Exit</button>
      <h2 className="text-2xl font-extrabold text-slate-800 font-display flex-1 text-center pr-16">{title}</h2>
    </div>
  )

  if (!op) return (
    <div>
      <Header title="Just Practice" />
      <p className="text-center text-slate-700 mb-6">Practice as much as you like. No stars, no timer.</p>
      <div className="grid grid-cols-2 gap-4 max-w-md mx-auto">
        {[['add', 'Addition', <Plus key="a" className="w-8 h-8" />], ['sub', 'Subtraction', <Minus key="s" className="w-8 h-8" />], ['div', 'Division', <Divide key="d" className="w-8 h-8" />], ['mul', 'Multiplication', <XIcon key="m" className="w-8 h-8" />]].map(([k, label, icon]) => (
          <button key={k} onClick={() => startOp(k)} className={`${theme.solid} text-white rounded-2xl p-6 flex flex-col items-center gap-2 shadow-lg active:scale-95 min-h-[110px] font-display`}>
            {icon}<span className="text-xl font-extrabold">{label}</span>
          </button>
        ))}
      </div>
    </div>
  )

  if (op === 'mul' && !table) return (
    <div>
      <Header title="Pick a table" />
      <div className="grid grid-cols-5 gap-2 max-w-md mx-auto">
        {Array.from({ length: 20 }, (_, i) => i + 1).map((t) => (
          <button key={t} onClick={() => startTable(t)} className="h-14 rounded-xl bg-white border border-slate-200 text-xl font-extrabold text-slate-800 active:scale-90 shadow-sm font-display">{t}</button>
        ))}
      </div>
    </div>
  )

  const isPage = op !== 'mul'
  const filledCount = items.filter((it) => it.locked || it.value !== '').length
  const rightCount = items.filter((it) => it.locked).length
  // jump to the next unanswered box after the current one (wraps around)
  const goNext = () => {
    if (!items.length) return
    const start = Math.max(0, items.findIndex((x) => x.id === active))
    for (let k = 1; k <= items.length; k++) {
      const it = items[(start + k) % items.length]
      if (!it.locked && it.value === '') { setActive(it.id); return }
    }
  }
  return (
    <div className="pb-4">
      <Header title={op === 'mul' ? `Table of ${table}` : { add: 'Addition', sub: 'Subtraction', div: 'Division' }[op]} />
      {isPage && (
        <p data-testid="practice-progress" className="text-center text-sm font-semibold text-slate-600 -mt-2 mb-3">
          {items.length} problems · {filledCount} filled{checked ? ` · ${rightCount} right` : ''}
        </p>
      )}
      <div className={`grid grid-cols-2 ${isPage ? 'gap-x-2 sm:gap-x-3 gap-y-1.5' : 'gap-x-4 gap-y-2'} max-w-lg mx-auto mb-4`}>
        {items.map((it) => (
          <button key={it.id} data-practice-id={it.id} onClick={() => !it.locked && setActive(it.id)}
            className={`flex items-center justify-between rounded-xl px-2 sm:px-3 ${isPage ? 'h-12 text-lg' : 'h-14 text-xl'} border-2 font-bold font-display scroll-mb-80 scroll-mt-20 ${it.locked ? 'bg-emerald-50 border-emerald-400 text-emerald-700' : active === it.id ? 'bg-white border-indigo-500 ring-2 ring-indigo-300' : checked ? 'bg-amber-50 border-amber-400' : 'bg-white border-slate-200'}`}>
            <span className="text-slate-800 whitespace-nowrap">{it.display}</span>
            <span className="min-w-[42px] text-right">{it.locked ? <Check className="w-6 h-6 inline text-emerald-600" /> : (it.value || <span className="text-slate-300">?</span>)}</span>
          </button>
        ))}
      </div>

      {done ? (
        <div className="text-center space-y-3">
          <div className="text-2xl font-extrabold text-emerald-600 font-display">Great job! All correct 🎉</div>
          <div className="flex gap-2 justify-center">
            {op === 'mul'
              ? <Button onClick={() => setTable(null)} className={`h-14 px-6 text-lg text-white ${theme.solid} font-display`}>Another table</Button>
              : <Button onClick={nextPage} className={`h-14 px-6 text-lg text-white ${theme.solid} font-display`}>Next page</Button>}
            <Button variant="outline" onClick={onExit} className="h-14 px-6 text-lg">Done</Button>
          </div>
        </div>
      ) : isPage ? (
        <div data-practice-pad className="sticky bottom-0 z-10 -mx-4 px-4 pt-2 pb-2 bg-white/95 backdrop-blur border-t border-slate-200">
          <NumberPad compact onDigit={type} onClear={clear} onBack={back}
            onSubmit={allFilled ? submit : goNext} submitDisabled={false} submitClass={theme.solid}
            submitLabel={allFilled ? <><Check className="w-6 h-6 mr-2" /> Check answers</> : <>Next box <ChevronRight className="w-6 h-6 ml-1" /></>} />
        </div>
      ) : (
        <NumberPad onDigit={type} onClear={clear} onBack={back} onSubmit={submit} submitDisabled={!allFilled} submitClass={theme.solid} />
      )}
    </div>
  )
}

// ============================ V1.2: Fun Math =================================
function FunMath({ kid, theme, sound, reducedMotion, api, onExit, onDone }) {
  const [run, setRun] = useState(null)
  const [idx, setIdx] = useState(0)
  const [typed, setTyped] = useState('')
  const [feedback, setFeedback] = useState(null)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const startedRef = useRef(false)

  useEffect(() => {
    if (startedRef.current) return
    startedRef.current = true
    ;(async () => {
      const { data } = await api(`/api/kids/${kid.id}/funmath`, { method: 'POST', body: JSON.stringify({ date: today() }) })
      if (data?.run) setRun(data.run)
    })()
  }, [api, kid.id])

  const q = run?.questions[idx]
  const submit = async () => {
    if (!q || typed === '' || busy) return
    setBusy(true)
    const { data } = await api(`/api/funmath/${run.id}/answer`, { method: 'POST', body: JSON.stringify({ questionId: q.id, answer: Number(typed) }) })
    setBusy(false); if (!data) return
    if (data.correct) {
      sound.correct(); setFeedback({ type: 'correct' }); setTyped('')
      if (data.runComplete) { sound.fanfare(); if (!reducedMotion) fireConfetti(true, theme.name, reducedMotion); setResult(data); onDone() }
      else setTimeout(() => { setFeedback(null); setIdx((i) => i + 1) }, 600)
    } else { sound.wrong(); setFeedback({ type: 'wrong' }); setTyped(''); setTimeout(() => setFeedback(null), 900) }
  }

  useEffect(() => {
    const onKey = (e) => { if (e.key >= '0' && e.key <= '9') setTyped((t) => (t + e.key).slice(0, 6)); else if (e.key === 'Backspace') setTyped((t) => t.slice(0, -1)); else if (e.key === 'Enter') submit() }
    window.addEventListener('keydown', onKey); return () => window.removeEventListener('keydown', onKey)
  })

  if (result) return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <Card className="w-full max-w-md p-8 text-center bg-white shadow-2xl">
        {reducedMotion ? <div className="text-7xl mb-2">🌟</div> : <div className="text-7xl mb-2 animate-bounce">🎉</div>}
        <h2 className="text-3xl font-extrabold text-emerald-700 font-display">Perfect run!</h2>
        {result.avatarUnlocked ? (
          <div className="mt-4">
            <p className="text-lg font-bold text-slate-700">You unlocked a new character!</p>
            <div className="flex justify-center my-3"><AvatarImg id={result.avatarUnlocked} size={96} /></div>
            <p className="text-base font-extrabold text-slate-800 font-display mb-3">{AVATAR_LABELS[result.avatarUnlocked]}</p>
            <Button onClick={() => onExit('avatar')} className={`w-full h-14 text-lg text-white ${theme.solid} font-display`}>Go to My Avatar</Button>
            <Button variant="outline" onClick={() => onExit()} className="w-full h-12 mt-2">Done</Button>
          </div>
        ) : (
          <div className="mt-4"><p className="text-lg font-bold text-slate-700">You have every character! 🌈</p><Button onClick={() => onExit()} className={`w-full h-14 text-lg mt-3 text-white ${theme.solid} font-display`}>Done</Button></div>
        )}
      </Card>
    </div>
  )

  if (!run) return <div className="text-center py-20 text-slate-500 font-display">Getting your questions…</div>

  return (
    <div className="flex flex-col min-h-[calc(100vh-8rem)]">
      <div className="flex items-center gap-2 mb-3">
        <button onClick={() => onExit()} aria-label="Exit" className="flex items-center gap-1 h-11 px-3 rounded-full bg-white border border-slate-200 text-slate-600 font-bold shadow-sm"><DoorOpen className="w-5 h-5" /> Exit</button>
        <div className="flex-1 flex items-center justify-center gap-1 font-extrabold text-indigo-600 font-display"><Puzzle className="w-5 h-5" /> Fun Math</div>
        <span className="text-sm font-bold text-slate-600 w-16 text-right">{idx + 1} / {run.total}</span>
      </div>
      <div className="flex-1 flex flex-col items-center justify-center py-2">
        <Card className="px-6 py-6 bg-white/95 shadow-md max-w-lg w-full">
          <div className="text-2xl md:text-3xl font-bold text-slate-800 text-center leading-relaxed" style={{ minHeight: '3em' }}>{q?.questionText}</div>
        </Card>
        <div className={`mt-4 min-w-[200px] h-20 md:h-24 rounded-2xl border-4 flex items-center justify-center text-4xl md:text-5xl font-extrabold px-6 bg-white ${feedback?.type === 'correct' ? 'border-emerald-500 text-emerald-700' : feedback?.type === 'wrong' ? 'border-amber-500 text-amber-700' : 'border-slate-300 text-slate-800'}`}>{typed || <span className="text-slate-300">?</span>}</div>
        <div className="h-8 mt-2 flex items-center" role="status" aria-live="polite">
          {feedback?.type === 'correct' && <div className="flex items-center gap-1 text-emerald-600 font-extrabold"><Check className="w-6 h-6" /> Nice!</div>}
          {feedback?.type === 'wrong' && <div className="flex items-center gap-1 text-amber-600 font-extrabold"><Heart className="w-6 h-6" /> Almost! Try again</div>}
        </div>
      </div>
      <NumberPad onDigit={(d) => setTyped((t) => (t + d).slice(0, 6))} onClear={() => setTyped('')} onBack={() => setTyped((t) => t.slice(0, -1))} onSubmit={submit} submitDisabled={busy || typed === ''} submitClass={theme.solid} />
    </div>
  )
}

// ============================ V1.3: Fun Math sub-section picker ==============
function FunMathPicker({ theme, onPick, onExit }) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <button onClick={onExit} aria-label="Exit" className="flex items-center gap-1 h-11 px-3 rounded-full bg-white border border-slate-200 text-slate-600 font-bold shadow-sm"><ArrowLeft className="w-5 h-5" /> Back</button>
        <h2 className="text-2xl font-extrabold text-slate-800 font-display flex-1 text-center pr-16">Fun Math</h2>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-lg mx-auto">
        <button onClick={() => onPick('read')} className="rounded-2xl p-6 bg-white/95 border-2 border-slate-200 hover:border-fuchsia-400 flex flex-col items-center gap-2 shadow-sm active:scale-95 min-h-[140px]">
          <Puzzle className="w-9 h-9 text-fuchsia-600" />
          <span className="text-xl font-extrabold text-slate-800 font-display">Read and Think</span>
          <span className="text-xs text-slate-600 text-center">20 word problems · win a character</span>
        </button>
        <button onClick={() => onPick('ordershapes')} className="rounded-2xl p-6 bg-white/95 border-2 border-slate-200 hover:border-indigo-400 flex flex-col items-center gap-2 shadow-sm active:scale-95 min-h-[140px]">
          <Sparkles className="w-9 h-9 text-indigo-600" />
          <span className="text-xl font-extrabold text-slate-800 font-display">Order and Shapes</span>
          <span className="text-xs text-slate-600 text-center">10 questions · order numbers & shapes</span>
        </button>
      </div>
    </div>
  )
}

// ============================ V1.3: inline SVG shape renderer ================
const SHAPE_ICON = {
  star: '★', heart: '♥', circle: '●',
  apple: '🍎', ball: '⚽', balloon: '🎈', bug: '🐛', car: '🚗',
  cube_block: '🧊', fish: '🐟', flower: '🌸', kite: '🪁', leaf: '🍃', train_car: '🚃',
}
const OS_FILL = { sky: '#3b82f6', mint: '#10b981', grape: '#8b5cf6', sunset: '#f97316', bubblegum: '#ec4899' }
function polyPoints(cx, cy, r, n, rot = -Math.PI / 2) {
  return Array.from({ length: n }, (_, i) => { const a = rot + (i * 2 * Math.PI) / n; return `${cx + r * Math.cos(a)},${cy + r * Math.sin(a)}` }).join(' ')
}
function Shape2D({ shape, fill }) {
  const s = { fill, stroke: '#1f2937', strokeWidth: 3, strokeLinejoin: 'round' }
  if (shape === 'circle') return <circle cx="60" cy="60" r="42" style={s} />
  if (shape === 'square') return <rect x="20" y="20" width="80" height="80" rx="4" style={s} />
  if (shape === 'rectangle') return <rect x="12" y="32" width="96" height="56" rx="4" style={s} />
  if (shape === 'triangle') return <polygon points="60,16 104,100 16,100" style={s} />
  if (shape === 'pentagon') return <polygon points={polyPoints(60, 62, 44, 5)} style={s} />
  if (shape === 'hexagon') return <polygon points={polyPoints(60, 60, 44, 6, 0)} style={s} />
  if (shape === 'trapezoid') return <polygon points="30,32 90,32 108,92 12,92" style={s} />
  if (shape === 'rhombus') return <polygon points="60,14 106,60 60,106 14,60" style={s} />
  return <rect x="20" y="20" width="80" height="80" style={s} />
}
function Shape3D({ shape, fill }) {
  const s = { fill, stroke: '#1f2937', strokeWidth: 3, strokeLinejoin: 'round' }
  const dk = { fill: '#00000030', stroke: '#1f2937', strokeWidth: 3, strokeLinejoin: 'round' }
  if (shape === 'sphere') return <g><circle cx="60" cy="60" r="42" style={s} /><ellipse cx="48" cy="46" rx="14" ry="9" fill="#ffffff66" /></g>
  if (shape === 'cylinder') return <g><rect x="26" y="30" width="68" height="60" style={s} /><ellipse cx="60" cy="30" rx="34" ry="11" style={s} /><ellipse cx="60" cy="90" rx="34" ry="11" style={dk} /></g>
  if (shape === 'cone') return <g><ellipse cx="60" cy="94" rx="36" ry="11" style={dk} /><polygon points="60,14 96,94 24,94" style={s} /></g>
  if (shape === 'pyramid') return <g><polygon points="60,16 104,96 16,96" style={s} /><polygon points="60,16 104,96 60,80" style={dk} /></g>
  // cube / rectangular prism
  const w = shape === 'rectangular prism' ? 64 : 52
  return <g><rect x="26" y="40" width={w} height="52" style={s} /><polygon points={`26,40 ${26 + 18},22 ${26 + 18 + w},22 ${26 + w},40`} style={dk} /><polygon points={`${26 + w},40 ${26 + w + 18},22 ${26 + w + 18},74 ${26 + w},92`} style={dk} /></g>
}
// --- V1.3 bank-1000-v1: figure helpers keyed off questionType ---------------
function IconRow({ icon, count, markIndex }) {
  const g = SHAPE_ICON[icon] || '★'
  // markIndex from the bank is 1-based (position 1 = "first"); convert to 0-based array index
  const mark = (Number(markIndex) || 1) - 1
  return (
    <div className="flex flex-wrap justify-center gap-2 max-w-md">
      {Array.from({ length: count || 0 }).map((_, i) => (
        <div key={i} className={`text-4xl md:text-5xl ${i === mark ? 'scale-110' : 'opacity-60'}`}>
          <span style={{ color: i === mark ? '#f59e0b' : '#64748b' }}>{g}</span>
          {i === mark && <div className="text-xs font-bold text-amber-600 text-center">↑</div>}
        </div>
      ))}
    </div>
  )
}
function ValueRow({ items, cls }) {
  return <div className="flex flex-wrap gap-2 justify-center">{(items || []).map((n, i) => <div key={i} className={`px-4 h-12 rounded-xl flex items-center text-xl font-extrabold ${cls}`}>{String(n)}</div>)}</div>
}
function RectFigure({ length, width, fill }) {
  return (
    <svg width="180" height="120" viewBox="0 0 180 120">
      <rect x="20" y="26" width="140" height="70" style={{ fill, stroke: '#1f2937', strokeWidth: 3 }} />
      <text x="90" y="18" textAnchor="middle" fontSize="15" fill="#334155" fontWeight="700">{length}</text>
      <text x="176" y="61" textAnchor="middle" fontSize="15" fill="#334155" fontWeight="700" transform="rotate(90 176 61)">{width}</text>
    </svg>
  )
}
function CompositeFigure({ rect1, rect2, fill }) {
  return (
    <div className="flex flex-col items-center gap-1">
      <svg width="180" height="120" viewBox="0 0 180 120">
        <rect x="14" y="28" width="86" height="72" style={{ fill, stroke: '#1f2937', strokeWidth: 3, strokeLinejoin: 'round' }} />
        <rect x="100" y="56" width="66" height="44" style={{ fill, stroke: '#1f2937', strokeWidth: 3, strokeLinejoin: 'round' }} />
      </svg>
      <div className="text-sm font-bold text-slate-600">{rect1?.[0]}×{rect1?.[1]} + {rect2?.[0]}×{rect2?.[1]}</div>
    </div>
  )
}
function PrismFigure({ length, width, height, fill }) {
  return (
    <div className="flex flex-col items-center">
      <svg width="150" height="130" viewBox="0 0 150 130"><Shape3D shape="rectangular prism" fill={fill} /></svg>
      <div className="text-sm font-bold text-slate-600">{length} × {width} × {height}</div>
    </div>
  )
}
function AngleFigure({ angle }) {
  const deg = angle === 'right' ? 90 : angle === 'acute' ? 45 : 130
  const rad = (deg * Math.PI) / 180
  const len = 78, ox = 26, oy = 104
  const x2 = ox + len * Math.cos(-rad), y2 = oy + len * Math.sin(-rad)
  const st = { stroke: '#1f2937', strokeWidth: 4, strokeLinecap: 'round' }
  return (
    <svg width="150" height="120" viewBox="0 0 150 120">
      <line x1={ox} y1={oy} x2={ox + len + 10} y2={oy} style={st} />
      <line x1={ox} y1={oy} x2={x2} y2={y2} style={st} />
      {angle === 'right' && <rect x={ox} y={oy - 18} width="18" height="18" fill="none" stroke="#1f2937" strokeWidth="2" />}
    </svg>
  )
}
function PartitionFigure({ parts, shaded, fill }) {
  const p = parts || 1
  return (
    <svg width="200" height="90" viewBox="0 0 200 90">
      {Array.from({ length: p }).map((_, i) => (
        <rect key={i} x={10 + i * (180 / p)} y="15" width={180 / p} height="60" style={{ fill: i < (shaded || 0) ? fill : '#ffffff', stroke: '#1f2937', strokeWidth: 2 }} />
      ))}
    </svg>
  )
}

function ShapeSVG({ q }) {
  if (!q) return null
  const qt = q.questionType
  const dd = q.displayData || {}
  const fill = OS_FILL[dd.color] || '#3b82f6'

  // ----- ORDER strand -----
  if (qt === 'ordinal_position' || qt === 'ordinal_before_after') {
    return <IconRow icon={dd.iconType} count={dd.itemCount} markIndex={dd.markedIndex} />
  }
  if (qt === 'order_numbers' || qt === 'order_numbers_list' || qt === 'order_decimals_list') {
    return <ValueRow items={dd.numbers} cls="bg-indigo-50 border border-indigo-200 text-indigo-800" />
  }
  if (qt === 'compare_fractions') {
    return <ValueRow items={dd.fractions} cls="bg-fuchsia-50 border border-fuchsia-200 text-fuchsia-800" />
  }
  if (qt === 'compare_numbers' || qt === 'compare_decimals') {
    return <div className="text-4xl font-extrabold text-slate-800 flex items-center gap-3">{String(dd.a)}<span className="text-slate-400">?</span>{String(dd.b)}</div>
  }

  // ----- SHAPES strand -----
  if (qt === 'shape_perimeter' || qt === 'shape_area') {
    return <RectFigure length={dd.length} width={dd.width} fill={fill} />
  }
  if (qt === 'shape_composite_area') {
    return <CompositeFigure rect1={dd.rect1} rect2={dd.rect2} fill={fill} />
  }
  if (qt === 'shape_volume_unit_cubes') {
    return <PrismFigure length={dd.length} width={dd.width} height={dd.height} fill={fill} />
  }
  if (qt === 'shape_angle_type') {
    return <AngleFigure angle={dd.angle} />
  }
  if (qt === 'shape_partition_name') {
    return <PartitionFigure parts={dd.parts} shaded={0} fill={fill} />
  }
  if (qt === 'shape_fraction_part') {
    return <PartitionFigure parts={dd.parts} shaded={dd.shaded} fill={fill} />
  }
  // Text/logic-only questions carry no figure data
  if (qt === 'shape_classify_quad' || qt === 'shape_hierarchy') {
    return null
  }
  // Any question that provides a `shape` renders that shape (2D or 3D)
  if (dd.shape) {
    const shape = String(dd.shape).replace(/_/g, ' ')
    const is3d = ['cube', 'rectangular prism', 'cylinder', 'cone', 'sphere', 'pyramid'].includes(shape)
    return <svg width="130" height="130" viewBox="0 0 120 120">{is3d ? <Shape3D shape={shape} fill={fill} /> : <Shape2D shape={shape} fill={fill} />}</svg>
  }

  // ----- graceful fallbacks so nothing renders blank when data is present -----
  if (Array.isArray(dd.numbers)) return <ValueRow items={dd.numbers} cls="bg-slate-50 border border-slate-200 text-slate-800" />
  if (Array.isArray(dd.fractions)) return <ValueRow items={dd.fractions} cls="bg-slate-50 border border-slate-200 text-slate-800" />
  if (dd.a !== undefined && dd.b !== undefined) return <div className="text-4xl font-extrabold text-slate-800 flex items-center gap-3">{String(dd.a)}<span className="text-slate-400">?</span>{String(dd.b)}</div>
  return null
}

// ============================ V1.3: Order and Shapes player ==================
function OrderShapes({ kid, theme, sound, api, onExit }) {
  const [qs, setQs] = useState(null)
  const [idx, setIdx] = useState(0)
  const [typed, setTyped] = useState('')
  const [feedback, setFeedback] = useState(null)
  const [done, setDone] = useState(false)
  const startedRef = useRef(false)

  useEffect(() => {
    if (startedRef.current) return
    startedRef.current = true
    ;(async () => {
      const { data } = await api(`/api/kids/${kid.id}/ordershapes`, { method: 'POST', body: JSON.stringify({ date: today() }) })
      if (data?.questions) setQs(data.questions)
    })()
  }, [api, kid.id])

  const q = qs?.[idx]
  const isMC = q && Array.isArray(q.options) && q.options.length > 0
  // Guarantee the correct answer is always one of the choices shown (defends against any bank drift)
  const options = (() => {
    if (!isMC) return []
    const ans = String(q.correctAnswer).trim()
    if (q.options.some((o) => String(o).trim() === ans)) return q.options
    const copy = [...q.options]
    copy[copy.length - 1] = q.correctAnswer
    return copy
  })()

  const advance = () => {
    setTyped(''); setFeedback(null)
    if (idx + 1 >= qs.length) { sound.fanfare(); setDone(true) }
    else setIdx((i) => i + 1)
  }
  const check = (val) => {
    const ok = String(val).trim() === String(q.correctAnswer).trim()
    if (ok) { sound.correct(); setFeedback({ type: 'correct' }); setTimeout(advance, 650) }
    else { sound.wrong(); setFeedback({ type: 'wrong' }); setTimeout(() => setFeedback(null), 800) }
  }

  useEffect(() => {
    if (isMC) return
    const onKey = (e) => { if (e.key >= '0' && e.key <= '9') setTyped((t) => (t + e.key).slice(0, 7)); else if (e.key === 'Backspace') setTyped((t) => t.slice(0, -1)); else if (e.key === 'Enter' && typed !== '') check(typed) }
    window.addEventListener('keydown', onKey); return () => window.removeEventListener('keydown', onKey)
  })

  if (done) return (
    <div className="text-center py-10">
      <div className="text-6xl mb-3">🌟</div>
      <h2 className="text-3xl font-extrabold text-emerald-700 font-display">Nice work!</h2>
      <p className="text-slate-600 mt-2">You finished 10 Order and Shapes questions.</p>
      <div className="flex gap-2 justify-center mt-5">
        <Button onClick={() => { setQs(null); setIdx(0); setDone(false); startedRef.current = false; (async () => { const { data } = await api(`/api/kids/${kid.id}/ordershapes`, { method: 'POST', body: JSON.stringify({ date: today() }) }); if (data?.questions) { setQs(data.questions); startedRef.current = true } })() }} className={`h-14 px-6 text-lg text-white ${theme.solid} font-display`}>Play again</Button>
        <Button variant="outline" onClick={onExit} className="h-14 px-6 text-lg">Done</Button>
      </div>
    </div>
  )

  if (!qs) return <div className="text-center py-20 text-slate-500 font-display">Getting your questions…</div>

  return (
    <div className="flex flex-col min-h-[calc(100vh-8rem)]">
      <div className="flex items-center gap-2 mb-3">
        <button onClick={onExit} aria-label="Exit" className="flex items-center gap-1 h-11 px-3 rounded-full bg-white border border-slate-200 text-slate-600 font-bold shadow-sm"><DoorOpen className="w-5 h-5" /> Exit</button>
        <div className="flex-1 flex items-center justify-center gap-1 font-extrabold text-indigo-600 font-display"><Sparkles className="w-5 h-5" /> Order and Shapes</div>
        <span className="text-sm font-bold text-slate-600 w-14 text-right">{idx + 1} / 10</span>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center py-2">
        <Card className="px-6 py-5 bg-white/95 shadow-md max-w-lg w-full text-center">
          <div className="text-xl md:text-2xl font-bold text-slate-800 mb-4">{q?.prompt}</div>
          <div className="flex justify-center min-h-[80px] items-center"><ShapeSVG q={q} /></div>
        </Card>

        {isMC ? (
          <div className="mt-5 w-full max-w-md grid grid-cols-1 gap-3">
            {options.map((opt) => (
              <button key={opt} onClick={() => check(opt)}
                className={`min-h-[56px] rounded-2xl border-2 text-xl font-extrabold px-4 py-3 active:scale-95 font-display bg-white ${feedback?.type === 'correct' && String(opt) === String(q.correctAnswer) ? 'border-emerald-500 text-emerald-700' : 'border-slate-300 text-slate-800 hover:border-indigo-400'}`}>
                {opt}
              </button>
            ))}
          </div>
        ) : (
          <>
            <div className={`mt-4 min-w-[180px] h-20 rounded-2xl border-4 flex items-center justify-center text-4xl font-extrabold px-6 bg-white ${feedback?.type === 'correct' ? 'border-emerald-500 text-emerald-700' : feedback?.type === 'wrong' ? 'border-amber-500 text-amber-700' : 'border-slate-300 text-slate-800'}`}>{typed || <span className="text-slate-300">?</span>}</div>
          </>
        )}

        <div className="h-8 mt-2 flex items-center" role="status" aria-live="polite">
          {feedback?.type === 'correct' && <div className="flex items-center gap-1 text-emerald-600 font-extrabold"><Check className="w-6 h-6" /> Yes!</div>}
          {feedback?.type === 'wrong' && <div className="flex items-center gap-1 text-amber-600 font-extrabold"><Heart className="w-6 h-6" /> Try again</div>}
        </div>
      </div>

      {!isMC && (
        <NumberPad onDigit={(d) => setTyped((t) => (t + d).slice(0, 7))} onClear={() => setTyped('')} onBack={() => setTyped((t) => t.slice(0, -1))} onSubmit={() => typed !== '' && check(typed)} submitDisabled={typed === ''} submitClass={theme.solid} />
      )}
    </div>
  )
}

// ============================ V1.5: Parent Dashboard =========================
// Apple HIG-inspired, read-only. The math gate below is a UX speed-bump for kids only;
// real data isolation is enforced server-side (GET /api/kids/:id/dashboard checks parent ownership).
const HIG_FONT = { fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif' }
const GATE_Q = { text: 'What is 7 × 8?', answer: 56 }
const OP_LABELS = { add: 'Addition', sub: 'Subtraction', mul: 'Multiplication', div: 'Division', fraction: 'Fractions' }
const fmtDay = (d) => { try { return new Date(d + 'T00:00:00Z').toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' }) } catch (_) { return d } }
const fmtWeekday = (d) => { try { return new Date(d + 'T00:00:00Z').toLocaleDateString('en-US', { weekday: 'narrow', timeZone: 'UTC' }) } catch (_) { return '' } }
const fmtPct = (n) => (n === null || n === undefined ? '—' : `${n}%`)

function ParentGate({ onCancel, onPass }) {
  const [val, setVal] = useState('')
  const [err, setErr] = useState('')
  const [tries, setTries] = useState(0)
  const [lockedUntil, setLockedUntil] = useState(0)
  const [now, setNow] = useState(Date.now())
  const inputRef = useRef(null)
  useEffect(() => { inputRef.current?.focus() }, [])
  useEffect(() => {
    if (!lockedUntil) return
    const t = setInterval(() => { setNow(Date.now()); if (Date.now() >= lockedUntil) { setLockedUntil(0); setErr('') } }, 500)
    return () => clearInterval(t)
  }, [lockedUntil])
  const locked = lockedUntil && now < lockedUntil
  const check = (e) => {
    e?.preventDefault()
    if (locked || val === '') return
    if (Number(val) === GATE_Q.answer) { onPass(); return }
    const n = tries + 1; setTries(n); setVal('')
    if (n >= 3) { setLockedUntil(Date.now() + 30000); setNow(Date.now()); setTries(0); setErr('Too many tries. Please wait 30 seconds.') }
    else setErr("That's not right. Please try again.")
  }
  return (
    <div className="fixed inset-0 z-[60] bg-black/40 backdrop-blur-sm flex items-center justify-center p-4" style={HIG_FONT} role="dialog" aria-modal="true" aria-labelledby="gate-title">
      <form onSubmit={check} className="w-full max-w-[320px] bg-white/95 rounded-[14px] shadow-2xl overflow-hidden text-center">
        <div className="px-5 pt-5 pb-4">
          <div className="mx-auto mb-2 w-11 h-11 rounded-full bg-[#007AFF]/10 flex items-center justify-center"><ShieldCheck className="w-6 h-6 text-[#007AFF]" /></div>
          <h2 id="gate-title" className="text-[17px] font-semibold text-black">Parents only</h2>
          <p className="text-[13px] text-[#3C3C43]/70 mt-1">Answer this to open the Parent Dashboard.</p>
          <p className="text-[22px] font-semibold text-black mt-3" data-testid="gate-question">{GATE_Q.text}</p>
          <input ref={inputRef} data-testid="gate-input" inputMode="numeric" pattern="[0-9]*" autoComplete="off" aria-label="Answer"
            value={val} disabled={!!locked} onChange={(e) => setVal(e.target.value.replace(/\D/g, '').slice(0, 4))}
            className="mt-3 w-full h-11 rounded-[10px] bg-[#767680]/[0.12] px-3 text-center text-[17px] text-black outline-none focus:ring-2 focus:ring-[#007AFF] disabled:opacity-50" placeholder="Answer" />
          <p className="min-h-[18px] mt-2 text-[13px] text-[#FF3B30]" role="status" aria-live="polite" data-testid="gate-error">
            {locked ? `Too many tries. Wait ${Math.ceil((lockedUntil - now) / 1000)}s.` : err}
          </p>
        </div>
        <div className="grid grid-cols-2 border-t border-[#3C3C43]/20">
          <button type="button" onClick={onCancel} className="h-11 text-[17px] text-[#007AFF] border-r border-[#3C3C43]/20 active:bg-black/5">Cancel</button>
          <button type="submit" data-testid="gate-submit" disabled={!!locked || val === ''} className="h-11 text-[17px] font-semibold text-[#007AFF] active:bg-black/5 disabled:text-[#3C3C43]/30">Continue</button>
        </div>
      </form>
    </div>
  )
}

function HigSection({ title, footer, children }) {
  return (
    <section className="mt-7">
      {title && <h3 className="px-4 mb-1.5 text-[13px] uppercase tracking-wide text-[#6D6D72]">{title}</h3>}
      {children}
      {footer && <p className="px-4 mt-1.5 text-[13px] text-[#6D6D72] leading-snug">{footer}</p>}
    </section>
  )
}
function HigTile({ label, value, sub, color = '#000', testid }) {
  return (
    <div className="bg-white rounded-[12px] p-3.5" data-testid={testid}>
      <div className="text-[13px] text-[#8E8E93] leading-tight">{label}</div>
      <div className="text-[28px] font-semibold tracking-tight leading-tight mt-1" style={{ color }}>{value}</div>
      {sub && <div className="text-[12px] text-[#8E8E93] mt-0.5 leading-tight">{sub}</div>}
    </div>
  )
}
function HigRow({ label, value, last, children }) {
  return (
    <div className="pl-4">
      <div className={`flex items-center justify-between gap-3 pr-4 min-h-[44px] py-2 ${last ? '' : 'border-b border-[#C6C6C8]/70'}`}>
        <div className="text-[17px] text-black min-w-0 flex-1">{label}{children}</div>
        {value !== undefined && <div className="text-[17px] text-[#8E8E93] shrink-0 text-right">{value}</div>}
      </div>
    </div>
  )
}
function HigRing({ value, color = '#34C759', size = 64 }) {
  const r = 26, c = 2 * Math.PI * r, v = value === null || value === undefined ? 0 : value
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" className="-rotate-90 shrink-0" aria-hidden>
      <circle cx="32" cy="32" r={r} fill="none" stroke="#E5E5EA" strokeWidth="7" />
      <circle cx="32" cy="32" r={r} fill="none" stroke={color} strokeWidth="7" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - v / 100)} />
    </svg>
  )
}
function HigBar({ value, color }) {
  return (
    <div className="h-1.5 rounded-full bg-[#E5E5EA] overflow-hidden mt-1.5">
      <div className="h-full rounded-full" style={{ width: `${value || 0}%`, background: color }} />
    </div>
  )
}

function ParentDashboard({ kids, api, onClose }) {
  const [selId, setSelId] = useState(kids[0]?.id || null)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey); return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  useEffect(() => {
    if (!selId) { setLoading(false); return }
    let alive = true
    setLoading(true); setError('')
    ;(async () => {
      const res = await api(`/api/kids/${selId}/dashboard?date=${today()}`)
      if (!alive) return
      if (res.ok && res.data?.dashboard) setData(res.data.dashboard)
      else { setData(null); setError(res.data?.error || 'Could not load the dashboard.') }
      setLoading(false)
    })()
    return () => { alive = false }
  }, [selId, api])

  const d = data
  const maxStars = d ? Math.max(4, ...d.activity.last14.map((x) => x.stars)) : 4

  return (
    <div className="fixed inset-0 z-50 bg-[#F2F2F7] overflow-y-auto text-black antialiased" style={HIG_FONT} data-testid="parent-dashboard">
      <div className="sticky top-0 z-10 bg-[#F2F2F7]/85 backdrop-blur-xl border-b border-[#C6C6C8]/50">
        <div className="max-w-3xl mx-auto h-11 px-4 flex items-center justify-between">
          <span className="text-[13px] text-[#8E8E93] flex items-center gap-1"><Lock className="w-3.5 h-3.5" /> Read-only</span>
          <span className="text-[17px] font-semibold">Parent Dashboard</span>
          <button onClick={onClose} data-testid="dashboard-done" className="text-[17px] font-semibold text-[#007AFF] px-1 h-11">Done</button>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 pb-16">
        <h1 className="text-[34px] font-bold tracking-tight mt-3">Dashboard</h1>
        <p className="text-[15px] text-[#8E8E93] -mt-0.5">Calculated live from your kids&apos; activity.</p>

        {kids.length > 1 && (
          <div className="mt-4 bg-[#767680]/[0.12] rounded-[9px] p-[2px] flex" role="tablist" aria-label="Choose a kid">
            {kids.map((k) => (
              <button key={k.id} role="tab" aria-selected={selId === k.id} onClick={() => setSelId(k.id)} data-testid={`dash-tab-${k.id}`}
                className={`flex-1 h-8 rounded-[7px] text-[13px] font-semibold truncate px-2 transition ${selId === k.id ? 'bg-white shadow-[0_3px_8px_rgba(0,0,0,0.12),0_3px_1px_rgba(0,0,0,0.04)]' : 'text-black/80'}`}>
                {k.firstName}
              </button>
            ))}
          </div>
        )}

        {loading && <div className="py-24 text-center text-[15px] text-[#8E8E93]">Loading…</div>}
        {!loading && error && <div className="mt-8 bg-white rounded-[12px] p-6 text-center text-[15px] text-[#FF3B30]">{error}</div>}
        {!loading && !selId && <div className="mt-8 bg-white rounded-[12px] p-6 text-center text-[15px] text-[#8E8E93]">Add a player to see their progress.</div>}

        {!loading && d && (
          <>
            {/* profile */}
            <div className="mt-5 bg-white rounded-[12px] p-4 flex items-center gap-3">
              <AvatarImg id={d.kid.avatarId} size={56} />
              <div className="flex-1 min-w-0">
                <div className="text-[20px] font-semibold truncate" data-testid="dash-kid-name">{d.kid.firstName}</div>
                <div className="text-[15px] text-[#8E8E93]">Grade {d.kid.grade} · {String(d.kid.levelLabel).replace(/[^A-Za-z ].*$/, '').trim()}</div>
              </div>
              <div className="text-right">
                <div className="text-[22px] font-semibold flex items-center gap-1 justify-end"><Star className="w-5 h-5 fill-[#FF9500] text-[#FF9500]" />{fmtStars(d.kid.totalStars)}</div>
                <div className="text-[12px] text-[#8E8E93]">total stars</div>
              </div>
            </div>

            {/* activity */}
            <HigSection title="Activity" footer="An active day is any day with a finished practice set, a finished Speed Math round, or Fun Math answers. The streak counts days in a row with a finished practice set.">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                <HigTile testid="dash-active-7" label="Active days" value={`${d.activity.activeDaysLast7}/7`} sub="last 7 days" color="#007AFF" />
                <HigTile testid="dash-active-30" label="Active days" value={d.activity.activeDaysLast30} sub="last 30 days" />
                <HigTile testid="dash-streak" label="Current streak" value={d.activity.streak} sub={`best ${d.activity.bestStreak} days`} color="#FF9500" />
                <HigTile testid="dash-active-total" label="All time" value={d.activity.activeDaysTotal} sub={d.activity.lastActive ? `last active ${fmtDay(d.activity.lastActive)}` : 'not active yet'} />
              </div>
              <div className="mt-2.5 bg-white rounded-[12px] p-4">
                <div className="flex items-baseline justify-between">
                  <div className="text-[15px] font-semibold">Stars, last 14 days</div>
                  <div className="text-[13px] text-[#8E8E93]">{fmtDay(d.activity.last14[0].date)} – {fmtDay(d.activity.last14[13].date)}</div>
                </div>
                <div className="mt-3 flex items-end gap-1 h-28" data-testid="dash-14day">
                  {d.activity.last14.map((x) => (
                    <div key={x.date} className="flex-1 flex flex-col items-center justify-end h-full gap-1" title={`${fmtDay(x.date)}: ${fmtStars(x.stars)} stars`}>
                      {x.stars > 0
                        ? <div className="w-full max-w-[18px] rounded-[4px] bg-[#007AFF]" style={{ height: `${Math.max(6, (x.stars / maxStars) * 88)}px` }} />
                        : <div className={`w-1.5 h-1.5 rounded-full ${x.active ? 'bg-[#34C759]' : 'bg-[#D1D1D6]'}`} />}
                      <div className="text-[10px] text-[#8E8E93] leading-none">{fmtWeekday(x.date)}</div>
                    </div>
                  ))}
                </div>
              </div>
            </HigSection>

            {/* practice sets */}
            <HigSection title="Practice sets" footer="First-try accuracy is the share of problems answered correctly on the first attempt.">
              <div className="bg-white rounded-[12px] overflow-hidden">
                <div className="p-4 flex items-center gap-4 border-b border-[#C6C6C8]/70">
                  <div className="relative">
                    <HigRing value={d.practice.firstTryAccuracy} color="#34C759" />
                    <div className="absolute inset-0 flex items-center justify-center text-[13px] font-semibold">{fmtPct(d.practice.firstTryAccuracy)}</div>
                  </div>
                  <div>
                    <div className="text-[17px] font-semibold" data-testid="dash-firsttry">First-try accuracy: {fmtPct(d.practice.firstTryAccuracy)}</div>
                    <div className="text-[15px] text-[#8E8E93]">{d.practice.setsCompleted} sets finished · {d.practice.problemsAttempted} problems tried</div>
                  </div>
                </div>
                {d.practice.byOperation.length === 0 && <HigRow label={<span className="text-[#8E8E93]">No problems tried yet</span>} last />}
                {d.practice.byOperation.map((o, i) => (
                  <HigRow key={o.operation} last={i === d.practice.byOperation.length - 1} label={
                    <div>
                      <div className="flex justify-between text-[17px]"><span>{OP_LABELS[o.operation] || o.operation}</span><span className="text-[#8E8E93]">{fmtPct(o.firstTryAccuracy)}</span></div>
                      <HigBar value={o.firstTryAccuracy} color={o.firstTryAccuracy >= 80 ? '#34C759' : o.firstTryAccuracy >= 60 ? '#FF9500' : '#FF3B30'} />
                      <div className="text-[12px] text-[#8E8E93] mt-1">{o.attempted} tried</div>
                    </div>
                  } />
                ))}
              </div>
            </HigSection>

            {/* speed math */}
            <HigSection title="Speed Math" footer="Stars per round range from 4 (all right) down to −1. Rounds left early earn nothing and are not included in accuracy.">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                <HigTile testid="dash-speed-rounds" label="Rounds finished" value={d.speed.sessionsFinished} sub={d.speed.sessionsLeftEarly ? `${d.speed.sessionsLeftEarly} left early` : ' '} />
                <HigTile testid="dash-speed-accuracy" label="Accuracy" value={fmtPct(d.speed.accuracy)} color="#34C759" />
                <HigTile label="Average stars" value={d.speed.avgStars === null ? '—' : fmtStars(d.speed.avgStars)} color="#FF9500" />
                <HigTile label="Best round" value={d.speed.bestStars === null ? '—' : fmtStars(d.speed.bestStars)} sub={`${d.speed.perfectSessions} perfect`} />
              </div>
              {d.speed.recent.length > 0 && (
                <div className="mt-2.5 bg-white rounded-[12px] overflow-hidden" data-testid="dash-speed-recent">
                  {d.speed.recent.map((s, i) => (
                    <HigRow key={i} last={i === d.speed.recent.length - 1}
                      label={<span>{fmtDay(s.date)} <span className="text-[#8E8E93]">· {s.correct} of {s.total} right</span></span>}
                      value={<span className="inline-flex items-center gap-1">{fmtSigned(s.stars)} <Star className="w-4 h-4 fill-[#FF9500] text-[#FF9500]" /></span>} />
                  ))}
                </div>
              )}
            </HigSection>

            {/* fun math */}
            <HigSection title="Fun Math · Read and Think" footer="A run is completed when all 20 word problems are answered correctly. First-try accuracy is tracked for runs played from this update on. Order and Shapes is unscored and not tracked.">
              <div className="bg-white rounded-[12px] overflow-hidden">
                <HigRow label="Completed" value={<span data-testid="dash-fun-completed">{d.funMath.completed} {d.funMath.completed === 1 ? 'time' : 'times'}</span>} />
                <HigRow label="Runs started" value={d.funMath.started} />
                <HigRow label="Completion rate" value={fmtPct(d.funMath.completionRate)} />
                <HigRow label="First-try accuracy" value={fmtPct(d.funMath.firstTryAccuracy)} />
                <HigRow label="Characters unlocked" value={`${d.funMath.avatarsUnlocked} of ${d.funMath.avatarsTotal}`} last />
              </div>
            </HigSection>
          </>
        )}
      </div>
    </div>
  )
}
