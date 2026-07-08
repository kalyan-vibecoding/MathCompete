#!/usr/bin/env python3
"""
MathCompete Backend Enhancement Test Suite
Tests all 11 enhancement items from the review request.
"""

import requests
import jwt
import time
from datetime import datetime, timedelta
from pymongo import MongoClient
from uuid import uuid4

# Configuration from .env
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "your_database_name"
JWT_SECRET = "64c92630d866552ea20d2ff0b04605569e9f340fdb102de797973036232c4373"
BASE_URL = "http://localhost:3000/api"

# Test data
PARENT_EMAIL = "test_parent_enhancements@test.com"

def mint_jwt(user_id, email):
    """Mint an HS256 JWT for authentication"""
    payload = {
        "sub": user_id,
        "email": email,
        "role": "parent",
        "iat": int(time.time()),
        "exp": int(time.time()) + 86400 * 30  # 30 days
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def setup_test_user():
    """Insert test parent into MongoDB"""
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    users = db["users"]
    
    # Clean up existing test user
    users.delete_many({"email": PARENT_EMAIL})
    
    parent_id = str(uuid4())
    users.insert_one({
        "id": parent_id,
        "googleId": "test-parent-enh",
        "email": PARENT_EMAIL,
        "name": "Test Parent Enhancements",
        "createdAt": datetime.utcnow()
    })
    
    client.close()
    return parent_id

def cleanup_test_data(parent_id):
    """Clean up test data from MongoDB"""
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Get all kids for parent
    kids = db["kids"]
    parent_kids = list(kids.find({"userId": parent_id}))
    kid_ids = [k["id"] for k in parent_kids]
    
    # Delete daily sets and speed sessions for these kids
    db["dailySets"].delete_many({"kidId": {"$in": kid_ids}})
    db["speedSessions"].delete_many({"kidId": {"$in": kid_ids}})
    
    # Delete kids
    kids.delete_many({"userId": parent_id})
    
    # Delete user
    db["users"].delete_many({"id": parent_id})
    
    client.close()

def get_mongo_db():
    """Get MongoDB database connection"""
    client = MongoClient(MONGO_URL)
    return client[DB_NAME]

def test_1_stars_rename_and_totals():
    """
    TEST 1: STARS RENAME + TOTALS
    - GET /api/kids?date=YYYY-MM-DD returns each kid with: totalStars, todayStars, 
      history[].stars, theme, speedRemaining, speedLocked, speedEver (NOT totalDollars/dollars).
    - Create a kid, complete one normal set (read correctAnswers from dailySets doc, 
      POST /api/sets/:id/answer for all 30). Final answer response must include 
      starsEarned=2, starsToday, totalStars. Verify totalStars increased by exactly 2.
    """
    print("\n" + "="*80)
    print("TEST 1: STARS RENAME + TOTALS")
    print("="*80)
    
    parent_id = setup_test_user()
    token = mint_jwt(parent_id, PARENT_EMAIL)
    cookies = {"mc_session": token}
    
    try:
        # Create a kid
        print("\n[1.1] Creating a kid...")
        resp = requests.post(f"{BASE_URL}/kids", 
                           json={"firstName": "StarKid", "grade": 2},
                           cookies=cookies)
        assert resp.status_code == 200, f"Failed to create kid: {resp.status_code} {resp.text}"
        kid_data = resp.json()["kid"]
        kid_id = kid_data["id"]
        print(f"✓ Kid created: {kid_id}")
        
        # Verify initial stats have stars fields (not dollars)
        print("\n[1.2] Verifying initial stats have stars fields...")
        assert "totalStars" in kid_data, "Missing totalStars field"
        assert "todayStars" in kid_data, "Missing todayStars field"
        assert "theme" in kid_data, "Missing theme field"
        assert "speedRemaining" in kid_data, "Missing speedRemaining field"
        assert "speedLocked" in kid_data, "Missing speedLocked field"
        assert "speedEver" in kid_data, "Missing speedEver field"
        assert "totalDollars" not in kid_data, "Should NOT have totalDollars field"
        assert "dollars" not in kid_data, "Should NOT have dollars field"
        assert kid_data["totalStars"] == 0, f"Initial totalStars should be 0, got {kid_data['totalStars']}"
        assert kid_data["todayStars"] == 0, f"Initial todayStars should be 0, got {kid_data['todayStars']}"
        print(f"✓ Initial stats correct: totalStars={kid_data['totalStars']}, todayStars={kid_data['todayStars']}")
        
        # Start a normal set
        today = datetime.utcnow().strftime("%Y-%m-%d")
        print(f"\n[1.3] Starting a normal set for date {today}...")
        resp = requests.post(f"{BASE_URL}/kids/{kid_id}/set",
                           json={"date": today},
                           cookies=cookies)
        assert resp.status_code == 200, f"Failed to start set: {resp.status_code} {resp.text}"
        set_data = resp.json()["set"]
        set_id = set_data["id"]
        print(f"✓ Set started: {set_id}")
        
        # Read correct answers from MongoDB
        print("\n[1.4] Reading correct answers from MongoDB...")
        db = get_mongo_db()
        set_doc = db["dailySets"].find_one({"id": set_id})
        assert set_doc is not None, "Set not found in database"
        problems = set_doc["problems"]
        assert len(problems) == 30, f"Expected 30 problems, got {len(problems)}"
        print(f"✓ Found {len(problems)} problems in database")
        
        # Answer all 30 problems correctly
        print("\n[1.5] Answering all 30 problems correctly...")
        for i, prob in enumerate(problems):
            resp = requests.post(f"{BASE_URL}/sets/{set_id}/answer",
                               json={"problemId": prob["id"], "answer": prob["correctAnswer"]},
                               cookies=cookies)
            assert resp.status_code == 200, f"Failed to answer problem {i+1}: {resp.status_code} {resp.text}"
            result = resp.json()
            assert result["correct"] == True, f"Problem {i+1} marked as incorrect"
            
            # Check final answer response
            if i == 29:  # Last problem
                print(f"\n[1.6] Verifying final answer response...")
                assert result["setComplete"] == True, "setComplete should be True"
                assert "starsEarned" in result, "Missing starsEarned field"
                assert result["starsEarned"] == 2, f"starsEarned should be 2, got {result['starsEarned']}"
                assert "starsToday" in result, "Missing starsToday field"
                assert "totalStars" in result, "Missing totalStars field"
                assert result["totalStars"] == 2, f"totalStars should be 2, got {result['totalStars']}"
                assert result["starsToday"] == 2, f"starsToday should be 2, got {result['starsToday']}"
                print(f"✓ Final answer response correct: starsEarned=2, starsToday=2, totalStars=2")
        
        print(f"✓ All 30 problems answered correctly")
        
        # Verify GET /api/kids returns stars fields
        print("\n[1.7] Verifying GET /api/kids returns stars fields...")
        resp = requests.get(f"{BASE_URL}/kids?date={today}", cookies=cookies)
        assert resp.status_code == 200, f"Failed to get kids: {resp.status_code} {resp.text}"
        kids = resp.json()["kids"]
        assert len(kids) == 1, f"Expected 1 kid, got {len(kids)}"
        kid = kids[0]
        assert kid["totalStars"] == 2, f"totalStars should be 2, got {kid['totalStars']}"
        assert kid["todayStars"] == 2, f"todayStars should be 2, got {kid['todayStars']}"
        assert len(kid["history"]) == 1, f"Expected 1 history entry, got {len(kid['history'])}"
        assert kid["history"][0]["stars"] == 2, f"history[0].stars should be 2, got {kid['history'][0]['stars']}"
        print(f"✓ GET /api/kids returns correct stars fields")
        
        print("\n" + "="*80)
        print("✅ TEST 1 PASSED: Stars rename + totals working correctly")
        print("="*80)
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST 1 FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ TEST 1 ERROR: {e}")
        return False
    finally:
        cleanup_test_data(parent_id)

def test_2_speed_math_start_and_structure():
    """
    TEST 2: SPEED MATH — start & structure
    - POST /api/kids/:id/speed {date} returns { session:{id,sessionNumber,status:'in_progress',
      problems:[10 items each {id,operation,display,answered,correct}], startedAt, timeLimit=180}, 
      serverNow, timeLimit=180, firstEver:true (first time) }. 
    - Confirm NO correctAnswer in client payload. 
    - Confirm a speedSessions doc was created with 10 problems + correctAnswer stored server-side.
    """
    print("\n" + "="*80)
    print("TEST 2: SPEED MATH — START & STRUCTURE")
    print("="*80)
    
    parent_id = setup_test_user()
    token = mint_jwt(parent_id, PARENT_EMAIL)
    cookies = {"mc_session": token}
    
    try:
        # Create a kid
        print("\n[2.1] Creating a kid...")
        resp = requests.post(f"{BASE_URL}/kids", 
                           json={"firstName": "SpeedKid", "grade": 3},
                           cookies=cookies)
        assert resp.status_code == 200, f"Failed to create kid: {resp.status_code} {resp.text}"
        kid_id = resp.json()["kid"]["id"]
        print(f"✓ Kid created: {kid_id}")
        
        # Start a speed session
        today = datetime.utcnow().strftime("%Y-%m-%d")
        print(f"\n[2.2] Starting a speed session for date {today}...")
        resp = requests.post(f"{BASE_URL}/kids/{kid_id}/speed",
                           json={"date": today},
                           cookies=cookies)
        assert resp.status_code == 200, f"Failed to start speed session: {resp.status_code} {resp.text}"
        data = resp.json()
        print(f"✓ Speed session started")
        
        # Verify response structure
        print("\n[2.3] Verifying response structure...")
        assert "session" in data, "Missing session field"
        assert "serverNow" in data, "Missing serverNow field"
        assert "timeLimit" in data, "Missing timeLimit field"
        assert "firstEver" in data, "Missing firstEver field"
        assert data["timeLimit"] == 180, f"timeLimit should be 180, got {data['timeLimit']}"
        assert data["firstEver"] == True, f"firstEver should be True for first session, got {data['firstEver']}"
        print(f"✓ Response structure correct: timeLimit=180, firstEver=True")
        
        session = data["session"]
        session_id = session["id"]
        assert "id" in session, "Missing session.id"
        assert "sessionNumber" in session, "Missing session.sessionNumber"
        assert "status" in session, "Missing session.status"
        assert "problems" in session, "Missing session.problems"
        assert "startedAt" in session, "Missing session.startedAt"
        assert "timeLimit" in session, "Missing session.timeLimit"
        assert session["status"] == "in_progress", f"status should be 'in_progress', got {session['status']}"
        assert session["sessionNumber"] == 1, f"sessionNumber should be 1, got {session['sessionNumber']}"
        assert session["timeLimit"] == 180, f"session.timeLimit should be 180, got {session['timeLimit']}"
        print(f"✓ Session structure correct: id={session_id}, sessionNumber=1, status=in_progress")
        
        # Verify problems structure
        print("\n[2.4] Verifying problems structure...")
        problems = session["problems"]
        assert len(problems) == 10, f"Expected 10 problems, got {len(problems)}"
        for i, prob in enumerate(problems):
            assert "id" in prob, f"Problem {i} missing id"
            assert "operation" in prob, f"Problem {i} missing operation"
            assert "display" in prob, f"Problem {i} missing display"
            assert "answered" in prob, f"Problem {i} missing answered"
            assert "correct" in prob, f"Problem {i} missing correct"
            assert "correctAnswer" not in prob, f"Problem {i} should NOT have correctAnswer in client payload"
            assert prob["answered"] == False, f"Problem {i} answered should be False initially"
            assert prob["correct"] == False, f"Problem {i} correct should be False initially"
        print(f"✓ All 10 problems have correct structure, NO correctAnswer in client payload")
        
        # Verify MongoDB document
        print("\n[2.5] Verifying MongoDB document...")
        db = get_mongo_db()
        session_doc = db["speedSessions"].find_one({"id": session_id})
        assert session_doc is not None, "Speed session not found in database"
        assert len(session_doc["problems"]) == 10, f"Expected 10 problems in DB, got {len(session_doc['problems'])}"
        for i, prob in enumerate(session_doc["problems"]):
            assert "correctAnswer" in prob, f"Problem {i} missing correctAnswer in DB"
            assert isinstance(prob["correctAnswer"], (int, float)), f"Problem {i} correctAnswer should be a number"
        print(f"✓ MongoDB document has 10 problems with correctAnswer stored server-side")
        
        print("\n" + "="*80)
        print("✅ TEST 2 PASSED: Speed math start & structure working correctly")
        print("="*80)
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST 2 FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ TEST 2 ERROR: {e}")
        return False
    finally:
        cleanup_test_data(parent_id)

def test_3_speed_scoring():
    """
    TEST 3: SPEED SCORING (score = 4 - 0.5*wrong, unanswered counts as wrong)
    - Perfect session: answer all 10 correctly. Response on 10th answer must have 
      sessionComplete=true, starsEarned=4, perfect=true, totalStars increased by 4.
    - 2-wrong session: answer 8 correct + 2 wrong. starsEarned=3.
    - Very-wrong session: answer all 10 wrong. starsEarned should be negative (e.g. -1 for 10 wrong).
      Verify kid's raw total drops, but GET /api/kids totalStars is clamped at 0 (never negative) 
      and rounded to at most 1 decimal.
    """
    print("\n" + "="*80)
    print("TEST 3: SPEED SCORING")
    print("="*80)
    
    parent_id = setup_test_user()
    token = mint_jwt(parent_id, PARENT_EMAIL)
    cookies = {"mc_session": token}
    
    try:
        # Create a kid
        print("\n[3.1] Creating a kid...")
        resp = requests.post(f"{BASE_URL}/kids", 
                           json={"firstName": "ScoreKid", "grade": 2},
                           cookies=cookies)
        assert resp.status_code == 200, f"Failed to create kid: {resp.status_code} {resp.text}"
        kid_id = resp.json()["kid"]["id"]
        print(f"✓ Kid created: {kid_id}")
        
        # TEST 3A: Perfect session (all 10 correct) = +4 stars
        print("\n[3.2] TEST 3A: Perfect session (all 10 correct)...")
        date1 = "2025-01-15"
        resp = requests.post(f"{BASE_URL}/kids/{kid_id}/speed",
                           json={"date": date1},
                           cookies=cookies)
        assert resp.status_code == 200, f"Failed to start speed session: {resp.status_code} {resp.text}"
        session1_id = resp.json()["session"]["id"]
        
        # Read correct answers from MongoDB
        db = get_mongo_db()
        session1_doc = db["speedSessions"].find_one({"id": session1_id})
        problems1 = session1_doc["problems"]
        
        # Answer all 10 correctly
        for i, prob in enumerate(problems1):
            resp = requests.post(f"{BASE_URL}/speed/{session1_id}/answer",
                               json={"problemId": prob["id"], "answer": prob["correctAnswer"]},
                               cookies=cookies)
            assert resp.status_code == 200, f"Failed to answer problem {i+1}: {resp.status_code} {resp.text}"
            result = resp.json()
            assert result["correct"] == True, f"Problem {i+1} marked as incorrect"
            
            # Check final answer response
            if i == 9:  # Last problem (10th)
                assert result.get("sessionComplete") == True, "sessionComplete should be True"
                assert "starsEarned" in result, "Missing starsEarned field"
                assert result["starsEarned"] == 4, f"starsEarned should be 4 for perfect, got {result['starsEarned']}"
                assert "perfect" in result, "Missing perfect field"
                assert result["perfect"] == True, f"perfect should be True, got {result['perfect']}"
                assert "totalStars" in result, "Missing totalStars field"
                assert result["totalStars"] == 4, f"totalStars should be 4, got {result['totalStars']}"
                print(f"✓ Perfect session: starsEarned=4, perfect=True, totalStars=4")
        
        # TEST 3B: 2-wrong session (8 correct + 2 wrong) = +3 stars
        print("\n[3.3] TEST 3B: 2-wrong session (8 correct + 2 wrong)...")
        date2 = "2025-01-16"
        resp = requests.post(f"{BASE_URL}/kids/{kid_id}/speed",
                           json={"date": date2},
                           cookies=cookies)
        assert resp.status_code == 200, f"Failed to start speed session: {resp.status_code} {resp.text}"
        session2_id = resp.json()["session"]["id"]
        
        # Read correct answers from MongoDB
        session2_doc = db["speedSessions"].find_one({"id": session2_id})
        problems2 = session2_doc["problems"]
        
        # Answer 8 correct + 2 wrong
        for i, prob in enumerate(problems2):
            if i < 8:  # First 8 correct
                answer = prob["correctAnswer"]
            else:  # Last 2 wrong
                answer = prob["correctAnswer"] + 999
            
            resp = requests.post(f"{BASE_URL}/speed/{session2_id}/answer",
                               json={"problemId": prob["id"], "answer": answer},
                               cookies=cookies)
            assert resp.status_code == 200, f"Failed to answer problem {i+1}: {resp.status_code} {resp.text}"
            result = resp.json()
            
            # Check final answer response
            if i == 9:  # Last problem (10th)
                assert result.get("sessionComplete") == True, "sessionComplete should be True"
                assert "starsEarned" in result, "Missing starsEarned field"
                assert result["starsEarned"] == 3, f"starsEarned should be 3 for 2 wrong, got {result['starsEarned']}"
                assert result.get("perfect") == False, f"perfect should be False, got {result.get('perfect')}"
                assert "totalStars" in result, "Missing totalStars field"
                assert result["totalStars"] == 7, f"totalStars should be 7 (4+3), got {result['totalStars']}"
                print(f"✓ 2-wrong session: starsEarned=3, perfect=False, totalStars=7")
        
        # TEST 3C: Very-wrong session (all 10 wrong) = negative stars
        print("\n[3.4] TEST 3C: Very-wrong session (all 10 wrong)...")
        date3 = "2025-01-17"
        resp = requests.post(f"{BASE_URL}/kids/{kid_id}/speed",
                           json={"date": date3},
                           cookies=cookies)
        assert resp.status_code == 200, f"Failed to start speed session: {resp.status_code} {resp.text}"
        session3_id = resp.json()["session"]["id"]
        
        # Read correct answers from MongoDB
        session3_doc = db["speedSessions"].find_one({"id": session3_id})
        problems3 = session3_doc["problems"]
        
        # Answer all 10 wrong
        for i, prob in enumerate(problems3):
            answer = prob["correctAnswer"] + 999  # Wrong answer
            
            resp = requests.post(f"{BASE_URL}/speed/{session3_id}/answer",
                               json={"problemId": prob["id"], "answer": answer},
                               cookies=cookies)
            assert resp.status_code == 200, f"Failed to answer problem {i+1}: {resp.status_code} {resp.text}"
            result = resp.json()
            
            # Check final answer response
            if i == 9:  # Last problem (10th)
                assert result.get("sessionComplete") == True, "sessionComplete should be True"
                assert "starsEarned" in result, "Missing starsEarned field"
                # Score = 4 - 0.5*10 = 4 - 5 = -1
                assert result["starsEarned"] == -1, f"starsEarned should be -1 for 10 wrong, got {result['starsEarned']}"
                assert result.get("perfect") == False, f"perfect should be False"
                # totalStars should be clamped at 0 (7 + (-1) = 6, but if it was 0 before, it stays 0)
                # Actually, kid had 7 stars, so 7 + (-1) = 6
                assert "totalStars" in result, "Missing totalStars field"
                print(f"✓ Very-wrong session: starsEarned=-1, totalStars={result['totalStars']}")
        
        # Verify GET /api/kids totalStars is clamped at 0 and rounded to 1 decimal
        print("\n[3.5] Verifying GET /api/kids totalStars clamping and rounding...")
        resp = requests.get(f"{BASE_URL}/kids?date={date3}", cookies=cookies)
        assert resp.status_code == 200, f"Failed to get kids: {resp.status_code} {resp.text}"
        kid = resp.json()["kids"][0]
        assert kid["totalStars"] >= 0, f"totalStars should be clamped at 0, got {kid['totalStars']}"
        # Check if rounded to at most 1 decimal
        assert kid["totalStars"] == round(kid["totalStars"], 1), f"totalStars should be rounded to 1 decimal"
        print(f"✓ totalStars is clamped at 0 and rounded to 1 decimal: {kid['totalStars']}")
        
        print("\n" + "="*80)
        print("✅ TEST 3 PASSED: Speed scoring working correctly")
        print("="*80)
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST 3 FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ TEST 3 ERROR: {e}")
        return False
    finally:
        cleanup_test_data(parent_id)

def test_4_timer_expiry():
    """
    TEST 4: TIMER EXPIRY (server-enforced 180s + 10s grace)
    - Start a session, then directly set its startedAt in Mongo to ~200 seconds in the past.
    - Answer a problem: the answer must be rejected and the session finalized (timeUp:true) 
      with unanswered problems counted as wrong.
    """
    print("\n" + "="*80)
    print("TEST 4: TIMER EXPIRY")
    print("="*80)
    
    parent_id = setup_test_user()
    token = mint_jwt(parent_id, PARENT_EMAIL)
    cookies = {"mc_session": token}
    
    try:
        # Create a kid
        print("\n[4.1] Creating a kid...")
        resp = requests.post(f"{BASE_URL}/kids", 
                           json={"firstName": "TimerKid", "grade": 2},
                           cookies=cookies)
        assert resp.status_code == 200, f"Failed to create kid: {resp.status_code} {resp.text}"
        kid_id = resp.json()["kid"]["id"]
        print(f"✓ Kid created: {kid_id}")
        
        # Start a speed session
        today = datetime.utcnow().strftime("%Y-%m-%d")
        print(f"\n[4.2] Starting a speed session...")
        resp = requests.post(f"{BASE_URL}/kids/{kid_id}/speed",
                           json={"date": today},
                           cookies=cookies)
        assert resp.status_code == 200, f"Failed to start speed session: {resp.status_code} {resp.text}"
        session_id = resp.json()["session"]["id"]
        print(f"✓ Speed session started: {session_id}")
        
        # Answer 6 problems first
        print("\n[4.3] Answering 6 problems first...")
        db = get_mongo_db()
        session_doc = db["speedSessions"].find_one({"id": session_id})
        problems = session_doc["problems"]
        
        for i in range(6):
            prob = problems[i]
            resp = requests.post(f"{BASE_URL}/speed/{session_id}/answer",
                               json={"problemId": prob["id"], "answer": prob["correctAnswer"]},
                               cookies=cookies)
            assert resp.status_code == 200, f"Failed to answer problem {i+1}: {resp.status_code} {resp.text}"
        print(f"✓ Answered 6 problems correctly")
        
        # Back-date the session startedAt to 200 seconds in the past
        print("\n[4.4] Back-dating session startedAt to 200 seconds in the past...")
        past_time = datetime.utcnow() - timedelta(seconds=200)
        db["speedSessions"].update_one(
            {"id": session_id},
            {"$set": {"startedAt": past_time}}
        )
        print(f"✓ Session startedAt set to {past_time}")
        
        # Try to answer the 7th problem - should be rejected
        print("\n[4.5] Trying to answer 7th problem (should be rejected)...")
        prob7 = problems[6]
        resp = requests.post(f"{BASE_URL}/speed/{session_id}/answer",
                           json={"problemId": prob7["id"], "answer": prob7["correctAnswer"]},
                           cookies=cookies)
        assert resp.status_code == 200, f"Request failed: {resp.status_code} {resp.text}"
        result = resp.json()
        
        # Verify time's up response
        assert "timeUp" in result, "Missing timeUp field"
        assert result["timeUp"] == True, f"timeUp should be True, got {result['timeUp']}"
        assert result.get("sessionComplete") == True, "sessionComplete should be True"
        print(f"✓ Answer rejected with timeUp=True")
        
        # Verify unanswered problems counted as wrong in score
        # 6 correct + 4 unanswered (counted as wrong) = 4 - 0.5*4 = 2
        assert "starsEarned" in result, "Missing starsEarned field"
        expected_score = 4 - 0.5 * 4  # 4 unanswered = 4 wrong
        assert result["starsEarned"] == expected_score, f"starsEarned should be {expected_score}, got {result['starsEarned']}"
        print(f"✓ Unanswered problems counted as wrong: starsEarned={result['starsEarned']}")
        
        # Verify session is finalized in DB
        print("\n[4.6] Verifying session is finalized in DB...")
        session_doc = db["speedSessions"].find_one({"id": session_id})
        assert session_doc["status"] == "finished", f"Session status should be 'finished', got {session_doc['status']}"
        print(f"✓ Session finalized in DB with status='finished'")
        
        print("\n" + "="*80)
        print("✅ TEST 4 PASSED: Timer expiry working correctly")
        print("="*80)
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST 4 FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ TEST 4 ERROR: {e}")
        return False
    finally:
        cleanup_test_data(parent_id)

def test_5_three_per_day_speed_cap():
    """
    TEST 5: 3-PER-DAY SPEED CAP
    - On a single date, start and finish 3 speed sessions.
    - A 4th POST /api/kids/:id/speed {same date} must return {locked:true}.
    - Confirm normal sets still allow 2 that same day independently.
    """
    print("\n" + "="*80)
    print("TEST 5: 3-PER-DAY SPEED CAP")
    print("="*80)
    
    parent_id = setup_test_user()
    token = mint_jwt(parent_id, PARENT_EMAIL)
    cookies = {"mc_session": token}
    
    try:
        # Create a kid
        print("\n[5.1] Creating a kid...")
        resp = requests.post(f"{BASE_URL}/kids", 
                           json={"firstName": "CapKid", "grade": 2},
                           cookies=cookies)
        assert resp.status_code == 200, f"Failed to create kid: {resp.status_code} {resp.text}"
        kid_id = resp.json()["kid"]["id"]
        print(f"✓ Kid created: {kid_id}")
        
        today = datetime.utcnow().strftime("%Y-%m-%d")
        db = get_mongo_db()
        
        # Complete 3 speed sessions
        print(f"\n[5.2] Completing 3 speed sessions on {today}...")
        for session_num in range(1, 4):
            print(f"\n  Session {session_num}:")
            # Start session
            resp = requests.post(f"{BASE_URL}/kids/{kid_id}/speed",
                               json={"date": today},
                               cookies=cookies)
            assert resp.status_code == 200, f"Failed to start session {session_num}: {resp.status_code} {resp.text}"
            session_id = resp.json()["session"]["id"]
            print(f"  ✓ Started session {session_num}: {session_id}")
            
            # Read correct answers and complete session
            session_doc = db["speedSessions"].find_one({"id": session_id})
            problems = session_doc["problems"]
            
            for prob in problems:
                resp = requests.post(f"{BASE_URL}/speed/{session_id}/answer",
                                   json={"problemId": prob["id"], "answer": prob["correctAnswer"]},
                                   cookies=cookies)
                assert resp.status_code == 200, f"Failed to answer: {resp.status_code} {resp.text}"
            print(f"  ✓ Completed session {session_num}")
        
        print(f"✓ Completed 3 speed sessions")
        
        # Try to start a 4th session - should be locked
        print(f"\n[5.3] Trying to start 4th speed session (should be locked)...")
        resp = requests.post(f"{BASE_URL}/kids/{kid_id}/speed",
                           json={"date": today},
                           cookies=cookies)
        assert resp.status_code == 200, f"Request failed: {resp.status_code} {resp.text}"
        result = resp.json()
        assert "locked" in result, "Missing locked field"
        assert result["locked"] == True, f"locked should be True, got {result['locked']}"
        print(f"✓ 4th speed session blocked with locked=True")
        
        # Verify normal sets still allow 2 on the same day
        print(f"\n[5.4] Verifying normal sets still allow 2 on the same day...")
        
        # Start and complete first normal set
        resp = requests.post(f"{BASE_URL}/kids/{kid_id}/set",
                           json={"date": today},
                           cookies=cookies)
        assert resp.status_code == 200, f"Failed to start normal set 1: {resp.status_code} {resp.text}"
        set1_id = resp.json()["set"]["id"]
        
        set1_doc = db["dailySets"].find_one({"id": set1_id})
        for prob in set1_doc["problems"]:
            resp = requests.post(f"{BASE_URL}/sets/{set1_id}/answer",
                               json={"problemId": prob["id"], "answer": prob["correctAnswer"]},
                               cookies=cookies)
            assert resp.status_code == 200, f"Failed to answer: {resp.status_code} {resp.text}"
        print(f"✓ Completed normal set 1")
        
        # Start and complete second normal set
        resp = requests.post(f"{BASE_URL}/kids/{kid_id}/set",
                           json={"date": today},
                           cookies=cookies)
        assert resp.status_code == 200, f"Failed to start normal set 2: {resp.status_code} {resp.text}"
        set2_id = resp.json()["set"]["id"]
        
        set2_doc = db["dailySets"].find_one({"id": set2_id})
        for prob in set2_doc["problems"]:
            resp = requests.post(f"{BASE_URL}/sets/{set2_id}/answer",
                               json={"problemId": prob["id"], "answer": prob["correctAnswer"]},
                               cookies=cookies)
            assert resp.status_code == 200, f"Failed to answer: {resp.status_code} {resp.text}"
        print(f"✓ Completed normal set 2")
        
        # Try to start a 3rd normal set - should be locked
        resp = requests.post(f"{BASE_URL}/kids/{kid_id}/set",
                           json={"date": today},
                           cookies=cookies)
        assert resp.status_code == 200, f"Request failed: {resp.status_code} {resp.text}"
        result = resp.json()
        assert "locked" in result, "Missing locked field"
        assert result["locked"] == True, f"Normal set locked should be True, got {result['locked']}"
        print(f"✓ Normal sets allow 2 per day independently (3rd blocked)")
        
        print("\n" + "="*80)
        print("✅ TEST 5 PASSED: 3-per-day speed cap working correctly")
        print("="*80)
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST 5 FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ TEST 5 ERROR: {e}")
        return False
    finally:
        cleanup_test_data(parent_id)

def test_6_speed_does_not_affect_leveling():
    """
    TEST 6: SPEED DOES NOT AFFECT LEVELING
    - Note kid.difficultyStep before.
    - Complete 3 PERFECT speed sessions (across 3 dates to avoid cap).
    - Verify difficultyStep did NOT increase.
    - Complete a speed session with many wrong.
    - Verify difficultyStep did NOT decrease.
    """
    print("\n" + "="*80)
    print("TEST 6: SPEED DOES NOT AFFECT LEVELING")
    print("="*80)
    
    parent_id = setup_test_user()
    token = mint_jwt(parent_id, PARENT_EMAIL)
    cookies = {"mc_session": token}
    
    try:
        # Create a kid
        print("\n[6.1] Creating a kid...")
        resp = requests.post(f"{BASE_URL}/kids", 
                           json={"firstName": "LevelKid", "grade": 2},
                           cookies=cookies)
        assert resp.status_code == 200, f"Failed to create kid: {resp.status_code} {resp.text}"
        kid_id = resp.json()["kid"]["id"]
        print(f"✓ Kid created: {kid_id}")
        
        # Note initial difficultyStep
        db = get_mongo_db()
        kid_doc = db["kids"].find_one({"id": kid_id})
        initial_step = kid_doc.get("difficultyStep", 0)
        print(f"\n[6.2] Initial difficultyStep: {initial_step}")
        
        # Complete 3 PERFECT speed sessions across 3 dates
        print(f"\n[6.3] Completing 3 PERFECT speed sessions across 3 dates...")
        dates = ["2025-01-15", "2025-01-16", "2025-01-17"]
        
        for i, date in enumerate(dates):
            print(f"\n  Session {i+1} on {date}:")
            # Start session
            resp = requests.post(f"{BASE_URL}/kids/{kid_id}/speed",
                               json={"date": date},
                               cookies=cookies)
            assert resp.status_code == 200, f"Failed to start session: {resp.status_code} {resp.text}"
            session_id = resp.json()["session"]["id"]
            
            # Read correct answers and complete perfectly
            session_doc = db["speedSessions"].find_one({"id": session_id})
            problems = session_doc["problems"]
            
            for prob in problems:
                resp = requests.post(f"{BASE_URL}/speed/{session_id}/answer",
                                   json={"problemId": prob["id"], "answer": prob["correctAnswer"]},
                                   cookies=cookies)
                assert resp.status_code == 200, f"Failed to answer: {resp.status_code} {resp.text}"
            print(f"  ✓ Completed perfect session {i+1}")
        
        # Verify difficultyStep did NOT increase
        print(f"\n[6.4] Verifying difficultyStep did NOT increase...")
        kid_doc = db["kids"].find_one({"id": kid_id})
        step_after_perfect = kid_doc.get("difficultyStep", 0)
        assert step_after_perfect == initial_step, f"difficultyStep should NOT change after perfect speed sessions, was {initial_step}, now {step_after_perfect}"
        print(f"✓ difficultyStep unchanged after 3 perfect speed sessions: {step_after_perfect}")
        
        # Complete a speed session with many wrong
        print(f"\n[6.5] Completing a speed session with all wrong answers...")
        date4 = "2025-01-18"
        resp = requests.post(f"{BASE_URL}/kids/{kid_id}/speed",
                           json={"date": date4},
                           cookies=cookies)
        assert resp.status_code == 200, f"Failed to start session: {resp.status_code} {resp.text}"
        session_id = resp.json()["session"]["id"]
        
        # Read correct answers and answer all wrong
        session_doc = db["speedSessions"].find_one({"id": session_id})
        problems = session_doc["problems"]
        
        for prob in problems:
            wrong_answer = prob["correctAnswer"] + 999
            resp = requests.post(f"{BASE_URL}/speed/{session_id}/answer",
                               json={"problemId": prob["id"], "answer": wrong_answer},
                               cookies=cookies)
            assert resp.status_code == 200, f"Failed to answer: {resp.status_code} {resp.text}"
        print(f"✓ Completed session with all wrong answers")
        
        # Verify difficultyStep did NOT decrease
        print(f"\n[6.6] Verifying difficultyStep did NOT decrease...")
        kid_doc = db["kids"].find_one({"id": kid_id})
        step_after_wrong = kid_doc.get("difficultyStep", 0)
        assert step_after_wrong == initial_step, f"difficultyStep should NOT change after wrong speed session, was {initial_step}, now {step_after_wrong}"
        print(f"✓ difficultyStep unchanged after wrong speed session: {step_after_wrong}")
        
        print("\n" + "="*80)
        print("✅ TEST 6 PASSED: Speed does not affect leveling")
        print("="*80)
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST 6 FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ TEST 6 ERROR: {e}")
        return False
    finally:
        cleanup_test_data(parent_id)

def test_7_no_repeats_within_day():
    """
    TEST 7: NO REPEATS WITHIN A DAY (Grade 1 heavy day)
    - Create a Grade 1 kid.
    - On ONE date: complete 2 normal sets (60 problems) AND 3 speed sessions (30 problems) = 90 total.
    - Collect all problem display strings from that day's dailySets + speedSessions.
    - Assert there are NO duplicate display strings across the entire day.
    - Verify generator did not stall/hang.
    """
    print("\n" + "="*80)
    print("TEST 7: NO REPEATS WITHIN A DAY (Grade 1 heavy day)")
    print("="*80)
    
    parent_id = setup_test_user()
    token = mint_jwt(parent_id, PARENT_EMAIL)
    cookies = {"mc_session": token}
    
    try:
        # Create a Grade 1 kid
        print("\n[7.1] Creating a Grade 1 kid...")
        resp = requests.post(f"{BASE_URL}/kids", 
                           json={"firstName": "RepeatKid", "grade": 1},
                           cookies=cookies)
        assert resp.status_code == 200, f"Failed to create kid: {resp.status_code} {resp.text}"
        kid_id = resp.json()["kid"]["id"]
        print(f"✓ Grade 1 kid created: {kid_id}")
        
        today = datetime.utcnow().strftime("%Y-%m-%d")
        db = get_mongo_db()
        all_displays = []
        
        # Complete 2 normal sets (60 problems)
        print(f"\n[7.2] Completing 2 normal sets (60 problems) on {today}...")
        for set_num in range(1, 3):
            print(f"\n  Normal set {set_num}:")
            # Start set
            resp = requests.post(f"{BASE_URL}/kids/{kid_id}/set",
                               json={"date": today},
                               cookies=cookies)
            assert resp.status_code == 200, f"Failed to start set {set_num}: {resp.status_code} {resp.text}"
            set_id = resp.json()["set"]["id"]
            
            # Read problems and collect displays
            set_doc = db["dailySets"].find_one({"id": set_id})
            problems = set_doc["problems"]
            assert len(problems) == 30, f"Expected 30 problems, got {len(problems)}"
            
            for prob in problems:
                all_displays.append(prob["display"])
                # Answer problem
                resp = requests.post(f"{BASE_URL}/sets/{set_id}/answer",
                                   json={"problemId": prob["id"], "answer": prob["correctAnswer"]},
                                   cookies=cookies)
                assert resp.status_code == 200, f"Failed to answer: {resp.status_code} {resp.text}"
            
            print(f"  ✓ Completed normal set {set_num} (30 problems)")
        
        print(f"✓ Completed 2 normal sets (60 problems total)")
        
        # Complete 3 speed sessions (30 problems)
        print(f"\n[7.3] Completing 3 speed sessions (30 problems) on {today}...")
        for session_num in range(1, 4):
            print(f"\n  Speed session {session_num}:")
            # Start session
            resp = requests.post(f"{BASE_URL}/kids/{kid_id}/speed",
                               json={"date": today},
                               cookies=cookies)
            assert resp.status_code == 200, f"Failed to start session {session_num}: {resp.status_code} {resp.text}"
            session_id = resp.json()["session"]["id"]
            
            # Read problems and collect displays
            session_doc = db["speedSessions"].find_one({"id": session_id})
            problems = session_doc["problems"]
            assert len(problems) == 10, f"Expected 10 problems, got {len(problems)}"
            
            for prob in problems:
                all_displays.append(prob["display"])
                # Answer problem
                resp = requests.post(f"{BASE_URL}/speed/{session_id}/answer",
                                   json={"problemId": prob["id"], "answer": prob["correctAnswer"]},
                                   cookies=cookies)
                assert resp.status_code == 200, f"Failed to answer: {resp.status_code} {resp.text}"
            
            print(f"  ✓ Completed speed session {session_num} (10 problems)")
        
        print(f"✓ Completed 3 speed sessions (30 problems total)")
        
        # Verify no duplicates
        print(f"\n[7.4] Verifying no duplicate display strings...")
        total_problems = len(all_displays)
        unique_displays = len(set(all_displays))
        
        print(f"  Total problems: {total_problems}")
        print(f"  Unique displays: {unique_displays}")
        
        assert total_problems == 90, f"Expected 90 total problems, got {total_problems}"
        assert unique_displays == 90, f"Found {total_problems - unique_displays} duplicate display strings"
        
        print(f"✓ No duplicate display strings across the entire day (90 unique problems)")
        
        print("\n" + "="*80)
        print("✅ TEST 7 PASSED: No repeats within a day")
        print("="*80)
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST 7 FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ TEST 7 ERROR: {e}")
        return False
    finally:
        cleanup_test_data(parent_id)

def test_8_exit():
    """
    TEST 8: EXIT
    - Normal exit: start a normal set, answer 29 correct (leave 1), POST /api/sets/:id/exit.
      The dailySet status becomes 'exited', no stars awarded, does NOT count toward 2/day cap.
      Immediately start a NEW normal set same date and complete it -> counts as one of the day's 2.
    - Speed exit: start a speed session, POST /api/speed/:id/exit. Status becomes 'exited',
      totalStars unchanged, BUT it consumes a speed slot: speedRemaining drops by 1.
    """
    print("\n" + "="*80)
    print("TEST 8: EXIT")
    print("="*80)
    
    parent_id = setup_test_user()
    token = mint_jwt(parent_id, PARENT_EMAIL)
    cookies = {"mc_session": token}
    
    try:
        # Create a kid
        print("\n[8.1] Creating a kid...")
        resp = requests.post(f"{BASE_URL}/kids", 
                           json={"firstName": "ExitKid", "grade": 2},
                           cookies=cookies)
        assert resp.status_code == 200, f"Failed to create kid: {resp.status_code} {resp.text}"
        kid_id = resp.json()["kid"]["id"]
        print(f"✓ Kid created: {kid_id}")
        
        today = datetime.utcnow().strftime("%Y-%m-%d")
        db = get_mongo_db()
        
        # TEST 8A: Normal exit
        print(f"\n[8.2] TEST 8A: Normal exit...")
        
        # Start a normal set
        resp = requests.post(f"{BASE_URL}/kids/{kid_id}/set",
                           json={"date": today},
                           cookies=cookies)
        assert resp.status_code == 200, f"Failed to start set: {resp.status_code} {resp.text}"
        set1_id = resp.json()["set"]["id"]
        print(f"✓ Started normal set: {set1_id}")
        
        # Answer 29 problems (leave 1)
        set1_doc = db["dailySets"].find_one({"id": set1_id})
        problems = set1_doc["problems"]
        
        for i in range(29):
            prob = problems[i]
            resp = requests.post(f"{BASE_URL}/sets/{set1_id}/answer",
                               json={"problemId": prob["id"], "answer": prob["correctAnswer"]},
                               cookies=cookies)
            assert resp.status_code == 200, f"Failed to answer: {resp.status_code} {resp.text}"
        print(f"✓ Answered 29 problems (left 1 unsolved)")
        
        # Note totalStars before exit
        resp = requests.get(f"{BASE_URL}/kids?date={today}", cookies=cookies)
        stars_before_exit = resp.json()["kids"][0]["totalStars"]
        print(f"✓ totalStars before exit: {stars_before_exit}")
        
        # Exit the set
        resp = requests.post(f"{BASE_URL}/sets/{set1_id}/exit", cookies=cookies)
        assert resp.status_code == 200, f"Failed to exit set: {resp.status_code} {resp.text}"
        print(f"✓ Exited normal set")
        
        # Verify set status is 'exited'
        set1_doc = db["dailySets"].find_one({"id": set1_id})
        assert set1_doc["status"] == "exited", f"Set status should be 'exited', got {set1_doc['status']}"
        print(f"✓ Set status is 'exited'")
        
        # Verify no stars awarded
        resp = requests.get(f"{BASE_URL}/kids?date={today}", cookies=cookies)
        stars_after_exit = resp.json()["kids"][0]["totalStars"]
        assert stars_after_exit == stars_before_exit, f"totalStars should be unchanged, was {stars_before_exit}, now {stars_after_exit}"
        print(f"✓ No stars awarded (totalStars unchanged: {stars_after_exit})")
        
        # Start a NEW normal set same date (should work - exit doesn't count toward cap)
        resp = requests.post(f"{BASE_URL}/kids/{kid_id}/set",
                           json={"date": today},
                           cookies=cookies)
        assert resp.status_code == 200, f"Failed to start new set after exit: {resp.status_code} {resp.text}"
        set2_id = resp.json()["set"]["id"]
        print(f"✓ Started new normal set after exit: {set2_id}")
        
        # Complete the new set
        set2_doc = db["dailySets"].find_one({"id": set2_id})
        for prob in set2_doc["problems"]:
            resp = requests.post(f"{BASE_URL}/sets/{set2_id}/answer",
                               json={"problemId": prob["id"], "answer": prob["correctAnswer"]},
                               cookies=cookies)
            assert resp.status_code == 200, f"Failed to answer: {resp.status_code} {resp.text}"
        print(f"✓ Completed new set (counts as 1 of 2 for the day)")
        
        # Verify can still complete another set (total 2 for the day)
        resp = requests.post(f"{BASE_URL}/kids/{kid_id}/set",
                           json={"date": today},
                           cookies=cookies)
        assert resp.status_code == 200, f"Failed to start 2nd earning set: {resp.status_code} {resp.text}"
        set3_id = resp.json()["set"]["id"]
        
        set3_doc = db["dailySets"].find_one({"id": set3_id})
        for prob in set3_doc["problems"]:
            resp = requests.post(f"{BASE_URL}/sets/{set3_id}/answer",
                               json={"problemId": prob["id"], "answer": prob["correctAnswer"]},
                               cookies=cookies)
            assert resp.status_code == 200, f"Failed to answer: {resp.status_code} {resp.text}"
        print(f"✓ Completed 2nd earning set (total 2 completed sets for the day)")
        
        # Verify 3rd set is locked
        resp = requests.post(f"{BASE_URL}/kids/{kid_id}/set",
                           json={"date": today},
                           cookies=cookies)
        assert resp.json().get("locked") == True, "3rd set should be locked"
        print(f"✓ Exit does NOT count toward 2/day cap (3rd set locked)")
        
        # TEST 8B: Speed exit
        print(f"\n[8.3] TEST 8B: Speed exit...")
        
        # Note speedRemaining before
        resp = requests.get(f"{BASE_URL}/kids?date={today}", cookies=cookies)
        kid_stats = resp.json()["kids"][0]
        speed_remaining_before = kid_stats["speedRemaining"]
        stars_before_speed_exit = kid_stats["totalStars"]
        print(f"✓ speedRemaining before: {speed_remaining_before}, totalStars: {stars_before_speed_exit}")
        
        # Start a speed session
        resp = requests.post(f"{BASE_URL}/kids/{kid_id}/speed",
                           json={"date": today},
                           cookies=cookies)
        assert resp.status_code == 200, f"Failed to start speed session: {resp.status_code} {resp.text}"
        session_id = resp.json()["session"]["id"]
        print(f"✓ Started speed session: {session_id}")
        
        # Exit the speed session
        resp = requests.post(f"{BASE_URL}/speed/{session_id}/exit", cookies=cookies)
        assert resp.status_code == 200, f"Failed to exit speed session: {resp.status_code} {resp.text}"
        print(f"✓ Exited speed session")
        
        # Verify session status is 'exited'
        session_doc = db["speedSessions"].find_one({"id": session_id})
        assert session_doc["status"] == "exited", f"Session status should be 'exited', got {session_doc['status']}"
        print(f"✓ Session status is 'exited'")
        
        # Verify totalStars unchanged
        resp = requests.get(f"{BASE_URL}/kids?date={today}", cookies=cookies)
        kid_stats = resp.json()["kids"][0]
        stars_after_speed_exit = kid_stats["totalStars"]
        assert stars_after_speed_exit == stars_before_speed_exit, f"totalStars should be unchanged, was {stars_before_speed_exit}, now {stars_after_speed_exit}"
        print(f"✓ totalStars unchanged: {stars_after_speed_exit}")
        
        # Verify speedRemaining dropped by 1 (exit consumes a slot)
        speed_remaining_after = kid_stats["speedRemaining"]
        assert speed_remaining_after == speed_remaining_before - 1, f"speedRemaining should drop by 1, was {speed_remaining_before}, now {speed_remaining_after}"
        print(f"✓ speedRemaining dropped by 1: {speed_remaining_after} (exit consumes a speed slot)")
        
        print("\n" + "="*80)
        print("✅ TEST 8 PASSED: Exit functionality working correctly")
        print("="*80)
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST 8 FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ TEST 8 ERROR: {e}")
        return False
    finally:
        cleanup_test_data(parent_id)

def test_9_daily_rollover_stale_expiry():
    """
    TEST 9: DAILY ROLLOVER / STALE EXPIRY
    - Create an in_progress dailySet AND an in_progress speedSession with date = yesterday.
    - Then POST /api/kids/:id/set {date: today} (or GET /api/kids?date=today).
    - Verify the yesterday in_progress docs are marked status 'expired' (dead — contribute no stars).
    - Verify a FRESH set is created for today.
    - Verify totalStars did not change from the expired docs.
    """
    print("\n" + "="*80)
    print("TEST 9: DAILY ROLLOVER / STALE EXPIRY")
    print("="*80)
    
    parent_id = setup_test_user()
    token = mint_jwt(parent_id, PARENT_EMAIL)
    cookies = {"mc_session": token}
    
    try:
        # Create a kid
        print("\n[9.1] Creating a kid...")
        resp = requests.post(f"{BASE_URL}/kids", 
                           json={"firstName": "RolloverKid", "grade": 2},
                           cookies=cookies)
        assert resp.status_code == 200, f"Failed to create kid: {resp.status_code} {resp.text}"
        kid_id = resp.json()["kid"]["id"]
        print(f"✓ Kid created: {kid_id}")
        
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        today = datetime.utcnow().strftime("%Y-%m-%d")
        db = get_mongo_db()
        
        # Note totalStars before
        resp = requests.get(f"{BASE_URL}/kids?date={today}", cookies=cookies)
        stars_before = resp.json()["kids"][0]["totalStars"]
        print(f"\n[9.2] totalStars before: {stars_before}")
        
        # Create an in_progress dailySet with yesterday's date
        print(f"\n[9.3] Creating in_progress dailySet with date={yesterday}...")
        set_id = str(uuid4())
        db["dailySets"].insert_one({
            "id": set_id,
            "kidId": kid_id,
            "date": yesterday,
            "status": "in_progress",
            "difficultyStep": 0,
            "problems": [{"id": str(uuid4()), "display": "1 + 1", "correctAnswer": 2, "solved": False, "attempts": 0}] * 30,
            "createdAt": datetime.utcnow() - timedelta(days=1)
        })
        print(f"✓ Created in_progress dailySet: {set_id}")
        
        # Create an in_progress speedSession with yesterday's date
        print(f"\n[9.4] Creating in_progress speedSession with date={yesterday}...")
        session_id = str(uuid4())
        db["speedSessions"].insert_one({
            "id": session_id,
            "kidId": kid_id,
            "date": yesterday,
            "sessionNumber": 1,
            "status": "in_progress",
            "startedAt": datetime.utcnow() - timedelta(days=1),
            "difficultyStep": 0,
            "problems": [{"id": str(uuid4()), "display": "2 + 2", "correctAnswer": 4, "answered": False, "correct": False}] * 10,
            "createdAt": datetime.utcnow() - timedelta(days=1)
        })
        print(f"✓ Created in_progress speedSession: {session_id}")
        
        # Trigger expiry by starting a new set for today
        print(f"\n[9.5] Starting a new set for today (triggers expiry)...")
        resp = requests.post(f"{BASE_URL}/kids/{kid_id}/set",
                           json={"date": today},
                           cookies=cookies)
        assert resp.status_code == 200, f"Failed to start set: {resp.status_code} {resp.text}"
        new_set_id = resp.json()["set"]["id"]
        print(f"✓ Started new set for today: {new_set_id}")
        
        # Verify yesterday's in_progress docs are marked 'expired'
        print(f"\n[9.6] Verifying yesterday's in_progress docs are marked 'expired'...")
        set_doc = db["dailySets"].find_one({"id": set_id})
        assert set_doc["status"] == "expired", f"dailySet status should be 'expired', got {set_doc['status']}"
        print(f"✓ Yesterday's dailySet marked 'expired'")
        
        session_doc = db["speedSessions"].find_one({"id": session_id})
        assert session_doc["status"] == "expired", f"speedSession status should be 'expired', got {session_doc['status']}"
        print(f"✓ Yesterday's speedSession marked 'expired'")
        
        # Verify a FRESH set was created for today
        print(f"\n[9.7] Verifying a FRESH set was created for today...")
        new_set_doc = db["dailySets"].find_one({"id": new_set_id})
        assert new_set_doc["date"] == today, f"New set date should be {today}, got {new_set_doc['date']}"
        assert new_set_doc["status"] == "in_progress", f"New set status should be 'in_progress', got {new_set_doc['status']}"
        print(f"✓ Fresh set created for today with status 'in_progress'")
        
        # Verify totalStars did not change from expired docs
        print(f"\n[9.8] Verifying totalStars did not change from expired docs...")
        resp = requests.get(f"{BASE_URL}/kids?date={today}", cookies=cookies)
        stars_after = resp.json()["kids"][0]["totalStars"]
        assert stars_after == stars_before, f"totalStars should be unchanged, was {stars_before}, now {stars_after}"
        print(f"✓ totalStars unchanged: {stars_after} (expired docs contribute no stars)")
        
        print("\n" + "="*80)
        print("✅ TEST 9 PASSED: Daily rollover / stale expiry working correctly")
        print("="*80)
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST 9 FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ TEST 9 ERROR: {e}")
        return False
    finally:
        cleanup_test_data(parent_id)

def test_10_theme():
    """
    TEST 10: THEME (additive)
    - POST /api/kids with theme 'ocean' -> kidStats.theme === 'ocean'.
    - A kid created WITHOUT theme (simulate existing kid) -> kidStats.theme defaults to 'animals'.
    - PUT /api/kids/:id { theme: 'space' } updates it; invalid theme 'purple' -> 400.
    - Two kids under the same parent can hold different themes simultaneously.
    """
    print("\n" + "="*80)
    print("TEST 10: THEME (additive)")
    print("="*80)
    
    parent_id = setup_test_user()
    token = mint_jwt(parent_id, PARENT_EMAIL)
    cookies = {"mc_session": token}
    
    try:
        # TEST 10A: Create kid with theme 'ocean'
        print("\n[10.1] TEST 10A: Create kid with theme 'ocean'...")
        resp = requests.post(f"{BASE_URL}/kids", 
                           json={"firstName": "OceanKid", "grade": 2, "theme": "ocean"},
                           cookies=cookies)
        assert resp.status_code == 200, f"Failed to create kid: {resp.status_code} {resp.text}"
        kid1 = resp.json()["kid"]
        kid1_id = kid1["id"]
        assert kid1["theme"] == "ocean", f"theme should be 'ocean', got {kid1['theme']}"
        print(f"✓ Kid created with theme 'ocean': {kid1_id}")
        
        # TEST 10B: Create kid WITHOUT theme (should default to 'animals')
        print("\n[10.2] TEST 10B: Create kid WITHOUT theme (should default to 'animals')...")
        resp = requests.post(f"{BASE_URL}/kids", 
                           json={"firstName": "DefaultKid", "grade": 3},
                           cookies=cookies)
        assert resp.status_code == 200, f"Failed to create kid: {resp.status_code} {resp.text}"
        kid2 = resp.json()["kid"]
        kid2_id = kid2["id"]
        assert kid2["theme"] == "animals", f"theme should default to 'animals', got {kid2['theme']}"
        print(f"✓ Kid created without theme, defaults to 'animals': {kid2_id}")
        
        # TEST 10C: Simulate existing kid without theme field in DB
        print("\n[10.3] TEST 10C: Simulate existing kid without theme field in DB...")
        db = get_mongo_db()
        kid3_id = str(uuid4())
        db["kids"].insert_one({
            "id": kid3_id,
            "userId": parent_id,
            "firstName": "LegacyKid",
            "grade": 1,
            "difficultyStep": 0,
            "soundOn": True,
            # NO theme field
            "createdAt": datetime.utcnow()
        })
        
        # Get kid stats - should default to 'animals'
        resp = requests.get(f"{BASE_URL}/kids", cookies=cookies)
        assert resp.status_code == 200, f"Failed to get kids: {resp.status_code} {resp.text}"
        kids = resp.json()["kids"]
        kid3 = next((k for k in kids if k["id"] == kid3_id), None)
        assert kid3 is not None, "Legacy kid not found"
        assert kid3["theme"] == "animals", f"Legacy kid theme should default to 'animals', got {kid3['theme']}"
        print(f"✓ Legacy kid without theme field defaults to 'animals': {kid3_id}")
        
        # TEST 10D: Update theme to 'space'
        print("\n[10.4] TEST 10D: Update theme to 'space'...")
        resp = requests.put(f"{BASE_URL}/kids/{kid1_id}",
                          json={"theme": "space"},
                          cookies=cookies)
        assert resp.status_code == 200, f"Failed to update theme: {resp.status_code} {resp.text}"
        updated_kid = resp.json()["kid"]
        assert updated_kid["theme"] == "space", f"theme should be 'space', got {updated_kid['theme']}"
        print(f"✓ Theme updated to 'space'")
        
        # TEST 10E: Try invalid theme 'purple' -> 400
        print("\n[10.5] TEST 10E: Try invalid theme 'purple' (should return 400)...")
        resp = requests.put(f"{BASE_URL}/kids/{kid1_id}",
                          json={"theme": "purple"},
                          cookies=cookies)
        assert resp.status_code == 400, f"Invalid theme should return 400, got {resp.status_code}"
        print(f"✓ Invalid theme 'purple' rejected with 400")
        
        # TEST 10F: Verify two kids can hold different themes
        print("\n[10.6] TEST 10F: Verify two kids can hold different themes...")
        resp = requests.get(f"{BASE_URL}/kids", cookies=cookies)
        assert resp.status_code == 200, f"Failed to get kids: {resp.status_code} {resp.text}"
        kids = resp.json()["kids"]
        
        kid1_current = next((k for k in kids if k["id"] == kid1_id), None)
        kid2_current = next((k for k in kids if k["id"] == kid2_id), None)
        
        assert kid1_current["theme"] == "space", f"Kid1 theme should be 'space', got {kid1_current['theme']}"
        assert kid2_current["theme"] == "animals", f"Kid2 theme should be 'animals', got {kid2_current['theme']}"
        print(f"✓ Two kids hold different themes: Kid1='space', Kid2='animals'")
        
        print("\n" + "="*80)
        print("✅ TEST 10 PASSED: Theme functionality working correctly")
        print("="*80)
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST 10 FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ TEST 10 ERROR: {e}")
        return False
    finally:
        cleanup_test_data(parent_id)

def test_11_regression():
    """
    TEST 11: REGRESSION (must still pass)
    - Unauthenticated routes return 401
    - A parent cannot access another parent's kid (404/401)
    - Grade 1 normal set is single-digit add/sub only
    - Normal-set completion still pays exactly 2 and 2-set/day cap still works
    - Adaptive difficulty for NORMAL sets still steps up after 3 perfect normal sets
    """
    print("\n" + "="*80)
    print("TEST 11: REGRESSION")
    print("="*80)
    
    parent_a_id = setup_test_user()
    token_a = mint_jwt(parent_a_id, PARENT_EMAIL)
    cookies_a = {"mc_session": token_a}
    
    # Create second parent
    parent_b_email = "parent_b_regression@test.com"
    client = MongoClient(MONGO_URL)
    db_conn = client[DB_NAME]
    parent_b_id = str(uuid4())
    db_conn["users"].insert_one({
        "id": parent_b_id,
        "googleId": "test-parent-b-reg",
        "email": parent_b_email,
        "name": "Parent B Regression",
        "createdAt": datetime.utcnow()
    })
    token_b = mint_jwt(parent_b_id, parent_b_email)
    cookies_b = {"mc_session": token_b}
    
    try:
        # TEST 11A: Unauthenticated routes return 401
        print("\n[11.1] TEST 11A: Unauthenticated routes return 401...")
        resp = requests.get(f"{BASE_URL}/me")
        assert resp.status_code == 401, f"Unauthenticated /me should return 401, got {resp.status_code}"
        
        resp = requests.get(f"{BASE_URL}/kids")
        assert resp.status_code == 401, f"Unauthenticated /kids should return 401, got {resp.status_code}"
        
        resp = requests.post(f"{BASE_URL}/kids", json={"firstName": "Test", "grade": 1})
        assert resp.status_code == 401, f"Unauthenticated POST /kids should return 401, got {resp.status_code}"
        print(f"✓ Unauthenticated routes return 401")
        
        # TEST 11B: Cross-parent access denied
        print("\n[11.2] TEST 11B: Parent cannot access another parent's kid...")
        # Parent A creates a kid
        resp = requests.post(f"{BASE_URL}/kids", 
                           json={"firstName": "ParentAKid", "grade": 2},
                           cookies=cookies_a)
        assert resp.status_code == 200, f"Failed to create kid: {resp.status_code} {resp.text}"
        kid_a_id = resp.json()["kid"]["id"]
        
        # Parent B tries to access Parent A's kid
        resp = requests.put(f"{BASE_URL}/kids/{kid_a_id}",
                          json={"grade": 3},
                          cookies=cookies_b)
        assert resp.status_code in [401, 404], f"Cross-parent access should return 401/404, got {resp.status_code}"
        
        resp = requests.post(f"{BASE_URL}/kids/{kid_a_id}/set",
                           json={"date": datetime.utcnow().strftime("%Y-%m-%d")},
                           cookies=cookies_b)
        assert resp.status_code in [401, 404], f"Cross-parent access should return 401/404, got {resp.status_code}"
        print(f"✓ Parent cannot access another parent's kid")
        
        # TEST 11C: Grade 1 normal set is single-digit add/sub only
        print("\n[11.3] TEST 11C: Grade 1 normal set is single-digit add/sub only...")
        resp = requests.post(f"{BASE_URL}/kids", 
                           json={"firstName": "Grade1Kid", "grade": 1},
                           cookies=cookies_a)
        assert resp.status_code == 200, f"Failed to create kid: {resp.status_code} {resp.text}"
        kid_g1_id = resp.json()["kid"]["id"]
        
        today = datetime.utcnow().strftime("%Y-%m-%d")
        resp = requests.post(f"{BASE_URL}/kids/{kid_g1_id}/set",
                           json={"date": today},
                           cookies=cookies_a)
        assert resp.status_code == 200, f"Failed to start set: {resp.status_code} {resp.text}"
        set_id = resp.json()["set"]["id"]
        
        db = get_mongo_db()
        set_doc = db["dailySets"].find_one({"id": set_id})
        problems = set_doc["problems"]
        
        for prob in problems:
            assert prob["operation"] in ["add", "sub"], f"Grade 1 should only have add/sub, got {prob['operation']}"
            for operand in prob["operands"]:
                assert operand <= 9, f"Grade 1 operands should be <=9, got {operand}"
            # Verify no negative answers for subtraction
            if prob["operation"] == "sub":
                assert prob["correctAnswer"] >= 0, f"Grade 1 subtraction should not have negative answers, got {prob['correctAnswer']}"
        print(f"✓ Grade 1 normal set is single-digit add/sub only")
        
        # TEST 11D: Normal-set completion pays exactly 2 and 2-set/day cap works
        print("\n[11.4] TEST 11D: Normal-set completion pays exactly 2 and 2-set/day cap works...")
        # Complete the Grade 1 set
        for prob in problems:
            resp = requests.post(f"{BASE_URL}/sets/{set_id}/answer",
                               json={"problemId": prob["id"], "answer": prob["correctAnswer"]},
                               cookies=cookies_a)
            assert resp.status_code == 200, f"Failed to answer: {resp.status_code} {resp.text}"
        
        # Check stars earned
        resp = requests.get(f"{BASE_URL}/kids?date={today}", cookies=cookies_a)
        kids = resp.json()["kids"]
        kid_g1 = next((k for k in kids if k["id"] == kid_g1_id), None)
        assert kid_g1["totalStars"] == 2, f"totalStars should be 2 after 1 set, got {kid_g1['totalStars']}"
        print(f"✓ Normal-set completion pays exactly 2 stars")
        
        # Complete second set
        resp = requests.post(f"{BASE_URL}/kids/{kid_g1_id}/set",
                           json={"date": today},
                           cookies=cookies_a)
        assert resp.status_code == 200, f"Failed to start 2nd set: {resp.status_code} {resp.text}"
        set2_id = resp.json()["set"]["id"]
        
        set2_doc = db["dailySets"].find_one({"id": set2_id})
        for prob in set2_doc["problems"]:
            resp = requests.post(f"{BASE_URL}/sets/{set2_id}/answer",
                               json={"problemId": prob["id"], "answer": prob["correctAnswer"]},
                               cookies=cookies_a)
            assert resp.status_code == 200, f"Failed to answer: {resp.status_code} {resp.text}"
        
        resp = requests.get(f"{BASE_URL}/kids?date={today}", cookies=cookies_a)
        kids = resp.json()["kids"]
        kid_g1 = next((k for k in kids if k["id"] == kid_g1_id), None)
        assert kid_g1["totalStars"] == 4, f"totalStars should be 4 after 2 sets, got {kid_g1['totalStars']}"
        
        # Try to start 3rd set - should be locked
        resp = requests.post(f"{BASE_URL}/kids/{kid_g1_id}/set",
                           json={"date": today},
                           cookies=cookies_a)
        assert resp.json().get("locked") == True, "3rd set should be locked"
        print(f"✓ 2-set/day cap works")
        
        # TEST 11E: Adaptive difficulty for NORMAL sets steps up after 3 perfect sets
        print("\n[11.5] TEST 11E: Adaptive difficulty steps up after 3 perfect normal sets...")
        resp = requests.post(f"{BASE_URL}/kids", 
                           json={"firstName": "AdaptiveKid", "grade": 2},
                           cookies=cookies_a)
        assert resp.status_code == 200, f"Failed to create kid: {resp.status_code} {resp.text}"
        kid_adapt_id = resp.json()["kid"]["id"]
        
        # Insert 2 prior perfect completed sets
        for i in range(2):
            set_id_prior = str(uuid4())
            date_prior = (datetime.utcnow() - timedelta(days=2-i)).strftime("%Y-%m-%d")
            problems_prior = []
            for j in range(30):
                problems_prior.append({
                    "id": str(uuid4()),
                    "display": f"{j+1} + {j+1}",
                    "correctAnswer": (j+1)*2,
                    "operation": "add",
                    "operands": [j+1, j+1],
                    "solved": True,
                    "attempts": 1,
                    "firstTryCorrect": True
                })
            db["dailySets"].insert_one({
                "id": set_id_prior,
                "kidId": kid_adapt_id,
                "date": date_prior,
                "status": "completed",
                "difficultyStep": 0,
                "problems": problems_prior,
                "createdAt": datetime.utcnow() - timedelta(days=2-i),
                "completedAt": datetime.utcnow() - timedelta(days=2-i)
            })
        
        # Complete 3rd perfect set via API
        date3 = datetime.utcnow().strftime("%Y-%m-%d")
        resp = requests.post(f"{BASE_URL}/kids/{kid_adapt_id}/set",
                           json={"date": date3},
                           cookies=cookies_a)
        assert resp.status_code == 200, f"Failed to start 3rd set: {resp.status_code} {resp.text}"
        set3_id = resp.json()["set"]["id"]
        
        set3_doc = db["dailySets"].find_one({"id": set3_id})
        for prob in set3_doc["problems"]:
            resp = requests.post(f"{BASE_URL}/sets/{set3_id}/answer",
                               json={"problemId": prob["id"], "answer": prob["correctAnswer"]},
                               cookies=cookies_a)
            assert resp.status_code == 200, f"Failed to answer: {resp.status_code} {resp.text}"
            result = resp.json()
        
        # Check if difficulty stepped up
        assert result.get("levelChanged") == True, "levelChanged should be True"
        assert result.get("levelDirection") == "up", f"levelDirection should be 'up', got {result.get('levelDirection')}"
        
        kid_doc = db["kids"].find_one({"id": kid_adapt_id})
        assert kid_doc["difficultyStep"] == 1, f"difficultyStep should be 1, got {kid_doc['difficultyStep']}"
        print(f"✓ Adaptive difficulty steps up after 3 perfect normal sets")
        
        print("\n" + "="*80)
        print("✅ TEST 11 PASSED: All regression tests passed")
        print("="*80)
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST 11 FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ TEST 11 ERROR: {e}")
        return False
    finally:
        cleanup_test_data(parent_a_id)
        db_conn["users"].delete_many({"id": parent_b_id})
        # Clean up parent B's kids
        kids = db_conn["kids"].find({"userId": parent_b_id})
        kid_ids = [k["id"] for k in kids]
        db_conn["dailySets"].delete_many({"kidId": {"$in": kid_ids}})
        db_conn["speedSessions"].delete_many({"kidId": {"$in": kid_ids}})
        db_conn["kids"].delete_many({"userId": parent_b_id})
        client.close()

def main():
    """Run all enhancement tests"""
    print("\n" + "="*80)
    print("MATHCOMPETE BACKEND ENHANCEMENT TEST SUITE")
    print("Testing all 11 enhancement items from review request")
    print("="*80)
    
    results = []
    
    # Run all tests
    results.append(("TEST 1: Stars rename + totals", test_1_stars_rename_and_totals()))
    results.append(("TEST 2: Speed math start & structure", test_2_speed_math_start_and_structure()))
    results.append(("TEST 3: Speed scoring", test_3_speed_scoring()))
    results.append(("TEST 4: Timer expiry", test_4_timer_expiry()))
    results.append(("TEST 5: 3-per-day speed cap", test_5_three_per_day_speed_cap()))
    results.append(("TEST 6: Speed does not affect leveling", test_6_speed_does_not_affect_leveling()))
    results.append(("TEST 7: No repeats within a day", test_7_no_repeats_within_day()))
    results.append(("TEST 8: Exit", test_8_exit()))
    results.append(("TEST 9: Daily rollover / stale expiry", test_9_daily_rollover_stale_expiry()))
    results.append(("TEST 10: Theme", test_10_theme()))
    results.append(("TEST 11: Regression", test_11_regression()))
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print("\n" + "="*80)
    print(f"TOTAL: {passed}/{total} tests passed")
    print("="*80)
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    exit(main())
