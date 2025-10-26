# Post-Migration Verification Checklist

Use this checklist to verify that the migration was successful and everything is working correctly.

## ✅ Files Check

- [ ] `env` file exists with all required variables
- [ ] `.env.example` file exists (template)
- [ ] `.gitignore` includes `env`, `credentials.json`, `token.json`
- [ ] Old `credentials.json` file deleted (optional, but recommended)
- [ ] Old `token.json` file deleted (optional, but recommended)

## ✅ Environment Variables Check

Open your `env` file and verify:

- [ ] `GEMINI_API_KEY` is set
- [ ] `GOOGLE_APPLICATION_CREDENTIALS_JSON` is set (single line JSON)
- [ ] `GOOGLE_TOKEN_JSON` is set (single line JSON)
- [ ] `TELEGRAM_BOT_TOKEN` is set (if using Telegram)
- [ ] `TELEGRAM_CHAT_ID` is set (if using Telegram)

## ✅ Application Startup Check

Start the application:

```bash
python main.py
```

Verify in the logs:
- [ ] No error about missing credentials
- [ ] "Scheduler started" message appears
- [ ] "Data sync completed" message appears
- [ ] Application starts on port 8000

## ✅ API Endpoints Check

With the application running, test each endpoint:

### Status Endpoint
```bash
curl http://localhost:8000/status
```
- [ ] Returns `"authenticated": true`
- [ ] Shows event and task counts
- [ ] Shows last sync times

### Events Endpoint
```bash
curl http://localhost:8000/events
```
- [ ] Returns calendar events (or empty list if no events)
- [ ] Shows `last_updated` timestamp

### Tasks Endpoint
```bash
curl http://localhost:8000/tasks
```
- [ ] Returns tasks (or empty list if no tasks)
- [ ] Shows `last_updated` timestamp

### Data Endpoint
```bash
curl http://localhost:8000/data
```
- [ ] Returns both events and tasks
- [ ] Shows both last updated timestamps

### Manual Sync
```bash
curl -X POST http://localhost:8000/sync
```
- [ ] Returns success message
- [ ] Updates last sync times

### Recommendations (if GEMINI_API_KEY is set)
```bash
curl http://localhost:8000/recommendations
```
- [ ] Returns AI-generated recommendations
- [ ] No error about missing API key

### Telegram Test (if configured)
```bash
curl http://localhost:8000/telegram_recommendation
```
- [ ] Returns `{"sent": true}`
- [ ] Message received in Telegram

## ✅ Code Quality Check

- [ ] No hardcoded API keys in `main.py`
- [ ] No hardcoded tokens in `telegram_sender.py`
- [ ] All sensitive values use `os.getenv()`
- [ ] `load_dotenv('env')` is called at startup

## ✅ Security Check

- [ ] `env` file is in `.gitignore`
- [ ] Old credential files deleted
- [ ] No credentials visible in `git status`
- [ ] No credentials in git history (if previously committed)

## ✅ Documentation Check

- [ ] README.md is up to date
- [ ] SETUP.md explains how to configure
- [ ] OPTIMIZATION_SUMMARY.md explains changes
- [ ] `.env.example` shows all required variables

## 🎉 Success Criteria

All checks above should pass. If any fail:

1. Review the error message
2. Check SETUP.md for troubleshooting
3. Verify your `env` file format (no line breaks in JSON)
4. Ensure all required environment variables are set

## Notes

- Token refresh happens automatically
- If you see "Error refreshing credentials", delete GOOGLE_TOKEN_JSON and re-authenticate
- Scheduler runs every hour by default
- Manual sync available via `/sync` endpoint

## Optional: Clean Up

Once everything works:

```bash
# Remove old credential files if you haven't already
rm credentials.json token.json

# Run migration script to verify (should show nothing to migrate)
python migrate_to_env.py
```

## Getting Help

If issues persist:
1. Check application logs for detailed error messages
2. Verify environment variable format (especially JSON values)
3. Ensure Google Cloud project has Calendar and Tasks APIs enabled
4. Check OAuth redirect URI matches exactly
