#!/usr/bin/env python3
"""
Sleeper Injury Alerts Bot

This script monitors player injury statuses for all players on rosters in a
Sleeper fantasy football league and posts alerts to the Token Bowl group chat
when injuries are newly reported or when injury statuses change.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Set, List
import requests
from sleeper_wrapper import League, Players

# Hard-coded Token Bowl chat API URL
CHAT_API_URL = "https://api.tokenbowl.ai/messages"

# Injury status icons
INJURY_ICONS = {
    'Out': '🚑',
    'Doubtful': '⚠️',
    'Questionable': '❓',
    'IR': '🏥',
    'PUP': '📋',
    'Suspended': '🚫',
    'COVID': '😷',
    'NA': '❌'
}


class SleeperInjuryAlerts:
    """Handles fetching, comparing, and posting Sleeper injury alerts."""

    def __init__(
        self,
        league_id: str,
        chat_api_url: str,
        chat_api_key: str,
        injury_file: str = "seen_injuries.json"
    ):
        """
        Initialize the injury alerts.

        Args:
            league_id: The Sleeper league ID
            chat_api_url: The Token Bowl chat API URL
            chat_api_key: The API key for authentication
            injury_file: Path to JSON file storing seen injuries
        """
        self.league_id = league_id
        self.chat_api_url = chat_api_url
        self.chat_api_key = chat_api_key
        self.injury_file = Path(injury_file)
        self.league = League(league_id)
        self.players_api = Players()

    def load_seen_injuries(self) -> Dict[str, str]:
        """
        Load previously seen injury statuses from JSON file.

        Returns:
            Dict mapping player_id to last seen injury status
        """
        if not self.injury_file.exists():
            return {}

        try:
            with open(self.injury_file, 'r') as f:
                data = json.load(f)
                return data.get('injuries', {})
        except json.JSONDecodeError:
            print(f"Warning: Could not parse {self.injury_file}, starting fresh")
            return {}

    def save_seen_injuries(self, injuries: Dict[str, str]):
        """
        Save seen injury statuses to JSON file.

        Args:
            injuries: Dict mapping player_id to injury status
        """
        data = {
            'injuries': injuries,
            'last_updated': datetime.now().isoformat()
        }

        with open(self.injury_file, 'w') as f:
            json.dump(data, f, indent=2)

    def get_league_players(self) -> Set[str]:
        """
        Get all player IDs that are on rosters in the league.

        Returns:
            Set of player IDs
        """
        rosters = self.league.get_rosters()
        player_ids = set()

        for roster in rosters:
            # Add players from rosters
            if roster.get('players'):
                player_ids.update(roster['players'])
            # Add players from reserve/IR
            if roster.get('reserve'):
                player_ids.update(roster['reserve'])

        return player_ids

    def get_all_players(self) -> Dict:
        """
        Get all NFL player data from Sleeper API.

        Returns:
            Dict mapping player_id to player data
        """
        print("Fetching all NFL player data (this may take a moment)...")
        all_players = self.players_api.get_all_players()
        print(f"Loaded data for {len(all_players)} players")
        return all_players

    def get_current_injuries(self, league_player_ids: Set[str], all_players: Dict) -> Dict[str, Dict]:
        """
        Get current injury statuses for league players.

        Args:
            league_player_ids: Set of player IDs in the league
            all_players: All player data from Sleeper API

        Returns:
            Dict mapping player_id to injury info (status, player name, etc.)
        """
        current_injuries = {}

        for player_id in league_player_ids:
            if player_id not in all_players:
                continue

            player = all_players[player_id]
            injury_status = player.get('injury_status')

            # Check if player has an injury status
            if injury_status and injury_status.strip():
                current_injuries[player_id] = {
                    'status': injury_status,
                    'name': f"{player.get('first_name', '')} {player.get('last_name', '')}".strip(),
                    'team': player.get('team', 'FA'),
                    'position': player.get('position', 'N/A'),
                    'injury_start_date': player.get('injury_start_date'),
                    'injury_body_part': player.get('injury_body_part'),
                    'practice_participation': player.get('practice_participation')
                }

        return current_injuries

    def format_injury_alert(self, player_id: str, injury_info: Dict, is_new: bool, old_status: str = None) -> str:
        """
        Format an injury alert message.

        Args:
            player_id: The player ID
            injury_info: Injury information dict
            is_new: Whether this is a new injury or status change
            old_status: Previous injury status (if status changed)

        Returns:
            Formatted string describing the injury
        """
        status = injury_info['status']
        icon = INJURY_ICONS.get(status, '⚕️')
        name = injury_info['name']
        team = injury_info['team']
        position = injury_info['position']

        if is_new:
            msg = f"{icon} **NEW INJURY REPORT**\n"
        else:
            msg = f"{icon} **INJURY STATUS UPDATE**\n"

        msg += f"{name} ({team} - {position})\n"

        if is_new:
            msg += f"Status: **{status}**\n"
        else:
            msg += f"Status: {old_status} → **{status}**\n"

        # Add additional details if available
        if injury_info.get('injury_body_part'):
            msg += f"Injury: {injury_info['injury_body_part']}\n"

        if injury_info.get('practice_participation'):
            msg += f"Practice: {injury_info['practice_participation']}\n"

        if injury_info.get('injury_start_date'):
            msg += f"Since: {injury_info['injury_start_date']}\n"

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

    def check_injuries(self):
        """
        Main operation: fetch injuries, compare, and post alerts.
        """
        print(f"Checking injuries for league {self.league_id}...")

        # Check if this is the first run (data file doesn't exist)
        is_first_run = not self.injury_file.exists()
        if is_first_run:
            print(f"Data file {self.injury_file} does not exist - this is the first run")
            print("Will initialize tracking without sending alerts")

        # Load previously seen injuries
        seen_injuries = self.load_seen_injuries()
        print(f"Loaded {len(seen_injuries)} previously seen injury statuses")

        # Get all players on league rosters
        print("Fetching league rosters...")
        league_player_ids = self.get_league_players()
        print(f"Found {len(league_player_ids)} players on league rosters")

        # Get all NFL player data
        all_players = self.get_all_players()

        # Get current injuries for league players
        current_injuries = self.get_current_injuries(league_player_ids, all_players)
        print(f"Found {len(current_injuries)} currently injured players")

        # Find new and updated injuries
        new_alerts = []
        updated_injuries = {}

        for player_id, injury_info in current_injuries.items():
            current_status = injury_info['status']

            if player_id not in seen_injuries:
                # New injury
                new_alerts.append((player_id, injury_info, True, None))
            elif seen_injuries[player_id] != current_status:
                # Status changed
                old_status = seen_injuries[player_id]
                new_alerts.append((player_id, injury_info, False, old_status))

            # Track current status
            updated_injuries[player_id] = current_status

        # Check for recovered players (had injury before, now don't)
        recovered_players = []
        for player_id in seen_injuries:
            if player_id not in current_injuries and player_id in all_players:
                player = all_players[player_id]
                name = f"{player.get('first_name', '')} {player.get('last_name', '')}".strip()
                team = player.get('team', 'FA')
                position = player.get('position', 'N/A')
                recovered_players.append({
                    'name': name,
                    'team': team,
                    'position': position,
                    'previous_status': seen_injuries[player_id]
                })

        print(f"Found {len(new_alerts)} new/updated injuries")
        print(f"Found {len(recovered_players)} recovered players")

        # Skip posting alerts on first run - just initialize the tracking
        if is_first_run:
            print("\n⚠ First run detected - initializing injury tracking without sending alerts")
            print(f"Found {len(current_injuries)} currently injured players to track")
        else:
            # Post injury alerts
            if new_alerts:
                for player_id, injury_info, is_new, old_status in new_alerts:
                    message = self.format_injury_alert(player_id, injury_info, is_new, old_status)
                    print(f"\nPosting injury alert:\n{message}")

                    if self.chat_api_url and self.chat_api_key:
                        success = self.post_to_chat(message)
                        if success:
                            print("✓ Posted successfully")
                        else:
                            print("✗ Failed to post")
                    else:
                        print("⚠ Chat API not configured, skipping post")
            else:
                print("No new or updated injuries to report")

            # Post recovery alerts
            if recovered_players:
                for player_info in recovered_players:
                    message = f"✅ **PLAYER CLEARED**\n"
                    message += f"{player_info['name']} ({player_info['team']} - {player_info['position']})\n"
                    message += f"Previous status: {player_info['previous_status']}\n"
                    message += "Player no longer listed on injury report"

                    print(f"\nPosting recovery alert:\n{message}")

                    if self.chat_api_url and self.chat_api_key:
                        success = self.post_to_chat(message)
                        if success:
                            print("✓ Posted successfully")
                        else:
                            print("✗ Failed to post")

        # Save updated injury statuses
        self.save_seen_injuries(updated_injuries)
        print(f"\nSaved {len(updated_injuries)} injury statuses to {self.injury_file}")
        print("Injury check complete!")


def main():
    """Main entry point for the script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Monitor Sleeper fantasy football player injuries and post alerts to Token Bowl chat'
    )
    parser.add_argument(
        'league_id',
        help='Sleeper league ID (find it in your league URL: sleeper.com/leagues/LEAGUE_ID)'
    )
    parser.add_argument(
        '--api-key',
        required=True,
        help='Token Bowl API key'
    )
    parser.add_argument(
        '--injury-file',
        default='seen_injuries.json',
        help='Path to JSON file storing seen injuries (default: seen_injuries.json)'
    )

    args = parser.parse_args()

    chat_api_key = args.api_key

    # Run the injury check
    checker = SleeperInjuryAlerts(
        league_id=args.league_id,
        chat_api_url=CHAT_API_URL,
        chat_api_key=chat_api_key,
        injury_file=args.injury_file
    )

    checker.check_injuries()


if __name__ == '__main__':
    main()
