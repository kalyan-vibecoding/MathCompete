// =============================================================================
// MathCompete API — single catch-all route for all backend endpoints.
//
// Environment variables read in this file (server-side only, never sent to browser):
//   MONGO_URL          - MongoDB connection string
//   DB_NAME            - MongoDB database name
//   GOOGLE_CLIENT_ID   - Google OAuth Web client ID (audience for ID-token verify)
//   ALLOWED_EMAILS     - allowlist "email:label:name" comma separated per parent
//   JWT_SECRET         - secret used to sign parent session cookies
// (NEXT_PUBLIC_GOOGLE_CLIENT_ID is used client-side only, in the browser.)
//
// Collections: users, kids, dailySets, reference (existing) + speedSessions (new).
// All additions are backward compatible: new fields / new collections only.
// No stored star/dollar totals anywhere — everything is computed live.
// =============================================================================

import { NextResponse } from 'next/server'
import { MongoClient } from 'mongodb'
import { OAuth2Client } from 'google-auth-library'
import { SignJWT, jwtVerify } from 'jose'
import { v4 as uuidv4 } from 'uuid'

// ----------------------------- constants -------------------------------------
const MAX_STEP = 4
const SET_SIZE = 30
const SPEED_SIZE = 10
const SPEED_SECONDS = 180        // 3 minutes
const SPEED_GRACE = 10           // network grace window
const MAX_SPEED_PER_DAY = 3
const COOKIE = 'mc_session'
const THEMES = ['animals', 'ocean', 'dinosaurs', 'space', 'forest']

const LEVEL_LABELS = ['Explorer', 'Adventurer', 'Champion', 'Master', 'Legend']
const ENCOURAGEMENTS = [
  'Amazing!', 'You rock!', 'Super brain!', 'Way to go!', 'Brilliant!',
  'Fantastic!', "You're a star!", 'Math wizard!', 'Awesome!', 'Genius!',
]

function levelLabel(step) {
  const i = Math.min(Math.max(step, 0), 4)
  return `${LEVEL_LABELS[i]} ${'\u2b50'.repeat(i + 1)}`
}
function round1(n) { return Math.round(n * 10) / 10 }
function clamp0(n) { return Math.max(0, n) }

// ----------------------------- mongo -----------------------------------------
let cached = global._mc_mongo
if (!cached) cached = global._mc_mongo = { client: null, promise: null, seeded: false }

async function getDb() {
  if (!cached.client) {
    if (!cached.promise) cached.promise = MongoClient.connect(process.env.MONGO_URL)
    cached.client = await cached.promise
  }
  const db = cached.client.db(process.env.DB_NAME)
  if (!cached.seeded) {
    const ref = db.collection('reference')
    const count = await ref.countDocuments()
    if (count === 0) {
      await ref.insertMany([
        { id: uuidv4(), key: 'encouragements', values: ENCOURAGEMENTS },
        { id: uuidv4(), key: 'levelLabels', values: LEVEL_LABELS },
      ])
    }
    cached.seeded = true
  }
  return db
}

// ----------------------------- auth helpers ----------------------------------
function secret() { return new TextEncoder().encode(process.env.JWT_SECRET) }

async function makeSession(userId, email) {
  return await new SignJWT({ email, role: 'parent' })
    .setProtectedHeader({ alg: 'HS256', typ: 'JWT' })
    .setSubject(userId)
    .setIssuedAt()
    .setExpirationTime('30d')
    .sign(secret())
}

async function getParent(req) {
  const token = req.cookies.get(COOKIE)?.value
  if (!token) return null
  try {
    const { payload } = await jwtVerify(token, secret())
    if (payload.role !== 'parent' || !payload.sub) return null
    const db = await getDb()
    const user = await db.collection('users').findOne({ id: payload.sub })
    return user || null
  } catch (e) {
    return null
  }
}

function parseAllowlist() {
  const raw = process.env.ALLOWED_EMAILS || ''
  const map = {}
  raw.split(',').forEach((entry) => {
    const parts = entry.split(':').map((s) => s.trim())
    const email = (parts[0] || '').toLowerCase()
    if (!email) return
    map[email] = { label: parts[1] || '', name: parts[2] || '' }
  })
  return map
}

