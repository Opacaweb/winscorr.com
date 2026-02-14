# WinScorr Complete Deployment Guide for Railway

## 🚀 Quick Start - Deploy to Railway in 15 Minutes

Your WinScorr AI-Powered Tutoring Bot is 100% ready to deploy!

---

## Part 1: Deploy the Backend API (with AI)

### Step 1: Create GitHub Repository

1. Go to GitHub.com and create a new repository named `winscorr-backend`
2. Upload all files from the `backend/` folder:
   - `app.py`
   - `ai_tutor_service.py`
   - `tutoring_service.py`
   - `fatigue_detector.py`
   - `load_questions.py`
   - `original_questions.json`
   - `schema.sql`
   - `requirements.txt`
   - `Procfile`
   - `runtime.txt`
   - `.env.example`

### Step 2: Deploy Backend to Railway

1. Go to [railway.app](https://railway.app) and sign in
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your `winscorr-backend` repository
4. Railway will automatically detect it's a Python app

### Step 3: Add PostgreSQL Database

1. In your Railway project, click "+ New"
2. Select "Database" → "Add PostgreSQL"
3. Railway will create a database and add the connection string automatically

### Step 4: Configure Environment Variables

In Railway, go to your backend service → Variables tab and add:

```
ANTHROPIC_API_KEY=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

SECRET_KEY=your-random-secret-key-here
JWT_SECRET_KEY=another-random-secret-key-here

PORT=5000
DEBUG=False
```

Railway automatically provides these database variables (no need to add):
- `DATABASE_URL` or
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`

### Step 5: Initialize Database

Once deployed, go to your Railway backend service → click "Shell" and run:

```bash
# Create tables
psql $DATABASE_URL < schema.sql

# Load the 50 original questions
python load_questions.py
```

### Step 6: Test the Backend

Your backend should now be live! Test it:

```bash
curl https://your-backend-url.railway.app/api/health
```

You should see:
```json
{
  "status": "healthy",
  "ai_enabled": true,
  "services": {
    "database": "connected",
    "ai_tutor": "active",
    "fatigue_detection": "active"
  }
}
```

---

## Part 2: Deploy the Frontend

### Step 1: Create Frontend GitHub Repository

1. Create another repository named `winscorr-frontend`
2. Upload all files from the `frontend/` folder:
   - `index.html`
   - `diagnostic.html`
   - `css/styles.css`
   - `js/api-client.js`
   - `js/diagnostic-flow.js`
   - `js/fatigue-tracker.js`
   - `js/main.js`

### Step 2: Deploy Frontend to Railway

1. In Railway, click "+ New" in your project
2. Select "Deploy from GitHub repo"
3. Choose `winscorr-frontend`
4. Railway will detect it's a static site

### Step 3: Configure Frontend

Create a `staticfile.json` in your frontend repo to tell Railway it's static:

```json
{
  "root": "."
}
```

Or create a simple `package.json`:

```json
{
  "name": "winscorr-frontend",
  "version": "1.0.0",
  "scripts": {
    "start": "python3 -m http.server $PORT"
  }
}
```

### Step 4: Update API URL in Frontend

In `frontend/js/api-client.js`, update the baseUrl:

```javascript
this.baseUrl = window.location.hostname === 'localhost' 
    ? 'http://localhost:5000/api'
    : 'https://your-backend-url.railway.app/api';  // ← Update this!
```

### Step 5: Connect Your Domain

1. In Railway → Frontend service → Settings
2. Scroll to "Domains"
3. Click "Custom Domain"
4. Enter: `winscorr.com`

### Step 6: Update Ionos DNS

Go to your Ionos dashboard and add these records:

**A Record:**
- Host: `@`
- Points to: Railway will show you the IP address

**CNAME Record:**
- Host: `www`
- Points to: `your-frontend.railway.app`

DNS propagation takes 5-60 minutes.

---

## Part 3: Final Configuration

### Enable CORS (if needed)

If frontend and backend are on different domains, ensure CORS is enabled in `app.py`:

```python
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://winscorr.com", "https://www.winscorr.com"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})
```

---

## 🎯 Testing Your Live Site

Once everything is deployed:

1. Visit `https://winscorr.com`
2. You should see the beautiful landing page
3. Click "Start Free Diagnostic"
4. Take the 20-question test
5. Get AI-powered explanations for wrong answers
6. See your fatigue analysis results

---

## 📊 What's Included

### Backend Features:
- ✅ 50 Original SSAT Middle Level math questions
- ✅ Evidence-based fatigue detection (Mann-Whitney U test)
- ✅ AI-powered explanations (Claude Sonnet 4)
- ✅ Progressive hints system
- ✅ Conversational AI tutor
- ✅ Adaptive question selection
- ✅ Concept mastery tracking (8 math concepts)
- ✅ Progress analytics

### Frontend Features:
- ✅ Beautiful, distinctive landing page
- ✅ Interactive diagnostic test
- ✅ Real-time AI help
- ✅ Fatigue analysis results
- ✅ Responsive design
- ✅ Professional UI/UX

---

## 🔧 Troubleshooting

### Backend not starting:
```bash
# Check logs in Railway
railway logs
```

### Database connection issues:
```bash
# In Railway shell, test connection
psql $DATABASE_URL -c "SELECT COUNT(*) FROM questions;"
```

Should return 50 questions.

### Frontend can't connect to backend:
- Check CORS settings in `app.py`
- Verify API URL in `api-client.js`
- Check browser console for errors

### AI not working:
- Verify `ANTHROPIC_API_KEY` in environment variables
- Check Railway logs for AI errors
- Test API key with: `curl https://api.anthropic.com/v1/messages -H "x-api-key: YOUR_KEY"`

---

## 💰 Cost Estimate

**Railway Costs:**
- Backend: ~$5/month (Hobby plan)
- Frontend: ~$5/month (Hobby plan)
- PostgreSQL: Included

**AI Costs (Claude Sonnet 4):**
- ~$0.08 per diagnostic (100 students = $8/month)
- Input: $3 per million tokens
- Output: $15 per million tokens

**Total: ~$18-20/month for 100 students**

---

## 🎉 You're Live!

Your complete AI-powered SSAT tutoring bot is now running at:
- **Frontend:** https://winscorr.com
- **Backend API:** https://your-backend.railway.app

Students can now:
1. Take the diagnostic test
2. Get AI explanations for mistakes
3. Request progressive hints
4. Chat with the AI tutor
5. See evidence-based fatigue analysis
6. Track their progress

**All powered by Claude Sonnet 4 and your custom adaptive algorithm!**

---

## 📞 Need Help?

If you encounter any issues:
1. Check Railway logs
2. Test API endpoints with curl
3. Verify environment variables
4. Check browser console for frontend errors

Your system is 100% complete and production-ready! 🚀
