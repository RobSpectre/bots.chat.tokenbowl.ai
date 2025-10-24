#!/usr/bin/env python3
"""
Sleeper Transaction Sync Bot

This script fetches recent transactions from the Sleeper Fantasy Football API,
compares them against previously seen transactions stored in a JSON file,
and posts new transactions to a group chat via webhook.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set
import requests
from sleeper_wrapper import League


class SleeperTransactionSync:
    """Handles fetching, comparing, and posting Sleeper transactions."""

    def __init__(
        self,
        league_id: str,
        chat_api_url: str,
        chat_api_key: str,
        transactions_file: str = "seen_transactions.json",
        current_week: int = None
    ):
        """
        Initialize the transaction sync.

        Args:
            league_id: The Sleeper league ID
            chat_api_url: The Token Bowl chat API URL
            chat_api_key: The API key for authentication
            transactions_file: Path to JSON file storing seen transactions
            current_week: Current week number (if None, will fetch all weeks)
        """
        self.league_id = league_id
        self.chat_api_url = chat_api_url
        self.chat_api_key = chat_api_key
        self.transactions_file = Path(transactions_file)
        self.current_week = current_week
        self.league = League(league_id)

    def load_seen_transactions(self) -> Set[str]:
        """
        Load previously seen transaction IDs from JSON file.

        Returns:
            Set of transaction IDs that have been seen before
        """
        if not self.transactions_file.exists():
            return set()

        try:
            with open(self.transactions_file, 'r') as f:
                data = json.load(f)
                return set(data.get('transaction_ids', []))
        except json.JSONDecodeError:
            print(f"Warning: Could not parse {self.transactions_file}, starting fresh")
            return set()

    def save_seen_transactions(self, transaction_ids: Set[str]):
        """
        Save seen transaction IDs to JSON file.

        Args:
            transaction_ids: Set of transaction IDs to save
        """
        data = {
            'transaction_ids': list(transaction_ids),
            'last_updated': datetime.now().isoformat()
        }

        with open(self.transactions_file, 'w') as f:
            json.dump(data, f, indent=2)

    def fetch_transactions(self) -> List[Dict]:
        """
        Fetch transactions from Sleeper API.

        Returns:
            List of transaction objects
        """
        all_transactions = []

        if self.current_week:
            # Fetch only the current week
            transactions = self.league.get_transactions(self.current_week)
            if transactions:
                all_transactions.extend(transactions)
        else:
            # Fetch all weeks (typically 1-18 for NFL regular season)
            for week in range(1, 19):
                try:
                    transactions = self.league.get_transactions(week)
                    if transactions:
                        all_transactions.extend(transactions)
                except Exception as e:
                    print(f"Error fetching week {week}: {e}")
                    continue

        return all_transactions

    def format_transaction(self, transaction: Dict) -> str:
        """
        Format a transaction into a readable message.

        Args:
            transaction: Transaction object from Sleeper API

        Returns:
            Formatted string describing the transaction
        """
        transaction_type = transaction.get('type', 'unknown')
        status = transaction.get('status', 'unknown')
        week = transaction.get('leg', 'N/A')

        # Get roster IDs involved
        roster_ids = transaction.get('roster_ids', [])

        # Get player adds/drops
        adds = transaction.get('adds', {})
        drops = transaction.get('drops', {})

        # Format the message based on transaction type
        if transaction_type == 'trade':
            msg = f"🔄 **TRADE** (Week {week})\n"
            msg += f"Status: {status}\n"
            if adds:
                for player_id, roster_id in adds.items():
                    msg += f"  • Player {player_id} → Roster {roster_id}\n"

        elif transaction_type == 'waiver':
            msg = f"📋 **WAIVER CLAIM** (Week {week})\n"
            msg += f"Status: {status}\n"
            if adds:
                for player_id, roster_id in adds.items():
                    msg += f"  • Added: Player {player_id} to Roster {roster_id}\n"
            if drops:
                for player_id, roster_id in drops.items():
                    msg += f"  • Dropped: Player {player_id} from Roster {roster_id}\n"

        elif transaction_type == 'free_agent':
            msg = f"🆓 **FREE AGENT** (Week {week})\n"
            if adds:
                for player_id, roster_id in adds.items():
                    msg += f"  • Added: Player {player_id} to Roster {roster_id}\n"
            if drops:
                for player_id, roster_id in drops.items():
                    msg += f"  • Dropped: Player {player_id} from Roster {roster_id}\n"

        else:
            msg = f"❓ **{transaction_type.upper()}** (Week {week})\n"
            msg += f"Status: {status}\n"

        return msg

    def post_to_chat(self, message: str) -> bool:
        """
        Post a message to the Token Bowl group chat.

        Args:
            message: The message to post

        Returns:
            True if successful, False otherwise
        """
        try:
            # Format for Token Bowl chat API
            payload = {
                'content': message
            }

            headers = {
                'X-API-Key': self.chat_api_key,
                'Content-Type': 'application/json'
            }

            response = requests.post(
                self.chat_api_url,
                json=payload,
                headers=headers,
                timeout=10
            )

            if response.status_code in [200, 201]:
                return True
            else:
                print(f"Error posting to chat API: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"Error posting to chat: {e}")
            return False

    def sync(self):
        """
        Main sync operation: fetch transactions, compare, and post new ones.
        """
        print(f"Starting transaction sync for league {self.league_id}...")

        # Load previously seen transactions
        seen_transactions = self.load_seen_transactions()
        print(f"Loaded {len(seen_transactions)} previously seen transactions")

        # Fetch current transactions
        print("Fetching transactions from Sleeper API...")
        all_transactions = self.fetch_transactions()
        print(f"Found {len(all_transactions)} total transactions")

        # Find new transactions
        new_transactions = []
        all_transaction_ids = set()

        for transaction in all_transactions:
            transaction_id = transaction.get('transaction_id')
            if transaction_id:
                all_transaction_ids.add(transaction_id)

                if transaction_id not in seen_transactions:
                    new_transactions.append(transaction)

        print(f"Found {len(new_transactions)} new transactions")

        # Post new transactions to chat
        if new_transactions:
            for transaction in new_transactions:
                message = self.format_transaction(transaction)
                print(f"\nPosting transaction:\n{message}")

                if self.chat_api_url and self.chat_api_key:
                    success = self.post_to_chat(message)
                    if success:
                        print("✓ Posted successfully")
                    else:
                        print("✗ Failed to post")
                else:
                    print("⚠ Chat API not configured, skipping post")
        else:
            print("No new transactions to post")

        # Update seen transactions
        self.save_seen_transactions(all_transaction_ids)
        print(f"\nSaved {len(all_transaction_ids)} transaction IDs to {self.transactions_file}")
        print("Sync complete!")


def main():
    """Main entry point for the script."""
    # Load configuration from environment variables
    league_id = os.getenv('SLEEPER_LEAGUE_ID')
    chat_api_url = os.getenv('CHAT_API_URL', 'http://localhost:8000/messages')
    chat_api_key = os.getenv('CHAT_API_KEY')
    transactions_file = os.getenv('TRANSACTIONS_FILE', 'seen_transactions.json')
    current_week = os.getenv('CURRENT_WEEK')

    # Validate required configuration
    if not league_id:
        print("Error: SLEEPER_LEAGUE_ID environment variable is required")
        print("\nUsage:")
        print("  export SLEEPER_LEAGUE_ID=your_league_id")
        print("  export CHAT_API_URL=http://your-api-url/messages")
        print("  export CHAT_API_KEY=your_api_key")
        print("  export CURRENT_WEEK=1  # Optional: specific week to check")
        print("  python sleeper_transaction_sync.py")
        sys.exit(1)

    if not chat_api_key:
        print("Warning: CHAT_API_KEY not set - messages will not be posted to chat")

    # Convert current_week to int if provided
    if current_week:
        try:
            current_week = int(current_week)
        except ValueError:
            print(f"Warning: Invalid CURRENT_WEEK value '{current_week}', ignoring")
            current_week = None

    # Run the sync
    syncer = SleeperTransactionSync(
        league_id=league_id,
        chat_api_url=chat_api_url,
        chat_api_key=chat_api_key,
        transactions_file=transactions_file,
        current_week=current_week
    )

    syncer.sync()


if __name__ == '__main__':
    main()
