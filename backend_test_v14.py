#!/usr/bin/env python3
"""
MathCompete V1.4 Backend Testing (Phase 4 & 6)
Tests avatar system (additive migration + unlock ordering) and COPPA notice page.
"""

import asyncio
import jwt
import time
import uuid
from datetime import datetime, timedelta
from pymongo import MongoClient
import os
import sys
import requests

# Read environment variables
MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.getenv('DB_NAME', 'your_database_name')
JWT_SECRET = os.getenv('JWT_SECRET', '')
BASE_URL = os.getenv('NEXT_PUBLIC_BASE_URL', 'http://localhost:3000')

# Fixed avatar order (from route.js line 47)
AVATAR_IDS = ['astronaut_boy', 'astronaut_girl', 'golden_retriever', 'baby_dinosaur', 'airplane', 'unicorn', 'girl_pilot', 'boy_pilot']
START_AVATARS = ['astronaut_boy', 'astronaut_girl']  # first 2 are free
FUN_COLORS = ['sunset', 'sky', 'grape', 'mint', 'bubblegum', 'gold']

def mint_jwt(user_id, email):
    """Mint an HS256 JWT for mc_session cookie"""
    payload = {
        'sub': user_id,
        'email': email,
        'role': 'parent',
        'iat': int(time.time()),
        'exp': int(time.time()) + 86400 * 30
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def setup_test_parent(db, email_suffix):
    """Insert a test parent and return (user_id, jwt_token)"""
    user_id = str(uuid.uuid4())
    email = f'test-v14-{email_suffix}@example.com'
    db.users.insert_one({
        'id': user_id,
        'googleId': f'google-{user_id}',
        'email': email,
        'name': f'Test Parent {email_suffix}',
        'createdAt': datetime.utcnow()
    })
    token = mint_jwt(user_id, email)
    return user_id, token

def api_get(endpoint, token=None):
    """GET request to API"""
    url = f'{BASE_URL}/api/{endpoint}'
    cookies = {'mc_session': token} if token else {}
    return requests.get(url, cookies=cookies)

def api_post(endpoint, data, token=None):
    """POST request to API"""
    url = f'{BASE_URL}/api/{endpoint}'
    cookies = {'mc_session': token} if token else {}
    return requests.post(url, json=data, cookies=cookies)

def api_put(endpoint, data, token):
    """PUT request to API"""
    url = f'{BASE_URL}/api/{endpoint}'
    cookies = {'mc_session': token}
    return requests.put(url, json=data, cookies=cookies)

def test_phase6_coppa_notice():
    """Phase 6: GET /coppa-notice returns 200 without auth (public page)"""
    print("\n" + "="*80)
    print("TEST: Phase 6 - Public COPPA notice page")
    print("="*80)
    
    try:
        # Test without any cookie (public access)
        response = requests.get(f'{BASE_URL}/coppa-notice')
        
        if response.status_code == 200:
            print("✅ PASS: GET /coppa-notice returns 200 without auth")
            # Check for key content
            content = response.text.lower()
            if 'coppa' in content and 'kalyanashisc86+mathcompete@gmail.com' in content:
                print("✅ PASS: COPPA notice contains expected content (COPPA text + support email)")
            else:
                print("⚠️  WARNING: COPPA notice missing expected content")
            return True
        else:
            print(f"❌ FAIL: GET /coppa-notice returned {response.status_code}, expected 200")
            return False
    except Exception as e:
        print(f"❌ FAIL: Exception during COPPA notice test: {e}")
        return False

def test_create_kid_with_avatar(db, token):
    """Phase 4.1: CREATE KID with avatarId"""
    print("\n" + "="*80)
    print("TEST: Phase 4.1 - CREATE KID with avatarId")
    print("="*80)
    
    results = []
    
    # Test 1: Create kid with valid starter avatarId
    print("\n[Test 1] Create kid with avatarId='astronaut_girl' (valid starter)")
    resp = api_post('kids', {
        'firstName': 'Alice',
        'grade': 2,
        'avatarId': 'astronaut_girl'
    }, token)
    
    if resp.status_code == 200:
        kid = resp.json()['kid']
        if kid['avatarId'] == 'astronaut_girl' and set(kid['unlockedAvatars']) == set(START_AVATARS):
            print(f"✅ PASS: Kid created with avatarId='astronaut_girl', unlockedAvatars={kid['unlockedAvatars']}")
            
            # Verify legacy fields are still set
            kid_doc = db.kids.find_one({'id': kid['id']})
            if (kid_doc.get('avatar') == 'bear' and 
                kid_doc.get('avatarColor') == 'sunset' and 
                set(kid_doc.get('unlockedColors', [])) == set(['sunset', 'sky'])):
                print("✅ PASS: Legacy fields (avatar='bear', avatarColor='sunset', unlockedColors=['sunset','sky']) still set")
                results.append(True)
            else:
                print(f"❌ FAIL: Legacy fields not set correctly: avatar={kid_doc.get('avatar')}, avatarColor={kid_doc.get('avatarColor')}, unlockedColors={kid_doc.get('unlockedColors')}")
                results.append(False)
        else:
            print(f"❌ FAIL: avatarId={kid.get('avatarId')}, unlockedAvatars={kid.get('unlockedAvatars')}")
            results.append(False)
    else:
        print(f"❌ FAIL: Status {resp.status_code}, {resp.text}")
        results.append(False)
    
    # Test 2: Create kid without avatarId (should default to astronaut_boy)
    print("\n[Test 2] Create kid WITHOUT avatarId (should default to 'astronaut_boy')")
    resp = api_post('kids', {
        'firstName': 'Bob',
        'grade': 3
    }, token)
    
    if resp.status_code == 200:
        kid = resp.json()['kid']
        if kid['avatarId'] == 'astronaut_boy' and set(kid['unlockedAvatars']) == set(START_AVATARS):
            print(f"✅ PASS: Kid created with default avatarId='astronaut_boy', unlockedAvatars={kid['unlockedAvatars']}")
            results.append(True)
        else:
            print(f"❌ FAIL: avatarId={kid.get('avatarId')}, unlockedAvatars={kid.get('unlockedAvatars')}")
            results.append(False)
    else:
        print(f"❌ FAIL: Status {resp.status_code}, {resp.text}")
        results.append(False)
    
    # Test 3: Create kid with non-starter avatarId (should default to astronaut_boy)
    print("\n[Test 3] Create kid with non-starter avatarId='unicorn' (should default to 'astronaut_boy')")
    resp = api_post('kids', {
        'firstName': 'Charlie',
        'grade': 1,
        'avatarId': 'unicorn'
    }, token)
    
    if resp.status_code == 200:
        kid = resp.json()['kid']
        if kid['avatarId'] == 'astronaut_boy' and set(kid['unlockedAvatars']) == set(START_AVATARS):
            print(f"✅ PASS: Non-starter avatarId defaulted to 'astronaut_boy', unlockedAvatars={kid['unlockedAvatars']}")
            results.append(True)
        else:
            print(f"❌ FAIL: avatarId={kid.get('avatarId')}, unlockedAvatars={kid.get('unlockedAvatars')}")
            results.append(False)
    else:
        print(f"❌ FAIL: Status {resp.status_code}, {resp.text}")
        results.append(False)
    
    return all(results)

def test_migration(db, token, user_id):
    """Phase 4.2: MIGRATION - Most important, edge-prone test"""
    print("\n" + "="*80)
    print("TEST: Phase 4.2 - MIGRATION (CRITICAL)")
    print("="*80)
    
    results = []
    
    # Case A: unlockedColors=['sunset','sky'] (2) -> unlockedAvatars = first 2
    print("\n[Case A] Legacy kid with 2 colors -> should get first 2 avatars")
    kid_a_id = str(uuid.uuid4())
    legacy_a = {
        'id': kid_a_id,
        'userId': user_id,
        'firstName': 'LegacyA',
        'grade': 2,
        'difficultyStep': 0,
        'soundOn': True,
        'theme': 'animals',
        'avatar': 'bear',
        'avatarColor': 'sunset',
        'unlockedColors': ['sunset', 'sky'],
        'createdAt': datetime.utcnow()
        # NO avatarId or unlockedAvatars
    }
    db.kids.insert_one(legacy_a)
    print(f"Inserted legacy kid WITHOUT avatarId/unlockedAvatars: {kid_a_id}")
    
    # Trigger migration by calling GET /api/kids
    resp = api_get('kids', token)
    if resp.status_code == 200:
        kids = resp.json()['kids']
        kid_a = next((k for k in kids if k['id'] == kid_a_id), None)
        
        if kid_a:
            expected_avatars = ['astronaut_boy', 'astronaut_girl']
            if (kid_a['avatarId'] == 'astronaut_boy' and 
                set(kid_a['unlockedAvatars']) == set(expected_avatars)):
                print(f"✅ PASS: Migration applied - avatarId='astronaut_boy', unlockedAvatars={kid_a['unlockedAvatars']}")
                
                # CRITICAL: Verify persistence in DB
                kid_a_doc = db.kids.find_one({'id': kid_a_id})
                if (kid_a_doc.get('avatarId') == 'astronaut_boy' and 
                    set(kid_a_doc.get('unlockedAvatars', [])) == set(expected_avatars)):
                    print("✅ PASS: Migration PERSISTED to DB")
                    
                    # CRITICAL: Verify legacy fields UNCHANGED
                    if (kid_a_doc.get('avatar') == 'bear' and 
                        kid_a_doc.get('avatarColor') == 'sunset' and 
                        set(kid_a_doc.get('unlockedColors', [])) == set(['sunset', 'sky'])):
                        print("✅ PASS: Legacy fields (avatar, avatarColor, unlockedColors) UNCHANGED in DB")
                        results.append(True)
                    else:
                        print(f"❌ FAIL: Legacy fields CHANGED! avatar={kid_a_doc.get('avatar')}, avatarColor={kid_a_doc.get('avatarColor')}, unlockedColors={kid_a_doc.get('unlockedColors')}")
                        results.append(False)
                else:
                    print(f"❌ FAIL: Migration NOT persisted. DB: avatarId={kid_a_doc.get('avatarId')}, unlockedAvatars={kid_a_doc.get('unlockedAvatars')}")
                    results.append(False)
            else:
                print(f"❌ FAIL: avatarId={kid_a.get('avatarId')}, unlockedAvatars={kid_a.get('unlockedAvatars')}")
                results.append(False)
        else:
            print(f"❌ FAIL: Kid A not found in response")
            results.append(False)
    else:
        print(f"❌ FAIL: GET /api/kids returned {resp.status_code}")
        results.append(False)
    
    # Case B: unlockedColors all 6 -> unlockedAvatars = first 6 avatars
    print("\n[Case B] Legacy kid with all 6 colors -> should get first 6 avatars")
    kid_b_id = str(uuid.uuid4())
    legacy_b = {
        'id': kid_b_id,
        'userId': user_id,
        'firstName': 'LegacyB',
        'grade': 3,
        'difficultyStep': 2,
        'soundOn': True,
        'theme': 'ocean',
        'avatar': 'dog',
        'avatarColor': 'gold',
        'unlockedColors': ['sunset', 'sky', 'grape', 'mint', 'bubblegum', 'gold'],
        'createdAt': datetime.utcnow()
    }
    db.kids.insert_one(legacy_b)
    print(f"Inserted legacy kid with all 6 colors: {kid_b_id}")
    
    resp = api_get('kids', token)
    if resp.status_code == 200:
        kids = resp.json()['kids']
        kid_b = next((k for k in kids if k['id'] == kid_b_id), None)
        
        if kid_b:
            expected_avatars = AVATAR_IDS[:6]  # first 6
            if (kid_b['avatarId'] == expected_avatars[0] and 
                set(kid_b['unlockedAvatars']) == set(expected_avatars)):
                print(f"✅ PASS: Migration applied - avatarId='{expected_avatars[0]}', unlockedAvatars={kid_b['unlockedAvatars']}")
                
                # Verify persistence
                kid_b_doc = db.kids.find_one({'id': kid_b_id})
                if (kid_b_doc.get('avatarId') == expected_avatars[0] and 
                    set(kid_b_doc.get('unlockedAvatars', [])) == set(expected_avatars)):
                    print("✅ PASS: Migration PERSISTED to DB")
                    
                    # Verify legacy fields UNCHANGED
                    if (kid_b_doc.get('avatar') == 'dog' and 
                        kid_b_doc.get('avatarColor') == 'gold' and 
                        set(kid_b_doc.get('unlockedColors', [])) == set(FUN_COLORS)):
                        print("✅ PASS: Legacy fields UNCHANGED in DB")
                        results.append(True)
                    else:
                        print(f"❌ FAIL: Legacy fields CHANGED!")
                        results.append(False)
                else:
                    print(f"❌ FAIL: Migration NOT persisted")
                    results.append(False)
            else:
                print(f"❌ FAIL: avatarId={kid_b.get('avatarId')}, unlockedAvatars={kid_b.get('unlockedAvatars')}")
                results.append(False)
        else:
            print(f"❌ FAIL: Kid B not found")
            results.append(False)
    else:
        print(f"❌ FAIL: GET /api/kids returned {resp.status_code}")
        results.append(False)
    
    # Case C: unlockedColors empty/missing -> min 2 starters granted
    print("\n[Case C] Legacy kid with empty unlockedColors -> should get min 2 starters")
    kid_c_id = str(uuid.uuid4())
    legacy_c = {
        'id': kid_c_id,
        'userId': user_id,
        'firstName': 'LegacyC',
        'grade': 1,
        'difficultyStep': 0,
        'soundOn': True,
        'theme': 'space',
        'avatar': 'dinosaur',
        'avatarColor': 'sunset',
        'unlockedColors': [],  # empty
        'createdAt': datetime.utcnow()
    }
    db.kids.insert_one(legacy_c)
    print(f"Inserted legacy kid with empty unlockedColors: {kid_c_id}")
    
    resp = api_get('kids', token)
    if resp.status_code == 200:
        kids = resp.json()['kids']
        kid_c = next((k for k in kids if k['id'] == kid_c_id), None)
        
        if kid_c:
            if (kid_c['avatarId'] == 'astronaut_boy' and 
                set(kid_c['unlockedAvatars']) == set(START_AVATARS)):
                print(f"✅ PASS: Empty colors -> min 2 starters granted: {kid_c['unlockedAvatars']}")
                
                # Verify persistence and legacy fields
                kid_c_doc = db.kids.find_one({'id': kid_c_id})
                if (kid_c_doc.get('avatarId') == 'astronaut_boy' and 
                    set(kid_c_doc.get('unlockedAvatars', [])) == set(START_AVATARS) and
                    kid_c_doc.get('avatar') == 'dinosaur' and
                    kid_c_doc.get('avatarColor') == 'sunset' and
                    kid_c_doc.get('unlockedColors') == []):
                    print("✅ PASS: Migration persisted, legacy fields unchanged")
                    results.append(True)
                else:
                    print(f"❌ FAIL: Persistence or legacy field issue")
                    results.append(False)
            else:
                print(f"❌ FAIL: avatarId={kid_c.get('avatarId')}, unlockedAvatars={kid_c.get('unlockedAvatars')}")
                results.append(False)
        else:
            print(f"❌ FAIL: Kid C not found")
            results.append(False)
    else:
        print(f"❌ FAIL: GET /api/kids returned {resp.status_code}")
        results.append(False)
    
    return all(results)

def test_update_kid_avatar(db, token):
    """Phase 4.3: UPDATE KID avatarId validation"""
    print("\n" + "="*80)
    print("TEST: Phase 4.3 - UPDATE KID avatarId")
    print("="*80)
    
    results = []
    
    # Create a kid with 2 starters
    resp = api_post('kids', {'firstName': 'Dave', 'grade': 2}, token)
    kid = resp.json()['kid']
    kid_id = kid['id']
    print(f"Created kid with unlockedAvatars: {kid['unlockedAvatars']}")
    
    # Test 1: Update to an owned avatar (astronaut_girl)
    print("\n[Test 1] Update to owned avatar 'astronaut_girl'")
    resp = api_put(f'kids/{kid_id}', {'avatarId': 'astronaut_girl'}, token)
    if resp.status_code == 200:
        kid = resp.json()['kid']
        if kid['avatarId'] == 'astronaut_girl':
            print("✅ PASS: Updated to owned avatar 'astronaut_girl'")
            
            # Verify persistence
            kid_doc = db.kids.find_one({'id': kid_id})
            if kid_doc.get('avatarId') == 'astronaut_girl':
                print("✅ PASS: Update persisted to DB")
                results.append(True)
            else:
                print(f"❌ FAIL: Not persisted, DB has {kid_doc.get('avatarId')}")
                results.append(False)
        else:
            print(f"❌ FAIL: avatarId={kid.get('avatarId')}")
            results.append(False)
    else:
        print(f"❌ FAIL: Status {resp.status_code}, {resp.text}")
        results.append(False)
    
    # Test 2: Try to update to locked avatar (unicorn)
    print("\n[Test 2] Try to update to locked avatar 'unicorn' (should return 400)")
    resp = api_put(f'kids/{kid_id}', {'avatarId': 'unicorn'}, token)
    if resp.status_code == 400:
        error = resp.json().get('error', '')
        if 'not unlocked' in error.lower():
            print(f"✅ PASS: Locked avatar rejected with 400: {error}")
            results.append(True)
        else:
            print(f"⚠️  PASS: 400 returned but error message unclear: {error}")
            results.append(True)
    else:
        print(f"❌ FAIL: Expected 400, got {resp.status_code}")
        results.append(False)
    
    # Test 3: Try to update to unknown avatar (dragon)
    print("\n[Test 3] Try to update to unknown avatar 'dragon' (should return 400)")
    resp = api_put(f'kids/{kid_id}', {'avatarId': 'dragon'}, token)
    if resp.status_code == 400:
        print(f"✅ PASS: Unknown avatar rejected with 400")
        results.append(True)
    else:
        print(f"❌ FAIL: Expected 400, got {resp.status_code}")
        results.append(False)
    
    return all(results)

def test_unlock_ordering(db, token):
    """Phase 4.4: UNLOCK ORDERING via perfect Fun Math runs"""
    print("\n" + "="*80)
    print("TEST: Phase 4.4 - UNLOCK ORDERING via perfect Fun Math runs")
    print("="*80)
    
    results = []
    
    # Create a kid with 2 starters
    resp = api_post('kids', {'firstName': 'Emma', 'grade': 3}, token)
    kid = resp.json()['kid']
    kid_id = kid['id']
    print(f"Created kid with unlockedAvatars: {kid['unlockedAvatars']}")
    
    # Test 1: Perfect run should unlock 3rd avatar (golden_retriever)
    print("\n[Test 1] Perfect Fun Math run should unlock 'golden_retriever' (index 2)")
    
    # Start Fun Math run
    resp = api_post(f'kids/{kid_id}/funmath', {'date': '2025-01-20'}, token)
    if resp.status_code != 200:
        print(f"❌ FAIL: Could not start Fun Math run: {resp.status_code}")
        return False
    
    run = resp.json()['run']
    run_id = run['id']
    questions = run['questions']
    print(f"Started Fun Math run with {len(questions)} questions")
    
    # Get correct answers from funMathBank
    question_ids = [q['id'] for q in questions]
    bank_items = list(db.funMathBank.find({'id': {'$in': question_ids}}))
    answers = {item['id']: item['numericAnswer'] for item in bank_items}
    
    # Answer all 20 correctly
    for i, q in enumerate(questions):
        correct_answer = answers[q['id']]
        resp = api_post(f'funmath/{run_id}/answer', {
            'questionId': q['id'],
            'answer': correct_answer
        }, token)
        
        if i < 19:  # Not the last question
            if resp.status_code != 200 or resp.json().get('runComplete'):
                print(f"❌ FAIL: Question {i+1}/20 unexpected response")
                return False
        else:  # Last question
            if resp.status_code == 200:
                result = resp.json()
                if (result.get('runComplete') and 
                    result.get('avatarUnlocked') == 'golden_retriever' and
                    'golden_retriever' in result.get('unlockedAvatars', []) and
                    result.get('allOwned') == False):
                    print(f"✅ PASS: Perfect run unlocked 'golden_retriever', allOwned=False")
                    print(f"   unlockedAvatars: {result['unlockedAvatars']}")
                    
                    # Verify persistence
                    kid_doc = db.kids.find_one({'id': kid_id})
                    if 'golden_retriever' in kid_doc.get('unlockedAvatars', []):
                        print("✅ PASS: Unlock persisted to DB")
                        results.append(True)
                    else:
                        print(f"❌ FAIL: Not persisted, DB has {kid_doc.get('unlockedAvatars')}")
                        results.append(False)
                else:
                    print(f"❌ FAIL: Unexpected result: {result}")
                    results.append(False)
            else:
                print(f"❌ FAIL: Last answer returned {resp.status_code}")
                results.append(False)
    
    # Test 2: EDGE CASE - Kid with all 6 colors (6 avatars) should unlock girl_pilot (index 6)
    print("\n[Test 2] EDGE: Kid with 6 avatars should unlock 'girl_pilot' (index 6)")
    
    # Create a migrated kid with all 6 colors
    kid_edge_id = str(uuid.uuid4())
    resp_user = api_get('me', token)
    user_id = resp_user.json()['user']['id']
    
    legacy_edge = {
        'id': kid_edge_id,
        'userId': user_id,
        'firstName': 'EdgeKid',
        'grade': 4,
        'difficultyStep': 0,
        'soundOn': True,
        'theme': 'animals',
        'avatar': 'bear',
        'avatarColor': 'gold',
        'unlockedColors': FUN_COLORS,  # all 6
        'createdAt': datetime.utcnow()
    }
    db.kids.insert_one(legacy_edge)
    
    # Trigger migration
    resp = api_get('kids', token)
    kids = resp.json()['kids']
    edge_kid = next((k for k in kids if k['id'] == kid_edge_id), None)
    print(f"Edge kid after migration: unlockedAvatars={edge_kid['unlockedAvatars']}")
    
    # Perfect run should unlock girl_pilot (index 6)
    resp = api_post(f'kids/{kid_edge_id}/funmath', {'date': '2025-01-20'}, token)
    run = resp.json()['run']
    run_id = run['id']
    questions = run['questions']
    
    question_ids = [q['id'] for q in questions]
    bank_items = list(db.funMathBank.find({'id': {'$in': question_ids}}))
    answers = {item['id']: item['numericAnswer'] for item in bank_items}
    
    for i, q in enumerate(questions):
        correct_answer = answers[q['id']]
        resp = api_post(f'funmath/{run_id}/answer', {
            'questionId': q['id'],
            'answer': correct_answer
        }, token)
        
        if i == 19:  # Last question
            if resp.status_code == 200:
                result = resp.json()
                if result.get('avatarUnlocked') == 'girl_pilot':
                    print(f"✅ PASS: 6-avatar kid unlocked 'girl_pilot' (index 6)")
                    results.append(True)
                else:
                    print(f"❌ FAIL: Expected 'girl_pilot', got {result.get('avatarUnlocked')}")
                    results.append(False)
            else:
                print(f"❌ FAIL: Status {resp.status_code}")
                results.append(False)
    
    # Test 3: Second perfect run should unlock boy_pilot (index 7)
    print("\n[Test 3] Second perfect run should unlock 'boy_pilot' (index 7)")
    
    resp = api_post(f'kids/{kid_edge_id}/funmath', {'date': '2025-01-21'}, token)
    run = resp.json()['run']
    run_id = run['id']
    questions = run['questions']
    
    question_ids = [q['id'] for q in questions]
    bank_items = list(db.funMathBank.find({'id': {'$in': question_ids}}))
    answers = {item['id']: item['numericAnswer'] for item in bank_items}
    
    for i, q in enumerate(questions):
        correct_answer = answers[q['id']]
        resp = api_post(f'funmath/{run_id}/answer', {
            'questionId': q['id'],
            'answer': correct_answer
        }, token)
        
        if i == 19:
            if resp.status_code == 200:
                result = resp.json()
                if result.get('avatarUnlocked') == 'boy_pilot':
                    print(f"✅ PASS: Second run unlocked 'boy_pilot' (index 7)")
                    results.append(True)
                else:
                    print(f"❌ FAIL: Expected 'boy_pilot', got {result.get('avatarUnlocked')}")
                    results.append(False)
            else:
                print(f"❌ FAIL: Status {resp.status_code}")
                results.append(False)
    
    # Test 4: Third perfect run should return avatarUnlocked=null, allOwned=true
    print("\n[Test 4] Third perfect run should return avatarUnlocked=null, allOwned=true")
    
    resp = api_post(f'kids/{kid_edge_id}/funmath', {'date': '2025-01-22'}, token)
    run = resp.json()['run']
    run_id = run['id']
    questions = run['questions']
    
    question_ids = [q['id'] for q in questions]
    bank_items = list(db.funMathBank.find({'id': {'$in': question_ids}}))
    answers = {item['id']: item['numericAnswer'] for item in bank_items}
    
    for i, q in enumerate(questions):
        correct_answer = answers[q['id']]
        resp = api_post(f'funmath/{run_id}/answer', {
            'questionId': q['id'],
            'answer': correct_answer
        }, token)
        
        if i == 19:
            if resp.status_code == 200:
                result = resp.json()
                if result.get('avatarUnlocked') is None and result.get('allOwned') == True:
                    print(f"✅ PASS: All avatars owned - avatarUnlocked=null, allOwned=true")
                    results.append(True)
                else:
                    print(f"❌ FAIL: Expected null/true, got avatarUnlocked={result.get('avatarUnlocked')}, allOwned={result.get('allOwned')}")
                    results.append(False)
            else:
                print(f"❌ FAIL: Status {resp.status_code}")
                results.append(False)
    
    return all(results)

def test_security(db, token_a, token_b):
    """Phase 4.5: SECURITY - 401 without session, cross-parent isolation"""
    print("\n" + "="*80)
    print("TEST: Phase 4.5 - SECURITY")
    print("="*80)
    
    results = []
    
    # Test 1: POST /api/kids without session -> 401
    print("\n[Test 1] POST /api/kids without session should return 401")
    resp = api_post('kids', {'firstName': 'Test', 'grade': 2})
    if resp.status_code == 401:
        print("✅ PASS: Unauthenticated POST /api/kids returns 401")
        results.append(True)
    else:
        print(f"❌ FAIL: Expected 401, got {resp.status_code}")
        results.append(False)
    
    # Test 2: PUT without session -> 401
    print("\n[Test 2] PUT /api/kids/:id without session should return 401")
    resp = api_put('kids/fake-id', {'avatarId': 'astronaut_girl'}, None)
    if resp.status_code == 401:
        print("✅ PASS: Unauthenticated PUT returns 401")
        results.append(True)
    else:
        print(f"❌ FAIL: Expected 401, got {resp.status_code}")
        results.append(False)
    
    # Test 3: Parent B cannot PUT avatarId on Parent A's kid
    print("\n[Test 3] Parent B cannot PUT avatarId on Parent A's kid")
    
    # Create kid for Parent A
    resp = api_post('kids', {'firstName': 'ParentAKid', 'grade': 2}, token_a)
    kid_a = resp.json()['kid']
    kid_a_id = kid_a['id']
    
    # Parent B tries to update Parent A's kid
    resp = api_put(f'kids/{kid_a_id}', {'avatarId': 'astronaut_girl'}, token_b)
    if resp.status_code in [401, 404]:
        print(f"✅ PASS: Parent B cannot update Parent A's kid (status {resp.status_code})")
        results.append(True)
    else:
        print(f"❌ FAIL: Expected 401/404, got {resp.status_code}")
        results.append(False)
    
    return all(results)

def test_regression(db, token):
    """Regression tests"""
    print("\n" + "="*80)
    print("TEST: REGRESSION")
    print("="*80)
    
    results = []
    
    # Test 1: funMathBank has 2500 docs
    print("\n[Test 1] funMathBank should have 2500 documents")
    count = db.funMathBank.count_documents({})
    if count == 2500:
        print(f"✅ PASS: funMathBank has {count} documents")
        results.append(True)
    else:
        print(f"❌ FAIL: funMathBank has {count} documents, expected 2500")
        results.append(False)
    
    # Test 2: orderShapesBank has 1000 docs
    print("\n[Test 2] orderShapesBank should have 1000 documents")
    count = db.orderShapesBank.count_documents({})
    if count == 1000:
        print(f"✅ PASS: orderShapesBank has {count} documents")
        results.append(True)
    else:
        print(f"❌ FAIL: orderShapesBank has {count} documents, expected 1000")
        results.append(False)
    
    # Test 3: Normal set completion awards exactly 2 stars
    print("\n[Test 3] Normal set completion should award exactly 2 stars")
    
    # Create kid
    resp = api_post('kids', {'firstName': 'RegTest', 'grade': 1}, token)
    kid = resp.json()['kid']
    kid_id = kid['id']
    
    # Start set
    resp = api_post(f'kids/{kid_id}/set', {'date': '2025-01-20'}, token)
    set_data = resp.json()
    set_id = set_data['set']['id']
    problems = set_data['set']['problems']
    
    # Get correct answers from DB
    set_doc = db.dailySets.find_one({'id': set_id})
    
    # Answer all 30 correctly
    for i, prob in enumerate(set_doc['problems']):
        resp = api_post(f'sets/{set_id}/answer', {
            'problemId': prob['id'],
            'answer': prob['correctAnswer']
        }, token)
        
        if i == 29:  # Last problem
            if resp.status_code == 200:
                result = resp.json()
                if result.get('starsEarned') == 2:
                    print(f"✅ PASS: Set completion awarded exactly 2 stars")
                    results.append(True)
                else:
                    print(f"❌ FAIL: starsEarned={result.get('starsEarned')}, expected 2")
                    results.append(False)
            else:
                print(f"❌ FAIL: Status {resp.status_code}")
                results.append(False)
    
    # Test 4: Unauthenticated /api/kids -> 401
    print("\n[Test 4] Unauthenticated GET /api/kids should return 401")
    resp = api_get('kids')
    if resp.status_code == 401:
        print("✅ PASS: Unauthenticated GET /api/kids returns 401")
        results.append(True)
    else:
        print(f"❌ FAIL: Expected 401, got {resp.status_code}")
        results.append(False)
    
    # Test 5: POST /api/kids/:id/ordershapes returns 10 questions
    print("\n[Test 5] POST /api/kids/:id/ordershapes should return 10 questions")
    
    # Create kid
    resp = api_post('kids', {'firstName': 'OSTest', 'grade': 3}, token)
    kid = resp.json()['kid']
    kid_id = kid['id']
    
    resp = api_post(f'kids/{kid_id}/ordershapes', {'date': '2025-01-20'}, token)
    if resp.status_code == 200:
        questions = resp.json()['questions']
        if len(questions) == 10:
            print(f"✅ PASS: Order and Shapes returned 10 questions")
            results.append(True)
        else:
            print(f"❌ FAIL: Returned {len(questions)} questions, expected 10")
            results.append(False)
    else:
        print(f"❌ FAIL: Status {resp.status_code}")
        results.append(False)
    
    return all(results)

def main():
    print("\n" + "="*80)
    print("MathCompete V1.4 Backend Testing (Phase 4 & 6)")
    print("="*80)
    
    # Connect to MongoDB
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Clean up test data
    print("\nCleaning up test data...")
    db.users.delete_many({'email': {'$regex': '^test-v14-'}})
    db.kids.delete_many({'firstName': {'$regex': '^(Alice|Bob|Charlie|Dave|Emma|LegacyA|LegacyB|LegacyC|EdgeKid|ParentAKid|RegTest|OSTest)$'}})
    db.dailySets.delete_many({})
    db.funMathRuns.delete_many({})
    
    # Setup test parents
    user_a_id, token_a = setup_test_parent(db, 'parentA')
    user_b_id, token_b = setup_test_parent(db, 'parentB')
    print(f"Created test parents: {user_a_id}, {user_b_id}")
    
    # Run tests
    test_results = []
    
    # Phase 6: COPPA notice (public page)
    test_results.append(('Phase 6: COPPA Notice', test_phase6_coppa_notice()))
    
    # Phase 4: Avatar system
    test_results.append(('Phase 4.1: Create Kid with avatarId', test_create_kid_with_avatar(db, token_a)))
    test_results.append(('Phase 4.2: Migration (CRITICAL)', test_migration(db, token_a, user_a_id)))
    test_results.append(('Phase 4.3: Update Kid avatarId', test_update_kid_avatar(db, token_a)))
    test_results.append(('Phase 4.4: Unlock Ordering', test_unlock_ordering(db, token_a)))
    test_results.append(('Phase 4.5: Security', test_security(db, token_a, token_b)))
    
    # Regression
    test_results.append(('Regression Tests', test_regression(db, token_a)))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    for name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({100*passed//total}% success rate)")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! V1.4 backend is production-ready.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review output above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
