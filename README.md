##🤖 AI Receptionist — Voice-Based Appointment Booking Assistant

An AI-powered voice receptionist that can answer phone calls, understand appointment requests, manage client details, check calendar availability, and book appointments automatically.
This project is designed as a lower-cost, customizable alternative to hosted AI receptionist platforms by using a custom backend with FastAPI, Twilio, WebSockets, LLM APIs, Supabase, Google Calendar, and Docker.

## 🎯 Project Overview

AI Receptionist helps businesses automate phone-based appointment handling.

Instead of manually answering every call, the system can:

- Receive incoming calls through Twilio
- Stream call audio in real time using WebSockets
- Convert speech to text
- Generate intelligent responses using an LLM
- Convert responses back to voice
- Store client and call information
- Check Google Calendar availability
- Book appointments automatically
- Track call logs, transcripts, and appointment details

This project focuses on building a practical AI voice assistant that can be extended for clinics, salons, consultants, agencies, service businesses, and appointment-based workflows.

Transform your VAPI + n8n AI receptionist into a production-ready, near-zero-cost system using open-source alternatives.

**Current Cost:** ~$50-100/month (VAPI + n8n + various services)
**New Cost:** ~$2-6/month (only Twilio telephony)
**Savings:** 95-98% cost reduction

---

---

## 🚀 Quick Start (TL;DR)

### Prerequisites:
```bash
# Install Python 3.11+
python --version

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your API keys
```

### Setup Accounts (Free Tier):
1. **Supabase** (Database) - https://supabase.com
2. **Groq** (STT + LLM fallback) - https://groq.com
3. **DeepSeek** (Primary LLM) - https://platform.deepseek.com
4. **Cartesia** (TTS) - https://cartesia.ai
5. **Twilio** (Telephony - PAID ~$1.15/mo) - https://twilio.com
6. **Google Cloud** (Calendar) - https://console.cloud.google.com
7. **Railway** (Hosting - Free tier) - https://railway.app

### Local Development:
```bash
# Run the application
python -m app.main

# In another terminal, start ngrok for Twilio webhook
ngrok http 8000

# Update Twilio webhook to ngrok URL
```

### Production Deployment:
```bash
# Option 1: Railway
railway login
railway init
railway up

# Option 2: Fly.io
flyctl launch
flyctl deploy

# Option 3: Oracle Cloud (Best free tier)
# See PART_5_DEPLOYMENT.md for detailed steps
```

---

## 💰 Cost Comparison

### Original System (VAPI + n8n):
| Component | Cost |
|-----------|------|
| VAPI | $30-50/month |
| n8n Cloud | $20/month |
| Various APIs | $10-30/month |
| **Total** | **$60-100/month** |

### New System (Open Source):
| Component | Service | Cost |
|-----------|---------|------|
| Hosting | Railway/Oracle | $0-5 |
| Database | Supabase | $0 |
| STT | Groq Whisper | $0 |
| LLM | DeepSeek | $0 |
| TTS | Cartesia | $0 |
| Calendar | Google | $0 |
| Telephony | Twilio | $1.15 + $0.005/min |
| **Total** | | **$1.15-6/month** |

**For 100 calls at 3 min each: ~$2.65/month**
**Savings: ~$97/month (97% reduction)**

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Phone Call                          │
│                         ↓                               │
│                   Twilio                                │
│                         ↓                               │
│                   WebSocket                             │
│                         ↓                               │
├─────────────────────────────────────────────────────────┤
│              FastAPI Backend                            │
│  ┌──────────────────────────────────────────────────┐  │
│  │           Voice Agent Core                        │  │
│  │  - Conversation Manager                           │  │
│  │  - State Machine                                  │  │
│  │  - Intent Detection                               │  │
│  └──────────────────────────────────────────────────┘  │
│                         ↓                               │
│  ┌──────────┬──────────┬──────────┬─────────────────┐  │
│  │   STT    │   LLM    │   TTS    │   Calendar      │  │
│  │  (Groq)  │(DeepSeek)│(Cartesia)│   (Google)      │  │
│  └──────────┴──────────┴──────────┴─────────────────┘  │
│                         ↓                               │
│                   Supabase DB                           │
│  ┌──────────┬────────────────┬──────────────────────┐  │
│  │ Clients  │  Appointments  │     Call Logs        │  │
│  └──────────┴────────────────┴──────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Key Features Implemented

### 1. **Client Management**
- Automatic client lookup by email/phone
- New client onboarding
- CRM database integration

### 2. **Appointment Booking**
- Real-time availability checking
- Google Calendar integration
- Booking confirmation via email
- Support for interior/exterior/full detailing

### 3. **Conversation Intelligence**
- Natural language understanding
- Intent detection
- Slot filling for appointment details
- Context-aware responses

