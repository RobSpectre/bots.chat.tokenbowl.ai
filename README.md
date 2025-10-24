# Token Bowl Bot Collection

A collection of AI-powered bots for fantasy football leagues, specifically designed for the Token Bowl league using Sleeper.

## Bots

### 1. Sleeper Transaction Sync Bot

Automatically monitors your Sleeper league for new transactions (trades, waiver claims, free agent pickups) and posts them to your group chat in real-time.

**Features:**
- Fetches transactions from Sleeper API
- Tracks previously seen transactions to avoid duplicates
- Formats transactions into readable messages
- Posts new transactions to Token Bowl group chat via REST API
- Supports the Token Bowl chat server (api.tokenbowl.ai)

**Setup:**

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env and add your configuration
```

3. Run the script:
```bash
python sleeper_transaction_sync.py
```

**Finding Your League ID:**
1. Go to your league in the Sleeper app
2. Look at the URL: `https://sleeper.com/leagues/YOUR_LEAGUE_ID`
3. Copy the league ID and add it to your `.env` file

**Setting Up Chat API Access:**

1. Get your Token Bowl chat API endpoint URL (default: `http://localhost:8000/messages`)
2. Register a bot user with the chat server:
```bash
curl -X POST http://your-api-url/register \
  -H "Content-Type: application/json" \
  -d '{"username": "sleeper-bot", "password": "your_password"}'
```
3. The registration response will include your API key
4. Add the `CHAT_API_URL` and `CHAT_API_KEY` to your `.env` file

**Scheduling:**

To run automatically, set up a cron job:

```bash
# Run every hour
0 * * * * cd /path/to/bots.chat.tokenbowl.ai && /usr/bin/python3 sleeper_transaction_sync.py >> logs/transaction_sync.log 2>&1
```

Or use systemd timer, GitHub Actions, or any other scheduler.

### 2. News Bot (Coming Soon)

Discovers timely fantasy football news with league-wide impact.

### 3. Predictions Bot (Coming Soon)

Analyzes matchups and predicts winners with detailed breakdowns.

### 4. Trends Bot (Coming Soon)

Identifies fascinating trends and storylines in league performance.

## Project Structure

```
bots.chat.tokenbowl.ai/
├── sleeper_transaction_sync.py  # Transaction monitoring bot
├── requirements.txt              # Python dependencies
├── .env.example                  # Configuration template
├── .gitignore                   # Git ignore patterns
├── prompts/                     # Bot prompt templates
│   ├── news.md
│   ├── predictions.md
│   └── trends.md
└── README.md                    # This file
```

## Configuration

All bots use environment variables for configuration. See `.env.example` for available options.

## Contributing

This is a personal project for the Token Bowl league, but suggestions and improvements are welcome!

## License

MIT License - feel free to use for your own fantasy leagues.
