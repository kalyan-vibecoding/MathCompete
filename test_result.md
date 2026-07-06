#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: |
  MathCompete - a Next.js + MongoDB web app giving kids grades 1-5 a daily set of 30 adaptive
  math problems styled as a game. Parents sign in with Google (allowlist gated), create kid
  profiles, kids answer via an on-screen number pad, complete sets to earn virtual dollars,
  with adaptive difficulty. All backend logic in ONE catch-all route file.

## HOW TO AUTHENTICATE FOR TESTING (no live Google token available):
## Every protected endpoint requires a parent session cookie named "mc_session".
## The cookie value is an HS256 JWT signed with env JWT_SECRET (read from /app/.env).
## JWT payload must be: { "sub": <user.id (uuid)>, "email": <email>, "role": "parent" }
## with standard iat/exp claims. Steps for the test agent:
##   1. Read MONGO_URL, DB_NAME, JWT_SECRET from /app/.env
##   2. Insert a test parent into the "users" collection: { id: <uuid>, googleId, email, name, createdAt }
##      (Insert a SECOND parent too, to test cross-parent data isolation.)
##   3. Mint a JWT (PyJWT HS256 with JWT_SECRET) and send it as Cookie: mc_session=<jwt>
##   4. Call APIs at http://localhost:3000/api/...  (all routes are under /api)
## Do NOT hit the real Google verify endpoint. Sign-in allowlist logic (/api/auth/google) cannot
## be end-to-end tested without a real Google ID token; verify only that it rejects bad/missing creds.

backend:
  - task: "Auth gating - protected routes return 401 without session"
    implemented: true
    working: true
    file: "app/api/[[...path]]/route.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "GET /api/me, /api/kids, POST /api/kids etc must return 401 without a valid mc_session cookie. GET /api and GET /api/reference are public."
        -working: true
        -agent: "testing"
        -comment: "PASSED. Verified: (1) Public endpoints GET /api and GET /api/reference return 200 without auth. (2) Protected endpoints GET /api/me, GET /api/kids, POST /api/kids return 401 without auth. (3) With valid JWT cookie, GET /api/me returns correct parent data."

  - task: "Kid CRUD + cross-parent data isolation"
    implemented: true
    working: true
    file: "app/api/[[...path]]/route.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "POST /api/kids creates kid (grade validated 1-5). GET /api/kids lists own kids with computed stats. Parent A must NOT be able to GET/PUT/answer for Parent B's kid (returns 404/401)."
        -working: true
        -agent: "testing"
        -comment: "PASSED. Verified: (1) POST /api/kids with grade 3 creates kid with stats. (2) Grade validation: grade 0 and 6 return 400, missing firstName returns 400. (3) GET /api/kids returns only parent's own kids. (4) Cross-parent isolation: Parent B cannot PUT or POST /api/kids/<parentA_kid_id>/set (returns 404). Parent B does not see Parent A's kids."

  - task: "Problem generation rules per grade"
    implemented: true
    working: true
    file: "app/api/[[...path]]/route.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "Start a set via POST /api/kids/:id/set. Grade 1 base set = only single-digit (<=9 operands) add/sub. Grade 2 set = never a fraction and division always whole (no remainder). Inspect DB dailySets.problems to verify operands/operations. 30 unique problems, no correctAnswer sent to client."
        -working: true
        -agent: "testing"
        -comment: "PASSED. Verified: (1) Grade 1 set has exactly 30 unique problems, only add/sub operations, all operands <=9, no negative answers. (2) Grade 2 set has no fraction operation, all division problems have whole results (no remainder), dividend <=100, divisor <=10. (3) No correctAnswer sent to client in API response. (4) Verified by inspecting DB dailySets.problems collection."

  - task: "Answer checking, re-queue, set completion pays exactly 2, 2-set/day cap"
    implemented: true
    working: true
    file: "app/api/[[...path]]/route.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "POST /api/sets/:id/answer checks server-side. Wrong answer keeps problem unsolved. Set completes only when all 30 solved -> totalDollars increases by exactly 2 (computed, not stored). After 2 completed sets in one day, POST /api/kids/:id/set returns {locked:true} and daily total is exactly 4. Read correctAnswers from DB to auto-solve during test."
        -working: true
        -agent: "testing"
        -comment: "PASSED. Verified: (1) Wrong answer returns correct=false, message present, solved count stays 0. (2) Completing all 30 problems: last answer returns setComplete=true, dollarsEarned=2, dollarsToday=2, totalDollars=2. (3) Second set completion: dollarsToday=4, totalDollars=4, locked=true. (4) Third set attempt returns {locked:true}. (5) Total dollars for the day is exactly 4 (2 completed sets * $2)."

  - task: "Reset produces new set, earns nothing, does not count to daily cap"
    implemented: true
    working: true
    file: "app/api/[[...path]]/route.js"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "POST /api/sets/:id/reset marks old set status=reset, returns 30 new problems. Awards nothing. Kid can still complete 2 earning sets that day."
        -working: true
        -agent: "testing"
        -comment: "PASSED. Verified: (1) Reset returns new set with 30 different problems and different set ID. (2) Old set status is 'reset' in DB. (3) Reset awards no dollars. (4) Kid can still complete 2 earning sets after reset (reset does not count toward daily cap). Total dollars after 2 completed sets = $4."

  - task: "Adaptive difficulty step up/down"
    implemented: true
    working: true
    file: "app/api/[[...path]]/route.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "3 consecutive perfect (zero-wrong) completed sets -> kid.difficultyStep +1 (cap 4). A completed set with 3+ total wrong attempts while difficultyStep>0 -> step -1 (min 0). Note: only 2 sets/day cap; to test step-up across 3 sets you may need to insert completed dailySets directly OR simulate across multiple dates. Verify difficultyStep changes and next set is measurably harder (larger operands)."
        -working: true
        -agent: "testing"
        -comment: "PASSED. Verified: (1) Step up: Inserted 2 prior perfect completed sets, then completed 3rd perfect set via API. Response shows levelChanged=true, levelDirection='up'. difficultyStep increased from 0 to 1 in DB. (2) Step down: Set kid's difficultyStep to 2, submitted 3+ wrong answers, then completed set. Response shows levelDirection='down'. difficultyStep decreased from 2 to 1 in DB."

  - task: "Grade change resets difficultyStep to 0, keeps dollars/history"
    implemented: true
    working: true
    file: "app/api/[[...path]]/route.js"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "PUT /api/kids/:id { grade } sets difficultyStep=0 and keeps completed sets (dollar total unchanged)."
        -working: true
        -agent: "testing"
        -comment: "PASSED. Verified: (1) Created kid with difficultyStep=2 and completed a set to earn $2. (2) Changed grade from 2 to 4 via PUT /api/kids/:id. (3) difficultyStep reset to 0 in DB, grade updated to 4. (4) totalDollars unchanged at $2. (5) Completed sets (history) unchanged - 1 completed set still exists in DB."

  - task: "Live-computed stats (totalDollars, daysPlayed, streak)"
    implemented: true
    working: true
    file: "app/api/[[...path]]/route.js"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "totalDollars = completed sets * 2. daysPlayed = distinct dates with a completed set. streak = consecutive dates ending at latest played date. No stored counters anywhere."
        -working: true
        -agent: "testing"
        -comment: "PASSED. Verified: (1) Inserted 8 completed sets across 4 dates (2025-01-10, 01-11, 01-12, 01-14 with gap on 01-13). (2) totalDollars = 16 (8 completed sets * $2). (3) daysPlayed = 4 (distinct dates). (4) streak = 1 (01-14 is isolated due to gap on 01-13). (5) No stored counter fields (totalDollars, daysPlayed, streak) in kids collection - all computed live from dailySets."

