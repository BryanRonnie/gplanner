#!/bin/bash
# Set Telegram webhook for Vercel deployment

# Configuration
BOT_TOKEN="7767903266:AAHFBVglMmnPVUs3fLr40aNtVpMEKQeGuHU"
WEBHOOK_URL="https://gplanner.vercel.app/telegram/webhook"

echo "=========================================="
echo "Setting Telegram Webhook"
echo "=========================================="
echo ""
echo "Bot Token: ${BOT_TOKEN:0:20}..."
echo "Webhook URL: $WEBHOOK_URL"
echo ""

# Set the webhook
RESPONSE=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook?url=${WEBHOOK_URL}")

echo "Response from Telegram:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# Verify the webhook was set
echo "=========================================="
echo "Verifying Webhook Configuration"
echo "=========================================="
echo ""

WEBHOOK_INFO=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo")
echo "$WEBHOOK_INFO" | python3 -m json.tool 2>/dev/null || echo "$WEBHOOK_INFO"
echo ""

# Check if webhook is set correctly
if echo "$WEBHOOK_INFO" | grep -q "$WEBHOOK_URL"; then
    echo "✅ Webhook successfully configured!"
    echo ""
    echo "Next steps:"
    echo "1. Send a message to your bot on Telegram"
    echo "2. Try commands like /help, /events, /tasks"
    echo "3. Check your Vercel logs for webhook activity"
else
    echo "❌ Webhook configuration failed or URL mismatch"
    echo "Please check the response above for errors"
fi
