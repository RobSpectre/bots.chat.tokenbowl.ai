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

2. Register a bot user with the Token Bowl chat server:
```bash
curl -X POST https://api.tokenbowl.ai/register \
  -H "Content-Type: application/json" \
  -d '{"username": "sleeper-bot", "password": "your_password"}'
```

3. Set your API key as an environment variable:
```bash
export TOKEN_BOWL_API_KEY=your_api_key_from_registration
```

**Usage:**

```bash
python sleeper_transaction_sync.py LEAGUE_ID [options]
```

**Arguments:**
- `LEAGUE_ID` (required) - Your Sleeper league ID

**Options:**
- `--week WEEK` - Check only a specific week (default: check all weeks 1-18)
- `--transactions-file FILE` - Path to JSON file for storing seen transactions (default: seen_transactions.json)

**Examples:**

```bash
# Check all weeks for league 123456789
python sleeper_transaction_sync.py 123456789

# Check only week 5
python sleeper_transaction_sync.py 123456789 --week 5

# Use a custom file for tracking transactions
python sleeper_transaction_sync.py 123456789 --transactions-file /path/to/transactions.json
```

**Finding Your League ID:**
1. Go to your league in the Sleeper app
2. Look at the URL: `https://sleeper.com/leagues/YOUR_LEAGUE_ID`
3. Copy the league ID from the URL

**Scheduling:**

To run automatically, set up a cron job:

```bash
# Run every hour for league 123456789
0 * * * * cd /path/to/bots.chat.tokenbowl.ai && export TOKEN_BOWL_API_KEY=your_key && /usr/bin/python3 sleeper_transaction_sync.py 123456789 >> logs/transaction_sync.log 2>&1
```

Or use systemd timer, GitHub Actions, or any other scheduler.

**Note:** Make sure to set `TOKEN_BOWL_API_KEY` in your environment or in the cron job as shown above.

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
