# 🐳 Docker Deployment Guide

Your WhatsApp RAG Bot is ready for Docker!

## ✅ Files Included

- **Dockerfile** - Container image definition
- **docker-compose.yml** - Orchestration with environment variables
- **.dockerignore** - Excludes unnecessary files from build
- **.env** - Your Supabase + Groq credentials (REQUIRED)

## 🚀 Quick Start

### 1. Make sure .env exists in this directory
```bash
cd server
ls -la .env  # Should exist with your credentials
```

File should have:
```env
SUPABASE_URL=https://vlqsxvyppqltewygdliq.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
GROQ_API_KEY=gsk_your_groq_key_here
```

### 2. Build & Run with Docker Compose

```bash
cd server
docker-compose up -d
```

This will:
- ✅ Build the image (first time takes 2-3 minutes)
- ✅ Pre-download embedding model (~90MB)
- ✅ Start the server on port 8000
- ✅ Enable auto-restart on crash
- ✅ Set up health checks

### 3. Verify it's running

```bash
# Check container is running
docker-compose ps

# View logs
docker-compose logs -f whatsapp-rag-bot

# Test health endpoint
curl http://localhost:8000/health
```

## 📋 Common Commands

```bash
# Stop the container
docker-compose down

# Restart
docker-compose restart

# View logs (last 100 lines)
docker-compose logs --tail=100

# Get a shell inside the container
docker-compose exec whatsapp-rag-bot bash

# Rebuild without cache (if you changed code)
docker-compose build --no-cache
docker-compose up -d
```

## 🔧 Customization

### Change port
Edit `docker-compose.yml`:
```yaml
ports:
  - "9000:8000"  # External:Internal
```

### Add volumes (persist data)
Edit `docker-compose.yml`:
```yaml
volumes:
  - ./chats:/app/chats
  - ./logs:/app/logs
```

### Environment variables
Add to `docker-compose.yml`:
```yaml
environment:
  - SOME_VAR=value
  - ANOTHER_VAR=value
```

## ☁️ Deploy to Cloud

### Option 1: Railway.app (Easiest)
```bash
# 1. Push to GitHub
# 2. Connect GitHub repo to Railway
# 3. Set environment variables in Railway dashboard
# 4. Done! Auto-deploys on git push
```

### Option 2: Docker Hub
```bash
docker build -t yourusername/whatsapp-rag-bot .
docker push yourusername/whatsapp-rag-bot
```

### Option 3: Self-hosted VPS (DigitalOcean, Hetzner)
```bash
# On your VPS:
docker pull yourusername/whatsapp-rag-bot
docker run -p 8000:8000 \
  -e SUPABASE_URL=... \
  -e SUPABASE_KEY=... \
  -e GROQ_API_KEY=... \
  yourusername/whatsapp-rag-bot
```

## 📊 Image Size

- Base image: ~150MB
- Dependencies: ~800MB
- Embedding model (cached): ~90MB
- **Total: ~1GB**

First build takes longer due to model download. Subsequent builds are much faster due to layer caching.

## ✅ Health Check

Container automatically checks if server is healthy every 30 seconds. If it fails 3 times in a row, Docker can restart it automatically.

## 🔒 Security Notes

- ✅ Never commit `.env` to git (already in .gitignore)
- ✅ Use secrets management on production (Railway Vault, AWS Secrets, etc.)
- ✅ Don't expose `GROQ_API_KEY` anywhere public
- ✅ Consider adding authentication to `/reply` endpoint before production

## 📞 Troubleshooting

**Container won't start:**
```bash
docker-compose logs whatsapp-rag-bot
```

**Port 8000 already in use:**
```bash
# Change port in docker-compose.yml
# Or kill the process: lsof -i :8000
```

**Model download during build:**
- First build: 2-3 minutes (model downloads)
- Subsequent builds: 30-60 seconds (uses cache)

**Out of memory:**
```bash
# Increase Docker memory limit in Docker Desktop settings
# Or in docker-compose.yml add:
# deploy:
#   resources:
#     limits:
#       memory: 4G
```

---

**Your bot is production-ready! 🚀**
