"""
Simple Chat Tester - Test your WhatsApp RAG Bot
Usage: python simple_chat.py
"""

import requests
import json

SERVER_URL = "http://localhost:8000/reply"

def chat_with_bot(contact_id="test_user", contact_name="Test User"):
    """Interactive chat with the bot"""
    print("\n" + "="*60)
    print("    🤖 WhatsApp RAG Bot - Chat Tester")
    print("="*60)
    print(f"\nChatting as: {contact_name} (ID: {contact_id})")
    print("Type your messages. Type 'quit' to exit.\n")
    print("-"*60)
    
    while True:
        # Get user input
        user_message = input("\n💬 You: ").strip()
        
        if not user_message:
            continue
            
        if user_message.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Goodbye!")
            break
        
        # Send to bot
        try:
            response = requests.post(
                SERVER_URL,
                json={
                    "contact_id": contact_id,
                    "contact_name": contact_name,
                    "message": user_message
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                reply = data.get("reply", "No reply")
                rag_count = data.get("rag_examples_used", 0)
                response_time = data.get("response_time_ms", 0)
                
                print(f"🤖 Bot: {reply}")
                print(f"   ⏱️  {response_time}ms | 📚 RAG: {rag_count} examples")
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("❌ Server not running! Start it with: python server/main.py")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    # You can change these values
    contact_id = input("Contact ID (default: harshit): ").strip() or "harshit"
    contact_name = input(f"Display name (default: {contact_id}): ").strip() or contact_id
    
    chat_with_bot(contact_id, contact_name)
