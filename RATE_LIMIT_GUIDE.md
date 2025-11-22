# Rate Limit Guide - Gemini API

## Current Issue
You've hit Gemini's **200 requests/hour** limit on the free tier.

## Solutions

### Option 1: Wait for Quota Reset ⏰
- **Wait 30-60 minutes** for the hourly quota to reset
- Gemini free tier resets every hour
- Check your usage: https://ai.dev/usage?tab=rate-limit

### Option 2: Increase Delay Time ⏳
- Increase `delay_time` to **60+ seconds** in Settings
- This reduces API calls (120 requests/hour → 60 requests/hour)
- Settings → Delay Time → Set to 60-90 seconds

### Option 3: Pause + Resume 🧘
- Stop the session for ~10 minutes to let the quota catch up
- Resume by clicking “Start Focus Session” again

## How to Switch Models

1. **In GUI:**
   - Click "Settings" button
   - Change "Model" dropdown
   - Click "OK"

2. **In settings.json:** set `"model": "gemini-2.0-flash"` (already the default)

## Recommended Settings for Free Tier

```json
{
  "model": "gemini-2.0-flash",
  "delay_time": 60
}
```

This gives you ~60 requests/hour on the free tier.

## Need Help?

- Check API keys in `.env` file
- Verify model names are correct
- Increase delay_time if rate limits persist

