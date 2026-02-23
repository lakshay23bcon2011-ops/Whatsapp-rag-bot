# Deploy to Render with Docker

## Step-by-Step Instructions

### 1. Create New Web Service on Render

1. Go to **https://dashboard.render.com/**
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository: `lakshay23bcon2011-ops/Whatsapp-rag-bot`

### 2. Configure the Service

**Basic Settings:**
- **Name**: `whatsapp-rag-bot-docker` (or any name)
- **Region**: Choose closest to you (Singapore/Frankfurt/Oregon)
- **Branch**: `main`
- **Root Directory**: `server`
- **Runtime**: **Docker** ⚠️ (Important!)

**Instance Type:**
- **Free** (for testing) - 512MB RAM, spins down after inactivity
- **Starter** ($7/month) - 512MB RAM, always on (recommended for production)

### 3. Environment Variables

Click **"Advanced"** → Add these environment variables:

| Key | Value | Notes |
|-----|-------|-------|
| `GROQ_API_KEY` | `gsk_your_key_here` | Get from https://console.groq.com |
| `SUPABASE_URL` | `https://xxxxx.supabase.co` | From Supabase project settings |
| `SUPABASE_KEY` | `your_anon_key` | Supabase anon/public key |
| `PORT` | `10000` | Render sets this automatically |
| `DISABLE_RAG` | `true` | Set to `false` when you have training data |

### 4. Deploy!

1. Click **"Create Web Service"**
2. Render will:
   - Pull your repo
   - Build the Docker image (~3-5 minutes)
   - Start the container
   - Assign a public URL

### 5. Test Your Deployment

Once **"Live"** status shows:

**Check Health:**
```bash
curl https://your-app-name.onrender.com/health
```

**Test Reply:**
```bash
curl -X POST https://your-app-name.onrender.com/reply \
  -H 'Content-Type: application/json' \
  -d '{
    "contact_id": "+919876543210",
    "contact_name": "Test",
    "message": "hey whats up?"
  }'
```

Expected response:
```json
{
  "reply": "hnn bhai sab badhiya",
  "rag_examples_used": 0,
  "response_time_ms": 45
}
```

---

## Docker vs Python Runtime

### Docker Advantages:
✅ Consistent environment across local/cloud  
✅ Pre-built dependencies (faster cold starts)  
✅ Better control over system packages  
✅ Easier debugging (run same container locally)

### Docker on Free Tier:
- Build time: ~3-5 minutes (one-time)
- Cold start: ~10-15 seconds (vs 30-60s Python runtime)
- Memory: 512MB (same as Python)

---

## Local Testing (Optional)

Before deploying, test the Docker image locally:

```bash
cd server

# Build the image
docker build -t whatsapp-rag-bot .

# Run the container
docker run -p 8000:8000 \
  -e GROQ_API_KEY=your_key \
  -e SUPABASE_URL=your_url \
  -e SUPABASE_KEY=your_key \
  -e DISABLE_RAG=true \
  whatsapp-rag-bot

# Test
curl http://localhost:8000/health
```

---

## Troubleshooting

**Build fails:**
- Check Dockerfile syntax
- Verify requirements.txt is in `server/` folder
- Check Render build logs

**Container crashes:**
- Check environment variables are set
- View logs: Render Dashboard → Your Service → Logs
- Test locally with `docker run`

**502 errors:**
- Verify `PORT` env var is set
- Check Dockerfile CMD uses `${PORT:-8000}`
- Review startup logs

---

## Next Steps After Deploy

1. ✅ Get your Render URL (e.g., `https://whatsapp-rag-bot-docker-xxxx.onrender.com`)
2. ✅ Test `/health` and `/reply` endpoints
3. ✅ Update Android app with new Render URL
4. ✅ (Later) Ingest training data and set `DISABLE_RAG=false`
