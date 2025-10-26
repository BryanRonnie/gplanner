# Telegram Receiver Documentation

## Overview

The GPlanner now supports receiving messages from Telegram users in two ways:
1. **Polling**: Periodically fetch messages using the API
2. **Webhook**: Real-time message processing via webhook

## Setup

Ensure you have set these environment variables in your `env` file:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

## Features

### 1. Get Messages from a Specific User

**Endpoint**: `GET /telegram/messages`

**Parameters**:
- `user_id` (optional): Telegram user/chat ID. If not provided, uses `TELEGRAM_CHAT_ID` from env
- `limit` (optional): Maximum number of messages to retrieve (default: 10)

**Example**:
```bash
# Get messages from configured user
curl http://localhost:8000/telegram/messages

# Get messages from specific user
curl http://localhost:8000/telegram/messages?user_id=123456789&limit=20
```

**Response**:
```json
{
  "user_id": "123456789",
  "message_count": 5,
  "messages": [
    {
      "update_id": 123456,
      "message_id": 789,
      "from_user": "username",
      "from_id": 123456789,
      "chat_id": 123456789,
      "text": "Hello!",
      "date": 1635264000
    }
  ]
}
```

### 2. Get All Telegram Updates

**Endpoint**: `GET /telegram/updates`

**Parameters**:
- `offset` (optional): Identifier of the first update to return
- `limit` (optional): Number of updates to retrieve (1-100, default: 100)

**Example**:
```bash
curl http://localhost:8000/telegram/updates
```

**Response**:
```json
{
  "ok": true,
  "result": [
    {
      "update_id": 123456,
      "message": {
        "message_id": 789,
        "from": {
          "id": 123456789,
          "username": "user"
        },
        "chat": {
          "id": 123456789,
          "type": "private"
        },
        "date": 1635264000,
        "text": "Hello!"
      }
    }
  ]
}
```

### 3. Mark Messages as Read

**Endpoint**: `POST /telegram/mark_read`

**Parameters**:
- `update_id` (required): The update_id of the last processed message

**Example**:
```bash
curl -X POST "http://localhost:8000/telegram/mark_read?update_id=123456"
```

**Response**:
```json
{
  "success": true,
  "last_update_id": 123456
}
```

### 4. Webhook for Real-Time Messages

**Endpoint**: `POST /telegram/webhook`

This endpoint receives messages from Telegram in real-time when configured as a webhook.

#### Setting Up Webhook

1. **Deploy your app with a public URL**:
   - Use ngrok for local testing: `ngrok http 8000`
   - Or deploy to a cloud service (Heroku, AWS, etc.)

2. **Set the webhook**:
   ```bash
   curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=<YOUR_PUBLIC_URL>/telegram/webhook"
   ```

   Example with ngrok:
   ```bash
   curl "https://api.telegram.org/bot7767903266:AAHFBVglMmnPVUs3fLr4OaNtVpMEKQeGuHU/setWebhook?url=https://abc123.ngrok.io/telegram/webhook"
   ```

3. **Verify webhook**:
   ```bash
   curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
   ```

#### Supported Commands

When a user sends a message to your bot, the webhook automatically processes these commands:

- `/start` - Welcome message
- `/help` - Show available commands
- `/events` - Get upcoming calendar events
- `/tasks` - Get your tasks
- `/recommendations` - Get AI-powered recommendations

#### Custom Message Handling

Non-command messages are echoed back by default. You can customize this in the webhook handler in `main.py`.

## Usage Examples

### Example 1: Polling for Messages

```python
import requests

# Get messages from configured user
response = requests.get('http://localhost:8000/telegram/messages')
data = response.json()

for message in data['messages']:
    print(f"{message['from_user']}: {message['text']}")
```

### Example 2: Process and Mark Messages as Read

```python
import requests

# Get updates
response = requests.get('http://localhost:8000/telegram/updates')
updates = response.json()

if updates['ok'] and updates['result']:
    last_update_id = updates['result'][-1]['update_id']
    
    # Process messages...
    for update in updates['result']:
        if 'message' in update:
            print(f"Message: {update['message'].get('text')}")
    
    # Mark as read
    requests.post(f'http://localhost:8000/telegram/mark_read?update_id={last_update_id}')
```

### Example 3: Using Webhook with Ngrok (Local Testing)

```bash
# Terminal 1: Start your app
python main.py

# Terminal 2: Start ngrok
ngrok http 8000

# Terminal 3: Set webhook (use the ngrok URL from terminal 2)
curl "https://api.telegram.org/bot7767903266:AAHFBVglMmnPVUs3fLr4OaNtVpMEKQeGuHU/setWebhook?url=https://YOUR_NGROK_URL.ngrok.io/telegram/webhook"

# Now send messages to your bot on Telegram - they'll be processed in real-time!
```

## Architecture

### Polling vs Webhook

**Polling** (using `/telegram/messages` or `/telegram/updates`):
- ✅ Simple to set up
- ✅ No public URL required
- ✅ Good for testing
- ❌ Not real-time (need to poll periodically)
- ❌ Higher latency

**Webhook** (using `/telegram/webhook`):
- ✅ Real-time message processing
- ✅ Lower latency
- ✅ More efficient (push-based)
- ❌ Requires public URL
- ❌ More complex setup

## Security Considerations

1. **Webhook Security**: Telegram webhooks should use HTTPS in production
2. **Token Protection**: Never expose your bot token in public repositories
3. **User Verification**: Add checks to ensure only authorized users can access sensitive data
4. **Rate Limiting**: Consider implementing rate limiting for webhook endpoints

## Troubleshooting

### Messages not appearing
- Ensure `TELEGRAM_BOT_TOKEN` is correctly set
- Check that you've started a conversation with the bot
- Verify the user_id/chat_id is correct

### Webhook not working
- Verify webhook is set: `curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo`
- Check that your public URL is accessible
- Ensure your app is running and accessible at the webhook URL
- Check application logs for errors

### Commands not responding
- Verify `TELEGRAM_CHAT_ID` is set in environment
- Check that calendar_data and tasks_data are populated (run `/sync` first)
- For `/recommendations`, ensure `GEMINI_API_KEY` is set

## Advanced Usage

### Custom Command Handler

You can extend the webhook handler to support custom commands:

```python
# In the webhook endpoint, add your custom commands:
elif text == "/custom":
    # Your custom logic here
    await asyncio.to_thread(
        send_message, 
        str(chat_id), 
        "Custom response!"
    )
```

### Filtering Messages

To only process messages from specific users:

```python
# Add to webhook handler
ALLOWED_USERS = [123456789, 987654321]  # Add allowed user IDs
if message.get("from", {}).get("id") not in ALLOWED_USERS:
    return {"ok": False, "error": "Unauthorized"}
```

## API Reference Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/telegram/messages` | GET | Get messages from a specific user |
| `/telegram/updates` | GET | Get all Telegram updates |
| `/telegram/mark_read` | POST | Mark messages as read |
| `/telegram/webhook` | POST | Webhook for real-time messages |

## Next Steps

1. Test the polling endpoints to retrieve messages
2. Set up ngrok for local webhook testing
3. Deploy to production with a proper domain
4. Customize the command handlers for your needs
5. Add authentication and rate limiting for production use
