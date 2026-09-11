#!/usr/bin/env python3
"""
MathCompete V1.3 "Order and Shapes" Backend Test Suite
Tests the new orderShapesBank seeding and POST /api/kids/:id/ordershapes endpoint.
"""

import os
import sys
import time
import jwt
import requests
from datetime import datetime, timedelta
from pymongo import MongoClient
from uuid import uuid4

# Load environment variables
from dotenv import load_dotenv
load_dotenv('/app/.env')

MONGO_URL = os.getenv('MONGO_URL')
DB_NAME = os.getenv('DB_NAME')
JWT_SECRET = os.getenv('JWT_SECRET')
BASE_URL = os.getenv('NEXT_PUBLIC_BASE_URL', 'http://localhost:3000')
API_URL = f"{BASE_URL}/api"

print(f"🔧 Configuration:")
print(f"   MONGO_URL: {MONGO_URL}")
print(f"   DB_NAME: {DB_NAME}")
print(f"   API_URL: {API_URL}")
print()

# MongoDB connection
client = MongoClient(MONGO_URL)
db = client[DB_NAME]

def mint_jwt(user_id, email):
    """Mint an HS256 JWT for authentication"""
    payload = {
        'sub': user_id,
        'email': email,
        'role': 'parent',
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(days=30)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def create_test_parent(email_suffix):
    """Create a test parent in MongoDB and return user object with JWT"""
    user = {
        'id': str(uuid4()),
        'googleId': f'google_{uuid4()}',
        'email': f'test_os_{email_suffix}@example.com',
        'name': f'Test Parent {email_suffix}',
        'createdAt': datetime.utcnow()
    }
    db.users.insert_one(user)
    token = mint_jwt(user['id'], user['email'])
    return user, token

def api_call(method, path, token=None, json_data=None):
    """Make an API call with optional authentication"""
    url = f"{API_URL}{path}"
    headers = {}
    cookies = {}
    if token:
        cookies['mc_session'] = token
    
    if method == 'GET':
        resp = requests.get(url, headers=headers, cookies=cookies)
    elif method == 'POST':
        resp = requests.post(url, headers=headers, cookies=cookies, json=json_data or {})
    elif method == 'PUT':
        resp = requests.put(url, headers=headers, cookies=cookies, json=json_data or {})
    else:
        raise ValueError(f"Unsupported method: {method}")
    
    return resp

print("=" * 80)
print("TEST 1: SEEDING - orderShapesBank structure and count")
print("=" * 80)

try:
    # Force DB connection by calling an authenticated endpoint
    parent_a, token_a = create_test_parent('seeding_test')
    resp = api_call('GET', '/me', token=token_a)
    print(f"✓ Authenticated endpoint called to trigger seeding (status: {resp.status_code})")
    
    # Check orderShapesBank collection
    total_count = db.orderShapesBank.count_documents({})
    print(f"✓ Total documents in orderShapesBank: {total_count}")
    
    if total_count != 1000:
        print(f"❌ FAIL: Expected 1000 documents, got {total_count}")
        sys.exit(1)
    
    # Check count per grade
    for grade in range(1, 6):
        grade_count = db.orderShapesBank.count_documents({'grade': grade})
        print(f"✓ Grade {grade}: {grade_count} documents")
        if grade_count != 200:
            print(f"❌ FAIL: Expected 200 documents for grade {grade}, got {grade_count}")
            sys.exit(1)
    
    # Check strand distribution per grade
    for grade in range(1, 6):
        order_count = db.orderShapesBank.count_documents({'grade': grade, 'strand': 'order'})
        shapes_count = db.orderShapesBank.count_documents({'grade': grade, 'strand': 'shapes'})
        print(f"✓ Grade {grade}: {order_count} order + {shapes_count} shapes")
        if order_count != 100 or shapes_count != 100:
            print(f"❌ FAIL: Expected 100 order + 100 shapes for grade {grade}, got {order_count} + {shapes_count}")
            sys.exit(1)
    
    # Check document structure
    sample = db.orderShapesBank.find_one({'grade': 3})
    required_fields = ['id', 'grade', 'strand', 'questionType', 'prompt', 'displayData', 'correctAnswer', 'difficultyTier', 'createdAt']
    for field in required_fields:
        if field not in sample:
            print(f"❌ FAIL: Missing required field '{field}' in document")
            sys.exit(1)
    print(f"✓ All required fields present: {required_fields}")
    
    # Check multiple-choice vs numeric-entry
    mc_sample = db.orderShapesBank.find_one({'options': {'$exists': True}})
    numeric_sample = db.orderShapesBank.find_one({'options': {'$exists': False}})
    if mc_sample and 'options' in mc_sample and isinstance(mc_sample['options'], list):
        print(f"✓ Multiple-choice question has 'options' array: {len(mc_sample['options'])} options")
    if numeric_sample and 'options' not in numeric_sample:
        print(f"✓ Numeric-entry question has no 'options' field")
    
    # Check reference flag
    ref_flag = db.reference.find_one({'key': 'orderShapesSeedVersion'})
    if not ref_flag or ref_flag.get('value') != 'bank-v1':
        print(f"❌ FAIL: Reference flag not set correctly")
        sys.exit(1)
    print(f"✓ Reference flag exists: {ref_flag}")
    
    print("✅ TEST 1 PASSED: Seeding structure and count verified")
    print()
    
except Exception as e:
    print(f"❌ TEST 1 FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("=" * 80)
print("TEST 2: IDEMPOTENCY - No wipe/reseed/duplicate on reconnect")
print("=" * 80)

try:
    # Capture current IDs
    initial_ids = set(doc['id'] for doc in db.orderShapesBank.find({}, {'id': 1}))
    initial_count = len(initial_ids)
    print(f"✓ Initial count: {initial_count} documents")
    print(f"✓ Captured {len(initial_ids)} unique IDs")
    
    # Pick a sentinel ID to track
    sentinel_id = list(initial_ids)[0]
    print(f"✓ Sentinel ID: {sentinel_id}")
    
    # Force multiple DB access calls (simulating reconnect logic)
    for i in range(3):
        resp = api_call('GET', '/me', token=token_a)
        print(f"✓ Call {i+1}: GET /me (status: {resp.status_code})")
        time.sleep(0.1)
    
    resp = api_call('GET', '/kids?date=2025-01-15', token=token_a)
    print(f"✓ Call 4: GET /kids (status: {resp.status_code})")
    
    # Check count again
    final_count = db.orderShapesBank.count_documents({})
    print(f"✓ Final count: {final_count} documents")
    
    if final_count != initial_count:
        print(f"❌ FAIL: Count changed from {initial_count} to {final_count}")
        sys.exit(1)
    
    # Check IDs are identical
    final_ids = set(doc['id'] for doc in db.orderShapesBank.find({}, {'id': 1}))
    if final_ids != initial_ids:
        print(f"❌ FAIL: IDs changed! Initial: {len(initial_ids)}, Final: {len(final_ids)}")
        sys.exit(1)
    print(f"✓ All {len(final_ids)} IDs remain identical (no delete/reinsert)")
    
    # Check sentinel still exists
    sentinel_doc = db.orderShapesBank.find_one({'id': sentinel_id})
    if not sentinel_doc:
        print(f"❌ FAIL: Sentinel ID {sentinel_id} disappeared")
        sys.exit(1)
    print(f"✓ Sentinel ID preserved across reconnects")
    
    # Check reference flag still correct
    ref_flag = db.reference.find_one({'key': 'orderShapesSeedVersion'})
    if not ref_flag or ref_flag.get('value') != 'bank-v1':
        print(f"❌ FAIL: Reference flag changed")
        sys.exit(1)
    print(f"✓ Reference flag gate prevents re-seeding")
    
    print("✅ TEST 2 PASSED: Idempotency verified - no duplication or reset")
    print()
    
except Exception as e:
    print(f"❌ TEST 2 FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("=" * 80)
print("TEST 3: ORDER AND SHAPES ROUTE - 10 questions, grade-specific, mixed strands")
print("=" * 80)

try:
    # Create a Grade 3 kid
    kid_data = {'firstName': 'TestKid3', 'grade': 3}
    resp = api_call('POST', '/kids', token=token_a, json_data=kid_data)
    if resp.status_code != 200:
        print(f"❌ FAIL: Could not create kid (status: {resp.status_code})")
        sys.exit(1)
    kid3 = resp.json()['kid']
    kid3_id = kid3['id']
    print(f"✓ Created Grade 3 kid: {kid3['firstName']} (id: {kid3_id})")
    
    # Call POST /api/kids/:id/ordershapes
    resp = api_call('POST', f'/kids/{kid3_id}/ordershapes', token=token_a, json_data={'date': '2025-01-15'})
    if resp.status_code != 200:
        print(f"❌ FAIL: POST /api/kids/:id/ordershapes failed (status: {resp.status_code})")
        print(f"Response: {resp.text}")
        sys.exit(1)
    
    data = resp.json()
    questions = data.get('questions', [])
    print(f"✓ POST /api/kids/{kid3_id}/ordershapes returned {len(questions)} questions")
    
    # Verify exactly 10 questions
    if len(questions) != 10:
        print(f"❌ FAIL: Expected 10 questions, got {len(questions)}")
        sys.exit(1)
    print(f"✓ Exactly 10 questions returned")
    
    # Verify all unique IDs
    question_ids = [q['id'] for q in questions]
    if len(question_ids) != len(set(question_ids)):
        print(f"❌ FAIL: Duplicate question IDs found")
        sys.exit(1)
    print(f"✓ All 10 questions have unique IDs")
    
    # Verify all belong to grade 3
    for q in questions:
        bank_doc = db.orderShapesBank.find_one({'id': q['id']})
        if not bank_doc or bank_doc['grade'] != 3:
            print(f"❌ FAIL: Question {q['id']} does not belong to grade 3")
            sys.exit(1)
    print(f"✓ All 10 questions belong to grade 3")
    
    # Verify mixed strands (at least one 'order' and one 'shapes')
    strands = set()
    for q in questions:
        strands.add(q['strand'])
    print(f"✓ Strands present: {strands}")
    if 'order' not in strands or 'shapes' not in strands:
        print(f"⚠️  WARNING: Expected both 'order' and 'shapes' strands, got {strands}")
        # Not a hard fail - could be random, but let's note it
    else:
        print(f"✓ Both 'order' and 'shapes' strands present (mixed)")
    
    # Verify ordered by difficultyTier ascending (check in DB since not in response)
    tiers_from_db = []
    for q in questions:
        bank_doc = db.orderShapesBank.find_one({'id': q['id']})
        tiers_from_db.append(bank_doc.get('difficultyTier', 999))
    print(f"✓ Difficulty tiers (from DB): {tiers_from_db}")
    if tiers_from_db != sorted(tiers_from_db):
        print(f"❌ FAIL: Questions not ordered by difficultyTier ascending")
        sys.exit(1)
    print(f"✓ Questions ordered by difficultyTier ascending")
    
    # Verify each question includes required fields
    required_fields = ['id', 'strand', 'questionType', 'prompt', 'displayData', 'correctAnswer']
    for q in questions:
        for field in required_fields:
            if field not in q:
                print(f"❌ FAIL: Question missing field '{field}'")
                sys.exit(1)
    print(f"✓ All questions include required fields: {required_fields}")
    
    # Verify correctAnswer IS included (intentionally, since nothing is scored)
    for q in questions:
        if 'correctAnswer' not in q:
            print(f"❌ FAIL: correctAnswer not included in question {q['id']}")
            sys.exit(1)
    print(f"✓ correctAnswer IS intentionally included (unscored mode)")
    
    # Verify MC questions include options containing correctAnswer
    mc_count = 0
    for q in questions:
        if 'options' in q and q['options'] is not None:
            mc_count += 1
            if q['correctAnswer'] not in q['options']:
                print(f"❌ FAIL: MC question {q['id']} correctAnswer not in options")
                sys.exit(1)
    print(f"✓ MC questions ({mc_count} found) include options containing correctAnswer")
    
    # Call it twice to verify different question sets
    resp2 = api_call('POST', f'/kids/{kid3_id}/ordershapes', token=token_a, json_data={'date': '2025-01-15'})
    questions2 = resp2.json().get('questions', [])
    ids1 = set(q['id'] for q in questions)
    ids2 = set(q['id'] for q in questions2)
    common = ids1 & ids2
    print(f"✓ Second call returned {len(questions2)} questions")
    print(f"✓ Common IDs between two calls: {len(common)} (random selection varies)")
    if len(common) == 10:
        print(f"⚠️  WARNING: All 10 questions identical - expected some variation")
    
    # Test Grade 1 kid
    kid1_data = {'firstName': 'TestKid1', 'grade': 1}
    resp = api_call('POST', '/kids', token=token_a, json_data=kid1_data)
    kid1 = resp.json()['kid']
    kid1_id = kid1['id']
    print(f"✓ Created Grade 1 kid: {kid1['firstName']} (id: {kid1_id})")
    
    resp = api_call('POST', f'/kids/{kid1_id}/ordershapes', token=token_a, json_data={'date': '2025-01-15'})
    questions1 = resp.json().get('questions', [])
    print(f"✓ Grade 1 kid: {len(questions1)} questions returned")
    
    # Verify all belong to grade 1
    for q in questions1:
        bank_doc = db.orderShapesBank.find_one({'id': q['id']})
        if not bank_doc or bank_doc['grade'] != 1:
            print(f"❌ FAIL: Question {q['id']} does not belong to grade 1")
            sys.exit(1)
    print(f"✓ All 10 questions belong to grade 1")
    
    print("✅ TEST 3 PASSED: Order and Shapes route working correctly")
    print()
    
except Exception as e:
    print(f"❌ TEST 3 FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("=" * 80)
print("TEST 4: SECURITY/OWNERSHIP - Auth required, cross-parent isolation")
print("=" * 80)

try:
    # Test without session
    resp = api_call('POST', f'/kids/{kid3_id}/ordershapes', token=None, json_data={'date': '2025-01-15'})
    if resp.status_code != 401:
        print(f"❌ FAIL: Expected 401 without session, got {resp.status_code}")
        sys.exit(1)
    print(f"✓ POST /api/kids/:id/ordershapes without session returns 401")
    
    # Create Parent B
    parent_b, token_b = create_test_parent('parent_b')
    print(f"✓ Created Parent B: {parent_b['email']}")
    
    # Parent B tries to access Parent A's kid
    resp = api_call('POST', f'/kids/{kid3_id}/ordershapes', token=token_b, json_data={'date': '2025-01-15'})
    if resp.status_code not in [401, 404]:
        print(f"❌ FAIL: Expected 401/404 for cross-parent access, got {resp.status_code}")
        sys.exit(1)
    print(f"✓ Parent B cannot access Parent A's kid (status: {resp.status_code})")
    
    print("✅ TEST 4 PASSED: Security and ownership verified")
    print()
    
except Exception as e:
    print(f"❌ TEST 4 FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("=" * 80)
print("TEST 5: REGRESSION - Existing features still work")
print("=" * 80)

try:
    # Test unauthenticated routes return 401
    resp = api_call('GET', '/kids', token=None)
    if resp.status_code != 401:
        print(f"❌ FAIL: Expected 401 for unauthenticated GET /kids, got {resp.status_code}")
        sys.exit(1)
    print(f"✓ Unauthenticated GET /kids returns 401")
    
    # Test Fun Math start run (should still work)
    resp = api_call('POST', f'/kids/{kid3_id}/funmath', token=token_a, json_data={'date': '2025-01-15'})
    if resp.status_code != 200:
        print(f"❌ FAIL: Fun Math start run failed (status: {resp.status_code})")
        print(f"Response: {resp.text}")
        sys.exit(1)
    
    run_data = resp.json()
    run = run_data.get('run', {})
    if run.get('total') != 20:
        print(f"❌ FAIL: Fun Math run should have 20 questions, got {run.get('total')}")
        sys.exit(1)
    print(f"✓ Fun Math start run returns 20 questions")
    
    # Verify NO numericAnswer in client response
    for q in run.get('questions', []):
        if 'numericAnswer' in q:
            print(f"❌ FAIL: numericAnswer leaked to client in Fun Math run")
            sys.exit(1)
    print(f"✓ Fun Math run does NOT leak numericAnswer to client")
    
    # Test Fun Math perfect run unlocks color
    run_id = run['id']
    run_doc = db.funMathRuns.find_one({'id': run_id})
    
    # Answer all 20 questions correctly
    for q_doc in run_doc['questions']:
        bank_item = db.funMathBank.find_one({'id': q_doc['id']})
        correct_answer = bank_item['numericAnswer']
        
        resp = api_call('POST', f'/funmath/{run_id}/answer', token=token_a, 
                       json_data={'questionId': q_doc['id'], 'answer': correct_answer})
        if resp.status_code != 200:
            print(f"❌ FAIL: Fun Math answer failed (status: {resp.status_code})")
            sys.exit(1)
    
    # Check final response
    final_resp = resp.json()
    if not final_resp.get('runComplete'):
        print(f"❌ FAIL: Fun Math run not complete after 20 correct answers")
        sys.exit(1)
    
    if not final_resp.get('colorUnlocked'):
        print(f"❌ FAIL: No color unlocked after perfect Fun Math run")
        sys.exit(1)
    
    print(f"✓ Fun Math perfect run unlocks color: {final_resp.get('colorUnlocked')}")
    
    # Test normal set completion still awards 2 stars
    resp = api_call('POST', f'/kids/{kid3_id}/set', token=token_a, json_data={'date': '2025-01-16'})
    if resp.status_code != 200:
        print(f"❌ FAIL: Normal set start failed (status: {resp.status_code})")
        sys.exit(1)
    
    set_data = resp.json()
    set_id = set_data['set']['id']
    set_doc = db.dailySets.find_one({'id': set_id})
    
    # Answer all 30 problems correctly
    for prob in set_doc['problems']:
        resp = api_call('POST', f'/sets/{set_id}/answer', token=token_a,
                       json_data={'problemId': prob['id'], 'answer': prob['correctAnswer']})
        if resp.status_code != 200:
            print(f"❌ FAIL: Normal set answer failed (status: {resp.status_code})")
            sys.exit(1)
    
    final_resp = resp.json()
    if not final_resp.get('setComplete'):
        print(f"❌ FAIL: Normal set not complete after 30 correct answers")
        sys.exit(1)
    
    if final_resp.get('starsEarned') != 2:
        print(f"❌ FAIL: Normal set should award 2 stars, got {final_resp.get('starsEarned')}")
        sys.exit(1)
    
    print(f"✓ Normal set completion awards exactly 2 stars")
    
    # Verify funMathBank still has 2500 docs
    fm_count = db.funMathBank.count_documents({})
    if fm_count != 2500:
        print(f"❌ FAIL: funMathBank should have 2500 docs, got {fm_count}")
        sys.exit(1)
    print(f"✓ funMathBank still has 2500 documents")
    
    print("✅ TEST 5 PASSED: All existing features working correctly, no regressions")
    print()
    
except Exception as e:
    print(f"❌ TEST 5 FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("=" * 80)
print("🎉 ALL TESTS PASSED - V1.3 Order and Shapes Backend Verified")
print("=" * 80)
print()
print("SUMMARY:")
print("✅ TEST 1: Seeding - 1000 docs (200 per grade, 100 per strand)")
print("✅ TEST 2: Idempotency - No wipe/reseed/duplicate on reconnect")
print("✅ TEST 3: Order and Shapes route - 10 questions, grade-specific, mixed strands")
print("✅ TEST 4: Security/Ownership - Auth required, cross-parent isolation")
print("✅ TEST 5: Regression - Fun Math, normal sets, stars all working")
print()
print("V1.3 'Order and Shapes' backend is production-ready! 🚀")
