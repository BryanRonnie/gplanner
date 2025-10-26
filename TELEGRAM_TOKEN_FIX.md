# 🚨 Telegram Bot Token Issue - Action Required

## Error

```
ERROR:telegram_sender:Failed to send Telegram message chunk: 401 {"ok":false,"error_code":401,"description":"Unauthorized"}
```

## Problem

Your Telegram bot token is **invalid or revoked**. This means:
- The token has expired
- The token was revoked/regenerated
- The token is incorrect

## ✅ Solution: Get a New Bot Token

### Option 1: Create a New Bot (Recommended)

1. **Open Telegram** and search for `@BotFather`

2. **Send this command**:
   ```
   /newbot
   ```

3. **Follow the prompts**:
   - Bot name: `GPlanner Bot` (or any name you like)
   - Bot username: Must end with 'bot', e.g., `gplanner_yourname_bot`

4. **Copy the token** BotFather gives you

5. **Update your `.env` file**:
   ```env
   TELEGRAM_BOT_TOKEN=YOUR_NEW_TOKEN_HERE
   ```

### Option 2: Regenerate Existing Bot Token

1. **Open Telegram** and find `@BotFather`

2. **Send**:
   ```
   /mybots
   ```

3. **Select your bot** from the list

4. **Choose "API Token"**

5. **Revoke current token** and get a new one

6. **Update your `.env` file** with the new token

## 🔧 Quick Fix Steps

```bash
# 1. Get new token from @BotFather (see above)

# 2. Update .env file
nano .env  # or use your favorite editor

# 3. Update this line:
TELEGRAM_BOT_TOKEN=YOUR_NEW_TOKEN_FROM_BOTFATHER

# 4. Save and restart your app
python main.py
```

## 📱 Getting Your Chat ID (if needed)

If you also need to get your chat ID:

1. **Start a conversation** with your bot on Telegram

2. **Send any message** to the bot

3. **Run this command** (with your new token):
   ```bash
   curl "https://api.telegram.org/bot<YOUR_NEW_TOKEN>/getUpdates"
   ```

4. **Look for** `"chat":{"id":123456789}` in the response

5. **Update `.env`**:
   ```env
   TELEGRAM_CHAT_ID=123456789
   ```

## 🧪 Testing Your New Token

After updating the token, test it:

```bash
# 1. Verify environment variables
python check_env.py

# 2. Test sending a message
curl "http://localhost:8000/telegram_recommendation"

# 3. Check if message was received on Telegram
```

## 🚀 For Vercel Deployment

Don't forget to update the token in Vercel too:

1. Go to: https://vercel.com/dashboard
2. Select your project
3. Settings → Environment Variables
4. Update `TELEGRAM_BOT_TOKEN` with the new token
5. Redeploy or wait for auto-deployment

## 🔍 Troubleshooting

### Still getting 401 error?

- ✅ Double-check the token is copied correctly (no spaces)
- ✅ Make sure you're using the new token, not the old one
- ✅ Restart your application after updating `.env`
- ✅ Verify with `python check_env.py`

### Token format

A valid bot token looks like:
```
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz-1234567890
```

It has:
- Numbers before the colon
- A colon `:`
- Random alphanumeric characters after

## 📝 Current Token Status

Your current token in `.env`:
```
7767903266:AAHFBVglMmnPVUs3fLr40aNtVpMEKQeGuHU
```

This token is **INVALID** ❌

You need to get a new one from @BotFather.

---

**Next Step**: Go to @BotFather on Telegram right now and get a new token! 🤖