frontend:
  - task: "Full game UI (sign-in, picker, game, celebrations)"
    implemented: true
    working: "NA"
    file: "app/page.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "Not yet tested. Awaiting user permission before frontend testing (Google sign-in requires real browser auth)."

metadata:
  created_by: "main_agent"
  version: "1.0"
  test_sequence: 1
  run_ui: false

test_plan:
  current_focus:
    - "Auth gating - protected routes return 401 without session"
    - "Kid CRUD + cross-parent data isolation"
    - "Problem generation rules per grade"
    - "Answer checking, re-queue, set completion pays exactly 2, 2-set/day cap"
    - "Adaptive difficulty step up/down"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
    -agent: "main"
    -message: "MathCompete backend built in single catch-all route. Please test backend per the HOW TO AUTHENTICATE section above (mint an HS256 JWT with JWT_SECRET as the mc_session cookie; insert test users directly into Mongo). Focus on auth gating, ownership isolation, grade-specific generation rules, answer/completion/$2 payout, 2-set daily cap, reset behavior, and adaptive difficulty. Do NOT test the real Google verify flow (no token available)."
    -agent: "testing"
    -message: "Backend testing complete. ALL 8 BACKEND TASKS PASSED. Created comprehensive test suite (backend_test.py) that mints JWT tokens for auth, inserts test users directly into MongoDB, and tests all functionality. All critical features working: auth gating, kid CRUD with cross-parent isolation, grade-specific problem generation rules, answer checking with $2 rewards and 2-set/day cap, reset functionality, adaptive difficulty (step up/down), grade change, and live-computed stats. No major issues found. Backend is production-ready."