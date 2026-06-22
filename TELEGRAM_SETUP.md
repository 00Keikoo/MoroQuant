# Telegram Signal Alerts — Setup Guide

MoroQuant sends a formatted Markdown alert to Telegram every time the
scheduler generates and persists a new ML trading signal. Alerts are
**optional and non-fatal**: if Telegram is not configured, or the API is
unreachable, signal generation continues normally.

---

## 1. Create a Telegram Bot via BotFather

1. Open Telegram and search for **@BotFather** (verified blue check).
2. Send `/newbot`.
3. Choose a **name** (e.g. `MoroQuant Signals`).
4. Choose a unique **username** ending in `bot`
   (e.g. `moroquant_signals_bot`).
5. BotFather replies with an **HTTP API token** that looks like:

   ```
   123456789:ABCdefGHIjklMNOpqrsTUVwxyz-0123456789
   ```

   This is your `TELEGRAM_BOT_TOKEN`. Keep it secret.

> You can regenerate the token anytime with `/token` in BotFather.

---

## 2. Obtain your `chat_id`

The bot needs a numeric **chat id** to know where to send messages.

### For personal / group chats

1. Send **any message** to your new bot from your Telegram account
   (or add the bot to a group and send a message there).
2. Open this URL in a browser, replacing `<BOT_TOKEN>`:

   ```
   https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
   ```

3. In the JSON response, find:

   ```json
   "chat": {
     "id": 123456789,          ← this is your TELEGRAM_CHAT_ID
     "first_name": "...",
     "type": "private"
   }
   ```

   * Group chat ids are typically **negative** numbers (e.g. `-1001234567890`).
   * For private chats, the id is your user id (positive).

### For public channels

Add the bot to the channel as an **administrator** with the *Post Messages*
permission, then use the channel username as the chat id:

```
TELEGRAM_CHAT_ID=@your_channel_name
```

---

## 3. Required environment variables

Add these to your environment (or a `.env` file at the project root or in
`ml_service/`):

```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz-0123456789
TELEGRAM_CHAT_ID=123456789
```

The notifier loads `.env` automatically if [python-dotenv](https://pypi.org/project/python-dotenv/)
is installed (it is listed in `ml_service/requirements.txt`). Otherwise it
reads from the real process environment.

> **Behaviour when not configured:**
> If either variable is missing, the notifier logs a `WARNING`
> (`Telegram not configured, skipping alert`) and returns `False`. The
> scheduler is **never** interrupted.

---

## 4. Verify the integration

Run the health-check script to send a sample signal message:

```bash
cd ml_service
python ../scripts/test_telegram_notification.py
```

Expected output when configured:

```
[INFO] Sending sample Telegram signal alert...
[INFO] Telegram alert sent: BTCUSDT 1h long
Sample alert delivered successfully.
```

When not configured:

```
[WARNING] Telegram not configured, skipping alert: ...
Sample alert was NOT delivered (see warnings above).
```

In both cases the script exits `0` — it never crashes.

---

## 5. Example alert message

The message delivered to Telegram uses Markdown formatting:

```
🚨 MOROQUANT SIGNAL

Symbol: BTCUSDT
Timeframe: 1h

Direction: LONG
Confidence: 78%

MTF Alignment: AGREE
Regime: Trending

Entry: 102450
Take Profit: 105800
Stop Loss: 100900

Raw Prob: 0.69
Calibrated Prob: 0.74

Model Version:
BTCUSDT_1h_xgboost_20260621_071847.pkl

Generated:
2026-06-22 18:00 UTC
```

<!-- Screenshot placeholder: replace with an actual screenshot of the
     delivered Telegram message once configured. -->
> _Screenshot placeholder — drop a `.png` of the rendered Telegram alert
> here once your bot is live._

---

## 6. How it integrates with the scheduler

In `ml_service/scheduler.py`, inside `signal_generation_job()`, after a
signal is generated **and** persisted to the database (the DB write happens
inside `predictor.generate_signal` → `save_signal_to_db`), the scheduler
calls:

```python
send_signal_alert(signal)
```

This call is wrapped in `try/except`, and `send_signal_alert` itself never
raises. A Telegram outage or a malformed signal is logged and swallowed:

| Outcome | Log level | Scheduler impact |
| --- | --- | --- |
| Alert delivered | `INFO`  — `Telegram alert sent` | None |
| Not configured  | `WARNING` — `Telegram not configured` | None |
| Send failed     | `ERROR` — `Telegram send failed` | None |

Signal generation is therefore guaranteed to be independent of the
notification channel.
