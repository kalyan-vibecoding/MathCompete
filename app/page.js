'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import { Switch } from '@/components/ui/switch'
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
  Check, RotateCcw, Volume2, VolumeX, Plus, Coins, Star, Pencil, LogOut,
  Delete, Heart, PartyPopper, CalendarDays, Flame, ArrowUp, ArrowDown, Sparkles,
} from 'lucide-react'

const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID
const today = () => new Date().toLocaleDateString('en-CA') // YYYY-MM-DD (device local)

const CARD_COLORS = [
  'bg-rose-600', 'bg-sky-600', 'bg-violet-600', 'bg-amber-600',
  'bg-emerald-600', 'bg-fuchsia-600', 'bg-cyan-600', 'bg-orange-600',
]

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
  const beep = (freqs, dur = 0.18, gain = 0.12, type = 'sine') => {
    if (!enabledRef.current) return
    const ctx = getCtx()
    if (!ctx) return
    if (ctx.state === 'suspended') ctx.resume()
    let t = ctx.currentTime
    freqs.forEach((f) => {
      const osc = ctx.createOscillator()
      const g = ctx.createGain()
      osc.type = type
      osc.frequency.value = f
      g.gain.setValueAtTime(0, t)
      g.gain.linearRampToValueAtTime(gain, t + 0.02)
      g.gain.exponentialRampToValueAtTime(0.0001, t + dur)
      osc.connect(g); g.connect(ctx.destination)
      osc.start(t); osc.stop(t + dur)
      t += dur * 0.85
    })
  }
  return {
    correct: () => beep([784, 1047], 0.16, 0.1, 'sine'),
    wrong: () => beep([196, 165], 0.28, 0.09, 'sine'),
    fanfare: () => beep([523, 659, 784, 1047, 1319], 0.22, 0.11, 'triangle'),
  }
}

