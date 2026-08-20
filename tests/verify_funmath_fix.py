#!/usr/bin/env python3
"""
Verify Fun Math ASI bug fix.
The bug: startedRef.current = true followed by IIFE was parsed as true(...) causing "true is not a function".
The fix: Prefix IIFE with leading semicolon.
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pymongo import MongoClient
import jwt

# Read environment variables
MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.getenv('DB_NAME', 'your_database_name')
JWT_SECRET = os.getenv('JWT_SECRET')
BASE_URL = os.getenv('NEXT_PUBLIC_BASE_URL', 'https://math-quest-kids-26.preview.emergentagent.com')

print(f"MONGO_URL: {MONGO_URL}")
print(f"DB_NAME: {DB_NAME}")
print(f"JWT_SECRET: {'***' if JWT_SECRET else 'NOT SET'}")
print(f"BASE_URL: {BASE_URL}")

if not JWT_SECRET:
    print("ERROR: JWT_SECRET not found in environment")
    sys.exit(1)

# Connect to MongoDB
client = MongoClient(MONGO_URL)
db = client[DB_NAME]

# Test user IDs
PARENT_ID = "fmfix-parent"
KID_ID = "fmfix-kid"

# Clean up any existing test data
print("\n=== Cleaning up existing test data ===")
db.users.delete_many({"id": PARENT_ID})
db.kids.delete_many({"id": KID_ID})
db.funMathRuns.delete_many({"kidId": KID_ID})
print("Cleanup complete")

# Insert test parent
print("\n=== Inserting test parent ===")
parent_doc = {
    "id": PARENT_ID,
    "googleId": "fmfix",
    "email": "fmfix@test.com",
    "name": "FM Fix",
    "createdAt": datetime.utcnow()
}
db.users.insert_one(parent_doc)
print(f"Inserted parent: {parent_doc}")

# Insert test kid
print("\n=== Inserting test kid ===")
kid_doc = {
    "id": KID_ID,
    "userId": PARENT_ID,
    "firstName": "Zoe",
    "grade": 2,
    "difficultyStep": 0,
    "soundOn": True,
    "theme": "ocean",
    "avatar": "dog",
    "avatarColor": "sky",
    "unlockedColors": ["sunset", "sky"],
    "createdAt": datetime.utcnow()
}
db.kids.insert_one(kid_doc)
print(f"Inserted kid: {kid_doc}")

# Mint JWT token
print("\n=== Minting JWT token ===")
now = datetime.utcnow()
exp = now + timedelta(days=30)
payload = {
    "sub": PARENT_ID,
    "email": "fmfix@test.com",
    "role": "parent",
    "iat": int(now.timestamp()),
    "exp": int(exp.timestamp())
}
token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
print(f"JWT token minted: {token[:50]}...")

print("\n=== Setup complete ===")
print(f"Parent ID: {PARENT_ID}")
print(f"Kid ID: {KID_ID}")
print(f"JWT Token: {token}")
print("\nReady for Playwright test")
