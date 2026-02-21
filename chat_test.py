"""
Interactive Chat Tester
Test your WhatsApp RAG Bot by chatting directly from the terminal
"""

import requests
import json
import sys
from datetime import datetime

SERVER_URL = "http://localhost:8000/reply"

def print_colored(text, color="white", end="\n"):
    """Print colored text for better readability"""
    colors = {
        "green": "\033[92m",
        "blue": "\033[94m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "cyan": "\033[96m",
        "end": "\033[0m"
    }
    print(f"{colors.get(color, '')}{text}{colors['end']}", end=end)

def send_message(contact_id, contact_name, message):
    """Send a message to the bot and get response"""
    try:
        payload = {
            "contact_id": contact_id,
            "contact_name": contact_name,
            "message": message
        }
        
        response = requests.post(
            SERVER_URL,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            return {"error": f"HTTP {response.status_code}: {response.text}"}
            
    except requests.exceptions.ConnectionError:
        return {"error": "⚠️  Server not running! Start it with: python server/main.py"}
    except Exception as e:
        return {"error": f"Error: {str(e)}"}

def main():
    print_colored("\n" + "="*60, "cyan")
    print_colored("    🤖 WhatsApp RAG Bot - Interactive Chat Tester", "cyan")
    print_colored("="*60 + "\n", "cyan")
    
    # Get contact info
    print_colored("Who do you want to chat as?", "yellow")
    contact_id = input("Contact ID (e.g., 'harshit', 'priya'): ").strip() or "test_user"
    contact_name = input(f"Display name (default: {contact_id}): ").strip() or contact_id
    
    print_colored(f"\n✅ Chatting as: {contact_name} (ID: {contact_id})", "green")
    print_colored("📝 Type your messages below. Type 'quit' or 'exit' to stop.\n", "yellow")
    print_colored("-"*60, "cyan")
    
    # Chat loop
    message_count = 0
    
    while True:
        # Get user input
        print_colored("\nYou: ", "blue", end="")
        user_message = input().strip()
        
        if not user_message:
            continue
            
        if user_message.lower() in ['quit', 'exit', 'q', 'bye']:
            print_colored("\n👋 Goodbye! Chat ended.", "yellow")
            print_colored(f"📊 Total messages: {message_count}", "cyan")
            break
        
        # Show typing indicator
        print_colored("Bot is typing...", "cyan")
        
        # Send message
        start_time = datetime.now()
        result = send_message(contact_id, contact_name, user_message)
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # Show response
        if "error" in result:
            print_colored(f"\n❌ {result['error']}", "red")
            if "Server not running" in result['error']:
                break
        else:
            message_count += 1
            reply = result.get("reply", "No reply")
            rag_count = result.get("rag_examples_used", 0)
            response_time = result.get("response_time_ms", 0)
            
            print_colored(f"\n🤖 Bot: {reply}", "green")
            print_colored(f"   ⏱️  {response_time}ms | 📚 RAG examples: {rag_count}", "cyan")
    
    print_colored("\n" + "="*60 + "\n", "cyan")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_colored("\n\n👋 Chat interrupted. Goodbye!", "yellow")
        sys.exit(0)