function rateOk(ip) {
  const store = global._mc_rl || (global._mc_rl = {})
  const now = Date.now()
  const win = 5 * 60 * 1000
  const max = 15
  const e = store[ip] || { count: 0, start: now }
  if (now - e.start > win) { e.count = 0; e.start = now }
  e.count++
  store[ip] = e
  return e.count <= max
}

// ----------------------------- problem generation ----------------------------
function randInt(min, max) { return Math.floor(Math.random() * (max - min + 1)) + min }
function pick(arr) { return arr[randInt(0, arr.length - 1)] }
function shuffle(a) {
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

function opsFor(grade, step) {
  if (grade === 1) return step >= 2 ? ['add', 'sub', 'mul'] : ['add', 'sub']
  if (grade === 2 || grade === 3) return ['add', 'sub', 'mul', 'div']
  return ['add', 'sub', 'mul', 'div', 'fraction'] // grades 4 & 5
}

function addSubMax(grade, step) {
  if (grade === 1) return step === 0 ? 9 : Math.min(9 + step * 10, 60)
  if (grade === 2) return Math.min(90 + step * 30, 999)
  if (grade === 3) return Math.min(300 + step * 100, 999)
  return Math.min(600 + step * 400, 5000) // grades 4-5
}

function makeAdd(grade, step) {
  const max = addSubMax(grade, step)
  const lo = grade === 1 ? 1 : (grade >= 4 ? 100 : 10)
  const a = randInt(lo, max), b = randInt(lo, max)
  return { operation: 'add', operands: [a, b], display: `${a} + ${b}`, correctAnswer: a + b }
}
function makeSub(grade, step) {
  const max = addSubMax(grade, step)
  const lo = grade === 1 ? 1 : (grade >= 4 ? 100 : 10)
  const a = randInt(lo, max)
  const b = randInt(grade === 1 ? 0 : 1, a)
  return { operation: 'sub', operands: [a, b], display: `${a} - ${b}`, correctAnswer: a - b }
}
function makeMul(grade, step) {
  let t, o
  if (grade === 1) { t = randInt(1, 5); o = randInt(1, 5) }
  else if (grade === 2) { t = randInt(2, 10); o = randInt(2, 10) }
  else if (grade === 3) { t = randInt(2, Math.min(10 + step, 12)); o = randInt(2, 10) }
  else { const m = Math.min(12 + step * 2, 20); t = randInt(2, m); o = randInt(2, m) }
  return { operation: 'mul', operands: [t, o], display: `${t} \u00d7 ${o}`, correctAnswer: t * o }
}
function makeDiv(grade, step) {
  let divisorMax, dividendMax
  if (grade === 2) { divisorMax = 10; dividendMax = 100 }
  else if (grade === 3) { divisorMax = Math.min(10 + step, 12); dividendMax = Math.min(100 + step * 20, 144) }
  else { divisorMax = Math.min(12 + step * 2, 20); dividendMax = Math.min(200 + step * 50, 500) }
  const divisor = randInt(2, divisorMax)
  const qMax = Math.max(2, Math.floor(dividendMax / divisor))
  const quotient = randInt(2, qMax)
  const dividend = divisor * quotient
  return { operation: 'div', operands: [dividend, divisor], display: `${dividend} \u00f7 ${divisor}`, correctAnswer: quotient }
}
function makeFraction(grade, step) {
  const denom = pick([2, 3, 4, 5])
  const num = randInt(1, denom - 1)
  const k = randInt(2, 10)
  const whole = denom * k
  return { operation: 'fraction', operands: [num, denom, whole], display: `${num}/${denom} of ${whole}`, correctAnswer: num * k }
}
function makeProblem(op, grade, step) {
  if (op === 'add') return makeAdd(grade, step)
  if (op === 'sub') return makeSub(grade, step)
  if (op === 'mul') return makeMul(grade, step)
  if (op === 'div') return makeDiv(grade, step)
  return makeFraction(grade, step)
}

// Generate `count` unique problems, excluding any display strings in `exclude`.
// If it cannot find enough unique problems, it gradually widens the numbers
// (by nudging the effective step up) rather than failing or looping forever.
function generateProblems(grade, step, count, exclude) {
  const problems = []
  const seen = new Set(exclude || [])
  let guard = 0
  let widen = 0
  while (problems.length < count && guard < 12000) {
    guard++
    const effStep = step + widen
    const ops = opsFor(grade, effStep)
    const op = ops[problems.length % ops.length]
    const p = makeProblem(op, grade, effStep)
    if (seen.has(p.display)) {
      if (guard % 2000 === 0) {
        widen += 1
        console.warn(`[MathCompete] generation widening (grade=${grade}, baseStep=${step}, widen=${widen})`)
      }
      continue
    }
    seen.add(p.display)
    problems.push({ id: uuidv4(), ...p, attempts: 0, firstTryCorrect: false, solved: false })
  }
  return shuffle(problems)
}

// client-safe view of a normal-set problem (NEVER includes correctAnswer)
function clientProblem(p) {
  return { id: p.id, operation: p.operation, display: p.display, solved: p.solved, attempts: p.attempts }
}
function clientSet(s) {
  return { id: s.id, date: s.date, status: s.status, problems: s.problems.map(clientProblem) }
}
// client-safe view of a speed session (NEVER includes correctAnswer)
function clientSpeed(s) {
  return {
    id: s.id, date: s.date, sessionNumber: s.sessionNumber, status: s.status,
    startedAt: new Date(s.startedAt).getTime(), timeLimit: SPEED_SECONDS,
    problems: s.problems.map((p) => ({ id: p.id, operation: p.operation, display: p.display, answered: !!p.answered, correct: !!p.correct })),
  }
}

// ----------------------------- shared helpers --------------------------------
function ymd(d) { return d.toISOString().slice(0, 10) }

// mark any in_progress set/session from a PAST day as expired (dead — no stars).
async function expireStale(db, kidId, today) {
  if (!today) return
  await db.collection('dailySets').updateMany(
    { kidId, status: 'in_progress', date: { $ne: today } }, { $set: { status: 'expired' } })
  await db.collection('speedSessions').updateMany(
    { kidId, status: 'in_progress', date: { $ne: today } }, { $set: { status: 'expired' } })
}

// every problem display already shown to this kid on this date (both modes).
async function usedDisplays(db, kidId, date) {
  const out = new Set()
  const sets = await db.collection('dailySets').find({ kidId, date }).toArray()
  for (const s of sets) for (const p of (s.problems || [])) out.add(p.display)
  const sess = await db.collection('speedSessions').find({ kidId, date }).toArray()
  for (const s of sess) for (const p of (s.problems || [])) out.add(p.display)
  return out
}

// live score of a speed session: 4 - 0.5 per wrong/unanswered problem.
function speedScore(session) {
  const wrong = (session.problems || []).filter((p) => !p.correct).length
  return 4 - 0.5 * wrong
}

// ----------------------------- stats (all computed live) ---------------------
function computeStreak(dates) {
  if (!dates.length) return 0
  const set = new Set(dates)
  const sorted = [...dates].sort()
  let d = new Date(sorted[sorted.length - 1] + 'T00:00:00Z')
  let streak = 0
  while (set.has(ymd(d))) { streak++; d.setUTCDate(d.getUTCDate() - 1) }
  return streak
}

async function kidStats(db, kid, today) {
  const completed = await db.collection('dailySets').find({ kidId: kid.id, status: 'completed' }).toArray()
  // Only FINISHED speed sessions contribute stars. 'exited' = no change, 'expired' = dead (no stars).
  const finishedSpeed = await db.collection('speedSessions').find({ kidId: kid.id, status: 'finished' }).toArray()

  const normalStars = completed.length * 2
  const speedStars = finishedSpeed.reduce((s, x) => s + speedScore(x), 0)
  const totalStars = round1(clamp0(normalStars + speedStars))

  const byDate = {}
  for (const s of completed) byDate[s.date] = (byDate[s.date] || 0) + 2
  for (const x of finishedSpeed) byDate[x.date] = (byDate[x.date] || 0) + speedScore(x)
  const dates = Object.keys(byDate).sort()
  const history = dates.map((d) => ({ date: d, stars: round1(clamp0(byDate[d])) }))

  const normalDates = [...new Set(completed.map((s) => s.date))].sort()
  const todayCompleted = today ? completed.filter((s) => s.date === today).length : 0

  let speedUsedToday = 0
  let speedEver = false
  if (today) {
    speedUsedToday = await db.collection('speedSessions')
      .countDocuments({ kidId: kid.id, date: today, status: { $in: ['finished', 'exited', 'expired'] } })
  }
  speedEver = (await db.collection('speedSessions').countDocuments({ kidId: kid.id })) > 0

  return {
    id: kid.id,
    firstName: kid.firstName,
    grade: kid.grade,
    soundOn: kid.soundOn !== false,
    theme: THEMES.includes(kid.theme) ? kid.theme : 'animals',
    difficultyStep: kid.difficultyStep || 0,
    levelLabel: levelLabel(kid.difficultyStep || 0),
    totalStars,
    todayStars: today ? round1(clamp0(byDate[today] || 0)) : 0,
    daysPlayed: dates.length,
    streak: computeStreak(normalDates),
    history,
    todayCompleted,
    locked: todayCompleted >= 2,
    speedUsedToday,
    speedRemaining: Math.max(0, MAX_SPEED_PER_DAY - speedUsedToday),
    speedLocked: speedUsedToday >= MAX_SPEED_PER_DAY,
    speedEver,
  }
}

// ----------------------------- responses -------------------------------------
function json(data, status = 200) { return NextResponse.json(data, { status }) }
function unauthorized() { return json({ error: 'Not signed in' }, 401) }

async function finalizeSpeed(db, session, status) {
  await db.collection('speedSessions').updateOne(
    { id: session.id }, { $set: { status, problems: session.problems, finishedAt: new Date() } })
  session.status = status
}

async function speedResultPayload(db, kid, session, today) {
  const stats = await kidStats(db, kid, today)
  const wrong = session.problems.filter((p) => !p.correct).length
  return {
    sessionComplete: true,
    starsEarned: round1(speedScore(session)),
    wrong,
    perfect: wrong === 0,
    totalStars: stats.totalStars,
    todayStars: stats.todayStars,
    speedUsedToday: stats.speedUsedToday,
    speedRemaining: stats.speedRemaining,
    speedLocked: stats.speedLocked,
  }
}

// ----------------------------- main router -----------------------------------
async function route(req, method) {
  const url = new URL(req.url)
  const parts = url.pathname.replace(/^\/api\/?/, '').split('/').filter(Boolean)
  const body = ['POST', 'PUT'].includes(method) ? await req.json().catch(() => ({})) : {}

  // ---- health ----
  if (parts.length === 0) return json({ message: 'MathCompete API', ok: true })

  // ---- reference (public, no secrets) ----
  if (parts[0] === 'reference' && method === 'GET') {
    return json({ encouragements: ENCOURAGEMENTS, levelLabels: LEVEL_LABELS })
  }

  // ---- auth: google sign-in ----
  if (parts[0] === 'auth' && parts[1] === 'google' && method === 'POST') {
    const ip = req.headers.get('x-forwarded-for')?.split(',')[0]?.trim() || 'unknown'
    if (!rateOk(ip)) return json({ error: 'Too many attempts. Please wait a bit.' }, 429)
    const credential = body?.credential
    if (!credential) return json({ error: 'Missing credential' }, 400)
    let payload
    try {
      const client = new OAuth2Client(process.env.GOOGLE_CLIENT_ID)
      const ticket = await client.verifyIdToken({ idToken: credential, audience: process.env.GOOGLE_CLIENT_ID })
      payload = ticket.getPayload()
    } catch (e) {
      return json({ error: 'Could not verify Google sign-in.' }, 401)
    }
    if (!payload?.email || payload.email_verified === false) {
      return json({ error: 'Google account email not verified.' }, 401)
    }
    const email = payload.email.toLowerCase()
    const allow = parseAllowlist()
    if (!allow[email]) {
      return json({ error: 'This Google account is not on the family allowlist. Ask the parent admin to add you.' }, 403)
    }
    const db = await getDb()
    const users = db.collection('users')
    let user = await users.findOne({ $or: [{ googleId: payload.sub }, { email }] })
    if (!user) {
      user = {
        id: uuidv4(), googleId: payload.sub, email,
        name: allow[email].name || payload.name || email,
        label: allow[email].label || '', createdAt: new Date(),
      }
      await users.insertOne(user)
    }
    const token = await makeSession(user.id, user.email)
    const res = json({ user: { id: user.id, email: user.email, name: user.name } })
    res.cookies.set(COOKIE, token, { httpOnly: true, secure: true, sameSite: 'none', path: '/', maxAge: 60 * 60 * 24 * 30 })
    return res
  }

  // ---- auth: logout ----
  if (parts[0] === 'auth' && parts[1] === 'logout' && method === 'POST') {
    const res = json({ ok: true })
    res.cookies.set(COOKIE, '', { httpOnly: true, secure: true, sameSite: 'none', path: '/', maxAge: 0 })
    return res
  }

  // ======== everything below requires an authenticated parent ========
  const parent = await getParent(req)
  if (!parent) return unauthorized()

  if (parts[0] === 'me' && method === 'GET') {
    return json({ user: { id: parent.id, email: parent.email, name: parent.name } })
  }

  const db = await getDb()
  const kidsCol = db.collection('kids')
  const setsCol = db.collection('dailySets')
  const speedCol = db.collection('speedSessions')

  // ---- list kids ----
  if (parts[0] === 'kids' && parts.length === 1 && method === 'GET') {
    const today = url.searchParams.get('date') || null
    const kids = await kidsCol.find({ userId: parent.id }).sort({ createdAt: 1 }).toArray()
    if (today) await Promise.all(kids.map((k) => expireStale(db, k.id, today)))
    const stats = await Promise.all(kids.map((k) => kidStats(db, k, today)))
    return json({ kids: stats })
  }

  // ---- create kid ----
  if (parts[0] === 'kids' && parts.length === 1 && method === 'POST') {
    const firstName = (body.firstName || '').toString().trim().slice(0, 40)
    const grade = parseInt(body.grade, 10)
    if (!firstName) return json({ error: 'Please enter a first name.' }, 400)
    if (!(grade >= 1 && grade <= 5)) return json({ error: 'Grade must be 1 to 5.' }, 400)
    const theme = THEMES.includes(body.theme) ? body.theme : 'animals'
    const kid = {
      id: uuidv4(), userId: parent.id, firstName, grade,
      difficultyStep: 0, soundOn: true, theme, createdAt: new Date(),
    }
    await kidsCol.insertOne(kid)
    return json({ kid: await kidStats(db, kid, null) })
  }

  // ---- update kid (grade / soundOn / theme) ----
  if (parts[0] === 'kids' && parts.length === 2 && method === 'PUT') {
    const kid = await kidsCol.findOne({ id: parts[1], userId: parent.id })
    if (!kid) return json({ error: 'Kid not found' }, 404)
    const update = {}
    if (body.grade !== undefined) {
      const grade = parseInt(body.grade, 10)
      if (!(grade >= 1 && grade <= 5)) return json({ error: 'Grade must be 1 to 5.' }, 400)
      update.grade = grade
      update.difficultyStep = 0 // school-year promotion resets step; history kept
    }
    if (body.soundOn !== undefined) update.soundOn = !!body.soundOn
    if (body.theme !== undefined) {
      if (!THEMES.includes(body.theme)) return json({ error: 'Unknown theme.' }, 400)
      update.theme = body.theme
    }
    if (Object.keys(update).length) await kidsCol.updateOne({ id: kid.id }, { $set: update })
    const fresh = await kidsCol.findOne({ id: kid.id })
    return json({ kid: await kidStats(db, fresh, url.searchParams.get('date') || null) })
  }

  // ---- start / resume a NORMAL set ----  POST /api/kids/:id/set { date }
  if (parts[0] === 'kids' && parts[2] === 'set' && method === 'POST') {
    const kid = await kidsCol.findOne({ id: parts[1], userId: parent.id })
    if (!kid) return json({ error: 'Kid not found' }, 404)
    const date = (body.date || ymd(new Date())).toString()
    await expireStale(db, kid.id, date)
    const completedToday = await setsCol.countDocuments({ kidId: kid.id, date, status: 'completed' })
    if (completedToday >= 2) return json({ locked: true })
    let set = await setsCol.findOne({ kidId: kid.id, date, status: 'in_progress' })
    if (!set) {
      const step = kid.difficultyStep || 0
      const exclude = await usedDisplays(db, kid.id, date)
      set = {
        id: uuidv4(), kidId: kid.id, date, status: 'in_progress',
        difficultyStep: step, problems: generateProblems(kid.grade, step, SET_SIZE, exclude), createdAt: new Date(),
      }
      await setsCol.insertOne(set)
    }
    return json({ set: clientSet(set), levelLabel: levelLabel(set.difficultyStep) })
  }

  // ---- reset a NORMAL set ----  POST /api/sets/:id/reset { date }
  if (parts[0] === 'sets' && parts[2] === 'reset' && method === 'POST') {
    const set = await setsCol.findOne({ id: parts[1] })
    if (!set) return json({ error: 'Set not found' }, 404)
    const kid = await kidsCol.findOne({ id: set.kidId, userId: parent.id })
    if (!kid) return unauthorized()
    if (set.status !== 'in_progress') return json({ error: 'Set already finished.' }, 400)
    await setsCol.updateOne({ id: set.id }, { $set: { status: 'reset' } })
    const step = kid.difficultyStep || 0
    const exclude = await usedDisplays(db, kid.id, set.date)
    const fresh = {
      id: uuidv4(), kidId: kid.id, date: set.date, status: 'in_progress',
      difficultyStep: step, problems: generateProblems(kid.grade, step, SET_SIZE, exclude), createdAt: new Date(),
    }
    await setsCol.insertOne(fresh)
    return json({ set: clientSet(fresh), levelLabel: levelLabel(step) })
  }

  // ---- exit a NORMAL set ----  POST /api/sets/:id/exit
  if (parts[0] === 'sets' && parts[2] === 'exit' && method === 'POST') {
    const set = await setsCol.findOne({ id: parts[1] })
    if (!set) return json({ error: 'Set not found' }, 404)
    const kid = await kidsCol.findOne({ id: set.kidId, userId: parent.id })
    if (!kid) return unauthorized()
    if (set.status === 'in_progress') await setsCol.updateOne({ id: set.id }, { $set: { status: 'exited' } })
    return json({ ok: true, kid: await kidStats(db, kid, set.date) })
  }

  // ---- answer a NORMAL problem ----  POST /api/sets/:id/answer { problemId, answer }
  if (parts[0] === 'sets' && parts[2] === 'answer' && method === 'POST') {
    const set = await setsCol.findOne({ id: parts[1] })
    if (!set) return json({ error: 'Set not found' }, 404)
    const kid = await kidsCol.findOne({ id: set.kidId, userId: parent.id })
    if (!kid) return unauthorized()
    if (set.status !== 'in_progress') return json({ error: 'Set already finished.' }, 400)

    const idx = set.problems.findIndex((p) => p.id === body.problemId)
    if (idx < 0) return json({ error: 'Problem not found' }, 400)
    const prob = set.problems[idx]
    const solvedCount = () => set.problems.filter((p) => p.solved).length

    if (prob.solved) return json({ correct: true, alreadySolved: true, solvedCount: solvedCount(), total: SET_SIZE })

    const answer = Number(body.answer)
    if (!Number.isFinite(answer)) return json({ error: 'Answer must be a number.' }, 400)

    prob.attempts += 1
    const correct = answer === prob.correctAnswer
    if (correct) { prob.solved = true; if (prob.attempts === 1) prob.firstTryCorrect = true }

    const allSolved = set.problems.every((p) => p.solved)
    const result = {
      correct,
      encouragement: correct ? pick(ENCOURAGEMENTS) : null,
      message: correct ? null : 'Almost! Try again',
      solvedCount: solvedCount(), total: SET_SIZE, setComplete: false,
    }

    if (allSolved) {
      await setsCol.updateOne({ id: set.id }, { $set: { problems: set.problems, status: 'completed', completedAt: new Date() } })
      // adaptive difficulty (NORMAL sets only — unchanged logic)
      const totalWrong = set.problems.reduce((s, p) => s + (p.attempts - 1), 0)
      const startStep = kid.difficultyStep || 0
      let newStep = startStep
      if (totalWrong >= 3 && startStep > 0) {
        newStep = startStep - 1
      } else {
        const completed = await setsCol.find({ kidId: kid.id, status: 'completed' }).sort({ completedAt: 1 }).toArray()
        let perfectStreak = 0
        for (let i = completed.length - 1; i >= 0; i--) {
          if (completed[i].problems.every((p) => p.firstTryCorrect)) perfectStreak++
          else break
        }
        if (perfectStreak > 0 && perfectStreak % 3 === 0) newStep = Math.min(startStep + 1, MAX_STEP)
      }
      if (newStep !== startStep) await kidsCol.updateOne({ id: kid.id }, { $set: { difficultyStep: newStep } })

      const stats = await kidStats(db, { ...kid, difficultyStep: newStep }, set.date)
      result.setComplete = true
      result.starsEarned = 2
      result.starsToday = stats.todayStars
      result.totalStars = stats.totalStars
      result.locked = stats.locked
      result.levelChanged = newStep !== startStep
      result.levelDirection = newStep > startStep ? 'up' : (newStep < startStep ? 'down' : 'same')
      result.levelLabel = levelLabel(newStep)
      result.streak = stats.streak
    } else {
      await setsCol.updateOne({ id: set.id }, { $set: { problems: set.problems } })
    }
    return json(result)
  }

  // ---- start / resume a SPEED session ----  POST /api/kids/:id/speed { date }
  if (parts[0] === 'kids' && parts[2] === 'speed' && method === 'POST') {
    const kid = await kidsCol.findOne({ id: parts[1], userId: parent.id })
    if (!kid) return json({ error: 'Kid not found' }, 404)
    const date = (body.date || ymd(new Date())).toString()
    await expireStale(db, kid.id, date)

    // resume a live in-progress session for today, or auto-finish one whose time is up
    let session = await speedCol.findOne({ kidId: kid.id, date, status: 'in_progress' })
    if (session) {
      const elapsed = (Date.now() - new Date(session.startedAt).getTime()) / 1000
      if (elapsed > SPEED_SECONDS + SPEED_GRACE) {
        await finalizeSpeed(db, session, 'finished')
        session = null
      } else {
        return json({ session: clientSpeed(session), serverNow: Date.now(), timeLimit: SPEED_SECONDS })
      }
    }

    const used = await speedCol.countDocuments({ kidId: kid.id, date, status: { $in: ['finished', 'exited', 'expired'] } })
    if (used >= MAX_SPEED_PER_DAY) return json({ locked: true })

    const everBefore = (await speedCol.countDocuments({ kidId: kid.id })) > 0
    const step = kid.difficultyStep || 0
    const exclude = await usedDisplays(db, kid.id, date)
    const gen = generateProblems(kid.grade, step, SPEED_SIZE, exclude)
    const problems = gen.map((p) => ({
      id: p.id, operation: p.operation, operands: p.operands, display: p.display,
      correctAnswer: p.correctAnswer, givenAnswer: null, correct: false, answered: false,
    }))
    session = {
      id: uuidv4(), kidId: kid.id, date, sessionNumber: used + 1, status: 'in_progress',
      startedAt: new Date(), problems, difficultyStep: step, createdAt: new Date(),
    }
    await speedCol.insertOne(session)
    return json({ session: clientSpeed(session), serverNow: Date.now(), timeLimit: SPEED_SECONDS, firstEver: !everBefore })
  }

  // ---- answer a SPEED problem ----  POST /api/speed/:id/answer { problemId, answer }
  if (parts[0] === 'speed' && parts[2] === 'answer' && method === 'POST') {
    const session = await speedCol.findOne({ id: parts[1] })
    if (!session) return json({ error: 'Session not found' }, 404)
    const kid = await kidsCol.findOne({ id: session.kidId, userId: parent.id })
    if (!kid) return unauthorized()
    if (session.status !== 'in_progress') return json({ error: 'Session already finished.' }, 400)

    const elapsed = (Date.now() - new Date(session.startedAt).getTime()) / 1000
    if (elapsed > SPEED_SECONDS + SPEED_GRACE) {
      // time's up — reject this answer and finalize the session
      await finalizeSpeed(db, session, 'finished')
      const payload = await speedResultPayload(db, kid, session, session.date)
      return json({ ...payload, timeUp: true })
    }

    const idx = session.problems.findIndex((p) => p.id === body.problemId)
    if (idx < 0) return json({ error: 'Problem not found' }, 400)
    const prob = session.problems[idx]
    if (prob.answered) {
      return json({ correct: prob.correct, alreadyAnswered: true, answeredCount: session.problems.filter((p) => p.answered).length, total: SPEED_SIZE })
    }
    const answer = Number(body.answer)
    if (!Number.isFinite(answer)) return json({ error: 'Answer must be a number.' }, 400)

    prob.answered = true
    prob.givenAnswer = answer
    prob.correct = answer === prob.correctAnswer

    const allAnswered = session.problems.every((p) => p.answered)
    if (allAnswered) {
      await finalizeSpeed(db, session, 'finished')
      const payload = await speedResultPayload(db, kid, session, session.date)
      return json({ correct: prob.correct, ...payload })
    }
    await speedCol.updateOne({ id: session.id }, { $set: { problems: session.problems } })
    return json({
      correct: prob.correct, setComplete: false,
      answeredCount: session.problems.filter((p) => p.answered).length, total: SPEED_SIZE,
    })
  }

  // ---- finish a SPEED session (timer ended, client-driven) ----  POST /api/speed/:id/finish
  if (parts[0] === 'speed' && parts[2] === 'finish' && method === 'POST') {
    const session = await speedCol.findOne({ id: parts[1] })
    if (!session) return json({ error: 'Session not found' }, 404)
    const kid = await kidsCol.findOne({ id: session.kidId, userId: parent.id })
    if (!kid) return unauthorized()
    if (session.status === 'in_progress') await finalizeSpeed(db, session, 'finished')
    const payload = await speedResultPayload(db, kid, session, session.date)
    return json(payload)
  }

  // ---- exit a SPEED session ----  POST /api/speed/:id/exit  (uses a daily slot, no star change)
  if (parts[0] === 'speed' && parts[2] === 'exit' && method === 'POST') {
    const session = await speedCol.findOne({ id: parts[1] })
    if (!session) return json({ error: 'Session not found' }, 404)
    const kid = await kidsCol.findOne({ id: session.kidId, userId: parent.id })
    if (!kid) return unauthorized()
    if (session.status === 'in_progress') await speedCol.updateOne({ id: session.id }, { $set: { status: 'exited' } })
    return json({ ok: true, kid: await kidStats(db, kid, session.date) })
  }

  return json({ error: 'Not found' }, 404)
}

// ----------------------------- method exports --------------------------------
export async function GET(req) { try { return await route(req, 'GET') } catch (e) { console.error(e); return json({ error: 'Server error' }, 500) } }
export async function POST(req) { try { return await route(req, 'POST') } catch (e) { console.error(e); return json({ error: 'Server error' }, 500) } }
export async function PUT(req) { try { return await route(req, 'PUT') } catch (e) { console.error(e); return json({ error: 'Server error' }, 500) } }
export async function DELETE(req) { try { return await route(req, 'DELETE') } catch (e) { console.error(e); return json({ error: 'Server error' }, 500) } }
export async function OPTIONS() { return new NextResponse(null, { status: 204 }) }
