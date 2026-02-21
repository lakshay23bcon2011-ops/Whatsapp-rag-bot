# 🚀 Quick Start Guide - WhatsApp RAG Bot

Your server is now deployed! Here's what to do next:

---

## ✅ Your Deployment Info

**Server URL**: `https://whatsapp-rag-bot-w7ns.onrender.com`

**Endpoints**:
- Health Check: https://whatsapp-rag-bot-w7ns.onrender.com/health
- API Docs: https://whatsapp-rag-bot-w7ns.onrender.com/docs
- Main Reply: https://whatsapp-rag-bot-w7ns.onrender.com/reply (POST)

---

## 📋 Next Steps

### Step 1: Verify Deployment ✓

Visit in your browser: https://whatsapp-rag-bot-w7ns.onrender.com/health

You should see: `{"status":"healthy"}`

*Note: First request might take 30-60 seconds (cold start on free tier)*

---

### Step 2: Prepare Your Chat Data

You need to train the bot on your WhatsApp chat history to sound like you.

#### 2a. Export WhatsApp Chats

For each contact you want the bot to handle:
1. Open WhatsApp → Go to chat
2. Tap ⋮ (three dots) → **More** → **Export Chat**
3. Choose **Without Media**
4. Save the `.txt` file

#### 2b. Convert & Ingest

```bash
# Convert WhatsApp export to JSON
python scripts/convert_export.py "WhatsApp Chat - Harshit.txt" --your-name "You" --output chats/harshit.json

# Ingest into Supabase vector DB
python scripts/ingest.py --chat chats/harshit.json --contact "+919876543210"
```

For your existing chat export:
```bash
cd d:\bot\whatsapp-rag-bot
python scripts/convert_export.py "WhatsApp Chat - Harshit Dkd\_chat.txt" --your-name "You" --output chats/harshit.json
```

#### 2c. Create Global Style (Fallback)

```bash
# Ingest all your chats for a global style
python scripts/ingest.py --all-chats ./chats/ --global-style
```

---

### Step 3: Test the Server

Test with a sample message:

**Windows PowerShell:**
```powershell
$body = @{
    contact_id = "+919876543210"
    contact_name = "Harshit"
    message = "hey what's up?"
} | ConvertTo-Json

Invoke-WebRequest -Uri "https://whatsapp-rag-bot-w7ns.onrender.com/reply" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

**Or using Python:**
```python
import requests

response = requests.post(
    "https://whatsapp-rag-bot-w7ns.onrender.com/reply",
    json={
        "contact_id": "+919876543210",
        "contact_name": "Harshit",
        "message": "hey what's up?"
    }
)
print(response.json())
```

Expected response:
```json
{
    "reply": "arre yaar nothing much, what about you?",
    "contact_id": "+919876543210",
    "response_time_ms": 487
}
```

---

### Step 4: Build the Android App

#### 4a. Install Android Studio
Download from: https://developer.android.com/studio

#### 4b. Create New Project
1. **Empty Activity**
2. **Language**: Java
3. **Minimum SDK**: API 26 (Android 8.0)
4. **Package name**: `com.yourname.whatsappautobot`

#### 4c. Add Project Files
Copy these files into your Android Studio project:
- `android-app/WhatsAppListenerService.java` → `app/src/main/java/com/yourname/whatsappautobot/`
- `android-app/MainActivity.java` → same folder
- `android-app/activity_main.xml` → `app/src/main/res/layout/`
- Update `AndroidManifest.xml` with the provided version

#### 4d. Build APK
1. In Android Studio: **Build** → **Build APK(s)**
2. Find APK at: `app/build/outputs/apk/debug/app-debug.apk`
3. Transfer to your phone and install

---

### Step 5: Configure the App on Your Phone

1. **Install the APK** on your Android phone
2. **Open the app**
3. **Tap "Grant Notification Access"**
   - This opens Settings → Notification Access
   - Enable **"WA RAG Bot Listener"**
   - Go back to the app
4. **Enter Server URL**:
   ```
   https://whatsapp-rag-bot-w7ns.onrender.com/reply
   ```
5. **Toggle "Enable Bot" to ON**
6. **Tap "Save Settings"**

---

### Step 6: Test It! 🎉

1. Ask a friend to send you a WhatsApp message
2. Watch as the bot auto-replies in your style!
3. Check logs in Render Dashboard → Your Service → Logs

---

## 🔧 Important Configuration

### Environment Variables (Already set in Render)
Make sure these are configured in your Render dashboard:

- `GROQ_API_KEY` - from https://console.groq.com
- `SUPABASE_URL` - from your Supabase project
- `SUPABASE_KEY` - anon/public key from Supabase

### Free Tier Limitations
- **Cold starts**: 30-60 seconds on first request after 15 min inactivity
- **750 hours/month**: Enough for testing
- **Upgrade to Starter ($7/mo)** for always-on service

### Keep It Warm (Optional)
Use UptimeRobot or similar to ping every 5 minutes:
```
https://whatsapp-rag-bot-w7ns.onrender.com/health
```

---

## 📊 Monitoring & Debugging

**Check Server Health:**
```
https://whatsapp-rag-bot-w7ns.onrender.com/health
```

**View API Docs:**
```
https://whatsapp-rag-bot-w7ns.onrender.com/docs
```

**Check Render Logs:**
https://dashboard.render.com → Your Service → Logs

**Android App Logs:**
- Open Android Studio
- **View** → **Tool Windows** → **Logcat**
- Filter by tag: `WABotListener`

---

## 🐛 Troubleshooting

### Bot not replying?
- ✓ Check Notification Access is granted
- ✓ Verify "Enable Bot" toggle is ON in app
- ✓ Confirm server URL ends with `/reply`
- ✓ Check Render logs for errors

### Replies sound generic?
- ✓ Ingest more chat examples
- ✓ Check Supabase has your training data
- ✓ Customize SYSTEM_PROMPT in main.py
- ✓ Run `python scripts/ingest.py --stats`

### Server errors?
- ✓ Verify GROQ_API_KEY in Render env vars
- ✓ Check SUPABASE_URL and SUPABASE_KEY
- ✓ View logs in Render dashboard

---

## 🎯 What's Next?

1. ✅ **Train the bot** - Ingest your chat history
2. ✅ **Test the API** - Use curl/PowerShell/Python
3. ✅ **Build Android app** - Android Studio
4. ✅ **Install & configure** - On your phone
5. ✅ **Go live!** - Auto-reply to WhatsApp messages

---

**Need help?** Check the logs or ask for assistance! 🚀
