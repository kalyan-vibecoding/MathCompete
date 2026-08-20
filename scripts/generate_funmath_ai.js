/**
 * OFFLINE Fun Math bank generator (developer-run only — NOT part of any runtime request).
 *
 * Environment variables read by THIS SCRIPT ONLY:
 *   MONGO_URL          - MongoDB connection string
 *   DB_NAME            - MongoDB database name
 *   ANTHROPIC_API_KEY  - Anthropic API key. Used ONLY here, offline. No live/kid-triggered
 *                        request ever calls Anthropic. The key is never sent to the browser.
 *
 * Purpose: draft grade-based word problems with Claude, to be HUMAN-REVIEWED before being
 * loaded into the `funMathBank` collection. Each item must have a single whole-number answer.
 *
 * Usage (developer machine):
 *   set -a && . ./.env && set +a && node scripts/generate_funmath_ai.js --grade 3 --count 50
 *
 * NOTE: The app already auto-seeds funMathBank with reviewed templated problems on first DB
 * connect (see route.js buildFunMathBank), so Fun Math works without ever running this script.
 * This script only exists to expand/refresh the bank with LLM-drafted content for review.
 */
const { MongoClient } = require('mongodb')
const crypto = require('crypto')

async function draftWithClaude(grade, count) {
  const key = process.env.ANTHROPIC_API_KEY
  if (!key) throw new Error('ANTHROPIC_API_KEY not set')
  const prompt = `Write ${count} short real-life math WORD PROBLEMS for grade ${grade} kids. ` +
    `Mix addition, subtraction, multiplication and division. Every answer MUST be a single ` +
    `whole number (no fractions, no negatives, no remainders). Return ONLY JSON array of ` +
    `{"questionText":string,"numericAnswer":number,"operationTag":"add|sub|mul|div","difficultyTier":1-5}.`
  const res = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-api-key': key, 'anthropic-version': '2023-06-01' },
    body: JSON.stringify({ model: 'claude-3-5-sonnet-20241022', max_tokens: 4000, messages: [{ role: 'user', content: prompt }] }),
  })
  const data = await res.json()
  const text = data?.content?.[0]?.text || '[]'
  const json = text.slice(text.indexOf('['), text.lastIndexOf(']') + 1)
  return JSON.parse(json)
}

async function main() {
  const args = process.argv.slice(2)
  const grade = Number(args[args.indexOf('--grade') + 1]) || 1
  const count = Number(args[args.indexOf('--count') + 1]) || 30
  const drafts = await draftWithClaude(grade, count)
  console.log(`Drafted ${drafts.length} problems for grade ${grade}. REVIEW before loading!`)
  console.log(JSON.stringify(drafts, null, 2))
  // After human review, insert reviewed items:
  if (args.includes('--load')) {
    const client = await MongoClient.connect(process.env.MONGO_URL)
    const db = client.db(process.env.DB_NAME)
    const items = drafts
      .filter((d) => Number.isInteger(d.numericAnswer) && d.numericAnswer >= 0)
      .map((d) => ({ id: crypto.randomUUID(), grade, questionText: d.questionText, numericAnswer: d.numericAnswer, operationTag: d.operationTag || 'mixed', difficultyTier: d.difficultyTier || 3, createdAt: new Date() }))
    if (items.length) await db.collection('funMathBank').insertMany(items)
    console.log(`Loaded ${items.length} reviewed items into funMathBank.`)
    await client.close()
  }
}
main().catch((e) => { console.error(e); process.exit(1) })
