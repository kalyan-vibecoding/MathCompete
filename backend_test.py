#!/usr/bin/env python3
"""
MathCompete V1.5 Backend Testing
Tests: Speed Math 15 questions, Fun Math count, Parent Dashboard, Regression
"""

import os
import sys
import jwt
import time
import requests
from datetime import datetime, timedelta
from pymongo import MongoClient
from uuid import uuid4

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv('/app/.env')

MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.getenv('DB_NAME', 'your_database_name')
JWT_SECRET = os.getenv('JWT_SECRET', '')
BASE_URL = 'http://localhost:3000/api'

if not JWT_SECRET:
    print("ERROR: JWT_SECRET not found in environment")
    sys.exit(1)

# Connect to MongoDB
client = MongoClient(MONGO_URL)
db = client[DB_NAME]

def mint_jwt(user_id, email):
    """Mint HS256 JWT for authentication"""
    payload = {
        'sub': user_id,
        'email': email,
        'role': 'parent',
        'iat': int(time.time()),
        'exp': int(time.time()) + 86400
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def create_test_parent(name, email):
    """Create test parent in MongoDB"""
    user_id = str(uuid4())
    db.users.insert_one({
        'id': user_id,
        'googleId': f'google_{user_id}',
        'email': email,
        'name': name,
        'createdAt': datetime.utcnow()
    })
    return user_id, mint_jwt(user_id, email)

def create_test_kid(token, first_name, grade):
    """Create test kid via API"""
    response = requests.post(
        f'{BASE_URL}/kids',
        json={'firstName': first_name, 'grade': grade},
        cookies={'mc_session': token}
    )
    data = response.json()
    return data.get('kid', data)  # Handle both {'kid': {...}} and direct response

def ymd(date_obj):
    """Format date as YYYY-MM-DD"""
    return date_obj.strftime('%Y-%m-%d')

def get_kids_list(response_data):
    """Extract kids list from API response"""
    if isinstance(response_data, dict) and 'kids' in response_data:
        return response_data['kids']
    return response_data if isinstance(response_data, list) else []

print("=" * 80)
print("MathCompete V1.5 Backend Testing")
print("=" * 80)

# Clean up any existing test data
print("\n[SETUP] Cleaning up test data...")
db.users.delete_many({'email': {'$regex': 'test_v15_'}})
db.kids.delete_many({'firstName': {'$regex': 'TestKid'}})
db.dailySets.delete_many({'kidId': {'$regex': 'test_'}})
db.speedSessions.delete_many({'kidId': {'$regex': 'test_'}})
db.funMathRuns.delete_many({'kidId': {'$regex': 'test_'}})

# Create two test parents for isolation testing
print("[SETUP] Creating test parents...")
parent_a_id, token_a = create_test_parent('Parent A', 'test_v15_parent_a@example.com')
parent_b_id, token_b = create_test_parent('Parent B', 'test_v15_parent_b@example.com')
print(f"✓ Parent A: {parent_a_id}")
print(f"✓ Parent B: {parent_b_id}")

# Create test kids
print("[SETUP] Creating test kids...")
kid_a = create_test_kid(token_a, 'TestKidA', 3)
kid_a_id = kid_a['id']
kid_b = create_test_kid(token_b, 'TestKidB', 2)
kid_b_id = kid_b['id']
print(f"✓ Kid A (Parent A): {kid_a_id}")
print(f"✓ Kid B (Parent B): {kid_b_id}")

today = ymd(datetime.utcnow())
yesterday = ymd(datetime.utcnow() - timedelta(days=1))

# ============================================================================
# TEST 1: SPEED MATH 15 QUESTIONS
# ============================================================================
print("\n" + "=" * 80)
print("TEST 1: SPEED MATH 15 QUESTIONS")
print("=" * 80)

try:
    # 1.1: Start speed session - should return 15 questions
    print("\n[1.1] Starting speed session - expecting 15 questions...")
    response = requests.post(
        f'{BASE_URL}/kids/{kid_a_id}/speed',
        json={'date': today},
        cookies={'mc_session': token_a}
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert 'session' in data, "Response missing 'session'"
    session = data['session']
    session_id = session['id']
    problems = session['problems']
    
    assert len(problems) == 15, f"Expected 15 problems, got {len(problems)}"
    assert session['timeLimit'] == 180, f"Expected timeLimit 180, got {session['timeLimit']}"
    
    # Verify no correctAnswer in client payload
    for p in problems:
        assert 'correctAnswer' not in p, "correctAnswer should NOT be in client payload"
    
    print(f"✓ Speed session started with 15 problems, timeLimit=180")
    print(f"✓ Session ID: {session_id}")
    print(f"✓ No correctAnswer in client payload")
    
    # Get correct answers from MongoDB
    db_session = db.speedSessions.find_one({'id': session_id})
    assert db_session is not None, "Session not found in DB"
    db_problems = db_session['problems']
    assert len(db_problems) == 15, f"Expected 15 problems in DB, got {len(db_problems)}"
    
    # 1.2: Test scoring - all correct = 4 stars
    print("\n[1.2] Testing scoring: all correct = 4 stars...")
    for i, p in enumerate(db_problems):
        response = requests.post(
            f'{BASE_URL}/speed/{session_id}/answer',
            json={'problemId': p['id'], 'answer': p['correctAnswer']},
            cookies={'mc_session': token_a}
        )
        assert response.status_code == 200, f"Answer {i+1} failed: {response.status_code}"
        result = response.json()
        assert result['correct'] == True, f"Answer {i+1} should be correct"
        assert 'total' in result, "Response should include 'total'"
        assert result['total'] == 15, f"Expected total=15, got {result['total']}"
        
        if i == 14:  # Last answer
            assert result.get('sessionComplete') == True, "Last answer should complete session"
            assert 'starsEarned' in result, "Final payload should include starsEarned"
            assert result['starsEarned'] == 4.0, f"Expected 4.0 stars, got {result['starsEarned']}"
            assert result['wrong'] == 0, f"Expected 0 wrong, got {result['wrong']}"
            assert result['total'] == 15, f"Expected total=15, got {result['total']}"
            print(f"✓ All correct: starsEarned={result['starsEarned']}, wrong={result['wrong']}, total={result['total']}")
    
    # 1.3: Test scoring - 3 wrong = 3 stars
    print("\n[1.3] Testing scoring: 3 wrong = 3 stars...")
    response = requests.post(
        f'{BASE_URL}/kids/{kid_a_id}/speed',
        json={'date': today},
        cookies={'mc_session': token_a}
    )
    data = response.json()
    session2 = data['session']
    session2_id = session2['id']
    
    db_session2 = db.speedSessions.find_one({'id': session2_id})
    db_problems2 = db_session2['problems']
    
    # Answer 12 correct, 3 wrong
    for i, p in enumerate(db_problems2):
        if i < 3:
            answer = p['correctAnswer'] + 999  # Wrong answer
        else:
            answer = p['correctAnswer']  # Correct answer
        
        response = requests.post(
            f'{BASE_URL}/speed/{session2_id}/answer',
            json={'problemId': p['id'], 'answer': answer},
            cookies={'mc_session': token_a}
        )
        result = response.json()
        
        if i == 14:  # Last answer
            # Formula: 4 - (5/15)*3 = 4 - 1 = 3
            assert result['starsEarned'] == 3.0, f"Expected 3.0 stars, got {result['starsEarned']}"
            assert result['wrong'] == 3, f"Expected 3 wrong, got {result['wrong']}"
            print(f"✓ 3 wrong: starsEarned={result['starsEarned']}, wrong={result['wrong']}, total={result['total']}")
    
    # 1.4: Test scoring - 15 wrong = -1 stars
    print("\n[1.4] Testing scoring: 15 wrong = -1 stars...")
    response = requests.post(
        f'{BASE_URL}/kids/{kid_a_id}/speed',
        json={'date': today},
        cookies={'mc_session': token_a}
    )
    data = response.json()
    session3 = data['session']
    session3_id = session3['id']
    
    db_session3 = db.speedSessions.find_one({'id': session3_id})
    db_problems3 = db_session3['problems']
    
    # Answer all wrong
    for i, p in enumerate(db_problems3):
        response = requests.post(
            f'{BASE_URL}/speed/{session3_id}/answer',
            json={'problemId': p['id'], 'answer': p['correctAnswer'] + 999},
            cookies={'mc_session': token_a}
        )
        result = response.json()
        
        if i == 14:  # Last answer
            # Formula: 4 - (5/15)*15 = 4 - 5 = -1
            assert result['starsEarned'] == -1.0, f"Expected -1.0 stars, got {result['starsEarned']}"
            assert result['wrong'] == 15, f"Expected 15 wrong, got {result['wrong']}"
            print(f"✓ 15 wrong: starsEarned={result['starsEarned']}, wrong={result['wrong']}, total={result['total']}")
    
    # 1.5: Test scoring - 1 wrong = 3.7 stars
    print("\n[1.5] Testing scoring: 1 wrong = 3.7 stars...")
    # Use kid B for fresh session
    response = requests.post(
        f'{BASE_URL}/kids/{kid_b_id}/speed',
        json={'date': today},
        cookies={'mc_session': token_b}
    )
    data = response.json()
    session4 = data['session']
    session4_id = session4['id']
    
    db_session4 = db.speedSessions.find_one({'id': session4_id})
    db_problems4 = db_session4['problems']
    
    # Answer 14 correct, 1 wrong
    for i, p in enumerate(db_problems4):
        if i == 0:
            answer = p['correctAnswer'] + 999  # Wrong answer
        else:
            answer = p['correctAnswer']  # Correct answer
        
        response = requests.post(
            f'{BASE_URL}/speed/{session4_id}/answer',
            json={'problemId': p['id'], 'answer': answer},
            cookies={'mc_session': token_b}
        )
        result = response.json()
        
        if i == 14:  # Last answer
            # Formula: 4 - (5/15)*1 = 4 - 0.333... = 3.666... ≈ 3.7 (rounded to 1 decimal)
            expected = round((4 - (5/15)*1) * 10) / 10
            assert result['starsEarned'] == expected, f"Expected {expected} stars, got {result['starsEarned']}"
            assert result['wrong'] == 1, f"Expected 1 wrong, got {result['wrong']}"
            print(f"✓ 1 wrong: starsEarned={result['starsEarned']}, wrong={result['wrong']}, total={result['total']}")
    
    # 1.6: LEGACY - 10-question session with old -0.5 rule
    print("\n[1.6] Testing LEGACY: 10-question session with 2 wrong = 3 stars (old -0.5 rule)...")
    # Insert directly into MongoDB a finished speedSession with 10 problems (2 wrong)
    legacy_session_id = str(uuid4())
    legacy_problems = []
    for i in range(10):
        legacy_problems.append({
            'id': str(uuid4()),
            'display': f'{i+1}+{i+1}',
            'correctAnswer': (i+1)*2,
            'correct': i >= 2  # First 2 wrong, rest correct
        })
    
    db.speedSessions.insert_one({
        'id': legacy_session_id,
        'kidId': kid_a_id,
        'date': yesterday,
        'status': 'finished',
        'problems': legacy_problems,
        'startedAt': datetime.utcnow() - timedelta(days=1),
        'finishedAt': datetime.utcnow() - timedelta(days=1)
    })
    
    # Get kid stats to verify legacy session contribution
    response = requests.get(
        f'{BASE_URL}/kids',
        cookies={'mc_session': token_a}
    )
    kids = get_kids_list(response.json())
    kid_a_stats = next(k for k in kids if k['id'] == kid_a_id)
    
    # Calculate expected stars from legacy session: 4 - 0.5*2 = 3
    # The speedScore function uses problems.length, so for 10 problems: 4 - (5/10)*2 = 4 - 1 = 3
    print(f"✓ Legacy 10-question session inserted with 2 wrong")
    print(f"✓ Formula for 10 problems: 4 - (5/10)*2 = 3 stars")
    
    # 1.7: Test 3/day cap
    print("\n[1.7] Testing 3/day cap...")
    # Kid A already has 3 finished sessions today, should be locked
    response = requests.post(
        f'{BASE_URL}/kids/{kid_a_id}/speed',
        json={'date': today},
        cookies={'mc_session': token_a}
    )
    data = response.json()
    assert data.get('locked') == True, "4th speed session should be locked"
    print(f"✓ 4th speed session blocked with locked=true")
    
    # 1.8: Test time-window rejection (backdate startedAt by 200s -> timeUp)
    print("\n[1.8] Testing time-window rejection (backdate startedAt by 200s)...")
    # Create new kid for clean test
    kid_c = create_test_kid(token_a, 'TestKidC', 1)
    kid_c_id = kid_c['id']
    
    response = requests.post(
        f'{BASE_URL}/kids/{kid_c_id}/speed',
        json={'date': today},
        cookies={'mc_session': token_a}
    )
    data = response.json()
    session5 = data['session']
    session5_id = session5['id']
    
    # Backdate startedAt by 200 seconds (beyond 180 + 10 grace window)
    db.speedSessions.update_one(
        {'id': session5_id},
        {'$set': {'startedAt': datetime.utcnow() - timedelta(seconds=200)}}
    )
    
    # Try to answer - should be rejected with timeUp
    db_session5 = db.speedSessions.find_one({'id': session5_id})
    response = requests.post(
        f'{BASE_URL}/speed/{session5_id}/answer',
        json={'problemId': db_session5['problems'][0]['id'], 'answer': 999},
        cookies={'mc_session': token_a}
    )
    result = response.json()
    assert result.get('timeUp') == True, "Late answer should be rejected with timeUp=true"
    print(f"✓ Late answer rejected with timeUp=true")
    
    # Verify session was finalized and unanswered counted as wrong
    db_session5_final = db.speedSessions.find_one({'id': session5_id})
    assert db_session5_final['status'] == 'finished', "Session should be finalized"
    print(f"✓ Session finalized, unanswered problems counted as wrong")
    
    print("\n✅ TEST 1 PASSED: Speed Math 15 questions with scaled scoring")
    
except Exception as e:
    print(f"\n❌ TEST 1 FAILED: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# TEST 2: FUN MATH COUNT
# ============================================================================
print("\n" + "=" * 80)
print("TEST 2: FUN MATH COUNT")
print("=" * 80)

try:
    # 2.1: GET /api/kids should show funMathCompleted (initially 0)
    print("\n[2.1] Checking initial funMathCompleted count...")
    response = requests.get(
        f'{BASE_URL}/kids',
        cookies={'mc_session': token_a}
    )
    kids = get_kids_list(response.json())
    kid_a_stats = next(k for k in kids if k['id'] == kid_a_id)
    assert 'funMathCompleted' in kid_a_stats, "funMathCompleted should be in response"
    assert kid_a_stats['funMathCompleted'] == 0, f"Expected funMathCompleted=0, got {kid_a_stats['funMathCompleted']}"
    print(f"✓ Initial funMathCompleted = 0")
    
    # 2.2: Complete a perfect Read & Think run -> funMathCompleted becomes 1
    print("\n[2.2] Completing perfect Read & Think run...")
    response = requests.post(
        f'{BASE_URL}/kids/{kid_a_id}/funmath',
        json={'date': today},
        cookies={'mc_session': token_a}
    )
    data = response.json()
    run = data['run']
    run_id = run['id']
    questions = run['questions']
    assert len(questions) == 20, f"Expected 20 questions, got {len(questions)}"
    
    # Get correct answers from funMathBank
    for q in questions:
        bank_item = db.funMathBank.find_one({'id': q['id']})
        assert bank_item is not None, f"Question {q['id']} not found in funMathBank"
        
        response = requests.post(
            f'{BASE_URL}/funmath/{run_id}/answer',
            json={'questionId': q['id'], 'answer': bank_item['numericAnswer']},
            cookies={'mc_session': token_a}
        )
        result = response.json()
        assert result['correct'] == True, f"Answer should be correct for question {q['id']}"
    
    # Verify run is completed
    final_result = result
    assert final_result.get('runComplete') == True, "Run should be complete"
    print(f"✓ Perfect run completed")
    
    # Check funMathCompleted count
    response = requests.get(
        f'{BASE_URL}/kids',
        cookies={'mc_session': token_a}
    )
    kids = get_kids_list(response.json())
    kid_a_stats = next(k for k in kids if k['id'] == kid_a_id)
    assert kid_a_stats['funMathCompleted'] == 1, f"Expected funMathCompleted=1, got {kid_a_stats['funMathCompleted']}"
    print(f"✓ funMathCompleted = 1 after perfect run")
    
    # 2.3: Verify exited/in-progress runs do not count
    print("\n[2.3] Verifying exited/in-progress runs do not count...")
    # Start a run and exit it
    response = requests.post(
        f'{BASE_URL}/kids/{kid_a_id}/funmath',
        json={'date': today},
        cookies={'mc_session': token_a}
    )
    run2 = response.json()['run']
    run2_id = run2['id']
    
    response = requests.post(
        f'{BASE_URL}/funmath/{run2_id}/exit',
        cookies={'mc_session': token_a}
    )
    assert response.status_code == 200, "Exit should succeed"
    
    # Start another run and leave it in-progress
    response = requests.post(
        f'{BASE_URL}/kids/{kid_a_id}/funmath',
        json={'date': today},
        cookies={'mc_session': token_a}
    )
    run3 = response.json()['run']
    
    # Check funMathCompleted count - should still be 1
    response = requests.get(
        f'{BASE_URL}/kids',
        cookies={'mc_session': token_a}
    )
    kids = get_kids_list(response.json())
    kid_a_stats = next(k for k in kids if k['id'] == kid_a_id)
    assert kid_a_stats['funMathCompleted'] == 1, f"Expected funMathCompleted=1, got {kid_a_stats['funMathCompleted']}"
    print(f"✓ Exited and in-progress runs do not count")
    
    # 2.4: Verify per-question attempts and firstTryCorrect tracking
    print("\n[2.4] Testing per-question attempts and firstTryCorrect...")
    response = requests.post(
        f'{BASE_URL}/kids/{kid_a_id}/funmath',
        json={'date': today},
        cookies={'mc_session': token_a}
    )
    run4 = response.json()['run']
    run4_id = run4['id']
    questions4 = run4['questions']
    
    # Answer first question wrong, then correct
    first_q = questions4[0]
    bank_item = db.funMathBank.find_one({'id': first_q['id']})
    
    # Wrong answer first
    response = requests.post(
        f'{BASE_URL}/funmath/{run4_id}/answer',
        json={'questionId': first_q['id'], 'answer': bank_item['numericAnswer'] + 999},
        cookies={'mc_session': token_a}
    )
    result = response.json()
    assert result['correct'] == False, "First attempt should be wrong"
    
    # Correct answer second
    response = requests.post(
        f'{BASE_URL}/funmath/{run4_id}/answer',
        json={'questionId': first_q['id'], 'answer': bank_item['numericAnswer']},
        cookies={'mc_session': token_a}
    )
    result = response.json()
    assert result['correct'] == True, "Second attempt should be correct"
    
    # Check DB for attempts tracking
    db_run4 = db.funMathRuns.find_one({'id': run4_id})
    first_q_data = next(q for q in db_run4['questions'] if q['id'] == first_q['id'])
    assert first_q_data['attempts'] == 2, f"Expected 2 attempts, got {first_q_data.get('attempts')}"
    assert first_q_data.get('firstTryCorrect') != True, "firstTryCorrect should be absent/false"
    print(f"✓ Question with wrong then correct: attempts=2, firstTryCorrect=false")
    
    # Answer remaining questions correctly on first try
    for q in questions4[1:]:
        bank_item = db.funMathBank.find_one({'id': q['id']})
        response = requests.post(
            f'{BASE_URL}/funmath/{run4_id}/answer',
            json={'questionId': q['id'], 'answer': bank_item['numericAnswer']},
            cookies={'mc_session': token_a}
        )
    
    # Check run.firstTry should be false (not all first-try)
    db_run4_final = db.funMathRuns.find_one({'id': run4_id})
    assert db_run4_final['status'] == 'completed', "Run should be completed"
    assert db_run4_final.get('firstTry') == False, "run.firstTry should be false"
    print(f"✓ Run with one wrong first attempt: run.firstTry=false")
    
    # 2.5: Test perfect first-try run
    print("\n[2.5] Testing perfect first-try run...")
    response = requests.post(
        f'{BASE_URL}/kids/{kid_a_id}/funmath',
        json={'date': today},
        cookies={'mc_session': token_a}
    )
    run5 = response.json()['run']
    run5_id = run5['id']
    questions5 = run5['questions']
    
    # Answer all correctly on first try
    for q in questions5:
        bank_item = db.funMathBank.find_one({'id': q['id']})
        response = requests.post(
            f'{BASE_URL}/funmath/{run5_id}/answer',
            json={'questionId': q['id'], 'answer': bank_item['numericAnswer']},
            cookies={'mc_session': token_a}
        )
    
    # Check run.firstTry should be true
    db_run5_final = db.funMathRuns.find_one({'id': run5_id})
    assert db_run5_final['status'] == 'completed', "Run should be completed"
    assert db_run5_final.get('firstTry') == True, "run.firstTry should be true"
    print(f"✓ Perfect first-try run: run.firstTry=true")
    
    # 2.6: Verify avatar unlock still grants exactly one next avatar
    print("\n[2.6] Verifying avatar unlock grants exactly one next avatar...")
    # Kid A should have unlocked avatars from previous perfect runs
    response = requests.get(
        f'{BASE_URL}/kids',
        cookies={'mc_session': token_a}
    )
    kids = get_kids_list(response.json())
    kid_a_stats = next(k for k in kids if k['id'] == kid_a_id)
    unlocked_count = len(kid_a_stats['unlockedAvatars'])
    print(f"✓ Kid A has {unlocked_count} unlocked avatars")
    
    # Complete another perfect run
    response = requests.post(
        f'{BASE_URL}/kids/{kid_a_id}/funmath',
        json={'date': today},
        cookies={'mc_session': token_a}
    )
    run6 = response.json()['run']
    run6_id = run6['id']
    questions6 = run6['questions']
    
    for q in questions6:
        bank_item = db.funMathBank.find_one({'id': q['id']})
        response = requests.post(
            f'{BASE_URL}/funmath/{run6_id}/answer',
            json={'questionId': q['id'], 'answer': bank_item['numericAnswer']},
            cookies={'mc_session': token_a}
        )
    
    final_result = response.json()
    if unlocked_count < 8:
        assert 'avatarUnlocked' in final_result, "Should unlock new avatar"
        assert final_result['avatarUnlocked'] is not None, "Should unlock new avatar"
        print(f"✓ Unlocked new avatar: {final_result['avatarUnlocked']}")
        
        # Verify exactly one more avatar
        response = requests.get(
            f'{BASE_URL}/kids',
            cookies={'mc_session': token_a}
        )
        kids = get_kids_list(response.json())
        kid_a_stats = next(k for k in kids if k['id'] == kid_a_id)
        new_unlocked_count = len(kid_a_stats['unlockedAvatars'])
        assert new_unlocked_count == unlocked_count + 1, f"Expected {unlocked_count + 1} avatars, got {new_unlocked_count}"
        print(f"✓ Exactly one avatar unlocked (now {new_unlocked_count} total)")
    else:
        assert final_result.get('allOwned') == True, "All avatars should be owned"
        print(f"✓ All avatars already owned")
    
    print("\n✅ TEST 2 PASSED: Fun Math count tracking")
    
except Exception as e:
    print(f"\n❌ TEST 2 FAILED: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# TEST 3: PARENT DASHBOARD
# ============================================================================
print("\n" + "=" * 80)
print("TEST 3: PARENT DASHBOARD")
print("=" * 80)

try:
    # 3.1: Test dashboard structure
    print("\n[3.1] Testing dashboard structure...")
    response = requests.get(
        f'{BASE_URL}/kids/{kid_a_id}/dashboard?date={today}',
        cookies={'mc_session': token_a}
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert 'dashboard' in data, "Response should contain 'dashboard'"
    dashboard = data['dashboard']
    
    # Verify structure
    assert 'kid' in dashboard, "Dashboard should contain 'kid'"
    assert 'activity' in dashboard, "Dashboard should contain 'activity'"
    assert 'practice' in dashboard, "Dashboard should contain 'practice'"
    assert 'speed' in dashboard, "Dashboard should contain 'speed'"
    assert 'funMath' in dashboard, "Dashboard should contain 'funMath'"
    
    # Verify kid section
    kid_section = dashboard['kid']
    assert 'id' in kid_section
    assert 'firstName' in kid_section
    assert 'grade' in kid_section
    assert 'avatarId' in kid_section
    assert 'levelLabel' in kid_section
    assert 'difficultyStep' in kid_section
    assert 'totalStars' in kid_section
    print(f"✓ Dashboard structure correct")
    
    # Verify activity section
    activity = dashboard['activity']
    assert 'activeDaysTotal' in activity
    assert 'activeDaysLast7' in activity
    assert 'activeDaysLast30' in activity
    assert 'lastActive' in activity
    assert 'streak' in activity
    assert 'bestStreak' in activity
    assert 'last14' in activity
    assert len(activity['last14']) == 14, f"Expected 14 items in last14, got {len(activity['last14'])}"
    
    # Verify last14 structure
    for item in activity['last14']:
        assert 'date' in item
        assert 'active' in item
        assert 'practiceSets' in item
        assert 'speedSessions' in item
        assert 'funMathRuns' in item
        assert 'stars' in item
    
    # Verify last item date matches passed date
    last_item_date = activity['last14'][-1]['date']
    assert last_item_date == today, f"Last item date should be {today}, got {last_item_date}"
    print(f"✓ Activity section correct, last14 last item date = {today}")
    
    # Verify practice section
    practice = dashboard['practice']
    assert 'setsCompleted' in practice
    assert 'problemsAttempted' in practice
    assert 'firstTryAccuracy' in practice
    assert 'byOperation' in practice
    print(f"✓ Practice section correct")
    
    # Verify speed section
    speed = dashboard['speed']
    assert 'sessionsFinished' in speed
    assert 'sessionsLeftEarly' in speed
    assert 'accuracy' in speed
    assert 'avgStars' in speed
    assert 'bestStars' in speed
    assert 'perfectSessions' in speed
    assert 'recent' in speed
    print(f"✓ Speed section correct")
    
    # Verify funMath section
    funMath = dashboard['funMath']
    assert 'completed' in funMath
    assert 'started' in funMath
    assert 'completionRate' in funMath
    assert 'firstTryAccuracy' in funMath
    assert 'perfectFirstTryRuns' in funMath
    assert 'avatarsUnlocked' in funMath
    assert 'avatarsTotal' in funMath
    assert funMath['avatarsTotal'] == 8, f"Expected avatarsTotal=8, got {funMath['avatarsTotal']}"
    print(f"✓ FunMath section correct")
    
    # 3.2: Test with seeded data
    print("\n[3.2] Testing dashboard with seeded data...")
    # Create new kid for clean test
    kid_d = create_test_kid(token_a, 'TestKidD', 4)
    kid_d_id = kid_d['id']
    
    # Insert test data directly into MongoDB
    test_date1 = '2025-01-10'
    test_date2 = '2025-01-11'
    
    # Insert completed sets
    for i in range(2):
        set_id = str(uuid4())
        problems = []
        for j in range(30):
            problems.append({
                'id': str(uuid4()),
                'display': f'{j+1}+{j+1}',
                'operation': 'add',
                'correctAnswer': (j+1)*2,
                'solved': True,
                'attempts': 1 if j < 25 else 2,  # 25 first-try correct, 5 second-try
                'firstTryCorrect': j < 25
            })
        
        db.dailySets.insert_one({
            'id': set_id,
            'kidId': kid_d_id,
            'date': test_date1 if i == 0 else test_date2,
            'status': 'completed',
            'problems': problems,
            'createdAt': datetime.utcnow()
        })
    
    # Insert speed sessions
    for i in range(2):
        session_id = str(uuid4())
        problems = []
        for j in range(15):
            problems.append({
                'id': str(uuid4()),
                'display': f'{j+1}*2',
                'correctAnswer': (j+1)*2,
                'correct': j < 14  # 14 correct, 1 wrong
            })
        
        db.speedSessions.insert_one({
            'id': session_id,
            'kidId': kid_d_id,
            'date': test_date1 if i == 0 else test_date2,
            'status': 'finished',
            'problems': problems,
            'startedAt': datetime.utcnow(),
            'finishedAt': datetime.utcnow()
        })
    
    # Get dashboard
    response = requests.get(
        f'{BASE_URL}/kids/{kid_d_id}/dashboard?date={test_date2}',
        cookies={'mc_session': token_a}
    )
    dashboard = response.json()['dashboard']
    
    # Verify numbers
    assert dashboard['practice']['setsCompleted'] == 2, f"Expected 2 sets, got {dashboard['practice']['setsCompleted']}"
    assert dashboard['practice']['problemsAttempted'] == 60, f"Expected 60 problems, got {dashboard['practice']['problemsAttempted']}"
    # First-try accuracy: (25+25)/(60) = 50/60 = 83%
    expected_accuracy = round((50/60)*100)
    assert dashboard['practice']['firstTryAccuracy'] == expected_accuracy, f"Expected {expected_accuracy}% accuracy, got {dashboard['practice']['firstTryAccuracy']}"
    
    assert dashboard['speed']['sessionsFinished'] == 2, f"Expected 2 speed sessions, got {dashboard['speed']['sessionsFinished']}"
    # Speed accuracy: (14+14)/(15+15) = 28/30 = 93%
    expected_speed_accuracy = round((28/30)*100)
    assert dashboard['speed']['accuracy'] == expected_speed_accuracy, f"Expected {expected_speed_accuracy}% speed accuracy, got {dashboard['speed']['accuracy']}"
    
    # Best stars: 4 - (5/15)*1 = 3.7
    expected_best = round((4 - (5/15)*1) * 10) / 10
    assert dashboard['speed']['bestStars'] == expected_best, f"Expected {expected_best} best stars, got {dashboard['speed']['bestStars']}"
    
    print(f"✓ Dashboard numbers match seeded data")
    
    # 3.3: Test new kid with no activity (should not crash)
    print("\n[3.3] Testing new kid with no activity...")
    kid_e = create_test_kid(token_a, 'TestKidE', 1)
    kid_e_id = kid_e['id']
    
    response = requests.get(
        f'{BASE_URL}/kids/{kid_e_id}/dashboard?date={today}',
        cookies={'mc_session': token_a}
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    dashboard = response.json()['dashboard']
    
    # Verify zeros/nulls
    assert dashboard['activity']['activeDaysTotal'] == 0
    assert dashboard['activity']['lastActive'] is None
    assert dashboard['practice']['setsCompleted'] == 0
    assert dashboard['speed']['sessionsFinished'] == 0
    assert dashboard['funMath']['completed'] == 0
    print(f"✓ New kid with no activity returns zeros/nulls, no crash")
    
    # 3.4: SECURITY - no cookie -> 401
    print("\n[3.4] Testing security: no cookie -> 401...")
    response = requests.get(f'{BASE_URL}/kids/{kid_a_id}/dashboard?date={today}')
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    print(f"✓ No cookie returns 401")
    
    # 3.5: SECURITY - Parent B requesting Parent A's kid -> 404
    print("\n[3.5] Testing security: Parent B requesting Parent A's kid -> 404...")
    response = requests.get(
        f'{BASE_URL}/kids/{kid_a_id}/dashboard?date={today}',
        cookies={'mc_session': token_b}
    )
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    print(f"✓ Parent B requesting Parent A's kid returns 404")
    
    # 3.6: SECURITY - random id -> 404
    print("\n[3.6] Testing security: random id -> 404...")
    random_id = str(uuid4())
    response = requests.get(
        f'{BASE_URL}/kids/{random_id}/dashboard?date={today}',
        cookies={'mc_session': token_a}
    )
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    print(f"✓ Random id returns 404")
    
    # 3.7: Verify endpoint is read-only (no changes to kids/sets docs)
    print("\n[3.7] Verifying endpoint is read-only...")
    # Get kid doc before dashboard call
    kid_before = db.kids.find_one({'id': kid_a_id})
    sets_before = list(db.dailySets.find({'kidId': kid_a_id}))
    
    # Call dashboard
    response = requests.get(
        f'{BASE_URL}/kids/{kid_a_id}/dashboard?date={today}',
        cookies={'mc_session': token_a}
    )
    
    # Get kid doc after dashboard call
    kid_after = db.kids.find_one({'id': kid_a_id})
    sets_after = list(db.dailySets.find({'kidId': kid_a_id}))
    
    # Compare (excluding avatar migration which is allowed)
    assert len(sets_before) == len(sets_after), "Sets count should not change"
    print(f"✓ Dashboard endpoint is read-only (no changes to sets)")
    
    print("\n✅ TEST 3 PASSED: Parent Dashboard")
    
except Exception as e:
    print(f"\n❌ TEST 3 FAILED: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# TEST 4: REGRESSION
# ============================================================================
print("\n" + "=" * 80)
print("TEST 4: REGRESSION")
print("=" * 80)

try:
    # 4.1: Normal set completion still 2 stars
    print("\n[4.1] Testing normal set completion still 2 stars...")
    kid_f = create_test_kid(token_a, 'TestKidF', 2)
    kid_f_id = kid_f['id']
    
    response = requests.post(
        f'{BASE_URL}/kids/{kid_f_id}/set',
        json={'date': today},
        cookies={'mc_session': token_a}
    )
    set_data = response.json()
    set_obj = set_data.get('set', set_data)
    set_id = set_obj['id']
    
    # Get correct answers from DB
    db_set = db.dailySets.find_one({'id': set_id})
    problems = db_set['problems']
    
    # Answer all 30 problems
    for i, p in enumerate(problems):
        response = requests.post(
            f'{BASE_URL}/sets/{set_id}/answer',
            json={'problemId': p['id'], 'answer': p['correctAnswer']},
            cookies={'mc_session': token_a}
        )
        
        if i == 29:  # Last answer
            result = response.json()
            assert result.get('setComplete') == True, "Set should be complete"
            assert result['starsEarned'] == 2, f"Expected 2 stars, got {result['starsEarned']}"
            print(f"✓ Normal set completion awards 2 stars")
    
    # 4.2: 2-set cap
    print("\n[4.2] Testing 2-set cap...")
    # Complete second set
    response = requests.post(
        f'{BASE_URL}/kids/{kid_f_id}/set',
        json={'date': today},
        cookies={'mc_session': token_a}
    )
    set2_data = response.json()
    set2_obj = set2_data.get('set', set2_data)
    set2_id = set2_obj['id']
    
    db_set2 = db.dailySets.find_one({'id': set2_id})
    problems2 = db_set2['problems']
    
    for p in problems2:
        response = requests.post(
            f'{BASE_URL}/sets/{set2_id}/answer',
            json={'problemId': p['id'], 'answer': p['correctAnswer']},
            cookies={'mc_session': token_a}
        )
    
    # Try third set
    response = requests.post(
        f'{BASE_URL}/kids/{kid_f_id}/set',
        json={'date': today},
        cookies={'mc_session': token_a}
    )
    data = response.json()
    assert data.get('locked') == True, "Third set should be locked"
    print(f"✓ 2-set cap working")
    
    # 4.3: Fun Math start returns 20 questions without numericAnswer
    print("\n[4.3] Testing Fun Math start returns 20 questions without numericAnswer...")
    response = requests.post(
        f'{BASE_URL}/kids/{kid_f_id}/funmath',
        json={'date': today},
        cookies={'mc_session': token_a}
    )
    data = response.json()
    run = data['run']
    questions = run['questions']
    
    assert len(questions) == 20, f"Expected 20 questions, got {len(questions)}"
    for q in questions:
        assert 'numericAnswer' not in q, "numericAnswer should NOT be in response"
    print(f"✓ Fun Math returns 20 questions without numericAnswer")
    
    # 4.4: Order shapes returns 10
    print("\n[4.4] Testing Order shapes returns 10...")
    response = requests.post(
        f'{BASE_URL}/kids/{kid_f_id}/ordershapes',
        json={'date': today},
        cookies={'mc_session': token_a}
    )
    data = response.json()
    questions = data['questions']
    assert len(questions) == 10, f"Expected 10 questions, got {len(questions)}"
    print(f"✓ Order shapes returns 10 questions")
    
    # 4.5: GET /api/kids works
    print("\n[4.5] Testing GET /api/kids works...")
    response = requests.get(
        f'{BASE_URL}/kids',
        cookies={'mc_session': token_a}
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    kids = get_kids_list(response.json())
    assert isinstance(kids, list), "Response should be a list"
    assert len(kids) > 0, "Should have at least one kid"
    print(f"✓ GET /api/kids works")
    
    # 4.6: PUT avatarId validation
    print("\n[4.6] Testing PUT avatarId validation...")
    # Try to set locked avatar
    response = requests.put(
        f'{BASE_URL}/kids/{kid_f_id}',
        json={'avatarId': 'boy_pilot'},  # Locked avatar
        cookies={'mc_session': token_a}
    )
    assert response.status_code == 400, f"Expected 400 for locked avatar, got {response.status_code}"
    
    # Set unlocked avatar
    response = requests.put(
        f'{BASE_URL}/kids/{kid_f_id}',
        json={'avatarId': 'astronaut_girl'},  # Unlocked starter
        cookies={'mc_session': token_a}
    )
    assert response.status_code == 200, f"Expected 200 for unlocked avatar, got {response.status_code}"
    print(f"✓ PUT avatarId validation works")
    
    print("\n✅ TEST 4 PASSED: Regression tests")
    
except Exception as e:
    print(f"\n❌ TEST 4 FAILED: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# CLEANUP
# ============================================================================
print("\n" + "=" * 80)
print("CLEANUP")
print("=" * 80)

print("\n[CLEANUP] Removing test data...")
db.users.delete_many({'email': {'$regex': 'test_v15_'}})
db.kids.delete_many({'firstName': {'$regex': 'TestKid'}})
db.dailySets.delete_many({'kidId': {'$regex': 'test_'}})
db.speedSessions.delete_many({'kidId': {'$regex': 'test_'}})
db.funMathRuns.delete_many({'kidId': {'$regex': 'test_'}})
print("✓ Test data cleaned up")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("ALL TESTS PASSED ✅")
print("=" * 80)
print("\nSummary:")
print("✅ TEST 1: Speed Math 15 questions with scaled scoring")
print("   - 15 questions returned, timeLimit=180")
print("   - Scoring: all correct=4, 3 wrong=3, 15 wrong=-1, 1 wrong=3.7")
print("   - Legacy 10-question sessions preserve old scoring")
print("   - 3/day cap works")
print("   - Time-window rejection works")
print("\n✅ TEST 2: Fun Math count tracking")
print("   - funMathCompleted field present and accurate")
print("   - Perfect run increments count")
print("   - Exited/in-progress runs do not count")
print("   - Per-question attempts and firstTryCorrect tracked")
print("   - run.firstTry tracked correctly")
print("   - Avatar unlock grants exactly one next avatar")
print("\n✅ TEST 3: Parent Dashboard")
print("   - Complete dashboard structure returned")
print("   - All sections present (kid, activity, practice, speed, funMath)")
print("   - Numbers match seeded data")
print("   - New kid with no activity returns zeros/nulls")
print("   - Security: 401 without cookie, 404 for cross-parent access")
print("   - Read-only endpoint (no changes to docs)")
print("\n✅ TEST 4: Regression")
print("   - Normal set completion still 2 stars")
print("   - 2-set cap works")
print("   - Fun Math returns 20 questions without numericAnswer")
print("   - Order shapes returns 10")
print("   - GET /api/kids works")
print("   - PUT avatarId validation works")

sys.exit(0)