export default function App() {
  const [booting, setBooting] = useState(true)
  const [user, setUser] = useState(null)
  const [signinError, setSigninError] = useState('')
  const [kids, setKids] = useState([])
  const [activeKid, setActiveKid] = useState(null)
  const [set, setSet] = useState(null)
  const [queue, setQueue] = useState([])
  const [typed, setTyped] = useState('')
  const [feedback, setFeedback] = useState(null) // {type, text}
  const [locked, setLocked] = useState(false)
  const [completion, setCompletion] = useState(null)
  const [reducedMotion, setReducedMotion] = useState(false)
  const [busy, setBusy] = useState(false)

  const soundRef = useRef(true)
  const sound = useSound(soundRef)

  useEffect(() => {
    if (typeof window !== 'undefined' && window.matchMedia) {
      setReducedMotion(window.matchMedia('(prefers-reduced-motion: reduce)').matches)
    }
  }, [])

  // keep sound flag in sync with active kid
  useEffect(() => { soundRef.current = activeKid ? activeKid.soundOn !== false : true }, [activeKid])

  const api = useCallback(async (path, opts = {}) => {
    const res = await fetch(path, {
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      ...opts,
    })
    const data = await res.json().catch(() => ({}))
    return { ok: res.ok, status: res.status, data }
  }, [])

  const loadKids = useCallback(async () => {
    const { data } = await api(`/api/kids?date=${today()}`)
    if (data?.kids) setKids(data.kids)
    return data?.kids || []
  }, [api])

  // boot: check session
  useEffect(() => {
    (async () => {
      const { ok, data } = await api('/api/me')
      if (ok && data?.user) { setUser(data.user); await loadKids() }
      setBooting(false)
    })()
  }, [api, loadKids])

  // ------------------------- Google sign-in ---------------------------------
  const onCredential = useCallback(async (resp) => {
    setSigninError('')
    const { ok, status, data } = await api('/api/auth/google', {
      method: 'POST', body: JSON.stringify({ credential: resp.credential }),
    })
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
          if (el) window.google.accounts.id.renderButton(el, {
            theme: 'filled_blue', size: 'large', text: 'signin_with', shape: 'pill', width: 300,
          })
        } catch (e) { /* noop */ }
      }
      if (tries > 50) clearInterval(t)
    }, 200)
    return () => clearInterval(t)
  }, [booting, user, onCredential])

  // ------------------------- confetti ---------------------------------------
  const fireConfetti = useCallback(async (big) => {
    if (reducedMotion) return
    try {
      const confetti = (await import('canvas-confetti')).default
      if (big) {
        const end = Date.now() + 900
        const colors = ['#f43f5e', '#3b82f6', '#22c55e', '#eab308', '#a855f7']
        ;(function frame() {
          confetti({ particleCount: 5, angle: 60, spread: 70, origin: { x: 0 }, colors })
          confetti({ particleCount: 5, angle: 120, spread: 70, origin: { x: 1 }, colors })
          if (Date.now() < end) requestAnimationFrame(frame)
        })()
        confetti({ particleCount: 120, spread: 100, origin: { y: 0.6 }, colors })
      } else {
        confetti({ particleCount: 30, spread: 55, startVelocity: 25, origin: { y: 0.7 }, scalar: 0.8 })
      }
    } catch (e) { /* noop */ }
  }, [reducedMotion])

  // ------------------------- kid / set actions ------------------------------
  const selectKid = (kid) => {
    setActiveKid(kid)
    setSet(null); setLocked(kid.locked); setCompletion(null); setFeedback(null)
  }

  const startSet = async (kid) => {
    setBusy(true)
    const { data } = await api(`/api/kids/${kid.id}/set`, {
      method: 'POST', body: JSON.stringify({ date: today() }),
    })
    setBusy(false)
    if (data?.locked) { setLocked(true); return }
    if (data?.set) {
      setSet(data.set)
      const unsolved = data.set.problems.filter((p) => !p.solved).map((p) => p.id)
      setQueue(unsolved)
      setTyped(''); setFeedback(null); setCompletion(null); setLocked(false)
    }
  }

  const resetSet = async () => {
    if (!set) return
    setBusy(true)
    const { data } = await api(`/api/sets/${set.id}/reset`, {
      method: 'POST', body: JSON.stringify({ date: today() }),
    })
    setBusy(false)
    if (data?.set) {
      setSet(data.set)
      setQueue(data.set.problems.map((p) => p.id))
      setTyped(''); setFeedback(null)
    }
  }

  const currentId = queue[0]
  const currentProblem = set?.problems.find((p) => p.id === currentId)
  const solvedCount = set ? set.problems.filter((p) => p.solved).length : 0

  const submit = useCallback(async () => {
    if (!set || !currentId || typed === '' || busy) return
    setBusy(true)
    const { data } = await api(`/api/sets/${set.id}/answer`, {
      method: 'POST', body: JSON.stringify({ problemId: currentId, answer: Number(typed) }),
    })
    setBusy(false)
    if (!data) return
    if (data.correct) {
      sound.correct(); fireConfetti(false)
      setFeedback({ type: 'correct', text: data.encouragement || 'Great!' })
      setSet((prev) => ({
        ...prev,
        problems: prev.problems.map((p) => p.id === currentId ? { ...p, solved: true } : p),
      }))
      setTyped('')
      if (data.setComplete) {
        sound.fanfare(); fireConfetti(true)
        setQueue([])
        setCompletion({
          dollarsEarned: data.dollarsEarned, dollarsToday: data.dollarsToday,
          totalDollars: data.totalDollars, locked: data.locked,
          levelChanged: data.levelChanged, levelDirection: data.levelDirection,
          levelLabel: data.levelLabel, streak: data.streak,
        })
        await loadKids()
      } else {
        setQueue((q) => q.slice(1))
      }
    } else {
      sound.wrong()
      setFeedback({ type: 'wrong', text: data.message || 'Almost! Try again' })
      setTyped('')
      setQueue((q) => q.length > 1 ? [...q.slice(1), q[0]] : q)
    }
    setTimeout(() => setFeedback(null), 1200)
  }, [set, currentId, typed, busy, api, sound, fireConfetti, loadKids])

  // physical keyboard
  useEffect(() => {
    if (!set || completion) return
    const onKey = (e) => {
      if (e.key >= '0' && e.key <= '9') setTyped((t) => (t + e.key).slice(0, 7))
      else if (e.key === 'Backspace') setTyped((t) => t.slice(0, -1))
      else if (e.key === 'Enter') submit()
      else if (e.key === 'Escape') setTyped('')
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [set, completion, submit])

  const toggleSound = async () => {
    if (!activeKid) return
    const next = !(activeKid.soundOn !== false)
    soundRef.current = next
    setActiveKid((k) => ({ ...k, soundOn: next }))
    await api(`/api/kids/${activeKid.id}`, { method: 'PUT', body: JSON.stringify({ soundOn: next }) })
    loadKids()
  }

  const signOut = async () => {
    await api('/api/auth/logout', { method: 'POST' })
    setUser(null); setKids([]); setActiveKid(null); setSet(null)
  }

  // =========================== RENDER =======================================
  if (booting) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-2xl font-bold text-slate-500 animate-pulse">Loading MathCompete…</div>
      </div>
    )
  }

  if (!user) return <SignIn error={signinError} />

  return (
    <div className="min-h-screen bg-gradient-to-b from-indigo-50 via-white to-emerald-50">
      <header className="sticky top-0 z-20 bg-white/90 backdrop-blur border-b border-slate-200">
        <div className="max-w-3xl mx-auto px-4 h-14 flex items-center justify-between">
          <button
            onClick={() => { setActiveKid(null); setSet(null); setCompletion(null) }}
            className="flex items-center gap-2 font-extrabold text-xl text-indigo-700"
          >
            <Sparkles className="w-6 h-6" /> MathCompete
          </button>
          <div className="flex items-center gap-2">
            {activeKid && !set && (
              <Button variant="ghost" size="sm" onClick={() => setActiveKid(null)}>Switch player</Button>
            )}
            <Button variant="outline" size="sm" onClick={signOut} className="gap-1">
              <LogOut className="w-4 h-4" /> Sign out
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-6">
        {!activeKid && (
          <Picker kids={kids} onSelect={selectKid} onAdd={loadKids} api={api} />
        )}

        {activeKid && !set && (
          <KidHome
            kid={activeKid} locked={locked} busy={busy}
            onPlay={() => startSet(activeKid)}
            onToggleSound={toggleSound}
            onGradeChange={async (grade) => {
              await api(`/api/kids/${activeKid.id}`, { method: 'PUT', body: JSON.stringify({ grade }) })
              const list = await loadKids()
              const updated = list.find((k) => k.id === activeKid.id)
              if (updated) setActiveKid(updated)
            }}
          />
        )}

        {activeKid && set && (
          <Game
            problem={currentProblem} solvedCount={solvedCount} total={30}
            typed={typed} setTyped={setTyped} onSubmit={submit}
            feedback={feedback} onReset={resetSet} busy={busy}
            soundOn={activeKid.soundOn !== false} onToggleSound={toggleSound}
            reducedMotion={reducedMotion}
          />
        )}
      </main>

      {completion && (
        <CompletionOverlay
          data={completion} reducedMotion={reducedMotion}
          onClose={async () => {
            const c = completion
            setCompletion(null); setSet(null); setQueue([])
            const list = await loadKids()
            const updated = list.find((k) => k.id === activeKid.id)
            if (updated) { setActiveKid(updated); setLocked(updated.locked) }
            else if (c.locked) setLocked(true)
          }}
        />
      )}
    </div>
  )
}

