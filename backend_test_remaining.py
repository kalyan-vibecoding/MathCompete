#!/usr/bin/env python3
"""
MathCompete Backend Test Suite - Remaining Tests (5-8)
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
        
        time.sleep(1)  # Small delay
        
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
        
        # Complete the new set (solve only 10 problems to speed up)
        print("\n[5.3] Completing the new set after reset...")
        daily_set = db["dailySets"].find_one({"id": new_set_id})
        problems = daily_set["problems"]
        
        for problem in problems:
            requests.post(
                f"{BASE_URL}/sets/{new_set_id}/answer",
                json={"problemId": problem["id"], "answer": problem["correctAnswer"]},
                cookies={"mc_session": token_a},
                timeout=5
            )
        
        time.sleep(1)  # Small delay
        
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
                cookies={"mc_session": token_a},
                timeout=5
            )
        
        time.sleep(1)  # Small delay
        
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
        try:
            client.close()
            cleanup_test_data(parent_a_id, parent_b_id)
        except:
            pass
        return False
    except Exception as e:
        print(f"\n❌ TEST 5 ERROR: {e}")
        try:
            client.close()
            cleanup_test_data(parent_a_id, parent_b_id)
        except:
            pass
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
        
        time.sleep(1)
        
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
                cookies={"mc_session": token_a},
                timeout=5
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
        
        time.sleep(2)
        
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
        
        time.sleep(1)
        
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
                    cookies={"mc_session": token_a},
                    timeout=5
                )
                wrong_count += 1
            
            # Submit correct answer
            resp = requests.post(
                f"{BASE_URL}/sets/{set_data2['id']}/answer",
                json={"problemId": problem["id"], "answer": problem["correctAnswer"]},
                cookies={"mc_session": token_a},
                timeout=5
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
        try:
            client.close()
            cleanup_test_data(parent_a_id, parent_b_id)
        except:
            pass
        return False
    except Exception as e:
        print(f"\n❌ TEST 6 ERROR: {e}")
        try:
            client.close()
            cleanup_test_data(parent_a_id, parent_b_id)
        except:
            pass
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
        
        time.sleep(1)
        
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
                cookies={"mc_session": token_a},
                timeout=5
            )
        
        time.sleep(1)
        
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
        try:
            client.close()
            cleanup_test_data(parent_a_id, parent_b_id)
        except:
            pass
        return False
    except Exception as e:
        print(f"\n❌ TEST 7 ERROR: {e}")
        try:
            client.close()
            cleanup_test_data(parent_a_id, parent_b_id)
        except:
            pass
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
        
        time.sleep(1)
        
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
        try:
            client.close()
            cleanup_test_data(parent_a_id, parent_b_id)
        except:
            pass
        return False
    except Exception as e:
        print(f"\n❌ TEST 8 ERROR: {e}")
        try:
            client.close()
            cleanup_test_data(parent_a_id, parent_b_id)
        except:
            pass
        return False

def main():
    """Run remaining backend tests"""
    print("\n" + "="*80)
    print("MATHCOMPETE BACKEND TEST SUITE - REMAINING TESTS (5-8)")
    print("="*80)
    
    results = {
        "Reset": test_reset(),
        "Adaptive difficulty": test_adaptive_difficulty(),
        "Grade change": test_grade_change(),
        "Live stats": test_live_stats()
    }
    
    print("\n" + "="*80)
    print("TEST SUMMARY (Tests 5-8)")
    print("="*80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL REMAINING TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    exit(main())
