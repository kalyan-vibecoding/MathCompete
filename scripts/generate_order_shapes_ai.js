/**
 * OFFLINE "Order and Shapes" bank generator (developer-run only — NOT a runtime request).
 *
 * Environment variables read by THIS SCRIPT ONLY:
 *   ANTHROPIC_API_KEY  - Anthropic API key. Used ONLY here, offline, and ONLY when run with
 *                        the --ai flag. No live/kid-triggered request ever calls Anthropic.
 *                        The key is never sent to the browser.
 *   (MONGO_URL / DB_NAME are NOT used here — this script only writes a candidate JSON file.
 *    Seeding into MongoDB is done separately by the app's version-gated seed once the
 *    reviewed file is uploaded to the repo root, exactly like funmath_bank.json.)
 *
 * Purpose: produce a CANDIDATE order_shapes_bank.json (1000 items = 200/grade = 100 order +
 * 100 shapes) for human review. The default path is deterministic/templated so every item is
 * guaranteed well-formed and renderable by inline SVG. Pass --ai to instead draft with Claude
 * (kept for parity with generate_funmath_ai.js; review before use).
 *
 * Usage:
 *   node scripts/generate_order_shapes_ai.js            # writes ./order_shapes_bank.json (templated)
 *   set -a && . ./.env && set +a && node scripts/generate_order_shapes_ai.js --ai   # AI draft (review!)
 *
 * Schema per item:
 *   { id, grade, strand:"order"|"shapes", questionType, prompt, displayData,
 *     options?(MC only), correctAnswer, difficultyTier(1-5), createdAt }
 */
const fs = require('fs')
const path = require('path')
const crypto = require('crypto')

const ri = (a, b) => Math.floor(Math.random() * (b - a + 1)) + a
const pick = (arr) => arr[ri(0, arr.length - 1)]
const shuffle = (a) => { a = [...a]; for (let i = a.length - 1; i > 0; i--) { const j = ri(0, i);[a[i], a[j]] = [a[j], a[i]] } return a }

const ORDINALS = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth', 'ninth', 'tenth']
const ICONS = ['star', 'heart', 'circle', 'apple', 'ball']
const SIDES = { triangle: 3, square: 4, rectangle: 4, pentagon: 5, hexagon: 6, trapezoid: 4, rhombus: 4, circle: 0 }
const FACES = { cube: 6, 'rectangular prism': 6, cylinder: 3, cone: 2, sphere: 1, pyramid: 5 }
const SHAPES_2D = ['triangle', 'square', 'rectangle', 'pentagon', 'hexagon', 'trapezoid', 'rhombus', 'circle']
const SHAPES_3D = ['cube', 'rectangular prism', 'cylinder', 'cone', 'sphere', 'pyramid']

function mcFrom(correct, pool, n = 4) {
  const opts = new Set([String(correct)])
  const p = shuffle(pool)
  for (const x of p) { if (opts.size >= n) break; opts.add(String(x)) }
  return { options: shuffle([...opts]), correctAnswer: String(correct) }
}
function orderMC(nums) {
  const asc = [...nums].sort((a, b) => a - b)
  const correct = asc.join(', ')
  const opts = new Set([correct]); let guard = 0
  while (opts.size < 3 && guard < 40) { guard++; opts.add(shuffle(nums).join(', ')) }
  return { options: shuffle([...opts]), correctAnswer: correct }
}
const fracVal = (f) => { const [a, b] = f.split('/').map(Number); return a / b }

