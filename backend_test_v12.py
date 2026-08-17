#!/usr/bin/env python3
"""
MathCompete V1.2 Backend Test Suite
Tests Fun Math, Avatars, and funMathBank seeding
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

client = MongoClient(MONGO_URL)
db = client[DB_NAME]

def mint_jwt(user_id, email):
    """Create a valid JWT session token"""
    payload = {
        'sub': user_id,
        'email': email,
        'role': 'parent',
        'iat': int(time.time()),
        'exp': int(time.time()) + 30*24*60*60
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def setup_test_users():
    """Insert test parents into DB"""
    users = db['users']
    users.delete_many({'email': {'$in': ['test_parent_a@test.com', 'test_parent_b@test.com']}})
    
    parent_a = {
        'id': str(uuid4()),
        'googleId': 'test_google_a',
        'email': 'test_parent_a@test.com',
        'name': 'Test Parent A',
        'createdAt': datetime.utcnow()
    }
    parent_b = {
        'id': str(uuid4()),
        'googleId': 'test_google_b',
        'email': 'test_parent_b@test.com',
        'name': 'Test Parent B',
        'createdAt': datetime.utcnow()
    }
    users.insert_one(parent_a)
    users.insert_one(parent_b)
    
    token_a = mint_jwt(parent_a['id'], parent_a['email'])
    token_b = mint_jwt(parent_b['id'], parent_b['email'])
    
    return parent_a, parent_b, token_a, token_b

def cleanup_test_data(parent_a_id, parent_b_id):
    """Clean up test data"""
    db['kids'].delete_many({'userId': {'$in': [parent_a_id, parent_b_id]}})
    db['dailySets'].delete_many({})
    db['speedSessions'].delete_many({})
    db['funMathRuns'].delete_many({})
    db['users'].delete_many({'email': {'$in': ['test_parent_a@test.com', 'test_parent_b@test.com']}})

def test_funmath_bank_seeding():
    """Test 1: funMathBank seeding - verify >=150 docs per grade 1-5"""
    print("\n=== TEST 1: funMathBank Seeding ===")
    try:
        bank = db['funMathBank']
        
        for grade in range(1, 6):
            docs = list(bank.find({'grade': grade}))
            count = len(docs)
            print(f"Grade {grade}: {count} questions")
            
            if count < 150:
                print(f"❌ FAIL: Grade {grade} has only {count} questions (expected >=150)")
                return False
            
            # Verify fields
            for doc in docs[:5]:  # Check first 5
                required_fields = ['id', 'grade', 'questionText', 'numericAnswer', 'operationTag', 'difficultyTier', 'createdAt']
                for field in required_fields:
                    if field not in doc:
                        print(f"❌ FAIL: Missing field '{field}' in question {doc.get('id', 'unknown')}")
                        return False
                
                # Verify numericAnswer is whole integer >= 0
                if not isinstance(doc['numericAnswer'], int) or doc['numericAnswer'] < 0:
                    print(f"❌ FAIL: numericAnswer must be whole integer >=0, got {doc['numericAnswer']}")
                    return False
        
        print("✅ PASS: funMathBank has >=150 questions per grade 1-5 with correct fields")
        return True
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False

def test_avatars_additive_validation(token_a):
    """Test 2: Avatars (additive + validation)"""
    print("\n=== TEST 2: Avatars (additive + validation) ===")
    try:
        # 2a: POST /api/kids with avatar='dog'
        print("\n2a: Create kid with avatar='dog'")
        resp = requests.post(f'{BASE_URL}/kids', 
            json={'firstName': 'TestKid1', 'grade': 2, 'avatar': 'dog'},
            cookies={'mc_session': token_a})
        if resp.status_code != 200:
            print(f"❌ FAIL: POST /api/kids returned {resp.status_code}")
            return False
        
        kid1 = resp.json()['kid']
        kid1_id = kid1['id']
        if kid1['avatar'] != 'dog':
            print(f"❌ FAIL: Expected avatar='dog', got '{kid1['avatar']}'")
            return False
        if kid1['avatarColor'] != 'sunset':
            print(f"❌ FAIL: Expected avatarColor='sunset', got '{kid1['avatarColor']}'")
            return False
        if kid1['unlockedColors'] != ['sunset', 'sky']:
            print(f"❌ FAIL: Expected unlockedColors=['sunset','sky'], got {kid1['unlockedColors']}")
            return False
        print(f"✅ Kid created with avatar='dog', avatarColor='sunset', unlockedColors=['sunset','sky']")
        
        # 2b: Legacy kid without avatar fields gets defaults
        print("\n2b: Legacy kid without avatar fields")
        legacy_kid_id = str(uuid4())
        db['kids'].insert_one({
            'id': legacy_kid_id,
            'userId': db['users'].find_one({'email': 'test_parent_a@test.com'})['id'],
            'firstName': 'LegacyKid',
            'grade': 3,
            'difficultyStep': 0,
            'soundOn': True,
            'theme': 'animals',
            'createdAt': datetime.utcnow()
            # NO avatar, avatarColor, unlockedColors fields
        })
        
        # GET /api/kids should backfill defaults
        resp = requests.get(f'{BASE_URL}/kids?date=2025-01-20', cookies={'mc_session': token_a})
        if resp.status_code != 200:
            print(f"❌ FAIL: GET /api/kids returned {resp.status_code}")
            return False
        
        kids = resp.json()['kids']
        legacy = next((k for k in kids if k['id'] == legacy_kid_id), None)
        if not legacy:
            print(f"❌ FAIL: Legacy kid not found in response")
            return False
        
        if legacy['avatar'] != 'bear':
            print(f"❌ FAIL: Expected default avatar='bear', got '{legacy['avatar']}'")
            return False
        if legacy['avatarColor'] != 'sunset':
            print(f"❌ FAIL: Expected default avatarColor='sunset', got '{legacy['avatarColor']}'")
            return False
        if legacy['unlockedColors'] != ['sunset', 'sky']:
            print(f"❌ FAIL: Expected default unlockedColors=['sunset','sky'], got {legacy['unlockedColors']}")
            return False
        
        # Verify DB doc still lacks the fields (defaults come from read)
        db_doc = db['kids'].find_one({'id': legacy_kid_id})
        if 'avatar' in db_doc or 'avatarColor' in db_doc or 'unlockedColors' in db_doc:
            print(f"❌ FAIL: DB doc should NOT have avatar fields (defaults should come from read)")
            return False
        print(f"✅ Legacy kid gets default avatar='bear', avatarColor='sunset', unlockedColors=['sunset','sky'] WITHOUT modifying DB")
        
        # 2c: PUT /api/kids/:id with avatar validation
        print("\n2c: PUT /api/kids/:id with avatar validation")
        
        # Valid avatar 'dinosaur'
        resp = requests.put(f'{BASE_URL}/kids/{kid1_id}', 
            json={'avatar': 'dinosaur'},
            cookies={'mc_session': token_a})
        if resp.status_code != 200:
            print(f"❌ FAIL: PUT with avatar='dinosaur' returned {resp.status_code}")
            return False
        print(f"✅ PUT with avatar='dinosaur' succeeded")
        
        # Invalid avatar 'cat'
        resp = requests.put(f'{BASE_URL}/kids/{kid1_id}', 
            json={'avatar': 'cat'},
            cookies={'mc_session': token_a})
        if resp.status_code != 400:
            print(f"❌ FAIL: PUT with invalid avatar='cat' should return 400, got {resp.status_code}")
            return False
        print(f"✅ PUT with invalid avatar='cat' returns 400")
        
        # avatarColor 'grape' when NOT unlocked
        resp = requests.put(f'{BASE_URL}/kids/{kid1_id}', 
            json={'avatarColor': 'grape'},
            cookies={'mc_session': token_a})
        if resp.status_code != 400:
            print(f"❌ FAIL: PUT with locked color 'grape' should return 400, got {resp.status_code}")
            return False
        print(f"✅ PUT with locked color 'grape' returns 400")
        
        # avatarColor 'sky' (unlocked)
        resp = requests.put(f'{BASE_URL}/kids/{kid1_id}', 
            json={'avatarColor': 'sky'},
            cookies={'mc_session': token_a})
        if resp.status_code != 200:
            print(f"❌ FAIL: PUT with unlocked color 'sky' returned {resp.status_code}")
            return False
        
        # Verify persistence
        resp = requests.get(f'{BASE_URL}/kids?date=2025-01-20', cookies={'mc_session': token_a})
        kids = resp.json()['kids']
        kid1_updated = next((k for k in kids if k['id'] == kid1_id), None)
        if kid1_updated['avatarColor'] != 'sky':
            print(f"❌ FAIL: avatarColor not persisted, expected 'sky', got '{kid1_updated['avatarColor']}'")
            return False
        print(f"✅ PUT with unlocked color 'sky' succeeded and persisted")
        
        # 2d: Two kids under one parent can hold different avatars
        print("\n2d: Two kids with different avatars")
        resp = requests.post(f'{BASE_URL}/kids', 
            json={'firstName': 'TestKid2', 'grade': 4, 'avatar': 'bear'},
            cookies={'mc_session': token_a})
        if resp.status_code != 200:
            print(f"❌ FAIL: POST /api/kids returned {resp.status_code}")
            return False
        kid2 = resp.json()['kid']
        
        resp = requests.get(f'{BASE_URL}/kids?date=2025-01-20', cookies={'mc_session': token_a})
        kids = resp.json()['kids']
        kid1_final = next((k for k in kids if k['id'] == kid1_id), None)
        kid2_final = next((k for k in kids if k['id'] == kid2['id']), None)
        
        if kid1_final['avatar'] == kid2_final['avatar']:
            print(f"❌ FAIL: Both kids have same avatar '{kid1_final['avatar']}'")
            return False
        print(f"✅ Two kids hold different avatars: kid1='{kid1_final['avatar']}', kid2='{kid2_final['avatar']}'")
        
        print("\n✅ PASS: All avatar tests passed")
        return True
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_funmath_run(token_a):
    """Test 3: Fun Math run"""
    print("\n=== TEST 3: Fun Math Run ===")
    try:
        # Create a kid
        resp = requests.post(f'{BASE_URL}/kids', 
            json={'firstName': 'FunKid', 'grade': 2},
            cookies={'mc_session': token_a})
        kid_id = resp.json()['kid']['id']
        
        # Start Fun Math run
        print("\n3a: POST /api/kids/:id/funmath")
        resp = requests.post(f'{BASE_URL}/kids/{kid_id}/funmath', 
            json={'date': '2025-01-20'},
            cookies={'mc_session': token_a})
        if resp.status_code != 200:
            print(f"❌ FAIL: POST /api/kids/:id/funmath returned {resp.status_code}")
            return False
        
        data = resp.json()
        run = data['run']
        run_id = run['id']
        
        # Verify structure
        if run['total'] != 20:
            print(f"❌ FAIL: Expected total=20, got {run['total']}")
            return False
        
        questions = run['questions']
        if len(questions) != 20:
            print(f"❌ FAIL: Expected 20 questions, got {len(questions)}")
            return False
        
        # Verify NO numericAnswer in response
        for q in questions:
            if 'numericAnswer' in q:
                print(f"❌ FAIL: numericAnswer should NOT be in client response")
                return False
            if 'id' not in q or 'questionText' not in q:
                print(f"❌ FAIL: Question missing id or questionText")
                return False
        print(f"✅ Run returns 20 questions, NO numericAnswer in response")
        
        # Verify no repeating questions within run
        question_ids = [q['id'] for q in questions]
        if len(question_ids) != len(set(question_ids)):
            print(f"❌ FAIL: Duplicate questions found in run")
            return False
        print(f"✅ No repeating questions within run")
        
        # Verify all from kid's grade
        bank_questions = list(db['funMathBank'].find({'id': {'$in': question_ids}}))
        if len(bank_questions) != 20:
            print(f"❌ FAIL: Not all questions found in bank")
            return False
        
        for bq in bank_questions:
            if bq['grade'] != 2:
                print(f"❌ FAIL: Question {bq['id']} is grade {bq['grade']}, expected 2")
                return False
        print(f"✅ All questions from kid's grade (2)")
        
        # Verify ordered by difficultyTier ascending
        tiers = [bq['difficultyTier'] for bq in bank_questions]
        # Match order from response
        ordered_tiers = []
        for q in questions:
            bq = next((b for b in bank_questions if b['id'] == q['id']), None)
            if bq:
                ordered_tiers.append(bq['difficultyTier'])
        
        if ordered_tiers != sorted(ordered_tiers):
            print(f"❌ FAIL: Questions not ordered by difficultyTier. Got: {ordered_tiers}")
            return False
        print(f"✅ Questions ordered by difficultyTier ascending: {ordered_tiers}")
        
        # Verify funMathRuns doc created with status 'in_progress'
        run_doc = db['funMathRuns'].find_one({'id': run_id})
        if not run_doc:
            print(f"❌ FAIL: funMathRuns doc not created")
            return False
        if run_doc['status'] != 'in_progress':
            print(f"❌ FAIL: Expected status='in_progress', got '{run_doc['status']}'")
            return False
        print(f"✅ funMathRuns doc created with status='in_progress'")
        
        print("\n✅ PASS: Fun Math run test passed")
        return True, kid_id, run_id, questions
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False, None, None, None

def test_funmath_checking_unlock(token_a, kid_id, run_id, questions):
    """Test 4: Fun Math server-side checking + unlock"""
    print("\n=== TEST 4: Fun Math Server-Side Checking + Unlock ===")
    try:
        # Get correct answers from DB
        question_ids = [q['id'] for q in questions]
        bank_questions = {bq['id']: bq for bq in db['funMathBank'].find({'id': {'$in': question_ids}})}
        
        # 4a: Answer first 19 correctly
        print("\n4a: Answer first 19 questions correctly")
        for i in range(19):
            q = questions[i]
            correct_answer = bank_questions[q['id']]['numericAnswer']
            resp = requests.post(f'{BASE_URL}/funmath/{run_id}/answer', 
                json={'questionId': q['id'], 'answer': correct_answer},
                cookies={'mc_session': token_a})
            if resp.status_code != 200:
                print(f"❌ FAIL: Answer {i+1} returned {resp.status_code}")
                return False
            data = resp.json()
            if not data['correct']:
                print(f"❌ FAIL: Answer {i+1} should be correct")
                return False
            if data.get('runComplete'):
                print(f"❌ FAIL: Run should not complete before all 20 answered")
                return False
        print(f"✅ First 19 answers correct, run not complete")
        
        # 4b: Try wrong answer on question 20
        print("\n4b: Try wrong answer on question 20")
        q20 = questions[19]
        correct_answer_20 = bank_questions[q20['id']]['numericAnswer']
        wrong_answer = correct_answer_20 + 999
        
        resp = requests.post(f'{BASE_URL}/funmath/{run_id}/answer', 
            json={'questionId': q20['id'], 'answer': wrong_answer},
            cookies={'mc_session': token_a})
        if resp.status_code != 200:
            print(f"❌ FAIL: Wrong answer returned {resp.status_code}")
            return False
        data = resp.json()
        if data['correct']:
            print(f"❌ FAIL: Wrong answer should return correct=false")
            return False
        if 'message' not in data:
            print(f"❌ FAIL: Wrong answer should return message")
            return False
        if data.get('runComplete'):
            print(f"❌ FAIL: Run should NOT complete with wrong answer")
            return False
        print(f"✅ Wrong answer returns correct=false, message present, run NOT complete")
        
        # 4c: Answer question 20 correctly
        print("\n4c: Answer question 20 correctly")
        resp = requests.post(f'{BASE_URL}/funmath/{run_id}/answer', 
            json={'questionId': q20['id'], 'answer': correct_answer_20},
            cookies={'mc_session': token_a})
        if resp.status_code != 200:
            print(f"❌ FAIL: Final answer returned {resp.status_code}")
            return False
        data = resp.json()
        
        if not data['correct']:
            print(f"❌ FAIL: Final answer should be correct")
            return False
        if not data.get('runComplete'):
            print(f"❌ FAIL: Run should be complete after all 20 correct")
            return False
        if data.get('colorUnlocked') != 'grape':
            print(f"❌ FAIL: Expected colorUnlocked='grape', got '{data.get('colorUnlocked')}'")
            return False
        if data.get('allOwned'):
            print(f"❌ FAIL: allOwned should be false (only 3 colors owned)")
            return False
        
        unlocked_colors = data.get('unlockedColors', [])
        if 'grape' not in unlocked_colors:
            print(f"❌ FAIL: 'grape' should be in unlockedColors")
            return False
        if len(unlocked_colors) != 3:
            print(f"❌ FAIL: Expected 3 colors, got {len(unlocked_colors)}")
            return False
        print(f"✅ Final answer: correct=true, runComplete=true, colorUnlocked='grape', allOwned=false, unlockedColors={unlocked_colors}")
        
        # Verify kid's unlockedColors in DB
        kid_doc = db['kids'].find_one({'id': kid_id})
        if 'grape' not in kid_doc['unlockedColors']:
            print(f"❌ FAIL: 'grape' not in kid's unlockedColors in DB")
            return False
        if len(kid_doc['unlockedColors']) != 3:
            print(f"❌ FAIL: Expected 3 colors in DB, got {len(kid_doc['unlockedColors'])}")
            return False
        print(f"✅ Kid's unlockedColors in DB: {kid_doc['unlockedColors']}")
        
        # 4d: Repeat perfect runs unlock next colors
        print("\n4d: Repeat perfect runs unlock next colors (mint, bubblegum, gold)")
        for expected_color in ['mint', 'bubblegum', 'gold']:
            # Start new run
            resp = requests.post(f'{BASE_URL}/kids/{kid_id}/funmath', 
                json={'date': '2025-01-20'},
                cookies={'mc_session': token_a})
            if resp.status_code != 200:
                print(f"❌ FAIL: Failed to start new run for {expected_color}")
                return False
            
            new_run = resp.json()['run']
            new_run_id = new_run['id']
            new_questions = new_run['questions']
            
            # Answer all 20 correctly
            for q in new_questions:
                bank_q = db['funMathBank'].find_one({'id': q['id']})
                resp = requests.post(f'{BASE_URL}/funmath/{new_run_id}/answer', 
                    json={'questionId': q['id'], 'answer': bank_q['numericAnswer']},
                    cookies={'mc_session': token_a})
                if resp.status_code != 200:
                    print(f"❌ FAIL: Answer failed for {expected_color} run")
                    return False
            
            # Check final response
            final_data = resp.json()
            if final_data.get('colorUnlocked') != expected_color:
                print(f"❌ FAIL: Expected colorUnlocked='{expected_color}', got '{final_data.get('colorUnlocked')}'")
                return False
            print(f"✅ Perfect run unlocked '{expected_color}'")
        
        # 4e: After all 6 owned, perfect run returns allOwned=true
        print("\n4e: After all 6 colors owned, perfect run returns allOwned=true")
        resp = requests.post(f'{BASE_URL}/kids/{kid_id}/funmath', 
            json={'date': '2025-01-20'},
            cookies={'mc_session': token_a})
        if resp.status_code != 200:
            print(f"❌ FAIL: Failed to start final run")
            return False
        
        final_run = resp.json()['run']
        final_run_id = final_run['id']
        final_questions = final_run['questions']
        
        # Answer all 20 correctly
        for q in final_questions:
            bank_q = db['funMathBank'].find_one({'id': q['id']})
            resp = requests.post(f'{BASE_URL}/funmath/{final_run_id}/answer', 
                json={'questionId': q['id'], 'answer': bank_q['numericAnswer']},
                cookies={'mc_session': token_a})
        
        final_data = resp.json()
        if not final_data.get('allOwned'):
            print(f"❌ FAIL: Expected allOwned=true after all colors owned")
            return False
        if final_data.get('colorUnlocked') is not None:
            print(f"❌ FAIL: Expected colorUnlocked=null when all owned, got '{final_data.get('colorUnlocked')}'")
            return False
        print(f"✅ After all 6 colors owned: allOwned=true, colorUnlocked=null")
        
        print("\n✅ PASS: Fun Math checking + unlock test passed")
        return True
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_funmath_exit(token_a):
    """Test 5: Fun Math exit"""
    print("\n=== TEST 5: Fun Math Exit ===")
    try:
        # Create a kid
        resp = requests.post(f'{BASE_URL}/kids', 
            json={'firstName': 'ExitKid', 'grade': 3},
            cookies={'mc_session': token_a})
        kid_id = resp.json()['kid']['id']
        
        # Get initial unlockedColors
        resp = requests.get(f'{BASE_URL}/kids?date=2025-01-20', cookies={'mc_session': token_a})
        kids = resp.json()['kids']
        exit_kid = next((k for k in kids if k['id'] == kid_id), None)
        initial_colors = exit_kid['unlockedColors']
        
        # Start Fun Math run
        resp = requests.post(f'{BASE_URL}/kids/{kid_id}/funmath', 
            json={'date': '2025-01-20'},
            cookies={'mc_session': token_a})
        run_id = resp.json()['run']['id']
        
        # Exit the run
        print("\n5a: POST /api/funmath/:id/exit")
        resp = requests.post(f'{BASE_URL}/funmath/{run_id}/exit', 
            json={},
            cookies={'mc_session': token_a})
        if resp.status_code != 200:
            print(f"❌ FAIL: Exit returned {resp.status_code}")
            return False
        
        # Verify run status is 'exited'
        run_doc = db['funMathRuns'].find_one({'id': run_id})
        if run_doc['status'] != 'exited':
            print(f"❌ FAIL: Expected status='exited', got '{run_doc['status']}'")
            return False
        print(f"✅ Run status set to 'exited'")
        
        # Verify no unlock
        kid_doc = db['kids'].find_one({'id': kid_id})
        if kid_doc['unlockedColors'] != initial_colors:
            print(f"❌ FAIL: unlockedColors changed after exit")
            return False
        print(f"✅ No color unlock after exit, unlockedColors unchanged")
        
        print("\n✅ PASS: Fun Math exit test passed")
        return True
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_security_ownership(token_a, token_b):
    """Test 6: Security / Ownership"""
    print("\n=== TEST 6: Security / Ownership ===")
    try:
        # 6a: Requires valid session (401 without)
        print("\n6a: Fun Math routes require valid session")
        resp = requests.post(f'{BASE_URL}/kids/fake-id/funmath', json={'date': '2025-01-20'})
        if resp.status_code != 401:
            print(f"❌ FAIL: Expected 401 without session, got {resp.status_code}")
            return False
        print(f"✅ POST /api/kids/:id/funmath returns 401 without session")
        
        # 6b: Parent B cannot access Parent A's run
        print("\n6b: Parent B cannot access Parent A's run")
        
        # Parent A creates kid and starts run
        resp = requests.post(f'{BASE_URL}/kids', 
            json={'firstName': 'ParentAKid', 'grade': 2},
            cookies={'mc_session': token_a})
        kid_a_id = resp.json()['kid']['id']
        
        resp = requests.post(f'{BASE_URL}/kids/{kid_a_id}/funmath', 
            json={'date': '2025-01-20'},
            cookies={'mc_session': token_a})
        run_a_id = resp.json()['run']['id']
        
        # Parent B tries to answer Parent A's run
        resp = requests.post(f'{BASE_URL}/funmath/{run_a_id}/answer', 
            json={'questionId': 'fake-id', 'answer': 42},
            cookies={'mc_session': token_b})
        if resp.status_code not in [401, 404]:
            print(f"❌ FAIL: Expected 401/404 for cross-parent access, got {resp.status_code}")
            return False
        print(f"✅ Parent B cannot answer Parent A's run (returns {resp.status_code})")
        
        # Parent B tries to exit Parent A's run
        resp = requests.post(f'{BASE_URL}/funmath/{run_a_id}/exit', 
            json={},
            cookies={'mc_session': token_b})
        if resp.status_code not in [401, 404]:
            print(f"❌ FAIL: Expected 401/404 for cross-parent exit, got {resp.status_code}")
            return False
        print(f"✅ Parent B cannot exit Parent A's run (returns {resp.status_code})")
        
        # 6c: numericAnswer never appears in any API response
        print("\n6c: numericAnswer never in API response")
        
        # Start run
        resp = requests.post(f'{BASE_URL}/kids', 
            json={'firstName': 'SecurityKid', 'grade': 2},
            cookies={'mc_session': token_a})
        kid_id = resp.json()['kid']['id']
        
        resp = requests.post(f'{BASE_URL}/kids/{kid_id}/funmath', 
            json={'date': '2025-01-20'},
            cookies={'mc_session': token_a})
        
        # Check response doesn't contain numericAnswer
        resp_text = resp.text
        if 'numericAnswer' in resp_text:
            print(f"❌ FAIL: numericAnswer found in start run response")
            return False
        print(f"✅ numericAnswer NOT in start run response")
        
        # Answer a question
        run_id = resp.json()['run']['id']
        question_id = resp.json()['run']['questions'][0]['id']
        bank_q = db['funMathBank'].find_one({'id': question_id})
        
        resp = requests.post(f'{BASE_URL}/funmath/{run_id}/answer', 
            json={'questionId': question_id, 'answer': bank_q['numericAnswer']},
            cookies={'mc_session': token_a})
        
        resp_text = resp.text
        if 'numericAnswer' in resp_text:
            print(f"❌ FAIL: numericAnswer found in answer response")
            return False
        print(f"✅ numericAnswer NOT in answer response")
        
        print("\n✅ PASS: Security / Ownership test passed")
        return True
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_regression(token_a):
    """Test 7: Regression - existing features still work"""
    print("\n=== TEST 7: Regression Testing ===")
    try:
        # 7a: Unauthenticated -> 401
        print("\n7a: Unauthenticated requests return 401")
        resp = requests.get(f'{BASE_URL}/kids')
        if resp.status_code != 401:
            print(f"❌ FAIL: Expected 401 without auth, got {resp.status_code}")
            return False
        print(f"✅ Unauthenticated GET /api/kids returns 401")
        
        # 7b: Stars totals & speed math unaffected
        print("\n7b: Stars totals & speed math still work")
        
        # Create kid
        resp = requests.post(f'{BASE_URL}/kids', 
            json={'firstName': 'RegressionKid', 'grade': 2},
            cookies={'mc_session': token_a})
        kid_id = resp.json()['kid']['id']
        
        # Complete a normal set
        resp = requests.post(f'{BASE_URL}/kids/{kid_id}/set', 
            json={'date': '2025-01-20'},
            cookies={'mc_session': token_a})
        set_id = resp.json()['set']['id']
        
        # Get problems from DB and answer all
        set_doc = db['dailySets'].find_one({'id': set_id})
        for prob in set_doc['problems']:
            resp = requests.post(f'{BASE_URL}/sets/{set_id}/answer', 
                json={'problemId': prob['id'], 'answer': prob['correctAnswer']},
                cookies={'mc_session': token_a})
        
        final_data = resp.json()
        if final_data.get('starsEarned') != 2:
            print(f"❌ FAIL: Expected starsEarned=2, got {final_data.get('starsEarned')}")
            return False
        if final_data.get('totalStars') != 2:
            print(f"❌ FAIL: Expected totalStars=2, got {final_data.get('totalStars')}")
            return False
        print(f"✅ Normal set completion: starsEarned=2, totalStars=2")
        
        # Start speed session
        resp = requests.post(f'{BASE_URL}/kids/{kid_id}/speed', 
            json={'date': '2025-01-20'},
            cookies={'mc_session': token_a})
        if resp.status_code != 200:
            print(f"❌ FAIL: Speed session start returned {resp.status_code}")
            return False
        
        session_id = resp.json()['session']['id']
        session_doc = db['speedSessions'].find_one({'id': session_id})
        
        # Answer all speed problems correctly
        for prob in session_doc['problems']:
            resp = requests.post(f'{BASE_URL}/speed/{session_id}/answer', 
                json={'problemId': prob['id'], 'answer': prob['correctAnswer']},
                cookies={'mc_session': token_a})
        
        speed_data = resp.json()
        if speed_data.get('starsEarned') != 4:
            print(f"❌ FAIL: Expected speed starsEarned=4, got {speed_data.get('starsEarned')}")
            return False
        if speed_data.get('totalStars') != 6:
            print(f"❌ FAIL: Expected totalStars=6 (2 normal + 4 speed), got {speed_data.get('totalStars')}")
            return False
        print(f"✅ Speed session: starsEarned=4, totalStars=6 (2 normal + 4 speed)")
        
        # 7c: Normal-set $2/2-per-day still works
        print("\n7c: Normal-set 2-per-day cap still works")
        
        # Complete second set
        resp = requests.post(f'{BASE_URL}/kids/{kid_id}/set', 
            json={'date': '2025-01-20'},
            cookies={'mc_session': token_a})
        set2_id = resp.json()['set']['id']
        
        set2_doc = db['dailySets'].find_one({'id': set2_id})
        for prob in set2_doc['problems']:
            resp = requests.post(f'{BASE_URL}/sets/{set2_id}/answer', 
                json={'problemId': prob['id'], 'answer': prob['correctAnswer']},
                cookies={'mc_session': token_a})
        
        final_data = resp.json()
        if not final_data.get('locked'):
            print(f"❌ FAIL: Expected locked=true after 2 sets")
            return False
        print(f"✅ 2-per-day cap: locked=true after 2 completed sets")
        
        # Try third set
        resp = requests.post(f'{BASE_URL}/kids/{kid_id}/set', 
            json={'date': '2025-01-20'},
            cookies={'mc_session': token_a})
        if not resp.json().get('locked'):
            print(f"❌ FAIL: Third set should return locked=true")
            return False
        print(f"✅ Third set attempt returns locked=true")
        
        # 7d: Existing kids still load
        print("\n7d: Existing kids still load")
        resp = requests.get(f'{BASE_URL}/kids?date=2025-01-20', cookies={'mc_session': token_a})
        if resp.status_code != 200:
            print(f"❌ FAIL: GET /api/kids returned {resp.status_code}")
            return False
        
        kids = resp.json()['kids']
        if len(kids) == 0:
            print(f"❌ FAIL: No kids returned")
            return False
        print(f"✅ GET /api/kids returns {len(kids)} kids")
        
        # 7e: No /api practice route
        print("\n7e: No /api practice route exists")
        resp = requests.post(f'{BASE_URL}/kids/{kid_id}/practice', 
            json={'date': '2025-01-20'},
            cookies={'mc_session': token_a})
        if resp.status_code != 404:
            print(f"❌ FAIL: /api practice route should not exist (expected 404), got {resp.status_code}")
            return False
        print(f"✅ No /api practice route (returns 404)")
        
        print("\n✅ PASS: All regression tests passed")
        return True
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 80)
    print("MathCompete V1.2 Backend Test Suite")
    print("Testing: Fun Math, Avatars, funMathBank seeding")
    print("=" * 80)
    
    # Setup
    parent_a, parent_b, token_a, token_b = setup_test_users()
    
    results = []
    
    try:
        # Test 1: funMathBank seeding
        results.append(("funMathBank Seeding", test_funmath_bank_seeding()))
        
        # Test 2: Avatars
        results.append(("Avatars (additive + validation)", test_avatars_additive_validation(token_a)))
        
        # Test 3: Fun Math run
        result, kid_id, run_id, questions = test_funmath_run(token_a)
        results.append(("Fun Math Run", result))
        
        # Test 4: Fun Math checking + unlock (only if test 3 passed)
        if result and kid_id and run_id and questions:
            results.append(("Fun Math Checking + Unlock", test_funmath_checking_unlock(token_a, kid_id, run_id, questions)))
        else:
            results.append(("Fun Math Checking + Unlock", False))
        
        # Test 5: Fun Math exit
        results.append(("Fun Math Exit", test_funmath_exit(token_a)))
        
        # Test 6: Security / Ownership
        results.append(("Security / Ownership", test_security_ownership(token_a, token_b)))
        
        # Test 7: Regression
        results.append(("Regression", test_regression(token_a)))
        
    finally:
        # Cleanup
        cleanup_test_data(parent_a['id'], parent_b['id'])
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({100*passed//total}% success rate)")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! V1.2 backend is working correctly.")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the output above.")
        sys.exit(1)

if __name__ == '__main__':
    main()