// ------------------------------- Sign In -------------------------------------
function SignIn({ error }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-b from-indigo-100 to-emerald-100 px-4">
      <div className="text-center mb-8">
        <div className="text-6xl mb-3">🧮</div>
        <h1 className="text-4xl md:text-5xl font-extrabold text-indigo-800">MathCompete</h1>
        <p className="text-lg text-slate-600 mt-2 max-w-md">
          A daily math game for kids in grades 1–5. Parents sign in to set up players.
        </p>
      </div>
      <Card className="w-full max-w-sm p-6 flex flex-col items-center gap-4 shadow-xl">
        <h2 className="text-xl font-bold text-slate-800">Parent Sign-In</h2>
        <p className="text-sm text-slate-500 text-center">
          Access is limited to families on the allowlist.
        </p>
        <div id="gbtn" className="flex justify-center min-h-[44px]" />
        {error && (
          <p role="alert" className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md p-3 text-center">
            {error}
          </p>
        )}
      </Card>
    </div>
  )
}

// ------------------------------- Picker --------------------------------------
function Picker({ kids, onSelect, onAdd, api }) {
  const [open, setOpen] = useState(false)
  const [firstName, setFirstName] = useState('')
  const [grade, setGrade] = useState('1')
  const [err, setErr] = useState('')
  const [saving, setSaving] = useState(false)

  const addKid = async () => {
    setErr(''); setSaving(true)
    const res = await api('/api/kids', {
      method: 'POST', body: JSON.stringify({ firstName, grade: Number(grade) }),
    })
    setSaving(false)
    if (!res.ok) { setErr(res.data?.error || 'Could not add player.'); return }
    setFirstName(''); setGrade('1'); setOpen(false)
    onAdd()
  }

  return (
    <div>
      <h2 className="text-3xl font-extrabold text-slate-800 mb-1">Choose your player</h2>
      <p className="text-slate-500 mb-6">Tap a card to start playing.</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {kids.map((kid, i) => (
          <button
            key={kid.id}
            onClick={() => onSelect(kid)}
            className={`${CARD_COLORS[i % CARD_COLORS.length]} text-white rounded-2xl p-6 text-left shadow-lg hover:scale-[1.02] active:scale-95 transition-transform min-h-[44px]`}
          >
            <div className="flex items-center justify-between">
              <span className="text-3xl font-extrabold">{kid.firstName}</span>
              <span className="text-4xl">🎈</span>
            </div>
            <div className="mt-2 text-white/90 font-semibold">Grade {kid.grade}</div>
            <div className="mt-4 flex items-center gap-2 bg-white/20 rounded-full px-3 py-1 w-fit">
              <Coins className="w-5 h-5" />
              <span className="font-bold text-lg">${kid.totalDollars}</span>
            </div>
          </button>
        ))}

        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <button className="border-2 border-dashed border-slate-300 rounded-2xl p-6 flex flex-col items-center justify-center gap-2 text-slate-500 hover:border-indigo-400 hover:text-indigo-600 transition-colors min-h-[120px]">
              <Plus className="w-8 h-8" />
              <span className="font-bold text-lg">New player</span>
            </button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Add a new player</DialogTitle></DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label htmlFor="fn">First name</Label>
                <Input id="fn" value={firstName} onChange={(e) => setFirstName(e.target.value)} placeholder="e.g. Aarav" />
              </div>
              <div className="space-y-2">
                <Label>Grade</Label>
                <Select value={grade} onValueChange={setGrade}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {[1, 2, 3, 4, 5].map((g) => <SelectItem key={g} value={String(g)}>Grade {g}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              {err && <p className="text-sm text-red-600">{err}</p>}
            </div>
            <DialogFooter>
              <Button onClick={addKid} disabled={saving || !firstName.trim()}>
                {saving ? 'Adding…' : 'Add player'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  )
}

// ------------------------------- KidHome -------------------------------------
function KidHome({ kid, locked, busy, onPlay, onToggleSound, onGradeChange }) {
  const [editOpen, setEditOpen] = useState(false)
  const [grade, setGrade] = useState(String(kid.grade))

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-extrabold text-slate-800">Hi {kid.firstName}! 👋</h2>
          <div className="flex items-center gap-2 mt-1 text-indigo-700 font-bold">
            <Star className="w-5 h-5 fill-amber-400 text-amber-400" /> {kid.levelLabel}
          </div>
        </div>
        <button onClick={onToggleSound} aria-label={kid.soundOn !== false ? 'Turn sound off' : 'Turn sound on'}
          className="w-12 h-12 rounded-full bg-white border border-slate-200 flex items-center justify-center shadow-sm">
          {kid.soundOn !== false ? <Volume2 className="w-6 h-6 text-indigo-600" /> : <VolumeX className="w-6 h-6 text-slate-400" />}
        </button>
      </div>

      <Card className="p-6 bg-gradient-to-br from-amber-400 to-orange-500 text-white shadow-lg">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-white/90 font-semibold">Total earned</div>
            <div className="text-5xl font-extrabold flex items-center gap-2">
              <Coins className="w-10 h-10" /> ${kid.totalDollars}
            </div>
          </div>
          <div className="text-6xl">💰</div>
        </div>
      </Card>

      <div className="grid grid-cols-3 gap-3">
        <StatBox icon={<CalendarDays className="w-5 h-5" />} label="Days played" value={kid.daysPlayed} />
        <StatBox icon={<Flame className="w-5 h-5" />} label="Day streak" value={kid.streak} />
        <StatBox icon={<Coins className="w-5 h-5" />} label="Today" value={`$${kid.todayCompleted * 2}`} />
      </div>

      {locked ? (
        <Card className="p-8 text-center bg-emerald-50 border-emerald-200">
          <div className="text-5xl mb-3">🌙</div>
          <h3 className="text-2xl font-extrabold text-emerald-800">Come back tomorrow!</h3>
          <p className="text-emerald-700 mt-1">You earned all $4 for today. Amazing work!</p>
        </Card>
      ) : (
        <Button onClick={onPlay} disabled={busy}
          className="w-full h-20 text-3xl font-extrabold rounded-2xl bg-emerald-600 hover:bg-emerald-700 shadow-lg">
          {busy ? 'Getting ready…' : `▶ Play (${2 - kid.todayCompleted} left today)`}
        </Button>
      )}

      {kid.history?.length > 0 && (
        <Card className="p-4">
          <h3 className="font-bold text-slate-700 mb-2">Your history</h3>
          <p className="text-sm text-slate-500 mb-3">{kid.daysPlayed} days played, ${kid.totalDollars} earned</p>
          <div className="flex flex-wrap gap-2">
            {kid.history.slice(-14).map((h) => (
              <div key={h.date} className="flex items-center gap-1 bg-indigo-50 text-indigo-700 rounded-full px-3 py-1 text-sm font-semibold">
                <span>{h.date.slice(5)}</span>
                <span className="text-emerald-600">${h.dollars}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      <div className="flex justify-center pt-2">
        <Dialog open={editOpen} onOpenChange={setEditOpen}>
          <DialogTrigger asChild>
            <Button variant="ghost" size="sm" className="gap-1 text-slate-500">
              <Pencil className="w-4 h-4" /> Change grade (parent)
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Change {kid.firstName}'s grade</DialogTitle></DialogHeader>
            <p className="text-sm text-slate-500">This resets the difficulty level for the new grade. Dollars and history are kept.</p>
            <Select value={grade} onValueChange={setGrade}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {[1, 2, 3, 4, 5].map((g) => <SelectItem key={g} value={String(g)}>Grade {g}</SelectItem>)}
              </SelectContent>
            </Select>
            <DialogFooter>
              <Button onClick={() => { onGradeChange(Number(grade)); setEditOpen(false) }}>Save</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  )
}

function StatBox({ icon, label, value }) {
  return (
    <Card className="p-3 text-center">
      <div className="flex justify-center text-indigo-500 mb-1">{icon}</div>
      <div className="text-2xl font-extrabold text-slate-800">{value}</div>
      <div className="text-xs text-slate-500 font-medium">{label}</div>
    </Card>
  )
}

// ------------------------------- Game ----------------------------------------
function Game({ problem, solvedCount, total, typed, setTyped, onSubmit, feedback, onReset, busy, soundOn, onToggleSound, reducedMotion }) {
  const pct = Math.round((solvedCount / total) * 100)
  const press = (d) => setTyped((t) => (t + d).slice(0, 7))
  const clear = () => setTyped('')
  const back = () => setTyped((t) => t.slice(0, -1))

  const pad = ['1', '2', '3', '4', '5', '6', '7', '8', '9']

  return (
    <div className="flex flex-col min-h-[calc(100vh-8rem)]">
      {/* top: progress + controls */}
      <div className="flex items-center gap-3 mb-3">
        <Progress value={pct} className="h-4" />
        <span className="text-sm font-bold text-slate-600 whitespace-nowrap">{solvedCount}/{total}</span>
        <button onClick={onToggleSound} aria-label={soundOn ? 'Turn sound off' : 'Turn sound on'}
          className="w-11 h-11 rounded-full bg-white border border-slate-200 flex items-center justify-center shrink-0">
          {soundOn ? <Volume2 className="w-5 h-5 text-indigo-600" /> : <VolumeX className="w-5 h-5 text-slate-400" />}
        </button>
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <button aria-label="Start fresh" className="w-11 h-11 rounded-full bg-white border border-slate-200 flex items-center justify-center shrink-0">
              <RotateCcw className="w-5 h-5 text-slate-500" />
            </button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Start fresh?</AlertDialogTitle>
              <AlertDialogDescription>Your current 30 questions will go away and you'll get 30 new ones. This earns nothing.</AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Keep playing</AlertDialogCancel>
              <AlertDialogAction onClick={onReset}>Start fresh</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>

      {/* problem display */}
      <div className="flex-1 flex flex-col items-center justify-center py-4">
        <div className="text-slate-400 font-semibold mb-2">Solve it!</div>
        <div className="text-6xl md:text-8xl font-extrabold text-slate-800 tracking-tight text-center px-2"
          style={{ minHeight: '1.2em' }}>
          {problem?.display}
        </div>

        {/* answer box */}
        <div className={`mt-6 min-w-[200px] h-24 md:h-28 rounded-2xl border-4 flex items-center justify-center text-5xl md:text-6xl font-extrabold px-6
          ${feedback?.type === 'correct' ? 'border-emerald-500 bg-emerald-50 text-emerald-700'
            : feedback?.type === 'wrong' ? 'border-amber-500 bg-amber-50 text-amber-700'
            : 'border-slate-300 bg-white text-slate-800'}`}>
          {typed || <span className="text-slate-300">?</span>}
        </div>

        {/* feedback (color + icon + word, never color alone) */}
        <div className="h-12 mt-3 flex items-center" role="status" aria-live="polite">
          {feedback?.type === 'correct' && (
            <div className="flex items-center gap-2 text-emerald-600 font-extrabold text-2xl">
              <Check className="w-7 h-7" /> {feedback.text}
            </div>
          )}
          {feedback?.type === 'wrong' && (
            <div className="flex items-center gap-2 text-amber-600 font-extrabold text-2xl">
              <Heart className="w-7 h-7" /> {feedback.text}
            </div>
          )}
        </div>
      </div>

      {/* number pad */}
      <div className="pb-4">
        <div className="grid grid-cols-3 gap-2 max-w-sm mx-auto">
          {pad.map((d) => (
            <PadKey key={d} onClick={() => press(d)}>{d}</PadKey>
          ))}
          <PadKey onClick={clear} variant="muted" aria-label="Clear">C</PadKey>
          <PadKey onClick={() => press('0')}>0</PadKey>
          <PadKey onClick={back} variant="muted" aria-label="Delete"><Delete className="w-7 h-7" /></PadKey>
        </div>
        <div className="max-w-sm mx-auto mt-2">
          <Button onClick={onSubmit} disabled={busy || typed === ''}
            className="w-full h-16 text-2xl font-extrabold rounded-xl bg-indigo-600 hover:bg-indigo-700">
            <Check className="w-7 h-7 mr-2" /> Submit
          </Button>
        </div>
      </div>
    </div>
  )
}

function PadKey({ children, onClick, variant, ...rest }) {
  const base = 'h-16 md:h-20 rounded-xl text-3xl font-extrabold flex items-center justify-center active:scale-90 transition-transform shadow-sm'
  const style = variant === 'muted'
    ? 'bg-slate-200 text-slate-700 hover:bg-slate-300'
    : 'bg-white text-slate-800 border border-slate-200 hover:bg-slate-50'
  return (
    <button onClick={onClick} className={`${base} ${style}`} {...rest}>{children}</button>
  )
}

// --------------------------- Completion Overlay ------------------------------
function CompletionOverlay({ data, onClose, reducedMotion }) {
  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <Card className="w-full max-w-md p-8 text-center bg-gradient-to-br from-emerald-50 to-indigo-50 shadow-2xl">
        {reducedMotion
          ? <div className="text-7xl mb-2">🌟</div>
          : <div className="text-7xl mb-2 animate-bounce">🎉</div>}
        <h2 className="text-3xl font-extrabold text-emerald-700 flex items-center justify-center gap-2">
          <PartyPopper className="w-8 h-8" /> Set complete!
        </h2>
        <div className="mt-4 text-6xl font-extrabold text-amber-500 flex items-center justify-center gap-2">
          <Coins className="w-12 h-12" /> +${data.dollarsEarned}
        </div>
        <p className="text-slate-600 mt-2 font-semibold">Total: ${data.totalDollars} · Today: ${data.dollarsToday}</p>

        {data.levelChanged && data.levelDirection === 'up' && (
          <div className="mt-4 flex items-center justify-center gap-2 text-indigo-700 font-bold bg-indigo-100 rounded-full py-2 px-4">
            <ArrowUp className="w-5 h-5" /> Level up! Now {data.levelLabel}
          </div>
        )}
        {data.levelChanged && data.levelDirection === 'down' && (
          <div className="mt-4 flex items-center justify-center gap-2 text-sky-700 font-bold bg-sky-100 rounded-full py-2 px-4">
            <ArrowDown className="w-5 h-5" /> Let's practice a bit more · {data.levelLabel}
          </div>
        )}

        {data.locked ? (
          <div className="mt-5">
            <div className="text-2xl mb-2">🌙</div>
            <p className="font-bold text-slate-700">That's 2 sets today — come back tomorrow!</p>
            <Button onClick={onClose} className="mt-4 w-full h-14 text-xl font-bold">Done</Button>
          </div>
        ) : (
          <Button onClick={onClose} className="mt-6 w-full h-14 text-xl font-bold bg-emerald-600 hover:bg-emerald-700">
            Keep going
          </Button>
        )}
      </Card>
    </div>
  )
}
