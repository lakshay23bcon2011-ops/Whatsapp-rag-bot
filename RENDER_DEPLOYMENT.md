# Deploy WhatsApp RAG Bot to Render

## Quick Deployment Steps

### 1. Push Your Code to GitHub
Your code is already on GitHub at: `https://github.com/lakshay23bcon2011-ops/Whatsapp-rag-bot.git`

### 2. Create Web Service on Render

1. **Go to Render Dashboard**: https://dashboard.render.com/
2. **Click "New +"** → Select **"Web Service"**
3. **Connect your GitHub repository**: `lakshay23bcon2011-ops/Whatsapp-rag-bot`
4. **Configure the service**:
   - **Name**: `whatsapp-rag-bot` (or any name you prefer)
   - **Region**: Choose closest to you (e.g., Singapore, Frankfurt, Oregon)
   - **Branch**: `main`
   - **Root Directory**: Leave blank (or use `server` if you want)
   - **Runtime**: `Python 3`
   - **Build Command**: 
     ```
     cd server && pip install -r requirements.txt
     ```
   - **Start Command**: 
     ```
     cd server && gunicorn main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
     ```
   - **Instance Type**: `Free` (for testing) or `Starter` ($7/month for production)

### 3. Add Environment Variables

In the **Environment** section, add these three variables:

| Key | Value | Where to get it |
|-----|-------|----------------|
| `GROQ_API_KEY` | `gsk_your_key_here` | Get from https://console.groq.com |
| `SUPABASE_URL` | `https://xxxxx.supabase.co` | From your Supabase project settings |
| `SUPABASE_KEY` | `your_anon_key` | From your Supabase project settings (anon/public key) |

### 4. Deploy!

1. Click **"Create Web Service"**
2. Render will:
   - Clone your repo
   - Install dependencies (~2-3 minutes for sentence-transformers)
   - Start the server
   - Give you a public URL like: `https://whatsapp-rag-bot-xxxx.onrender.com`

### 5. Test Your Deployment

Once deployed, test with:

```bash
curl -X POST https://your-app-name.onrender.com/reply \
  -H 'Content-Type: application/json' \
  -d '{
    "contact_id": "+919876543210",
    "contact_name": "Test User",
    "message": "hey whats up?"
  }'
```

Or visit: `https://your-app-name.onrender.com/health`

### 6. Update Android App

In `android-app/WhatsAppListenerService.java`, update line 38:

```java
private static final String SERVER_URL = "https://your-app-name.onrender.com/reply";
```

---

## Important Notes

### Free Tier Limitations
- **Spins down after 15 minutes of inactivity** (first request after sleep takes ~30 seconds)
- **750 hours/month free** (enough for testing)
- Upgrade to **Starter ($7/month)** for always-on service

### Automatic Deployments
- Every `git push` to `main` branch automatically redeploys
- You can disable this in Render settings if needed

### Logs & Monitoring
- View live logs in Render Dashboard → Your Service → Logs
- Check `/health` endpoint for uptime monitoring

### Disk Storage
- Render's filesystem is **ephemeral** (resets on each deploy)
- Your Supabase database persists (it's external)
- No local ChromaDB needed since you're using Supabase pgvector

---

## Troubleshooting

**Build fails:**
- Check that `requirements.txt` is in the `server/` folder
- Verify Python version (should be 3.11 or 3.12)

**Service crashes on startup:**
- Check environment variables are set correctly
- View logs in Render dashboard
- Test Groq and Supabase keys locally first

**Slow cold starts:**
- Upgrade to Starter tier for always-on
- Or use UptimeRobot to ping `/health` every 5 minutes (keeps it warm)

---

## Next Steps

✅ Deploy to Render
✅ Test with curl or Postman
✅ Update Android app with Render URL
✅ Build APK and install on phone
✅ Start auto-replying! 🚀
