#!/usr/bin/env python3
"""
Setup script for division bug fix test.
Creates test parent and kids in MongoDB, mints JWT token.
"""

import jwt
import time
from datetime import datetime
from pymongo import MongoClient

# Configuration
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "your_database_name"
JWT_SECRET = "64c92630d866552ea20d2ff0b04605569e9f340fdb102de797973036232c4373"

def setup_test_data():
    """Setup test parent and kids in MongoDB, return JWT token."""
    
    print("Connecting to MongoDB...")
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Insert test parent
    parent_id = "jp-parent"
    db.users.delete_many({"id": parent_id})
    
    parent_doc = {
        "id": parent_id,
        "googleId": "jp",
        "email": "jp@test.com",
        "name": "JP",
        "createdAt": datetime.utcnow()
    }
    db.users.insert_one(parent_doc)
    print(f"✓ Inserted parent: {parent_id}")
    
    # Insert two kids (Grade 1 and Grade 3)
    kid1_id = "jp-g1"
    kid2_id = "jp-g3"
    db.kids.delete_many({"id": {"$in": [kid1_id, kid2_id]}})
    
    kid1_doc = {
        "id": kid1_id,
        "userId": parent_id,
        "firstName": "Gina",
        "grade": 1,
        "difficultyStep": 0,
        "soundOn": True,
        "theme": "animals",
        "avatar": "bear",
        "avatarColor": "sunset",
        "unlockedColors": ["sunset", "sky"],
        "createdAt": datetime.utcnow()
    }
    
    kid2_doc = {
        "id": kid2_id,
        "userId": parent_id,
        "firstName": "Theo",
        "grade": 3,
        "difficultyStep": 0,
        "soundOn": True,
        "theme": "ocean",
        "avatar": "dog",
        "avatarColor": "sky",
        "unlockedColors": ["sunset", "sky"],
        "createdAt": datetime.utcnow()
    }
    
    db.kids.insert_many([kid1_doc, kid2_doc])
    print(f"✓ Inserted Grade 1 kid: {kid1_id} (Gina)")
    print(f"✓ Inserted Grade 3 kid: {kid2_id} (Theo)")
    
    # Mint JWT token
    payload = {
        "sub": parent_id,
        "email": "jp@test.com",
        "role": "parent",
        "iat": int(time.time()),
        "exp": int(time.time()) + (30 * 24 * 60 * 60)  # 30 days
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    print(f"✓ JWT token minted")
    
    return token

if __name__ == "__main__":
    token = setup_test_data()
    print(f"\nJWT Token:\n{token}")
