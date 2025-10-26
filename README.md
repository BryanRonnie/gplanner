# GPlanner - Google Calendar & Tasks API

A FastAPI-based application that syncs Google Calendar events and Tasks, provides AI-powered recommendations using Google Gemini, and sends notifications via Telegram.

## Features

- 🔐 OAuth2 authentication with Google
- 📅 Automatic sync of Google Calendar events
- ✅ Task management with Google Tasks
- 🤖 AI-powered recommendations using Google Gemini
- 📱 Telegram notifications (send & receive)
- 💬 Interactive Telegram bot with commands
- 🔔 Real-time message webhook support
- ⏰ Scheduled hourly data synchronization
- 🔄 Manual sync endpoint

## Prerequisites

- Python 3.8+
- Google Cloud Project with Calendar and Tasks APIs enabled
- Telegram Bot (optional, for notifications)

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example env
```

Edit the `env` file with your credentials:

#### Required Variables:

- **GEMINI_API_KEY**: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
- **GOOGLE_APPLICATION_CREDENTIALS_JSON**: Your OAuth2 client credentials from Google Cloud Console
- **TELEGRAM_BOT_TOKEN**: Get from [@BotFather](https://t.me/botfather) on Telegram (optional)
- **TELEGRAM_CHAT_ID**: Your Telegram chat ID (optional)

#### Obtaining Google OAuth2 Credentials:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Calendar API and Tasks API
4. Create OAuth2 credentials (Web application)
5. Add `http://localhost:8000/auth/callback` as authorized redirect URI
6. Download the credentials JSON
7. Copy the entire JSON content and paste it as a single line in `GOOGLE_APPLICATION_CREDENTIALS_JSON`

#### Note on GOOGLE_TOKEN_JSON:

- This will be automatically generated after you authenticate
- After running `/auth` endpoint and completing authentication, check the logs
- Copy the `GOOGLE_TOKEN_JSON` value from logs and add it to your `env` file
- This persists your authentication between restarts

### 3. Run the Application

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

## Authentication Flow

1. Start the application
2. Visit `http://localhost:8000/auth` to get the authentication URL
3. Open the returned `auth_url` in your browser
4. Complete the Google OAuth2 flow
5. After successful authentication, check the application logs
6. Copy the `GOOGLE_TOKEN_JSON` value from logs
7. Add it to your `env` file for persistence

## API Endpoints

### Authentication
- `GET /auth` - Get Google OAuth2 authentication URL
- `GET /auth/callback` - OAuth2 callback endpoint (used by Google)

### Data Retrieval
- `GET /` - API information and available endpoints
- `GET /data` - Get all calendar events and tasks
- `GET /events` - Get calendar events only
- `GET /tasks` - Get tasks only
- `GET /status` - Check authentication and sync status

### Actions
- `POST /sync` - Manually trigger data synchronization
- `GET /recommendations` - Get AI-powered recommendations using Gemini
- `GET /telegram_recommendations` - Send demo message to Telegram
- `GET /telegram_recommendation` - Send single demo message to Telegram

### Telegram Receiver (New!)
- `GET /telegram/messages` - Get messages from Telegram user
- `GET /telegram/updates` - Get all Telegram updates
- `POST /telegram/mark_read` - Mark messages as read
- `POST /telegram/webhook` - Webhook for real-time Telegram messages

**See [TELEGRAM_RECEIVER.md](TELEGRAM_RECEIVER.md) for detailed documentation.**

## Project Structure

```
gplanner/
├── main.py                     # Main FastAPI application
├── telegram_sender.py          # Telegram notification handler
├── telegram_receiver.py        # Telegram message receiver (NEW)
├── test_telegram_receiver.py   # Test suite for Telegram receiver (NEW)
├── requirements.txt            # Python dependencies
├── env                         # Environment variables (DO NOT commit)
├── .env.example               # Template for environment variables
├── .gitignore                 # Git ignore rules
├── TELEGRAM_RECEIVER.md       # Telegram receiver documentation (NEW)
├── TELEGRAM_FEATURE_SUMMARY.md # Feature implementation summary (NEW)
├── models/                    # Data models
│   └── responses.py
└── routes/                    # API routes
    └── sync.py
```

## Optimizations Made

### 1. **Environment Variable Configuration**
   - All credentials now stored in `env` file
   - No reliance on separate `credentials.json` or `token.json` files
   - Secure credential management

### 2. **Code Improvements**
   - Removed hardcoded API keys and tokens
   - Centralized configuration via environment variables
   - Better error handling and logging
   - Cleaner separation of concerns

### 3. **Security Enhancements**
   - Updated `.gitignore` to prevent credential leaks
   - Added `.env.example` for easy setup
   - No sensitive data in source code

### 4. **Maintainability**
   - Clear documentation
   - Template files for configuration
   - Improved code organization

## Security Notes

⚠️ **Important**: Never commit your `env` file or any files containing credentials to version control!

The following files are already in `.gitignore`:
- `env`
- `.env`
- `credentials.json`
- `token.json`
- `__pycache__/`

## Troubleshooting

### Authentication Issues

If you encounter authentication problems:
1. Ensure your `GOOGLE_APPLICATION_CREDENTIALS_JSON` is correct
2. Check that redirect URI matches exactly: `http://localhost:8000/auth/callback`
3. Verify Calendar and Tasks APIs are enabled in Google Cloud Console

### Token Expiry

Tokens are automatically refreshed. If you see authentication errors:
1. Delete `GOOGLE_TOKEN_JSON` from your `env` file
2. Restart the application
3. Complete the authentication flow again

### Telegram Not Working

Ensure:
1. `TELEGRAM_BOT_TOKEN` is correctly set
2. `TELEGRAM_CHAT_ID` is your actual chat ID
3. You've started a conversation with your bot

## Development

### Running in Development Mode

```bash
uvicorn main:app --reload
```

### API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## License

This project is for personal use. Modify as needed.

## Contributing

Feel free to submit issues or pull requests for improvements!