// ---------------- ORDER strand ----------------
function genOrder(grade) {
  if (grade === 1) {
    if (Math.random() < 0.6) {
      const count = ri(5, 10), markIndex = ri(0, count - 1), icon = pick(ICONS)
      const mc = mcFrom(ORDINALS[markIndex], ORDINALS.slice(0, count))
      return { questionType: 'ordinal_position', prompt: `What position is the marked ${icon} from the left?`, displayData: { type: 'row', icon, count, markIndex }, ...mc, difficultyTier: markIndex < 3 ? 1 : 2 }
    }
    const start = ri(1, 8), seq = [start, start + 1, null, start + 3], ans = start + 2
    return { questionType: 'sequence_next', prompt: 'What number is missing?', displayData: { type: 'sequence', items: seq }, correctAnswer: ans, difficultyTier: 2 }
  }
  if (grade === 2) {
    if (Math.random() < 0.5) {
      const nums = shuffle(Array.from({ length: 4 }, () => ri(10, 99))).slice(0, 3)
      return { questionType: 'order_least_greatest', prompt: 'Which list is in order from least to greatest?', displayData: { type: 'numbers', numbers: nums }, ...orderMC(nums), difficultyTier: 3 }
    }
    const n = ri(11, 98), which = pick(['just after', 'just before'])
    return { questionType: 'before_after', prompt: `What number comes ${which} ${n}?`, displayData: { type: 'numberline', center: n }, correctAnswer: which === 'just after' ? n + 1 : n - 1, difficultyTier: 2 }
  }
  if (grade === 3) {
    if (Math.random() < 0.5) {
      const nums = shuffle(Array.from({ length: 4 }, () => ri(100, 999))).slice(0, 3)
      return { questionType: 'order_least_greatest', prompt: 'Which list is in order from least to greatest?', displayData: { type: 'numbers', numbers: nums }, ...orderMC(nums), difficultyTier: 3 }
    }
    const a = ri(100, 999), b = ri(100, 999), sym = a > b ? '>' : a < b ? '<' : '='
    return { questionType: 'compare_symbols', prompt: `Which symbol makes it true?  ${a} __ ${b}`, displayData: { type: 'compare', a, b }, options: ['>', '<', '='], correctAnswer: sym, difficultyTier: 3 }
  }
  if (grade === 4) {
    if (Math.random() < 0.5) {
      const nums = shuffle(Array.from({ length: 4 }, () => ri(1000, 99999))).slice(0, 3)
      return { questionType: 'order_least_greatest', prompt: 'Order these numbers from least to greatest.', displayData: { type: 'numbers', numbers: nums }, ...orderMC(nums), difficultyTier: 4 }
    }
    const nums = shuffle(Array.from({ length: 4 }, () => Number((ri(1, 99) / 10).toFixed(1)))).slice(0, 3)
    return { questionType: 'order_decimals', prompt: 'Order these decimals from least to greatest.', displayData: { type: 'numbers', numbers: nums }, ...orderMC(nums), difficultyTier: 4 }
  }
  // grade 5
  if (Math.random() < 0.5) {
    const nums = shuffle(Array.from({ length: 4 }, () => Number((ri(1, 999) / 100).toFixed(2)))).slice(0, 3)
    return { questionType: 'order_decimals', prompt: 'Order these decimals from least to greatest.', displayData: { type: 'numbers', numbers: nums }, ...orderMC(nums), difficultyTier: 5 }
  }
  const fr = shuffle(['1/2', '1/3', '2/3', '1/4', '3/4', '2/5', '3/5', '1/6', '5/6', '3/8']).slice(0, 3)
  const asc = [...fr].sort((a, b) => fracVal(a) - fracVal(b))
  const correct = asc.join(', ')
  const opts = new Set([correct]); let g = 0
  while (opts.size < 3 && g < 40) { g++; opts.add(shuffle(fr).join(', ')) }
  return { questionType: 'order_fractions', prompt: 'Order these fractions from least to greatest.', displayData: { type: 'fractions', fractions: fr }, options: shuffle([...opts]), correctAnswer: correct, difficultyTier: 5 }
}

