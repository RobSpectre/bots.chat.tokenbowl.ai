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

Save the API key returned from registration.

**Usage:**

```bash
python sleeper_transaction_sync.py LEAGUE_ID --api-key YOUR_API_KEY [options]
```

**Arguments:**
- `LEAGUE_ID` (required) - Your Sleeper league ID
- `--api-key` (required) - Your Token Bowl API key from registration

**Options:**
- `--week WEEK` - Check only a specific week (default: check all weeks 1-18)
- `--transactions-file FILE` - Path to JSON file for storing seen transactions (default: seen_transactions.json)

**First Run Behavior:**

On the first run (when the data file doesn't exist), the bot will initialize the transaction tracking database without sending any alerts. This prevents spam from alerting on all existing transactions. Subsequent runs will only alert on new transactions.

**Examples:**

```bash
# Check all weeks for league 123456789
python sleeper_transaction_sync.py 123456789 --api-key YOUR_API_KEY

# Check only week 5
python sleeper_transaction_sync.py 123456789 --api-key YOUR_API_KEY --week 5

# Use a custom file for tracking transactions
python sleeper_transaction_sync.py 123456789 --api-key YOUR_API_KEY --transactions-file /path/to/transactions.json
```

**Finding Your League ID:**
1. Go to your league in the Sleeper app
2. Look at the URL: `https://sleeper.com/leagues/YOUR_LEAGUE_ID`
3. Copy the league ID from the URL

**Scheduling:**

To run automatically, set up a cron job:

```bash
# Run every hour for league 123456789
0 * * * * cd /path/to/bots.chat.tokenbowl.ai && source .venv/bin/activate && python sleeper_transaction_sync.py 123456789 --api-key YOUR_API_KEY >> logs/transaction_sync.log 2>&1
```

Or use systemd timer, GitHub Actions, or any other scheduler.

### 2. Sleeper Injury Alerts Bot

Automatically monitors all players on league rosters for injury status changes and posts alerts to the Token Bowl group chat when players are newly injured, have status updates, or are cleared from the injury report.

**Features:**
- Fetches all NFL player data from Sleeper API
- Monitors only players on league rosters (including IR/reserve)
- Tracks injury status changes (new injuries, status updates, recoveries)
- Posts formatted alerts with player details and injury information
- Includes emoji indicators for different injury statuses

**Setup:**

Same as Transaction Sync Bot - install dependencies and register for an API key.

**Usage:**

```bash
python sleeper_injury_alerts.py LEAGUE_ID --api-key YOUR_API_KEY [options]
```

**Arguments:**
- `LEAGUE_ID` (required) - Your Sleeper league ID
- `--api-key` (required) - Your Token Bowl API key

**Options:**
- `--injury-file FILE` - Path to JSON file for storing seen injuries (default: seen_injuries.json)

**First Run Behavior:**

On the first run (when the data file doesn't exist), the bot will initialize the injury tracking database without sending any alerts. This prevents spam from alerting on all existing injuries. Subsequent runs will only alert on new injuries or status changes.

**Examples:**

```bash
# Check for injury updates
python sleeper_injury_alerts.py 123456789 --api-key YOUR_API_KEY

# Use a custom file for tracking injuries
python sleeper_injury_alerts.py 123456789 --api-key YOUR_API_KEY --injury-file /path/to/injuries.json
```

**Injury Status Types:**
- 🚑 Out
- ⚠️ Doubtful
- ❓ Questionable
- 🏥 IR (Injured Reserve)
- 📋 PUP (Physically Unable to Perform)
- 🚫 Suspended
- 😷 COVID
- ✅ Cleared/Recovered

**Scheduling:**

Run this bot daily (recommended) or multiple times per day during game weeks:

```bash
# Check injuries twice daily at 9 AM and 5 PM
0 9,17 * * * cd /path/to/bots.chat.tokenbowl.ai && source .venv/bin/activate && python sleeper_injury_alerts.py 123456789 --api-key YOUR_API_KEY >> logs/injury_alerts.log 2>&1
```

**Important Note:** The Sleeper API recommends calling the players endpoint at most once per day. This bot caches nothing and fetches fresh data each run, so avoid running it too frequently.

### 3. Sleeper Zero Points Alerts Bot

Checks all team lineups before game time and alerts if any team has a starting player who will score zero points due to injury, bye week, or being a free agent.

**Features:**
- Checks all starting lineups in the league
- Detects players who will score zero points:
  - Injured/Out players (Out, IR, Suspended, PUP)
  - Players whose teams are on bye
  - Free agents without a team
- Posts alerts per team with all problematic starters
- Uses current NFL week or specific week
- Includes 2025 NFL bye week schedule

**Setup:**

Same as other bots - install dependencies and register for an API key.

**Usage:**

```bash
python sleeper_zero_points_alerts.py LEAGUE_ID --api-key YOUR_API_KEY [options]
```

**Arguments:**
- `LEAGUE_ID` (required) - Your Sleeper league ID
- `--api-key` (required) - Your Token Bowl API key

**Options:**
- `--week WEEK` - Check a specific week (default: current NFL week)
- `--alerts-file FILE` - Path to JSON file storing sent alerts (default: seen_alerts.json)

**First Run Behavior:**

On the first run (when the data file doesn't exist), the bot will initialize alert tracking without sending any alerts. This prevents spam from alerting on all existing lineup issues. Subsequent runs will only alert on new issues or issues that weren't previously alerted on.

**Preventing Duplicate Alerts:**

The bot tracks which alerts have been sent for each week, so you can safely run it multiple times before game day without spamming duplicate alerts. Only new lineup issues will trigger alerts.

**Examples:**

```bash
# Check current week's lineups
python sleeper_zero_points_alerts.py 123456789 --api-key YOUR_API_KEY

# Check lineups for week 5
python sleeper_zero_points_alerts.py 123456789 --api-key YOUR_API_KEY --week 5
```

**When to Run:**

Run this bot **before game time** each week to give teams time to fix their lineups:

```bash
# Run Thursday morning before TNF and Sunday morning before early games
0 8 * * 4,0 cd /path/to/bots.chat.tokenbowl.ai && source .venv/bin/activate && python sleeper_zero_points_alerts.py 123456789 --api-key YOUR_API_KEY >> logs/lineup_alerts.log 2>&1
```

**Alert Format:**

```
⚠️ LINEUP ALERT - Week 5
Team: Team Name

The following starters are projected to score ZERO POINTS:

❌ Christian McCaffrey (SF - RB)
   Reason: Injury Status: IR

❌ Justin Herbert (LAC - QB)
   Reason: Team on Bye (Week 5)

⏰ Please update your lineup before game time!
```

### 4. News Bot (Coming Soon)

Discovers timely fantasy football news with league-wide impact.

### 5. Predictions Bot (Coming Soon)

Analyzes matchups and predicts winners with detailed breakdowns.

### 6. Trends Bot (Coming Soon)

Identifies fascinating trends and storylines in league performance.

## Project Structure

```
bots.chat.tokenbowl.ai/
├── sleeper_transaction_sync.py    # Transaction monitoring bot
├── sleeper_injury_alerts.py       # Injury alerts bot
├── sleeper_zero_points_alerts.py  # Zero points lineup checker
├── requirements.txt                # Python dependencies
├── .env.example                    # Configuration template
├── .gitignore                     # Git ignore patterns
├── prompts/                       # Bot prompt templates
│   ├── news.md
│   ├── predictions.md
│   └── trends.md
└── README.md                      # This file
```

## Configuration

All bots require a Token Bowl API key passed as a CLI argument. Register your bot user at `https://api.tokenbowl.ai/register` to get your API key.

### First Run Behavior

All bots implement intelligent first-run detection. When run for the first time (when their data file doesn't exist), they will:
- Initialize their tracking database with the current state
- Skip sending any alerts to avoid spam
- Save the baseline for future comparisons

On subsequent runs, the bots will only send alerts for new events, changes, or issues that haven't been previously alerted on. This makes it safe to set up the bots without flooding your chat with historical data.

## Deployment

### Automated Deployment with Self-Hosted GitHub Runner

This repository includes a GitHub Actions workflow that automatically deploys when you push to the `main` branch. It uses a self-hosted GitHub runner on your private server for direct deployment.

**Setup Steps:**

1. **Set up a self-hosted GitHub runner** (if not already done):
   - Go to your repository on GitHub
   - Navigate to Settings → Actions → Runners
   - Click "New self-hosted runner"
   - Follow the instructions to install and configure the runner on your server

2. **Configure the runner working directory**:
   ```bash
   # The runner should be configured to check out code in your desired location
   # Example: /home/user/bots.chat.tokenbowl.ai
   ```

3. **Deploy by pushing to main**:
   ```bash
   git add .
   git commit -m "Your changes"
   git push origin main
   ```

   Or manually trigger:
   - Go to Actions → Deploy to Private Server → Run workflow

**What the workflow does:**
- Checks out your code directly on the server
- Preserves data and logs directories (using `clean: false`)
- Installs/updates `uv` package manager
- Creates a virtual environment using `uv venv`
- Installs Python dependencies with `uv pip install`
- Creates necessary directories if they don't exist
- Sets executable permissions on Python scripts

**Using the virtual environment:**

After deployment, activate the virtual environment in your cron jobs:

```bash
# Example cron job
0 * * * * cd /path/to/bots.chat.tokenbowl.ai && source .venv/bin/activate && python sleeper_transaction_sync.py 123456789 --api-key YOUR_API_KEY >> logs/transaction_sync.log 2>&1
```

**After initial setup**, you'll need to:
- Set up cron jobs manually (see scheduling sections above)
- Ensure your API key is passed to the scripts via CLI arguments
- Update cron jobs to use the `.venv/bin/activate` path

### Manual Deployment

If you prefer to deploy manually:

```bash
# SSH into your server
ssh user@your-server.com

# Clone or pull the repository
git clone https://github.com/yourusername/bots.chat.tokenbowl.ai.git
cd bots.chat.tokenbowl.ai
git pull origin main

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt

# Create necessary directories
mkdir -p data logs

# Set up cron jobs (edit with: crontab -e)
# Remember to activate the venv in your cron jobs!
# See bot-specific scheduling sections above
```

## Contributing

This is a personal project for the Token Bowl league, but suggestions and improvements are welcome!

## License

MIT License - feel free to use for your own fantasy leagues.
