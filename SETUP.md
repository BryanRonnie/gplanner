# Quick Setup Guide

## For New Setup (Fresh Installation)

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create your environment file:**
   ```bash
   cp .env.example env
   ```

3. **Edit the `env` file and add your credentials:**
   - GEMINI_API_KEY (from Google AI Studio)
   - GOOGLE_APPLICATION_CREDENTIALS_JSON (from Google Cloud Console)
   - TELEGRAM_BOT_TOKEN (optional, from BotFather)
   - TELEGRAM_CHAT_ID (optional, your Telegram chat ID)

4. **Run the application:**
   ```bash
   python main.py
   ```

5. **Authenticate:**
   - Visit `http://localhost:8000/auth`
   - Click the returned auth_url
   - Complete Google OAuth
   - Check logs for GOOGLE_TOKEN_JSON
   - Add GOOGLE_TOKEN_JSON to your `env` file

## For Existing Setup (Migration)

If you already have `credentials.json` and `token.json`:

1. **Run the migration script:**
   ```bash
   python migrate_to_env.py
   ```

2. **Delete old files (optional):**
   ```bash
   rm credentials.json token.json
   ```

3. **Restart the application:**
   ```bash
   python main.py
   ```

## Verifying Everything Works

Test these endpoints:

```bash
# Check status
curl http://localhost:8000/status

# Get calendar events
curl http://localhost:8000/events

# Get tasks
curl http://localhost:8000/tasks

# Get AI recommendations
curl http://localhost:8000/recommendations

# Test Telegram (if configured)
curl http://localhost:8000/telegram_recommendation
```

## Common Issues

### "GOOGLE_APPLICATION_CREDENTIALS_JSON not found"
- Make sure you copied `.env.example` to `env`
- Check that your `env` file has the GOOGLE_APPLICATION_CREDENTIALS_JSON line
- Ensure the JSON is on a single line

### "TELEGRAM_BOT_TOKEN environment variable is not set"
- Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to your `env` file
- Or skip Telegram features if you don't need them

### Token expired
- Delete GOOGLE_TOKEN_JSON from `env` file
- Visit `/auth` endpoint again
- Complete authentication
- Copy new token from logs to `env` file

## Environment File Structure

Your `env` file should look like this:

```env
GEMINI_API_KEY=your_key_here
GOOGLE_APPLICATION_CREDENTIALS_JSON={"web":{"client_id":"...","client_secret":"..."}}
GOOGLE_TOKEN_JSON={"token":"...","refresh_token":"...","scopes":[...]}
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

All values should be on a single line with no line breaks in the JSON strings.
