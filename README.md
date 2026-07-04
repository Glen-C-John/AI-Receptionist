# 🤖 AI Receptionist — Voice-Based Appointment Booking Assistant

An AI-powered voice receptionist that can answer phone calls, understand appointment requests, manage client details, check calendar availability, and book appointments automatically.

This project is designed to reduce reliance on hosted AI receptionist platforms by using a custom backend architecture with **FastAPI, Twilio, WebSockets, LLM APIs, Supabase, Google Calendar, and Docker**.

---

## 📌 Project Status

This project is currently under active development and is structured as a practical AI voice automation system for appointment-based businesses.

### Current Focus

* Voice call handling using Twilio
* Real-time audio streaming with WebSockets
* AI-powered conversation flow
* Appointment booking workflow
* Supabase-based data storage
* Google Calendar integration
* Docker-based deployment setup

### Planned Improvements

* Admin dashboard for managing calls and appointments
* SMS/email appointment confirmations
* Human handoff support
* Call analytics dashboard
* Production monitoring
* Multi-business support

---

## 🎯 Project Overview

AI Receptionist helps appointment-based businesses automate phone call handling.

Instead of manually answering every call, the system can:

* Receive incoming calls through Twilio
* Stream call audio in real time using WebSockets
* Convert speech to text
* Generate intelligent responses using an LLM
* Convert responses back to voice
* Store client and call information
* Check Google Calendar availability
* Book appointments automatically
* Track call logs, transcripts, and appointment details

This project can be extended for clinics, salons, consultants, agencies, service businesses, and other appointment-based workflows.

---

## 💡 Why This Project?

Many hosted AI receptionist platforms can become expensive when combined with workflow automation tools and third-party services.

This project explores a more customizable and cost-efficient approach by using a custom backend and low-cost API services.

### Estimated Cost Comparison

| System                                             | Estimated Monthly Cost |
| -------------------------------------------------- | ---------------------: |
| Hosted AI receptionist + workflow automation tools |          $60–100/month |
| Custom backend with Twilio and low-cost APIs       |             $2–6/month |

> Cost estimates are approximate and may vary depending on call duration, API pricing, region, provider changes, and usage volume.

---

## ✨ Key Features

### 📞 Voice Call Handling

* Incoming call support using Twilio
* Twilio webhook integration
* WebSocket-based audio streaming
* Call session management
* Call status tracking

### 🧠 AI Conversation Flow

* Speech-to-text transcription
* LLM-powered response generation
* Context-aware conversation handling
* Appointment intent detection
* Slot filling for appointment details
* Natural text-to-speech voice responses

### 📅 Appointment Booking

* Google Calendar availability checking
* Appointment creation workflow
* Date and time handling
* Booking confirmation flow
* Client appointment history support

### 🗄️ Client & Call Management

* Client lookup by phone/email
* New client onboarding support
* Supabase database integration
* Call logs and transcripts
* Appointment records
* Future analytics support

### 🐳 Deployment Ready Structure

* FastAPI backend
* Docker-based setup
* Environment variable configuration
* Health check endpoints
* Modular service-based architecture

---

## 🛠️ Tech Stack

| Category                | Technology                              |
| ----------------------- | --------------------------------------- |
| Backend                 | Python, FastAPI                         |
| Voice / Telephony       | Twilio                                  |
| Real-Time Communication | WebSockets                              |
| AI / LLM                | DeepSeek / Groq / LLM API integration   |
| Speech-to-Text          | Groq Whisper / STT API                  |
| Text-to-Speech          | Cartesia / TTS API                      |
| Database                | Supabase                                |
| Calendar                | Google Calendar API                     |
| Deployment              | Docker, Railway / Fly.io / Oracle Cloud |
| Testing                 | Pytest                                  |
| Local Webhook Testing   | ngrok                                   |

---

## 🏗️ System Architecture

```text
Incoming Phone Call
        │
        ▼
     Twilio
        │
        ▼
 WebSocket Audio Stream
        │
        ▼
 FastAPI Backend
        │
        ├── Conversation Manager
        ├── Intent Detection
        ├── Speech-to-Text
        ├── LLM Response Generation
        ├── Text-to-Speech
        ├── Supabase Database
        └── Google Calendar API
        │
        ▼
 Voice Response to Caller
```

---

## 📂 Project Structure

```text
AI-Receptionist/
│
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Environment/configuration handling
│   ├── routes/                 # API routes and webhook endpoints
│   ├── services/               # Twilio, AI, calendar, and database services
│   ├── models/                 # Data models and schemas
│   ├── utils/                  # Helper functions
│   └── websocket/              # WebSocket audio streaming logic
│
├── tests/                      # Test files
├── docs/                       # Additional documentation
├── scripts/                    # Utility scripts
├── Dockerfile                  # Docker image configuration
├── docker-compose.yml          # Docker Compose setup
├── requirements.txt            # Python dependencies
├── .env.example                # Example environment variables
├── .gitignore
└── README.md
```

---

## ⚙️ Environment Variables

Create a `.env` file in the root directory and add your configuration values.