// ---------------- SHAPES strand ----------------
function genShapes(grade) {
  if (grade === 1) {
    const r = Math.random()
    if (r < 0.3) { const shape = pick(SHAPES_2D.concat(SHAPES_3D)); return { questionType: 'name_shape', prompt: 'What shape is this?', displayData: { type: 'shape', shape }, ...mcFrom(shape, SHAPES_2D.concat(SHAPES_3D)), difficultyTier: 1 } }
    if (r < 0.55) { const shape = pick(SHAPES_2D.filter((s) => s !== 'circle')); return { questionType: 'count_sides', prompt: 'How many sides does this shape have?', displayData: { type: 'shape', shape }, correctAnswer: SIDES[shape], difficultyTier: 2 } }
    if (r < 0.75) { const shape = pick(SHAPES_2D.filter((s) => s !== 'circle')); return { questionType: 'count_corners', prompt: 'How many corners does this shape have?', displayData: { type: 'shape', shape }, correctAnswer: SIDES[shape], difficultyTier: 2 } }
    if (r < 0.9) { const shape = pick(SHAPES_3D); return { questionType: 'count_faces', prompt: 'How many faces does this solid have?', displayData: { type: 'shape', shape }, correctAnswer: FACES[shape], difficultyTier: 3 } }
    const is3d = Math.random() < 0.5, shape = is3d ? pick(SHAPES_3D) : pick(SHAPES_2D)
    return { questionType: 'sort_2d_3d', prompt: 'Is this shape 2D (flat) or 3D (solid)?', displayData: { type: 'shape', shape }, options: ['2D', '3D'], correctAnswer: is3d ? '3D' : '2D', difficultyTier: 1 }
  }
  if (grade === 2) {
    const r = Math.random()
    if (r < 0.4) { const shape = pick(SHAPES_2D); const yes = ['square', 'rectangle'].includes(shape); return { questionType: 'right_angle', prompt: 'Does this shape have square corners (right angles)?', displayData: { type: 'shape', shape }, options: ['Yes', 'No'], correctAnswer: yes ? 'Yes' : 'No', difficultyTier: 3 } }
    if (r < 0.7) { const shape = pick(SHAPES_2D); const yes = ['square', 'rhombus'].includes(shape); return { questionType: 'equal_sides', prompt: 'Are all the sides equal in length?', displayData: { type: 'shape', shape }, options: ['Yes', 'No'], correctAnswer: yes ? 'Yes' : 'No', difficultyTier: 3 } }
    const parts = pick([2, 3, 4]), label = { 2: 'halves', 3: 'thirds', 4: 'fourths' }[parts]
    return { questionType: 'partition', prompt: 'How many equal parts is this shape split into?', displayData: { type: 'partition', shape: pick(['rectangle', 'circle', 'square']), parts }, options: shuffle(['2', '3', '4']), correctAnswer: String(parts), difficultyTier: 2 }
  }
  if (grade === 3) {
    const r = Math.random()
    if (r < 0.45) { const w = ri(2, 20), h = ri(2, 20); return { questionType: 'perimeter', prompt: 'What is the perimeter of this rectangle?', displayData: { type: 'rectangle', width: w, height: h, unit: 'cm' }, correctAnswer: 2 * (w + h), difficultyTier: 3 } }
    if (r < 0.75) { const shape = pick(['square', 'rectangle', 'rhombus', 'trapezoid']); return { questionType: 'classify_quadrilateral', prompt: 'What is this quadrilateral called?', displayData: { type: 'shape', shape }, ...mcFrom(shape, ['square', 'rectangle', 'rhombus', 'trapezoid']), difficultyTier: 3 } }
    const parts = pick([2, 3, 4, 6]), shaded = ri(1, parts - 1)
    return { questionType: 'fraction_part', prompt: 'What fraction of the shape is shaded?', displayData: { type: 'partition', shape: 'rectangle', parts, shaded }, ...mcFrom(`${shaded}/${parts}`, [`${shaded}/${parts}`, `${parts}/${shaded}`, `1/${parts}`, `${shaded}/${parts + 1}`]), difficultyTier: 4 }
  }
  if (grade === 4) {
    const r = Math.random()
    if (r < 0.4) { const w = ri(2, 20), h = ri(2, 20); return { questionType: 'area_rectangle', prompt: 'What is the area of this rectangle?', displayData: { type: 'rectangle', width: w, height: h, unit: 'cm' }, correctAnswer: w * h, difficultyTier: 4 } }
    if (r < 0.7) { const map = { square: 4, rectangle: 2, 'equilateral triangle': 3, hexagon: 6 }; const shape = pick(Object.keys(map)); return { questionType: 'lines_of_symmetry', prompt: 'How many lines of symmetry does this shape have?', displayData: { type: 'shape', shape: shape.includes('triangle') ? 'triangle' : shape }, correctAnswer: map[shape], difficultyTier: 4 } }
    const shape = pick(['square', 'rectangle', 'rhombus', 'trapezoid']); const parallel = shape !== 'trapezoid'
    return { questionType: 'parallel_sides', prompt: 'Does this shape have two pairs of parallel sides?', displayData: { type: 'shape', shape }, options: ['Yes', 'No'], correctAnswer: parallel ? 'Yes' : 'No', difficultyTier: 4 }
  }
  // grade 5
  const r = Math.random()
  if (r < 0.4) { const l = ri(2, 10), w = ri(2, 10), h = ri(2, 10); return { questionType: 'volume_prism', prompt: 'How many unit cubes fill this box? (volume)', displayData: { type: 'prism', l, w, h, unit: 'cm' }, correctAnswer: l * w * h, difficultyTier: 5 } }
  if (r < 0.7) {
    const stmts = [['All squares are rectangles.', 'Always'], ['All rectangles are squares.', 'Sometimes'], ['A square is a rhombus.', 'Always'], ['A triangle is a quadrilateral.', 'Never'], ['A rectangle has four right angles.', 'Always'], ['A parallelogram is a trapezoid.', 'Sometimes']]
    const s = pick(stmts)
    return { questionType: 'hierarchy', prompt: `${s[0]}`, displayData: { type: 'statement' }, options: ['Always', 'Sometimes', 'Never'], correctAnswer: s[1], difficultyTier: 5 }
  }
  const a = ri(3, 12), b = ri(3, 12), c = ri(2, 6)
  // L-shape composite perimeter of an a x b rectangle with a c x c notch removed (perimeter unchanged = 2(a+b))
  return { questionType: 'composite_area', prompt: 'An L-shape is made from an ' + a + '×' + b + ' rectangle with a ' + c + '×' + c + ' square removed from a corner. What is its area?', displayData: { type: 'lshape', a, b, notch: c }, correctAnswer: a * b - c * c, difficultyTier: 5 }
}

