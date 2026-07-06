#!/usr/bin/env python3
"""
MathCompete Backend Test Suite
Tests all backend functionality per the review request.
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
PARENT_A_EMAIL = "parenta@test.com"
PARENT_B_EMAIL = "parentb@test.com"

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

def setup_test_users():
    """Insert test parents into MongoDB"""
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    users = db["users"]
    
    # Clean up existing test users
    users.delete_many({"email": {"$in": [PARENT_A_EMAIL, PARENT_B_EMAIL]}})
    
    parent_a_id = str(uuid4())
    parent_b_id = str(uuid4())
    
    users.insert_one({
        "id": parent_a_id,
        "googleId": "test-parent-a",
        "email": PARENT_A_EMAIL,
        "name": "Parent A",
        "createdAt": datetime.utcnow()
    })
    
    users.insert_one({
        "id": parent_b_id,
        "googleId": "test-parent-b",
        "email": PARENT_B_EMAIL,
        "name": "Parent B",
        "createdAt": datetime.utcnow()
    })
    
    client.close()
    return parent_a_id, parent_b_id

def cleanup_test_data(parent_a_id, parent_b_id):
    """Clean up test data from MongoDB"""
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Get all kids for both parents
    kids = db["kids"]
    parent_kids = list(kids.find({"userId": {"$in": [parent_a_id, parent_b_id]}}))
    kid_ids = [k["id"] for k in parent_kids]
    
    # Delete daily sets for these kids
    db["dailySets"].delete_many({"kidId": {"$in": kid_ids}})
    
    # Delete kids
    kids.delete_many({"userId": {"$in": [parent_a_id, parent_b_id]}})
    
    # Delete users
    db["users"].delete_many({"id": {"$in": [parent_a_id, parent_b_id]}})
    
    client.close()

def test_auth_gating():
    """Test 1: Auth gating - protected routes return 401 without session"""
    print("\n" + "="*80)
    print("TEST 1: AUTH GATING")
    print("="*80)
    
    try:
        # Test public endpoints (no auth required)
        print("\n[1.1] Testing public endpoints...")
        
        # Health check
        resp = requests.get(f"{BASE_URL}")
        assert resp.status_code == 200, f"Health check failed: {resp.status_code}"
        data = resp.json()
        assert data.get("ok") == True, "Health check should return ok:true"
        print("✅ GET /api (health) is public - 200")
        
        # Reference endpoint
        resp = requests.get(f"{BASE_URL}/reference")
        assert resp.status_code == 200, f"Reference failed: {resp.status_code}"
        data = resp.json()
        assert "encouragements" in data and "levelLabels" in data, "Reference should return encouragements and levelLabels"
        print("✅ GET /api/reference is public - 200")
        
        # Test protected endpoints without auth (should return 401)
        print("\n[1.2] Testing protected endpoints without auth...")
        
        protected_tests = [
            ("GET", f"{BASE_URL}/me"),
            ("GET", f"{BASE_URL}/kids"),
            ("POST", f"{BASE_URL}/kids", {"firstName": "Test", "grade": 3})
        ]
        
        for method, url, *body_args in protected_tests:
            body = body_args[0] if body_args else None
            if method == "GET":
                resp = requests.get(url)
            else:
                resp = requests.post(url, json=body)
            
            assert resp.status_code == 401, f"{method} {url} should return 401, got {resp.status_code}"
            print(f"✅ {method} {url.replace(BASE_URL, '')} returns 401 without auth")
        
        # Test with valid auth
        print("\n[1.3] Testing with valid auth...")
        parent_a_id, parent_b_id = setup_test_users()
        token_a = mint_jwt(parent_a_id, PARENT_A_EMAIL)
        
        resp = requests.get(f"{BASE_URL}/me", cookies={"mc_session": token_a})
        assert resp.status_code == 200, f"GET /me with auth failed: {resp.status_code}"
        data = resp.json()
        assert data["user"]["id"] == parent_a_id, "Should return correct parent"
        assert data["user"]["email"] == PARENT_A_EMAIL, "Should return correct email"
        print("✅ GET /api/me with valid auth returns 200 and correct parent")
        
        cleanup_test_data(parent_a_id, parent_b_id)
        print("\n✅ TEST 1 PASSED: Auth gating works correctly")
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST 1 FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ TEST 1 ERROR: {e}")
        return False

def test_kid_crud_and_isolation():
    """Test 2: Kid CRUD + cross-parent data isolation"""
    print("\n" + "="*80)
    print("TEST 2: KID CRUD + OWNERSHIP ISOLATION")
    print("="*80)
    
    try:
        parent_a_id, parent_b_id = setup_test_users()
        token_a = mint_jwt(parent_a_id, PARENT_A_EMAIL)
        token_b = mint_jwt(parent_b_id, PARENT_B_EMAIL)
        
        # Test kid creation with validation
        print("\n[2.1] Testing kid creation with validation...")
        
        # Valid kid creation (grade 3)
        resp = requests.post(
            f"{BASE_URL}/kids",
            json={"firstName": "Alice", "grade": 3},
            cookies={"mc_session": token_a}
        )
        assert resp.status_code == 200, f"Kid creation failed: {resp.status_code}"
        kid_a = resp.json()["kid"]
        assert kid_a["firstName"] == "Alice", "Kid name should match"
        assert kid_a["grade"] == 3, "Kid grade should match"
        assert kid_a["totalDollars"] == 0, "New kid should have 0 dollars"
        print("✅ POST /api/kids with grade 3 returns 200 and kid stats")
        
        # Invalid grade (0)
        resp = requests.post(
            f"{BASE_URL}/kids",
            json={"firstName": "Bob", "grade": 0},
            cookies={"mc_session": token_a}
        )
        assert resp.status_code == 400, f"Grade 0 should fail, got {resp.status_code}"
        print("✅ POST /api/kids with grade 0 returns 400")
        
        # Invalid grade (6)
        resp = requests.post(
            f"{BASE_URL}/kids",
            json={"firstName": "Charlie", "grade": 6},
            cookies={"mc_session": token_a}
        )
        assert resp.status_code == 400, f"Grade 6 should fail, got {resp.status_code}"
        print("✅ POST /api/kids with grade 6 returns 400")
        
        # Missing firstName
        resp = requests.post(
            f"{BASE_URL}/kids",
            json={"grade": 3},
            cookies={"mc_session": token_a}
        )
        assert resp.status_code == 400, f"Missing firstName should fail, got {resp.status_code}"
        print("✅ POST /api/kids without firstName returns 400")
        
        # Test GET /api/kids
        print("\n[2.2] Testing GET /api/kids...")
        resp = requests.get(f"{BASE_URL}/kids", cookies={"mc_session": token_a})
        assert resp.status_code == 200, f"GET /api/kids failed: {resp.status_code}"
        kids = resp.json()["kids"]
        assert len(kids) == 1, f"Parent A should have 1 kid, got {len(kids)}"
        assert kids[0]["id"] == kid_a["id"], "Should return correct kid"
        print("✅ GET /api/kids returns only Parent A's kids with computed stats")
        
        # Test cross-parent isolation
        print("\n[2.3] Testing cross-parent isolation...")
        
        # Parent B tries to update Parent A's kid
        resp = requests.put(
            f"{BASE_URL}/kids/{kid_a['id']}",
            json={"grade": 4},
            cookies={"mc_session": token_b}
        )
        assert resp.status_code == 404, f"Parent B updating Parent A's kid should fail, got {resp.status_code}"
        print("✅ Parent B cannot PUT /api/kids/<parentA_kid_id> - returns 404")
        
        # Parent B tries to start a set for Parent A's kid
        resp = requests.post(
            f"{BASE_URL}/kids/{kid_a['id']}/set",
            json={"date": "2025-01-15"},
            cookies={"mc_session": token_b}
        )
        assert resp.status_code == 404, f"Parent B starting set for Parent A's kid should fail, got {resp.status_code}"
        print("✅ Parent B cannot POST /api/kids/<parentA_kid_id>/set - returns 404")
        
        # Parent B should not see Parent A's kids
        resp = requests.get(f"{BASE_URL}/kids", cookies={"mc_session": token_b})
        assert resp.status_code == 200, f"GET /api/kids failed: {resp.status_code}"
        kids_b = resp.json()["kids"]
        assert len(kids_b) == 0, f"Parent B should have 0 kids, got {len(kids_b)}"
        print("✅ Parent B does not see Parent A's kids in GET /api/kids")
        
        cleanup_test_data(parent_a_id, parent_b_id)
        print("\n✅ TEST 2 PASSED: Kid CRUD and isolation work correctly")
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST 2 FAILED: {e}")
        cleanup_test_data(parent_a_id, parent_b_id)
        return False
    except Exception as e:
        print(f"\n❌ TEST 2 ERROR: {e}")
        cleanup_test_data(parent_a_id, parent_b_id)
        return False

def test_problem_generation():
    """Test 3: Problem generation rules per grade"""
    print("\n" + "="*80)
    print("TEST 3: PROBLEM GENERATION RULES")
    print("="*80)
    
    try:
        parent_a_id, parent_b_id = setup_test_users()
        token_a = mint_jwt(parent_a_id, PARENT_A_EMAIL)
        
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Test Grade 1 problem generation
        print("\n[3.1] Testing Grade 1 problem generation...")
        
        # Create Grade 1 kid
        resp = requests.post(
            f"{BASE_URL}/kids",
            json={"firstName": "Grade1Kid", "grade": 1},
            cookies={"mc_session": token_a}
        )
        kid1 = resp.json()["kid"]
        
        # Start a set
        resp = requests.post(
            f"{BASE_URL}/kids/{kid1['id']}/set",
            json={"date": "2025-01-15"},
            cookies={"mc_session": token_a}
        )
        assert resp.status_code == 200, f"Start set failed: {resp.status_code}"
        set_data = resp.json()["set"]
        
        # Verify 30 problems
        assert len(set_data["problems"]) == 30, f"Should have 30 problems, got {len(set_data['problems'])}"
        print("✅ Grade 1 set has exactly 30 problems")
        
        # Verify unique displays
        displays = [p["display"] for p in set_data["problems"]]
        assert len(displays) == len(set(displays)), "All problem displays should be unique"
        print("✅ All problem displays are unique")
        
        # Verify no correctAnswer in client response
        for p in set_data["problems"]:
            assert "correctAnswer" not in p, "correctAnswer should not be sent to client"
        print("✅ No correctAnswer in client response")
        
        # Get the set from DB to verify operands
        daily_set = db["dailySets"].find_one({"id": set_data["id"]})
        assert daily_set is not None, "Set should exist in DB"
        
        # Verify Grade 1 rules: only add/sub, single digit operands (<=9), no negative answers
        for p in daily_set["problems"]:
            assert p["operation"] in ["add", "sub"], f"Grade 1 should only have add/sub, got {p['operation']}"
            for operand in p["operands"]:
                assert operand <= 9, f"Grade 1 operands should be <=9, got {operand}"
            assert p["correctAnswer"] >= 0, f"Grade 1 answers should be non-negative, got {p['correctAnswer']}"
        print("✅ Grade 1: only add/sub operations, all operands <=9, no negative answers")
        
        # Test Grade 2 problem generation
        print("\n[3.2] Testing Grade 2 problem generation...")
        
        # Create Grade 2 kid
        resp = requests.post(
            f"{BASE_URL}/kids",
            json={"firstName": "Grade2Kid", "grade": 2},
            cookies={"mc_session": token_a}
        )
        kid2 = resp.json()["kid"]
        
        # Start a set
        resp = requests.post(
            f"{BASE_URL}/kids/{kid2['id']}/set",
            json={"date": "2025-01-15"},
            cookies={"mc_session": token_a}
        )
        assert resp.status_code == 200, f"Start set failed: {resp.status_code}"
        set_data2 = resp.json()["set"]
        
        # Get the set from DB
        daily_set2 = db["dailySets"].find_one({"id": set_data2["id"]})
        
        # Verify Grade 2 rules: no fraction, division always whole (no remainder)
        has_div = False
        for p in daily_set2["problems"]:
            assert p["operation"] != "fraction", "Grade 2 should not have fraction operation"
            
            if p["operation"] == "div":
                has_div = True
                dividend, divisor = p["operands"]
                assert dividend % divisor == 0, f"Grade 2 division should have no remainder: {dividend} / {divisor}"
                assert dividend <= 100, f"Grade 2 dividend should be <=100, got {dividend}"
                assert divisor <= 10, f"Grade 2 divisor should be <=10, got {divisor}"
            
            assert p["correctAnswer"] >= 0, f"Grade 2 answers should be non-negative, got {p['correctAnswer']}"
            assert isinstance(p["correctAnswer"], int), f"Grade 2 answers should be whole numbers, got {p['correctAnswer']}"
        
        print("✅ Grade 2: no fraction operation")
        if has_div:
            print("✅ Grade 2: all division problems have whole results (no remainder), dividend <=100, divisor <=10")
        
        client.close()
        cleanup_test_data(parent_a_id, parent_b_id)
        print("\n✅ TEST 3 PASSED: Problem generation rules work correctly")
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST 3 FAILED: {e}")
        client.close()
        cleanup_test_data(parent_a_id, parent_b_id)
        return False
    except Exception as e:
        print(f"\n❌ TEST 3 ERROR: {e}")
        client.close()
        cleanup_test_data(parent_a_id, parent_b_id)
        return False

def test_answer_checking_and_completion():
    """Test 4: Answer checking, completion, $2 reward, 2-set/day cap"""
    print("\n" + "="*80)
    print("TEST 4: ANSWER CHECKING, COMPLETION, $2 REWARD, 2-SET/DAY CAP")
    print("="*80)
    
    try:
        parent_a_id, parent_b_id = setup_test_users()
        token_a = mint_jwt(parent_a_id, PARENT_A_EMAIL)
        
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Create Grade 1 kid
        resp = requests.post(
            f"{BASE_URL}/kids",
            json={"firstName": "TestKid", "grade": 1},
            cookies={"mc_session": token_a}
        )
        kid = resp.json()["kid"]
        
        # Start first set
        print("\n[4.1] Starting first set...")
        resp = requests.post(
            f"{BASE_URL}/kids/{kid['id']}/set",
            json={"date": "2025-01-15"},
            cookies={"mc_session": token_a}
        )
        set_data = resp.json()["set"]
        set_id = set_data["id"]
        
        # Get correct answers from DB
        daily_set = db["dailySets"].find_one({"id": set_id})
        problems = daily_set["problems"]
        
        # Test wrong answer
        print("\n[4.2] Testing wrong answer...")
        first_problem = problems[0]
        wrong_answer = first_problem["correctAnswer"] + 999
        
        resp = requests.post(
            f"{BASE_URL}/sets/{set_id}/answer",
            json={"problemId": first_problem["id"], "answer": wrong_answer},
            cookies={"mc_session": token_a}
        )
        assert resp.status_code == 200, f"Answer submission failed: {resp.status_code}"
        result = resp.json()
        assert result["correct"] == False, "Wrong answer should return correct=false"
        assert "message" in result, "Wrong answer should have a message"
        assert result["solvedCount"] == 0, "Wrong answer should not increase solved count"
        print("✅ Wrong answer returns correct=false, message present, solved count stays 0")
        
        # Solve all 30 problems
        print("\n[4.3] Solving all 30 problems...")
        for i, problem in enumerate(problems):
            resp = requests.post(
                f"{BASE_URL}/sets/{set_id}/answer",
                json={"problemId": problem["id"], "answer": problem["correctAnswer"]},
                cookies={"mc_session": token_a}
            )
            result = resp.json()
            assert result["correct"] == True, f"Correct answer should return correct=true for problem {i+1}"
            
            if i == 29:  # Last problem
                assert result["setComplete"] == True, "Last problem should complete the set"
                assert result["dollarsEarned"] == 2, "Should earn exactly $2"
                assert result["dollarsToday"] == 2, "Today's total should be $2"
                assert result["totalDollars"] == 2, "Total dollars should be $2"
                print(f"✅ Completed set 1: dollarsEarned=2, dollarsToday=2, totalDollars=2")
        
        # Start and complete second set
        print("\n[4.4] Starting and completing second set...")
        resp = requests.post(
            f"{BASE_URL}/kids/{kid['id']}/set",
            json={"date": "2025-01-15"},
            cookies={"mc_session": token_a}
        )
        set_data2 = resp.json()["set"]
        set_id2 = set_data2["id"]
        
        daily_set2 = db["dailySets"].find_one({"id": set_id2})
        problems2 = daily_set2["problems"]
        
        for i, problem in enumerate(problems2):
            resp = requests.post(
                f"{BASE_URL}/sets/{set_id2}/answer",
                json={"problemId": problem["id"], "answer": problem["correctAnswer"]},
                cookies={"mc_session": token_a}
            )
            result = resp.json()
            
            if i == 29:  # Last problem
                assert result["setComplete"] == True, "Last problem should complete the set"
                assert result["dollarsEarned"] == 2, "Should earn exactly $2"
                assert result["dollarsToday"] == 4, "Today's total should be $4 (2 sets * $2)"
                assert result["totalDollars"] == 4, "Total dollars should be $4"
                assert result["locked"] == True, "Should be locked after 2 sets"
                print(f"✅ Completed set 2: dollarsEarned=2, dollarsToday=4, totalDollars=4, locked=true")
        
        # Try to start third set (should be locked)
        print("\n[4.5] Testing 2-set/day cap...")
        resp = requests.post(
            f"{BASE_URL}/kids/{kid['id']}/set",
            json={"date": "2025-01-15"},
            cookies={"mc_session": token_a}
        )
        assert resp.status_code == 200, f"Third set request failed: {resp.status_code}"
        result = resp.json()
        assert result.get("locked") == True, "Third set should return locked=true"
        print("✅ Third set attempt returns {locked: true}")
        
        # Verify total dollars is exactly 4
        resp = requests.get(f"{BASE_URL}/kids?date=2025-01-15", cookies={"mc_session": token_a})
        kids = resp.json()["kids"]
        assert kids[0]["totalDollars"] == 4, f"Total dollars should be exactly 4, got {kids[0]['totalDollars']}"
        print("✅ Total dollars for the day is exactly 4 (2 completed sets * $2)")
        
        client.close()
        cleanup_test_data(parent_a_id, parent_b_id)
        print("\n✅ TEST 4 PASSED: Answer checking, completion, and 2-set cap work correctly")
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST 4 FAILED: {e}")
        client.close()
        cleanup_test_data(parent_a_id, parent_b_id)
        return False
    except Exception as e:
        print(f"\n❌ TEST 4 ERROR: {e}")
        client.close()
        cleanup_test_data(parent_a_id, parent_b_id)
        return False

def test_reset():
    """Test 5: Reset produces new set, earns nothing, does not count to daily cap"""
    print("\n" + "="*80)
    print("TEST 5: RESET FUNCTIONALITY")
    print("="*80)
    
    try:
        parent_a_id, parent_b_id = setup_test_users()
        token_a = mint_jwt(parent_a_id, PARENT_A_EMAIL)
        
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Create Grade 1 kid
        resp = requests.post(
            f"{BASE_URL}/kids",
            json={"firstName": "ResetKid", "grade": 1},
            cookies={"mc_session": token_a}
        )
        kid = resp.json()["kid"]
        
        # Start a set
        print("\n[5.1] Starting a set...")
        resp = requests.post(
            f"{BASE_URL}/kids/{kid['id']}/set",
            json={"date": "2025-01-16"},
            cookies={"mc_session": token_a}
        )
        set_data = resp.json()["set"]
        old_set_id = set_data["id"]
        old_problems = [p["id"] for p in set_data["problems"]]
        
        # Reset the set
        print("\n[5.2] Resetting the set...")
        resp = requests.post(
            f"{BASE_URL}/sets/{old_set_id}/reset",
            json={"date": "2025-01-16"},
            cookies={"mc_session": token_a}
        )
        assert resp.status_code == 200, f"Reset failed: {resp.status_code}"
        new_set_data = resp.json()["set"]
        new_set_id = new_set_data["id"]
        new_problems = [p["id"] for p in new_set_data["problems"]]
        
        # Verify new set has different ID and problems
        assert new_set_id != old_set_id, "Reset should create a new set with different ID"
        assert len(new_set_data["problems"]) == 30, "New set should have 30 problems"
        assert new_problems != old_problems, "New set should have different problems"
        print("✅ Reset returns new set with 30 different problems")
        
        # Verify old set status is 'reset' in DB
        old_set_db = db["dailySets"].find_one({"id": old_set_id})
        assert old_set_db["status"] == "reset", f"Old set status should be 'reset', got {old_set_db['status']}"
        print("✅ Old set status is 'reset' in DB")
        
        # Verify no dollars awarded for reset
        resp = requests.get(f"{BASE_URL}/kids?date=2025-01-16", cookies={"mc_session": token_a})
        kids = resp.json()["kids"]
        assert kids[0]["totalDollars"] == 0, "Reset should not award dollars"
        print("✅ Reset awards no dollars")
        
        # Complete the new set
        print("\n[5.3] Completing the new set after reset...")
        daily_set = db["dailySets"].find_one({"id": new_set_id})
        problems = daily_set["problems"]
        
        for problem in problems:
            requests.post(
                f"{BASE_URL}/sets/{new_set_id}/answer",
                json={"problemId": problem["id"], "answer": problem["correctAnswer"]},
                cookies={"mc_session": token_a}
            )
        
        # Start and complete a second earning set
        print("\n[5.4] Completing second earning set...")
        resp = requests.post(
            f"{BASE_URL}/kids/{kid['id']}/set",
            json={"date": "2025-01-16"},
            cookies={"mc_session": token_a}
        )
        set_data3 = resp.json()["set"]
        
        daily_set3 = db["dailySets"].find_one({"id": set_data3["id"]})
        problems3 = daily_set3["problems"]
        
        for problem in problems3:
            requests.post(
                f"{BASE_URL}/sets/{set_data3['id']}/answer",
                json={"problemId": problem["id"], "answer": problem["correctAnswer"]},
                cookies={"mc_session": token_a}
            )
        
        # Verify kid can still complete 2 earning sets after reset
        resp = requests.get(f"{BASE_URL}/kids?date=2025-01-16", cookies={"mc_session": token_a})
        kids = resp.json()["kids"]
        assert kids[0]["totalDollars"] == 4, f"Should have $4 from 2 completed sets, got ${kids[0]['totalDollars']}"
        assert kids[0]["todayCompleted"] == 2, f"Should have 2 completed sets today, got {kids[0]['todayCompleted']}"
        print("✅ Kid can still complete 2 earning sets after reset (reset does not count toward cap)")
        
        client.close()
        cleanup_test_data(parent_a_id, parent_b_id)
        print("\n✅ TEST 5 PASSED: Reset functionality works correctly")
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST 5 FAILED: {e}")
        client.close()
        cleanup_test_data(parent_a_id, parent_b_id)
        return False
    except Exception as e:
        print(f"\n❌ TEST 5 ERROR: {e}")
        client.close()
        cleanup_test_data(parent_a_id, parent_b_id)
        return False

def test_adaptive_difficulty():
    """Test 6: Adaptive difficulty step up/down"""
    print("\n" + "="*80)
    print("TEST 6: ADAPTIVE DIFFICULTY")
    print("="*80)
    
    try:
        parent_a_id, parent_b_id = setup_test_users()
        token_a = mint_jwt(parent_a_id, PARENT_A_EMAIL)
        
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Test step up (3 consecutive perfect sets)
        print("\n[6.1] Testing difficulty step up (3 consecutive perfect sets)...")
        
        # Create Grade 2 kid
        resp = requests.post(
            f"{BASE_URL}/kids",
            json={"firstName": "StepUpKid", "grade": 2},
            cookies={"mc_session": token_a}
        )
        kid = resp.json()["kid"]
        kid_id = kid["id"]
        
        # Insert 2 prior perfect completed sets directly into DB
        for i in range(2):
            date = f"2025-01-{10+i:02d}"
            perfect_problems = []
            for j in range(30):
                perfect_problems.append({
                    "id": str(uuid4()),
                    "operation": "add",
                    "operands": [2, 3],
                    "display": f"2 + 3 (set {i+1}, prob {j+1})",
                    "correctAnswer": 5,
                    "attempts": 1,
                    "firstTryCorrect": True,
                    "solved": True
                })
            
            db["dailySets"].insert_one({
                "id": str(uuid4()),
                "kidId": kid_id,
                "date": date,
                "status": "completed",
                "difficultyStep": 0,
                "problems": perfect_problems,
                "createdAt": datetime.utcnow(),
                "completedAt": datetime.utcnow()
            })
        
        print("✅ Inserted 2 prior perfect completed sets")
        
        # Complete 3rd perfect set via API
        resp = requests.post(
            f"{BASE_URL}/kids/{kid_id}/set",
            json={"date": "2025-01-12"},
            cookies={"mc_session": token_a}
        )
        set_data = resp.json()["set"]
        
        daily_set = db["dailySets"].find_one({"id": set_data["id"]})
        problems = daily_set["problems"]
        
        # Solve all problems on first try (perfect)
        for i, problem in enumerate(problems):
            resp = requests.post(
                f"{BASE_URL}/sets/{set_data['id']}/answer",
                json={"problemId": problem["id"], "answer": problem["correctAnswer"]},
                cookies={"mc_session": token_a}
            )
            result = resp.json()
            
            if i == 29:  # Last problem
                assert result.get("levelChanged") == True, "Level should change after 3 perfect sets"
                assert result.get("levelDirection") == "up", "Level should go up"
                print(f"✅ After 3 perfect sets: levelChanged=true, levelDirection='up'")
        
        # Verify difficultyStep increased in DB
        kid_db = db["kids"].find_one({"id": kid_id})
        assert kid_db["difficultyStep"] == 1, f"difficultyStep should be 1, got {kid_db['difficultyStep']}"
        print("✅ difficultyStep increased to 1 in DB")
        
        # Test step down (3+ wrong answers)
        print("\n[6.2] Testing difficulty step down (3+ wrong answers)...")
        
        # Create another kid with difficultyStep = 2
        resp = requests.post(
            f"{BASE_URL}/kids",
            json={"firstName": "StepDownKid", "grade": 2},
            cookies={"mc_session": token_a}
        )
        kid2 = resp.json()["kid"]
        kid2_id = kid2["id"]
        
        # Set difficultyStep to 2 in DB
        db["kids"].update_one({"id": kid2_id}, {"$set": {"difficultyStep": 2}})
        
        # Start a set
        resp = requests.post(
            f"{BASE_URL}/kids/{kid2_id}/set",
            json={"date": "2025-01-15"},
            cookies={"mc_session": token_a}
        )
        set_data2 = resp.json()["set"]
        
        daily_set2 = db["dailySets"].find_one({"id": set_data2["id"]})
        problems2 = daily_set2["problems"]
        
        # Submit 3 wrong answers, then solve all
        wrong_count = 0
        for i, problem in enumerate(problems2):
            if wrong_count < 3:
                # Submit wrong answer first
                wrong_answer = problem["correctAnswer"] + 999
                requests.post(
                    f"{BASE_URL}/sets/{set_data2['id']}/answer",
                    json={"problemId": problem["id"], "answer": wrong_answer},
                    cookies={"mc_session": token_a}
                )
                wrong_count += 1
            
            # Submit correct answer
            resp = requests.post(
                f"{BASE_URL}/sets/{set_data2['id']}/answer",
                json={"problemId": problem["id"], "answer": problem["correctAnswer"]},
                cookies={"mc_session": token_a}
            )
            result = resp.json()
            
            if i == 29:  # Last problem
                assert result.get("levelDirection") == "down", "Level should go down after 3+ wrong"
                print(f"✅ After 3+ wrong answers: levelDirection='down'")
        
        # Verify difficultyStep decreased in DB
        kid2_db = db["kids"].find_one({"id": kid2_id})
        assert kid2_db["difficultyStep"] == 1, f"difficultyStep should be 1 (down from 2), got {kid2_db['difficultyStep']}"
        print("✅ difficultyStep decreased to 1 in DB")
        
        client.close()
        cleanup_test_data(parent_a_id, parent_b_id)
        print("\n✅ TEST 6 PASSED: Adaptive difficulty works correctly")
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST 6 FAILED: {e}")
        client.close()
        cleanup_test_data(parent_a_id, parent_b_id)
        return False
    except Exception as e:
        print(f"\n❌ TEST 6 ERROR: {e}")
        client.close()
        cleanup_test_data(parent_a_id, parent_b_id)
        return False

def test_grade_change():
    """Test 7: Grade change resets difficultyStep to 0, keeps dollars/history"""
    print("\n" + "="*80)
    print("TEST 7: GRADE CHANGE")
    print("="*80)
    
    try:
        parent_a_id, parent_b_id = setup_test_users()
        token_a = mint_jwt(parent_a_id, PARENT_A_EMAIL)
        
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Create kid and complete a set to earn dollars
        print("\n[7.1] Creating kid and completing a set...")
        resp = requests.post(
            f"{BASE_URL}/kids",
            json={"firstName": "GradeChangeKid", "grade": 2},
            cookies={"mc_session": token_a}
        )
        kid = resp.json()["kid"]
        kid_id = kid["id"]
        
        # Set difficultyStep to 2
        db["kids"].update_one({"id": kid_id}, {"$set": {"difficultyStep": 2}})
        
        # Complete a set to earn $2
        resp = requests.post(
            f"{BASE_URL}/kids/{kid_id}/set",
            json={"date": "2025-01-15"},
            cookies={"mc_session": token_a}
        )
        set_data = resp.json()["set"]
        
        daily_set = db["dailySets"].find_one({"id": set_data["id"]})
        problems = daily_set["problems"]
        
        for problem in problems:
            requests.post(
                f"{BASE_URL}/sets/{set_data['id']}/answer",
                json={"problemId": problem["id"], "answer": problem["correctAnswer"]},
                cookies={"mc_session": token_a}
            )
        
        # Verify kid has $2
        resp = requests.get(f"{BASE_URL}/kids", cookies={"mc_session": token_a})
        kids = resp.json()["kids"]
        assert kids[0]["totalDollars"] == 2, "Kid should have $2"
        print("✅ Kid has $2 from completed set")
        
        # Change grade to 4
        print("\n[7.2] Changing grade to 4...")
        resp = requests.put(
            f"{BASE_URL}/kids/{kid_id}",
            json={"grade": 4},
            cookies={"mc_session": token_a}
        )
        assert resp.status_code == 200, f"Grade change failed: {resp.status_code}"
        
        # Verify difficultyStep reset to 0
        kid_db = db["kids"].find_one({"id": kid_id})
        assert kid_db["difficultyStep"] == 0, f"difficultyStep should be 0, got {kid_db['difficultyStep']}"
        assert kid_db["grade"] == 4, f"grade should be 4, got {kid_db['grade']}"
        print("✅ difficultyStep reset to 0, grade updated to 4")
        
        # Verify totalDollars unchanged
        resp = requests.get(f"{BASE_URL}/kids", cookies={"mc_session": token_a})
        kids = resp.json()["kids"]
        assert kids[0]["totalDollars"] == 2, "totalDollars should remain $2"
        print("✅ totalDollars unchanged ($2)")
        
        # Verify completed sets still exist
        completed_sets = db["dailySets"].count_documents({"kidId": kid_id, "status": "completed"})
        assert completed_sets == 1, f"Should have 1 completed set, got {completed_sets}"
        print("✅ Completed sets (history) unchanged")
        
        client.close()
        cleanup_test_data(parent_a_id, parent_b_id)
        print("\n✅ TEST 7 PASSED: Grade change works correctly")
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST 7 FAILED: {e}")
        client.close()
        cleanup_test_data(parent_a_id, parent_b_id)
        return False
    except Exception as e:
        print(f"\n❌ TEST 7 ERROR: {e}")
        client.close()
        cleanup_test_data(parent_a_id, parent_b_id)
        return False

def test_live_stats():
    """Test 8: Live-computed stats (totalDollars, daysPlayed, streak)"""
    print("\n" + "="*80)
    print("TEST 8: LIVE-COMPUTED STATS")
    print("="*80)
    
    try:
        parent_a_id, parent_b_id = setup_test_users()
        token_a = mint_jwt(parent_a_id, PARENT_A_EMAIL)
        
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Create kid
        resp = requests.post(
            f"{BASE_URL}/kids",
            json={"firstName": "StatsKid", "grade": 1},
            cookies={"mc_session": token_a}
        )
        kid = resp.json()["kid"]
        kid_id = kid["id"]
        
        # Insert completed sets for different dates to test stats
        print("\n[8.1] Inserting completed sets for stats testing...")
        
        dates = ["2025-01-10", "2025-01-11", "2025-01-12", "2025-01-14"]  # Note: gap on 01-13
        for date in dates:
            for set_num in range(2):  # 2 sets per day
                problems = []
                for j in range(30):
                    problems.append({
                        "id": str(uuid4()),
                        "operation": "add",
                        "operands": [2, 3],
                        "display": f"2 + 3 ({date}, set {set_num+1}, prob {j+1})",
                        "correctAnswer": 5,
                        "attempts": 1,
                        "firstTryCorrect": True,
                        "solved": True
                    })
                
                db["dailySets"].insert_one({
                    "id": str(uuid4()),
                    "kidId": kid_id,
                    "date": date,
                    "status": "completed",
                    "difficultyStep": 0,
                    "problems": problems,
                    "createdAt": datetime.utcnow(),
                    "completedAt": datetime.utcnow()
                })
        
        # Get kid stats
        resp = requests.get(f"{BASE_URL}/kids", cookies={"mc_session": token_a})
        kids = resp.json()["kids"]
        stats = kids[0]
        
        # Verify totalDollars = completed sets * 2
        expected_dollars = 8 * 2  # 8 completed sets * $2
        assert stats["totalDollars"] == expected_dollars, f"totalDollars should be {expected_dollars}, got {stats['totalDollars']}"
        print(f"✅ totalDollars = {expected_dollars} (8 completed sets * $2)")
        
        # Verify daysPlayed = distinct dates
        expected_days = 4  # 4 distinct dates
        assert stats["daysPlayed"] == expected_days, f"daysPlayed should be {expected_days}, got {stats['daysPlayed']}"
        print(f"✅ daysPlayed = {expected_days} (distinct dates)")
        
        # Verify streak = consecutive dates ending at latest (01-14 is isolated, so streak = 1)
        # Latest date is 01-14, but 01-13 is missing, so streak should be 1
        expected_streak = 1
        assert stats["streak"] == expected_streak, f"streak should be {expected_streak}, got {stats['streak']}"
        print(f"✅ streak = {expected_streak} (01-14 is isolated due to gap on 01-13)")
        
        # Verify no stored counter fields in DB
        kid_db = db["kids"].find_one({"id": kid_id})
        assert "totalDollars" not in kid_db, "totalDollars should not be stored in kids collection"
        assert "daysPlayed" not in kid_db, "daysPlayed should not be stored in kids collection"
        assert "streak" not in kid_db, "streak should not be stored in kids collection"
        print("✅ No stored counter fields in kids collection (all computed live)")
        
        client.close()
        cleanup_test_data(parent_a_id, parent_b_id)
        print("\n✅ TEST 8 PASSED: Live-computed stats work correctly")
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST 8 FAILED: {e}")
        client.close()
        cleanup_test_data(parent_a_id, parent_b_id)
        return False
    except Exception as e:
        print(f"\n❌ TEST 8 ERROR: {e}")
        client.close()
        cleanup_test_data(parent_a_id, parent_b_id)
        return False

def main():
    """Run all backend tests"""
    print("\n" + "="*80)
    print("MATHCOMPETE BACKEND TEST SUITE")
    print("="*80)
    
    results = {
        "Auth gating": test_auth_gating(),
        "Kid CRUD + isolation": test_kid_crud_and_isolation(),
        "Problem generation": test_problem_generation(),
        "Answer checking + completion": test_answer_checking_and_completion(),
        "Reset": test_reset(),
        "Adaptive difficulty": test_adaptive_difficulty(),
        "Grade change": test_grade_change(),
        "Live stats": test_live_stats()
    }
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    exit(main())
