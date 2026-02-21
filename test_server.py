"""
Test Script for WhatsApp RAG Bot Server
========================================
Tests the deployed Render server with a sample message.
"""

import requests
import json
import time

# Your deployed server URL
SERVER_URL = "https://whatsapp-rag-bot-w7ns.onrender.com"

def test_health():
    """Test the health endpoint"""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=60)
        print(f"✅ Status: {response.status_code}")
        print(f"📄 Response: {response.json()}")
        return True
    except requests.exceptions.Timeout:
        print("⏱️  Timeout - Server might be cold starting (try again)")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_reply():
    """Test the reply endpoint with a sample message"""
    print("\n🔍 Testing reply endpoint...")
    
    payload = {
        "contact_id": "+919876543210",
        "contact_name": "Test User",
        "message": "hey what's up?"
    }
    
    print(f"📤 Sending: {json.dumps(payload, indent=2)}")
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{SERVER_URL}/reply",
            json=payload,
            timeout=60
        )
        elapsed = (time.time() - start_time) * 1000
        
        print(f"✅ Status: {response.status_code}")
        print(f"⏱️  Response time: {elapsed:.0f}ms")
        print(f"📄 Response: {json.dumps(response.json(), indent=2)}")
        return True
    except requests.exceptions.Timeout:
        print("⏱️  Timeout - Server might be cold starting or processing")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        if hasattr(e, 'response'):
            print(f"📄 Response text: {e.response.text}")
        return False

def test_stats():
    """Test the stats endpoint"""
    print("\n🔍 Testing stats endpoint...")
    try:
        response = requests.get(f"{SERVER_URL}/stats", timeout=30)
        print(f"✅ Status: {response.status_code}")
        print(f"📄 Response: {json.dumps(response.json(), indent=2)}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🤖 WhatsApp RAG Bot - Server Test")
    print("=" * 60)
    print(f"Server: {SERVER_URL}")
    print("=" * 60)
    
    # Note about cold starts
    print("\n⚠️  NOTE: Render free tier has cold starts.")
    print("   First request may take 30-60 seconds. Please wait...")
    print()
    
    # Test health first
    health_ok = test_health()
    
    if health_ok:
        # Test reply endpoint
        test_reply()
        
        # Test stats endpoint
        test_stats()
    else:
        print("\n⚠️  Health check failed. Server might still be starting.")
        print("   Wait a minute and run this script again.")
    
    print("\n" + "=" * 60)
    print("✨ Test complete!")
    print("=" * 60)