```env
# Application
APP_NAME=AI Receptionist
APP_ENV=development
APP_PORT=8000

# Twilio
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=your_twilio_phone_number

# AI / LLM
LLM_API_KEY=your_llm_api_key
LLM_MODEL=your_model_name

# Speech Services
STT_API_KEY=your_speech_to_text_api_key
TTS_API_KEY=your_text_to_speech_api_key

# Supabase
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_service_key

# Google Calendar
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REFRESH_TOKEN=your_google_refresh_token
GOOGLE_CALENDAR_ID=your_calendar_id
```

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/Glen-C-John/AI-Receptionist.git
cd AI-Receptionist
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate
```

For Windows:

```bash
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
```

Then update `.env` with your own API keys and service credentials.

### 5. Run the FastAPI Server

```bash
uvicorn app.main:app --reload
```

The backend will run at:

```text
http://localhost:8000
```

API documentation:

```text
http://localhost:8000/docs
```

---

## 📞 Local Twilio Webhook Testing

For local development, use ngrok to expose your FastAPI server:

```bash
ngrok http 8000
```

Then update your Twilio webhook URL with the generated ngrok URL.

Example:

```text
https://your-ngrok-url.ngrok-free.app/twilio/voice
```

---

## 🐳 Run with Docker

Build the Docker image:

```bash
docker build -t ai-receptionist .
```

Run the container:

```bash
docker run -p 8000:8000 --env-file .env ai-receptionist
```

Or use Docker Compose:

```bash
docker-compose up --build
```

To stop the containers:

```bash
docker-compose down
```

---

## 🔌 Core API Endpoints

| Method | Endpoint        | Description                        |
| ------ | --------------- | ---------------------------------- |
| `GET`  | `/health`       | Check backend health               |
| `GET`  | `/health/ready` | Check service readiness            |
| `POST` | `/twilio/voice` | Handle incoming Twilio voice calls |
| `WS`   | `/ws/audio`     | Real-time audio streaming endpoint |
| `POST` | `/appointments` | Create appointment record          |
| `GET`  | `/appointments` | Fetch appointment records          |
| `GET`  | `/clients`      | Fetch client records               |
| `GET`  | `/calls`        | Fetch call logs                    |

---

## 📞 Twilio Call Flow

```text
1. Caller dials the Twilio phone number
2. Twilio forwards the call to the FastAPI webhook
3. FastAPI returns TwiML and starts the call flow
4. Audio is streamed through WebSockets
5. Caller speech is converted to text
6. The LLM generates a suitable response
7. The response is converted back into voice
8. The caller receives the AI-generated voice reply
9. Appointment details are stored in Supabase
10. Booking details are synced with Google Calendar
```

---

## 🧠 AI Conversation Example

```text
Caller:
"Hi, I want to book an appointment for tomorrow evening."

AI Receptionist:
"Sure, I can help with that. May I know your name and preferred time?"

System Flow:
1. Detects appointment booking intent
2. Extracts preferred date and time
3. Collects missing client details
4. Checks Google Calendar availability
5. Confirms the appointment
6. Stores the booking in Supabase
7. Creates the event in Google Calendar
```

---

## 🗃️ Database Design

The system can store structured records for clients, calls, and appointments.

### Clients

```text
client_id
name
phone_number
email
created_at
```

### Calls

```text
call_id
client_id
twilio_call_sid
call_status
transcript
started_at
ended_at
```

### Appointments

```text
appointment_id
client_id
title
appointment_date
appointment_time
status
google_calendar_event_id
created_at
```

---

## 🧪 Testing

Run all tests:

```bash
pytest
```

Run tests with coverage:

```bash
pytest --cov=app tests/
```

Recommended test coverage:

* Health check endpoint
* Twilio webhook response
* WebSocket connection handling
* Appointment creation logic
* Google Calendar availability check
* Supabase client storage
* LLM response formatting

---

## 📊 Monitoring

Basic health check:

```bash
curl https://your-domain.com/health
```

Readiness check:

```bash
curl https://your-domain.com/health/ready
```

View Docker logs:

```bash
docker-compose logs -f
```

Check Twilio call logs:

```text
Twilio Console → Monitor → Logs → Calls
```

---

## 🔒 Security Notes

* Validate incoming Twilio webhook requests
* Avoid logging sensitive client information
* Use HTTPS in production
* Use `wss://` for production WebSocket connections
* Restrict database access using proper Supabase policies
* Store secrets using hosting-provider environment variables

---

## 🛣️ Future Improvements

* Admin dashboard for appointments and call logs
* SMS/email appointment confirmation
* Human handoff option
* Advanced appointment rescheduling
* Call analytics and reporting
* Multi-business support
* Better fallback handling
* Production monitoring and alerting
* Rate limiting and abuse protection
* Background job queue for heavy processing

---

## 🎯 What I Learned

Through this project, I worked with:

* FastAPI backend development
* Twilio voice call webhooks
* WebSocket-based real-time audio streaming
* LLM-based conversation design
* Speech-to-text and text-to-speech pipelines
* Supabase database integration
* Google Calendar API integration
* Dockerized backend deployment
* Secure environment variable management
* Designing AI automation systems for real business use cases

---

## 👨‍💻 Developer

**Glen John Chazhur**
Information Technology Engineering Graduate
Full Stack Developer focused on MERN, cloud deployment, backend APIs, and AI-powered applications.

GitHub: [Glen-C-John](https://github.com/Glen-C-John)

---

## ⭐ Support

If you found this project useful or interesting, consider giving it a star.