### 4. **Call Handling**
- Incoming call management
- WebSocket audio streaming
- Real-time transcription
- Natural TTS responses

### 5. **Data & Analytics**
- Call logging
- Conversation transcripts
- Performance metrics
- Cost tracking


---

## 🔧 Essential Commands

### Development:
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python -m app.main

# Run with auto-reload
uvicorn app.main:app --reload

# Test webhooks locally
ngrok http 8000
```

### Testing:
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test
pytest tests/test_voice_agent.py -v
```

### Docker:
```bash
# Build image
docker build -t ai-receptionist .

# Run container
docker run -p 8000:8000 --env-file .env ai-receptionist

# Using docker-compose
docker-compose up -d
docker-compose logs -f
docker-compose down
```

### Deployment:
```bash
# Railway
railway up

# Fly.io
flyctl deploy

# Check production health
curl https://your-domain.com/health
```

---

## 🐛 Common Issues & Solutions

### Issue: WebSocket won't connect
**Solution:** Ensure your production URL uses `wss://` (not `ws://`) and that your reverse proxy is configured for WebSocket upgrade.

### Issue: Google Calendar events not creating
**Solution:** Verify OAuth scopes include Calendar API and credentials file is in correct location.

### Issue: Audio quality poor
**Solution:** Check network bandwidth, reduce TTS bitrate in config, ensure server has sufficient CPU.

### Issue: Calls timeout after 10 seconds
**Solution:** Twilio requires webhook response within 10s. Ensure TwiML is returned immediately, don't do heavy processing before responding.

### Issue: Database connection errors
**Solution:** Check Supabase credentials, verify IP allowlist if configured, ensure connection pool isn't exhausted.

---

## 📊 Monitoring & Maintenance

### Health Checks:
```bash
# Basic health
curl https://your-domain.com/health

# Readiness check
curl https://your-domain.com/health/ready

# Metrics
curl https://your-domain.com/health/metrics
```

### Log Analysis:
```bash
# View live logs
docker-compose logs -f

# Check for errors
docker-compose logs | grep ERROR

# Twilio call logs
# Check in Twilio Console → Monitor → Logs → Calls
```

### Cost Monitoring:
```bash
# Run cost estimation script
python scripts/check_costs.py

# Check Twilio usage
# Twilio Console → Monitor → Usage
```

---

## 🚀 Optimization Tips

### 1. **Reduce Latency:**
- Use streaming TTS instead of full generation
- Cache frequent responses
- Use connection pooling
- Enable HTTP/2 if possible

### 2. **Reduce Costs:**
- Use lower TTS bitrate for acceptable quality
- Optimize LLM prompts to use fewer tokens
- Batch database operations
- Use efficient query indexes

### 3. **Improve Reliability:**
- Implement retry logic for API calls
- Use circuit breakers for external services
- Set up health checks and auto-restart
- Monitor error rates

### 4. **Scale Efficiently:**
- Use horizontal scaling (multiple instances)
- Implement rate limiting
- Use background tasks for heavy operations
- Consider message queue for high volume

---

## 🎓 Learning Resources

### FastAPI:
- Official Docs: https://fastapi.tiangolo.com
- Tutorial: https://fastapi.tiangolo.com/tutorial/

### Twilio:
- Media Streams: https://www.twilio.com/docs/voice/media-streams
- TwiML: https://www.twilio.com/docs/voice/twiml

### Supabase:
- Python Client: https://supabase.com/docs/reference/python
- Database: https://supabase.com/docs/guides/database

### Google Calendar API:
- Python Quickstart: https://developers.google.com/calendar/api/quickstart/python

---

## 📞 Support

### Getting Help:
1. Check `docs/TROUBLESHOOTING.md`
2. Review logs for error messages
3. Search GitHub issues
4. Check service status pages:
   - Twilio: https://status.twilio.com
   - Supabase: https://status.supabase.com
   - Groq: https://status.groq.com

### Contributing:
- Fork the repository
- Create a feature branch
- Make your changes
- Submit a pull request

---

🎯 What I Learned

Through this project, I worked with:
FastAPI backend development
Twilio voice call webhooks
WebSocket-based real-time audio streaming
LLM-based conversation design
Speech-to-text and text-to-speech pipelines
Supabase database integration
Google Calendar API integration
Dockerized backend deployment
Secure environment variable management
Designing AI automation systems for real business use cases

---

👨‍💻 Developer
-Glen John Chazhur
-Information Technology Engineering Graduate
-Full Stack Developer focused on MERN, cloud deployment, backend APIs, and AI-powered applications.
-GitHub: Glen-C-John

---

⭐ Support
If you found this project useful or interesting, consider giving it a star.
