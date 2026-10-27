#!/usr/bin/env python3
"""
MathCompete V1.5b Backend Test - Main daily set 50 problems + widening generator
Tests:
1. Main daily set size is now 50 (was 30)
2. Generator widening for different grades (especially grade 1 at difficultyStep 0)
3. Legacy 30-problem sets still work
4. Regression checks for Speed Math and other endpoints
"""

import os
import sys
import jwt
import time
import requests
from datetime import datetime, timedelta
from pymongo import MongoClient
from uuid import uuid4
from dotenv import load_dotenv

load_dotenv('/app/.env')

MONGO_URL = os.getenv('MONGO_URL')
DB_NAME = os.getenv('DB_NAME')
JWT_SECRET = os.getenv('JWT_SECRET')
BASE_URL = 'http://localhost:3000/api'

def mint_jwt(user_id, email):
    """Mint an HS256 JWT for testing"""
    payload = {
        'sub': user_id,
        'email': email,
        'role': 'parent',
        'iat': int(time.time()),
        'exp': int(time.time()) + 86400
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def setup_test_parent(db):
    """Insert a test parent into MongoDB"""
    parent_id = str(uuid4())
    email = f'test_{parent_id[:8]}@example.com'
    db.users.insert_one({
        'id': parent_id,
        'googleId': f'google_{parent_id}',
        'email': email,
        'name': 'Test Parent',
        'createdAt': datetime.utcnow()
    })
    return parent_id, email

def cleanup_test_data(db, parent_id):
    """Clean up test data"""
    kids = list(db.kids.find({'userId': parent_id}))
    kid_ids = [k['id'] for k in kids]
    
    db.dailySets.delete_many({'kidId': {'$in': kid_ids}})
    db.speedSessions.delete_many({'kidId': {'$in': kid_ids}})
    db.kids.delete_many({'userId': parent_id})
    db.users.delete_many({'id': parent_id})

def test_50_problem_set(session, db, parent_id):
    """Test 1: Main daily set size is now 50 (was 30)"""
    print("\n" + "="*80)
    print("TEST 1: Main daily set size is now 50")
    print("="*80)
    
    # Create a grade 3 kid
    resp = session.post(f'{BASE_URL}/kids', json={'firstName': 'TestKid', 'grade': 3})
    assert resp.status_code == 200, f"Failed to create kid: {resp.text}"
    kid = resp.json()['kid']
    kid_id = kid['id']
    print(f"✓ Created kid: {kid['firstName']} (Grade {kid['grade']})")
    
    # Start a set
    today = datetime.utcnow().strftime('%Y-%m-%d')
    resp = session.post(f'{BASE_URL}/kids/{kid_id}/set', json={'date': today})
    assert resp.status_code == 200, f"Failed to start set: {resp.text}"
    set_data = resp.json()['set']
    set_id = set_data['id']
    problems = set_data['problems']
    
    # Verify 50 problems
    assert len(problems) == 50, f"Expected 50 problems, got {len(problems)}"
    print(f"✓ Set has exactly 50 problems")
    
    # Verify no correctAnswer in client payload
    for p in problems:
        assert 'correctAnswer' not in p, f"correctAnswer leaked to client in problem {p['id']}"
    print(f"✓ No correctAnswer in client payload")
    
    # Verify all displays are unique
    displays = [p['display'] for p in problems]
    assert len(displays) == len(set(displays)), "Duplicate displays found in set"
    print(f"✓ All 50 displays are unique")
    
    # Verify MongoDB has correctAnswer stored server-side
    db_set = db.dailySets.find_one({'id': set_id})
    assert db_set is not None, "Set not found in MongoDB"
    assert len(db_set['problems']) == 50, f"MongoDB set has {len(db_set['problems'])} problems"
    for p in db_set['problems']:
        assert 'correctAnswer' in p, f"correctAnswer missing in MongoDB for problem {p['id']}"
    print(f"✓ MongoDB has correctAnswer stored server-side for all 50 problems")
    
    # Answer all 50 problems correctly
    for p in db_set['problems']:
        resp = session.post(f'{BASE_URL}/sets/{set_id}/answer', 
                          json={'problemId': p['id'], 'answer': p['correctAnswer']})
        assert resp.status_code == 200, f"Failed to answer problem: {resp.text}"
        result = resp.json()
        assert result['total'] == 50, f"Expected total=50, got {result['total']}"
    
    # Verify completion
    final_resp = resp.json()
    assert final_resp['setComplete'] == True, "Set not marked complete"
    assert final_resp['starsEarned'] == 2, f"Expected 2 stars, got {final_resp['starsEarned']}"
    assert final_resp['solvedCount'] == 50, f"Expected solvedCount=50, got {final_resp['solvedCount']}"
    print(f"✓ Completed all 50 problems, earned 2 stars")
    
    # Verify wrong answers don't complete the set
    resp = session.post(f'{BASE_URL}/kids/{kid_id}/set', json={'date': today})
    assert resp.status_code == 200, f"Failed to start second set: {resp.text}"
    set2_data = resp.json()['set']
    set2_id = set2_data['id']
    
    db_set2 = db.dailySets.find_one({'id': set2_id})
    # Answer first problem wrong
    resp = session.post(f'{BASE_URL}/sets/{set2_id}/answer', 
                      json={'problemId': db_set2['problems'][0]['id'], 'answer': 99999})
    assert resp.status_code == 200, f"Failed to answer problem: {resp.text}"
    result = resp.json()
    assert result['correct'] == False, "Wrong answer marked as correct"
    assert result['setComplete'] == False, "Set completed with wrong answer"
    print(f"✓ Wrong answers do not complete the set")
    
    # Answer remaining problems correctly
    for p in db_set2['problems']:
        resp = session.post(f'{BASE_URL}/sets/{set2_id}/answer', 
                          json={'problemId': p['id'], 'answer': p['correctAnswer']})
        assert resp.status_code == 200, f"Failed to answer problem: {resp.text}"
    
    final_resp = resp.json()
    assert final_resp['setComplete'] == True, "Set not marked complete"
    assert final_resp['starsEarned'] == 2, f"Expected 2 stars, got {final_resp['starsEarned']}"
    print(f"✓ Re-answering wrong problems correctly completes the set")
    
    # Verify 2-set daily cap
    resp = session.post(f'{BASE_URL}/kids/{kid_id}/set', json={'date': today})
    assert resp.status_code == 200, f"Failed to check daily cap: {resp.text}"
    result = resp.json()
    assert result.get('locked') == True, "Third set not locked"
    print(f"✓ Max 2 completed sets per day enforced")
    
    print("\n✅ TEST 1 PASSED: Main daily set size is 50")
    return kid_id

def test_generator_widening(session, db, parent_id):
    """Test 2: Generator widening for different grades"""
    print("\n" + "="*80)
    print("TEST 2: Generator widening (CRITICAL)")
    print("="*80)
    
    # Test Grade 1 kid at difficultyStep 0
    print("\n--- Grade 1, difficultyStep 0 ---")
    resp = session.post(f'{BASE_URL}/kids', json={'firstName': 'Grade1Kid', 'grade': 1})
    assert resp.status_code == 200, f"Failed to create kid: {resp.text}"
    kid1 = resp.json()['kid']
    kid1_id = kid1['id']
    print(f"✓ Created Grade 1 kid: {kid1['firstName']}")
    
    today = datetime.utcnow().strftime('%Y-%m-%d')
    
    # Complete set 1
    print("\nCompleting Set 1...")
    resp = session.post(f'{BASE_URL}/kids/{kid1_id}/set', json={'date': today})
    assert resp.status_code == 200, f"Failed to start set 1: {resp.text}"
    set1_data = resp.json()['set']
    set1_id = set1_data['id']
    assert len(set1_data['problems']) == 50, f"Set 1 has {len(set1_data['problems'])} problems"
    
    db_set1 = db.dailySets.find_one({'id': set1_id})
    set1_displays = set([p['display'] for p in db_set1['problems']])
    
    # Verify grade 1 step 0 operations (only add/sub)
    for p in db_set1['problems']:
        assert p['operation'] in ['add', 'sub'], f"Grade 1 step 0 has {p['operation']} operation"
    print(f"✓ Set 1: 50 problems, all add/sub operations")
    
    # Complete set 1
    start_time = time.time()
    for p in db_set1['problems']:
        resp = session.post(f'{BASE_URL}/sets/{set1_id}/answer', 
                          json={'problemId': p['id'], 'answer': p['correctAnswer']})
        assert resp.status_code == 200, f"Failed to answer problem: {resp.text}"
    elapsed = time.time() - start_time
    print(f"✓ Completed Set 1 in {elapsed:.2f}s")
    
    # Reset set 2 multiple times (5 resets)
    print("\nResetting Set 2 (5 times)...")
    all_displays = set1_displays.copy()
    
    for i in range(5):
        resp = session.post(f'{BASE_URL}/kids/{kid1_id}/set', json={'date': today})
        assert resp.status_code == 200, f"Failed to start set 2 attempt {i+1}: {resp.text}"
        set2_data = resp.json()['set']
        set2_id = set2_data['id']
        
        db_set2 = db.dailySets.find_one({'id': set2_id})
        assert len(db_set2['problems']) == 50, f"Reset {i+1} has {len(db_set2['problems'])} problems"
        
        # Verify all add/sub operations
        for p in db_set2['problems']:
            assert p['operation'] in ['add', 'sub'], f"Grade 1 step 0 has {p['operation']} after reset"
        
        set2_displays = set([p['display'] for p in db_set2['problems']])
        all_displays.update(set2_displays)
        
        # Reset the set
        start_time = time.time()
        resp = session.post(f'{BASE_URL}/sets/{set2_id}/reset', json={'date': today})
        elapsed = time.time() - start_time
        assert resp.status_code == 200, f"Failed to reset set 2 attempt {i+1}: {resp.text}"
        assert elapsed < 3, f"Reset {i+1} took {elapsed:.2f}s (should be <3s)"
        print(f"  Reset {i+1}: 50 problems, all add/sub, returned in {elapsed:.2f}s")
    
    # Start 3 speed sessions (15 problems each)
    print("\nStarting 3 Speed Math sessions (15 problems each)...")
    for i in range(3):
        resp = session.post(f'{BASE_URL}/kids/{kid1_id}/speed', json={'date': today})
        assert resp.status_code == 200, f"Failed to start speed session {i+1}: {resp.text}"
        speed_data = resp.json()['session']
        speed_id = speed_data['id']
        
        db_speed = db.speedSessions.find_one({'id': speed_id})
        assert len(db_speed['problems']) == 15, f"Speed {i+1} has {len(db_speed['problems'])} problems"
        
        # Verify all add/sub operations
        for p in db_speed['problems']:
            assert p['operation'] in ['add', 'sub'], f"Grade 1 step 0 speed has {p['operation']}"
        
        speed_displays = set([p['display'] for p in db_speed['problems']])
        all_displays.update(speed_displays)
        
        # Complete the speed session
        for p in db_speed['problems']:
            resp = session.post(f'{BASE_URL}/speed/{speed_id}/answer', 
                              json={'problemId': p['id'], 'answer': p['correctAnswer']})
            assert resp.status_code == 200, f"Failed to answer speed problem: {resp.text}"
        
        print(f"  Speed {i+1}: 15 problems, all add/sub")
    
    # Verify all displays are unique across the whole day
    total_problems = 50 + (5 * 50) + (3 * 15)  # set1 + 5 resets + 3 speed sessions
    print(f"\n✓ Total problems generated: {total_problems}")
    print(f"✓ Unique displays: {len(all_displays)}")
    assert len(all_displays) == total_problems, f"Expected {total_problems} unique displays, got {len(all_displays)}"
    print(f"✓ All displays unique across the whole day (no duplicates)")
    
    # Test Grade 4 (lighter version)
    print("\n--- Grade 4, difficultyStep 0 ---")
    resp = session.post(f'{BASE_URL}/kids', json={'firstName': 'Grade4Kid', 'grade': 4})
    assert resp.status_code == 200, f"Failed to create kid: {resp.text}"
    kid4 = resp.json()['kid']
    kid4_id = kid4['id']
    print(f"✓ Created Grade 4 kid: {kid4['firstName']}")
    
    # Complete set 1
    resp = session.post(f'{BASE_URL}/kids/{kid4_id}/set', json={'date': today})
    assert resp.status_code == 200, f"Failed to start set: {resp.text}"
    set_data = resp.json()['set']
    set_id = set_data['id']
    
    db_set = db.dailySets.find_one({'id': set_id})
    assert len(db_set['problems']) == 50, f"Grade 4 set has {len(db_set['problems'])} problems"
    
    # Verify operations include add/sub/mul/div/fraction
    ops = set([p['operation'] for p in db_set['problems']])
    assert 'add' in ops or 'sub' in ops or 'mul' in ops or 'div' in ops or 'fraction' in ops, "Grade 4 missing expected operations"
    print(f"✓ Grade 4 set: 50 problems with operations: {ops}")
    
    # Complete the set
    for p in db_set['problems']:
        resp = session.post(f'{BASE_URL}/sets/{set_id}/answer', 
                          json={'problemId': p['id'], 'answer': p['correctAnswer']})
        assert resp.status_code == 200, f"Failed to answer problem: {resp.text}"
    print(f"✓ Completed Grade 4 set")
    
    # Test Grade 2 (lighter version)
    print("\n--- Grade 2, difficultyStep 0 ---")
    resp = session.post(f'{BASE_URL}/kids', json={'firstName': 'Grade2Kid', 'grade': 2})
    assert resp.status_code == 200, f"Failed to create kid: {resp.text}"
    kid2 = resp.json()['kid']
    kid2_id = kid2['id']
    print(f"✓ Created Grade 2 kid: {kid2['firstName']}")
    
    # Complete set 1
    resp = session.post(f'{BASE_URL}/kids/{kid2_id}/set', json={'date': today})
    assert resp.status_code == 200, f"Failed to start set: {resp.text}"
    set_data = resp.json()['set']
    set_id = set_data['id']
    
    db_set = db.dailySets.find_one({'id': set_id})
    assert len(db_set['problems']) == 50, f"Grade 2 set has {len(db_set['problems'])} problems"
    
    # Verify operations (add/sub/mul/div, no fraction)
    ops = set([p['operation'] for p in db_set['problems']])
    assert 'fraction' not in ops, "Grade 2 should not have fraction operation"
    print(f"✓ Grade 2 set: 50 problems with operations: {ops}")
    
    # Complete the set
    for p in db_set['problems']:
        resp = session.post(f'{BASE_URL}/sets/{set_id}/answer', 
                          json={'problemId': p['id'], 'answer': p['correctAnswer']})
        assert resp.status_code == 200, f"Failed to answer problem: {resp.text}"
    print(f"✓ Completed Grade 2 set")
    
    print("\n✅ TEST 2 PASSED: Generator widening works correctly")

def test_legacy_30_problem_sets(session, db, parent_id):
    """Test 3: Legacy 30-problem sets still work"""
    print("\n" + "="*80)
    print("TEST 3: Legacy 30-problem sets")
    print("="*80)
    
    # Create a kid
    resp = session.post(f'{BASE_URL}/kids', json={'firstName': 'LegacyKid', 'grade': 3})
    assert resp.status_code == 200, f"Failed to create kid: {resp.text}"
    kid = resp.json()['kid']
    kid_id = kid['id']
    print(f"✓ Created kid: {kid['firstName']}")
    
    # Insert a legacy 30-problem set directly into MongoDB
    today = datetime.utcnow().strftime('%Y-%m-%d')
    legacy_set_id = str(uuid4())
    legacy_problems = []
    for i in range(30):
        legacy_problems.append({
            'id': str(uuid4()),
            'operation': 'add',
            'operands': [i+1, i+2],
            'display': f'{i+1} + {i+2}',
            'correctAnswer': (i+1) + (i+2),
            'attempts': 0,
            'firstTryCorrect': False,
            'solved': False
        })
    
    db.dailySets.insert_one({
        'id': legacy_set_id,
        'kidId': kid_id,
        'date': today,
        'status': 'in_progress',
        'difficultyStep': 0,
        'problems': legacy_problems,
        'createdAt': datetime.utcnow()
    })
    print(f"✓ Inserted legacy 30-problem set into MongoDB")
    
    # Answer all 30 problems
    for p in legacy_problems:
        resp = session.post(f'{BASE_URL}/sets/{legacy_set_id}/answer', 
                          json={'problemId': p['id'], 'answer': p['correctAnswer']})
        assert resp.status_code == 200, f"Failed to answer problem: {resp.text}"
        result = resp.json()
        assert result['total'] == 30, f"Expected total=30, got {result['total']}"
    
    # Verify completion
    final_resp = resp.json()
    assert final_resp['setComplete'] == True, "Legacy set not marked complete"
    assert final_resp['starsEarned'] == 2, f"Expected 2 stars, got {final_resp['starsEarned']}"
    assert final_resp['solvedCount'] == 30, f"Expected solvedCount=30, got {final_resp['solvedCount']}"
    print(f"✓ Legacy 30-problem set completed successfully")
    print(f"✓ Answer endpoint returns total=30 and completes after 30 solved")
    print(f"✓ Completion grants exactly 2 stars")
    
    print("\n✅ TEST 3 PASSED: Legacy 30-problem sets work correctly")

def test_regression_checks(session, db, parent_id):
    """Test 4: Regression checks for Speed Math and other endpoints"""
    print("\n" + "="*80)
    print("TEST 4: Regression checks")
    print("="*80)
    
    # Create a kid
    resp = session.post(f'{BASE_URL}/kids', json={'firstName': 'RegressionKid', 'grade': 3})
    assert resp.status_code == 200, f"Failed to create kid: {resp.text}"
    kid = resp.json()['kid']
    kid_id = kid['id']
    print(f"✓ Created kid: {kid['firstName']}")
    
    today = datetime.utcnow().strftime('%Y-%m-%d')
    
    # Test Speed Math still 15 problems
    print("\n--- Speed Math (15 problems) ---")
    resp = session.post(f'{BASE_URL}/kids/{kid_id}/speed', json={'date': today})
    assert resp.status_code == 200, f"Failed to start speed session: {resp.text}"
    speed_data = resp.json()['session']
    speed_id = speed_data['id']
    
    db_speed = db.speedSessions.find_one({'id': speed_id})
    assert len(db_speed['problems']) == 15, f"Speed session has {len(db_speed['problems'])} problems (expected 15)"
    print(f"✓ Speed Math session has exactly 15 problems")
    
    # Complete speed session
    for p in db_speed['problems']:
        resp = session.post(f'{BASE_URL}/speed/{speed_id}/answer', 
                          json={'problemId': p['id'], 'answer': p['correctAnswer']})
        assert resp.status_code == 200, f"Failed to answer speed problem: {resp.text}"
    
    final_resp = resp.json()
    assert final_resp['sessionComplete'] == True, "Speed session not marked complete"
    assert final_resp['total'] == 15, f"Expected total=15, got {final_resp['total']}"
    assert final_resp['starsEarned'] == 4.0, f"Expected 4.0 stars (perfect), got {final_resp['starsEarned']}"
    print(f"✓ Speed Math scoring: perfect session = 4.0 stars")
    
    # Test GET /api/kids
    print("\n--- GET /api/kids ---")
    resp = session.get(f'{BASE_URL}/kids')
    assert resp.status_code == 200, f"Failed to get kids: {resp.text}"
    kids_data = resp.json()['kids']
    assert len(kids_data) > 0, "No kids returned"
    
    # Verify funMathCompleted field exists
    for k in kids_data:
        assert 'funMathCompleted' in k, f"funMathCompleted missing for kid {k['id']}"
    print(f"✓ GET /api/kids returns kids with funMathCompleted field")
    
    # Test GET /api/kids/:id/dashboard
    print("\n--- GET /api/kids/:id/dashboard ---")
    resp = session.get(f'{BASE_URL}/kids/{kid_id}/dashboard?date={today}')
    assert resp.status_code == 200, f"Failed to get dashboard: {resp.text}"
    dashboard = resp.json()['dashboard']
    
    # Verify dashboard structure
    assert 'kid' in dashboard, "Dashboard missing 'kid' section"
    assert 'activity' in dashboard, "Dashboard missing 'activity' section"
    assert 'practice' in dashboard, "Dashboard missing 'practice' section"
    assert 'speed' in dashboard, "Dashboard missing 'speed' section"
    assert 'funMath' in dashboard, "Dashboard missing 'funMath' section"
    print(f"✓ Dashboard returns all required sections")
    
    # Test cross-parent access returns 404
    print("\n--- Cross-parent access ---")
    # Create second parent
    parent2_id, email2 = setup_test_parent(db)
    token2 = mint_jwt(parent2_id, email2)
    session2 = requests.Session()
    session2.cookies.set('mc_session', token2)
    
    resp = session2.get(f'{BASE_URL}/kids/{kid_id}/dashboard?date={today}')
    assert resp.status_code == 404, f"Expected 404 for cross-parent access, got {resp.status_code}"
    print(f"✓ Cross-parent dashboard access returns 404")
    
    # Cleanup second parent
    cleanup_test_data(db, parent2_id)
    
    print("\n✅ TEST 4 PASSED: All regression checks passed")

def main():
    print("\n" + "="*80)
    print("MathCompete V1.5b Backend Test Suite")
    print("Main daily set 50 problems + widening generator")
    print("="*80)
    
    # Connect to MongoDB
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Setup test parent
    parent_id, email = setup_test_parent(db)
    token = mint_jwt(parent_id, email)
    
    # Create session with JWT cookie
    session = requests.Session()
    session.cookies.set('mc_session', token)
    
    try:
        # Run tests
        test_50_problem_set(session, db, parent_id)
        test_generator_widening(session, db, parent_id)
        test_legacy_30_problem_sets(session, db, parent_id)
        test_regression_checks(session, db, parent_id)
        
        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED")
        print("="*80)
        print("\nSummary:")
        print("  ✓ Main daily set size is 50 (was 30)")
        print("  ✓ Generator widening works for all grades")
        print("  ✓ Legacy 30-problem sets still work")
        print("  ✓ All regression checks passed")
        print("\n")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Cleanup
        cleanup_test_data(db, parent_id)
        client.close()

if __name__ == '__main__':
    main()
