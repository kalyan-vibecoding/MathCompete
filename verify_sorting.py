#!/usr/bin/env python3
"""Quick verification that Fun Math runs are sorted by difficultyTier"""

import os
import jwt
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
    payload = {
        'sub': user_id,
        'email': email,
        'role': 'parent',
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(days=30)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

# Create test parent
parent_id = str(uuid4())
parent_email = 'test_sorting@example.com'
db.users.delete_many({'email': parent_email})
db.users.insert_one({
    'id': parent_id,
    'googleId': 'test_sorting_id',
    'email': parent_email,
    'name': 'Test Sorting',
    'createdAt': datetime.utcnow()
})

token = mint_jwt(parent_id, parent_email)
cookies = {'mc_session': token}

# Create kid
kid_resp = requests.post(f"{BASE_URL}/kids", cookies=cookies, json={
    'firstName': 'SortTest',
    'grade': 3
})
kid_id = kid_resp.json()['kid']['id']

# Start Fun Math run
run_resp = requests.post(f"{BASE_URL}/kids/{kid_id}/funmath", cookies=cookies, json={
    'date': '2025-01-25'
})
run_data = run_resp.json()
question_ids = [q['id'] for q in run_data['run']['questions']]

# Get tiers from bank
bank_docs = list(db.funMathBank.find({'id': {'$in': question_ids}}))
tier_map = {doc['id']: doc['difficultyTier'] for doc in bank_docs}
tiers_in_order = [tier_map[qid] for qid in question_ids]

print("Difficulty tiers in run order:")
print(tiers_in_order)
print(f"\nIs sorted ascending? {tiers_in_order == sorted(tiers_in_order)}")

if tiers_in_order == sorted(tiers_in_order):
    print("✅ PASS: Questions are ordered by difficultyTier ascending")
else:
    print("❌ FAIL: Questions are NOT properly sorted")
    print(f"Expected: {sorted(tiers_in_order)}")