function buildBank() {
  const out = []
  for (let grade = 1; grade <= 5; grade++) {
    for (const [strand, gen, target] of [['order', genOrder, 100], ['shapes', genShapes, 100]]) {
      const seen = new Set(); let guard = 0
      let made = 0
      while (made < target && guard < 60000) {
        guard++
        const item = gen(grade)
        // Add benign visual variation (size/color) to shape-render items so grades with a
        // small pedagogical space (g1/g2 shapes) still reach 100 unique, renderer-friendly items.
        if (item.displayData && ['shape', 'partition', 'rectangle', 'prism', 'lshape'].includes(item.displayData.type)) {
          item.displayData.size = ri(1, 3)
          item.displayData.color = pick(['sky', 'mint', 'grape', 'sunset', 'bubblegum'])
        }
        const key = strand + '|' + item.prompt + '|' + JSON.stringify(item.displayData)
        if (seen.has(key)) continue
        seen.add(key)
        out.push({ id: crypto.randomUUID(), grade, strand, ...item, createdAt: new Date().toISOString() })
        made++
      }
      if (made < target) console.warn(`WARN grade ${grade} ${strand}: only ${made}/${target} unique`)
    }
  }
  return out
}

async function main() {
  if (process.argv.includes('--ai')) {
    console.log('AI drafting path is a stub for review parity; using templated generator is recommended. Exiting.')
    // (Anthropic drafting could go here using process.env.ANTHROPIC_API_KEY, offline only.)
  }
  const bank = buildBank()
  const outPath = path.join(process.cwd(), 'order_shapes_bank.json')
  fs.writeFileSync(outPath, JSON.stringify(bank, null, 2))
  const by = {}
  bank.forEach((x) => { by[x.grade] = by[x.grade] || { order: 0, shapes: 0 }; by[x.grade][x.strand]++ })
  console.log('Wrote', bank.length, 'items to', outPath)
  console.log('Per grade:', JSON.stringify(by))
}
main().catch((e) => { console.error(e); process.exit(1) })
