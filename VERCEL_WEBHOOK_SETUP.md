# Setting Up Telegram Webhook for Vercel Deployment

## 🚨 Current Issue

Your Telegram bot token appears to be invalid or revoked. Error: `401 Unauthorized`

## 🔧 Solution: Get a New Bot Token

### Step 1: Get a Fresh Bot Token from BotFather

1. **Open Telegram** and search for `@BotFather`

2. **Send this command**:
   ```
   /newbot
   ```
   
3. **Follow the prompts**:
   - Choose a name for your bot (e.g., "GPlanner Bot")
   - Choose a username (must end in 'bot', e.g., "gplanner_assistant_bot")

4. **Copy the token** that BotFather gives you. It looks like:
   ```
   1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
   ```

5. **Update your `.env` file** with the new token:
   ```env
   TELEGRAM_BOT_TOKEN=YOUR_NEW_TOKEN_HERE
   ```

### Step 2: Set the Webhook

Once you have a valid token, run this command (replace `YOUR_BOT_TOKEN`):

```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://gplanner.vercel.app/telegram/webhook"
```

**Example**:
```bash
curl "https://api.telegram.org/bot7767903266:AAHFBVglMmnPVUs3fLr40aNtVpMEKQeGuHU/setWebhook?url=https://gplanner.vercel.app/telegram/webhook"
```

### Step 3: Verify the Webhook

Check that it was set correctly:

```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

You should see a response like:
```json
{
  "ok": true,
  "result": {
    "url": "https://gplanner.vercel.app/telegram/webhook",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}
```

## 📝 Complete Setup Commands

Save this as a script and run it after updating your bot token:

```bash
#!/bin/bash
# setup_vercel_webhook.sh

# Your bot token (get from @BotFather)
BOT_TOKEN="YOUR_BOT_TOKEN_HERE"

# Your Vercel URL
WEBHOOK_URL="https://gplanner.vercel.app/telegram/webhook"

echo "Setting webhook..."
curl "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook?url=${WEBHOOK_URL}"

echo -e "\n\nVerifying webhook..."
curl "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"
```

## 🎯 Alternative: Use Existing Bot

If you want to keep your existing bot, you might need to:

1. **Revoke and regenerate the token** via BotFather:
   ```
   /mybots
   → Select your bot
   → Bot Settings
   → Revoke Bot Token
   → Generate New Token
   ```

2. **Update your `.env` file** with the new token

3. **Set the webhook** again using the commands above

## ✅ Testing the Webhook

Once the webhook is set:

1. **Find your bot on Telegram** (use the username you chose)

2. **Send a message**:
   ```
   /start
   ```

3. **Check Vercel logs** to see if the webhook is receiving messages:
   - Go to: https://vercel.com/dashboard
   - Select your project
   - Go to "Logs" or "Functions"

4. **Try other commands**:
   - `/help` - Show available commands
   - `/events` - Get calendar events
   - `/tasks` - Get your tasks
   - `/recommendations` - Get AI recommendations

## 🔍 Troubleshooting

### "Unauthorized" Error
- Token is invalid or revoked
- Get a new token from @BotFather

### Webhook Not Receiving Messages
- Check Vercel deployment is successful
- Verify URL is correct: `https://gplanner.vercel.app/telegram/webhook`
- Check Vercel logs for errors
- Ensure your Vercel app has the `/telegram/webhook` endpoint

### Messages Not Responding
- Check environment variables are set in Vercel:
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_CHAT_ID`
  - `GEMINI_API_KEY`
  - `GOOGLE_APPLICATION_CREDENTIALS_JSON`
  - `GOOGLE_TOKEN_JSON`

### Check Current Webhook Status

```bash
# See current webhook configuration
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getWebhookInfo"

# Remove webhook (to test polling instead)
curl "https://api.telegram.org/bot<YOUR_TOKEN>/deleteWebhook"
```

## 🚀 Quick Reference

| Action | Command |
|--------|---------|
| Set webhook | `curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=<URL>"` |
| Check webhook | `curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"` |
| Delete webhook | `curl "https://api.telegram.org/bot<TOKEN>/deleteWebhook"` |

## 📱 Environment Variables for Vercel

Make sure these are set in your Vercel project settings:

1. Go to: https://vercel.com/dashboard → Your Project → Settings → Environment Variables

2. Add these variables:
   - `TELEGRAM_BOT_TOKEN` = Your bot token
   - `TELEGRAM_CHAT_ID` = Your chat ID (6858049450)
   - `GEMINI_API_KEY` = Your Gemini API key
   - `GOOGLE_APPLICATION_CREDENTIALS_JSON` = Your Google credentials
   - `GOOGLE_TOKEN_JSON` = Your Google token

3. Redeploy after adding environment variables

## 🎉 Success Criteria

✅ Webhook set without errors
✅ `/start` command gets a response
✅ Bot responds to commands
✅ Vercel logs show incoming webhook requests
✅ No errors in Vercel function logs

---

**Note**: The bot token in your env file appears to be invalid. Please get a new token from @BotFather and try again.
