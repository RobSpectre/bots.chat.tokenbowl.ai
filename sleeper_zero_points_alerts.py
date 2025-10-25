#!/usr/bin/env python3
"""
Sleeper Zero Points Alerts Bot

This script checks all rosters in a Sleeper fantasy football league and alerts
teams before game time if they have a starting player who will produce zero points
(due to injury, bye week, or being a free agent).
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple
import requests
from sleeper_wrapper import League, Players

# Hard-coded Token Bowl chat API URL
CHAT_API_URL = "https://api.tokenbowl.ai/messages"

# 2025 NFL Bye Week Schedule
# Source: https://www.fantasyalarm.com/articles/nfl/nfl-offseason/2025-nfl-bye-weeks-complete-schedule-and-fantasy-football-guide/175207
BYE_WEEKS_2025 = {
    5: ['ATL', 'CHI', 'GB', 'PIT'],
    6: ['CIN', 'CLE', 'HOU', 'NYG'],
    7: ['DAL', 'DEN', 'KC', 'LAC'],
    8: ['ARI', 'DET', 'JAX', 'LV', 'LAR', 'SEA'],
    9: ['BAL', 'MIA', 'MIN', 'PHI'],
    10: ['BUF', 'CAR', 'IND', 'NE'],
    11: ['NO', 'NYJ', 'SF', 'TB'],
    12: ['TEN', 'WAS'],
    14: []  # No byes in week 14
}

# Injury statuses that mean zero points
ZERO_POINT_STATUSES = ['Out', 'IR', 'Suspended', 'PUP', 'COV']


class SleeperZeroPointsAlerts:
    """Handles checking rosters for zero-point starters and posting alerts."""

    def __init__(
        self,
        league_id: str,
        chat_api_url: str,
        chat_api_key: str,
        week: int = None,
        alerts_file: str = "seen_alerts.json"
    ):
        """
        Initialize the zero points alerts.

        Args:
            league_id: The Sleeper league ID
            chat_api_url: The Token Bowl chat API URL
            chat_api_key: The API key for authentication
            week: Specific week to check (if None, uses current week)
            alerts_file: Path to JSON file storing sent alerts
        """
        self.league_id = league_id
        self.chat_api_url = chat_api_url
        self.chat_api_key = chat_api_key
        self.target_week = week
        self.alerts_file = Path(alerts_file)
        self.league = League(league_id)
        self.players_api = Players()

    def load_seen_alerts(self) -> Dict[str, Set[int]]:
        """
        Load previously sent alerts from JSON file.

        Returns:
            Dict mapping "week_roster_id" to set of player IDs already alerted
        """
        if not self.alerts_file.exists():
            return {}

        try:
            with open(self.alerts_file, 'r') as f:
                data = json.load(f)
                # Convert lists back to sets
                alerts = {}
                for key, player_ids in data.get('alerts', {}).items():
                    alerts[key] = set(player_ids)
                return alerts
        except json.JSONDecodeError:
            print(f"Warning: Could not parse {self.alerts_file}, starting fresh")
            return {}

    def save_seen_alerts(self, alerts: Dict[str, Set[int]]):
        """
        Save sent alerts to JSON file.

        Args:
            alerts: Dict mapping "week_roster_id" to set of player IDs
        """
        # Convert sets to lists for JSON serialization
        alerts_serializable = {}
        for key, player_ids in alerts.items():
            alerts_serializable[key] = list(player_ids)

        data = {
            'alerts': alerts_serializable,
            'last_updated': datetime.now().isoformat()
        }

        with open(self.alerts_file, 'w') as f:
            json.dump(data, f, indent=2)

    def get_nfl_state(self) -> Dict:
        """
        Get the current NFL state from Sleeper API.

        Returns:
            Dict with NFL state info including current week
        """
        try:
            response = requests.get('https://api.sleeper.app/v1/state/nfl', timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error fetching NFL state: {response.status_code}")
                return {}
        except Exception as e:
            print(f"Error fetching NFL state: {e}")
            return {}

    def get_current_week(self) -> int:
        """
        Get the current NFL week.

        Returns:
            Current week number
        """
        if self.target_week:
            return self.target_week

        nfl_state = self.get_nfl_state()
        week = nfl_state.get('week', 1)
        print(f"Current NFL week: {week}")
        return week

    def get_league_info(self) -> Dict:
        """
        Get league information.

        Returns:
            League info dict
        """
        return self.league.get_league()

    def get_rosters(self) -> List[Dict]:
        """
        Get all rosters in the league.

        Returns:
            List of roster objects
        """
        return self.league.get_rosters()

    def get_users(self) -> Dict[str, Dict]:
        """
        Get all users in the league mapped by user_id.

        Returns:
            Dict mapping user_id to user info
        """
        users = self.league.get_users()
        return {user['user_id']: user for user in users}

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

    def is_on_bye(self, team: str, week: int) -> bool:
        """
        Check if a team is on bye in the given week.

        Args:
            team: NFL team abbreviation
            week: Week number

        Returns:
            True if team is on bye, False otherwise
        """
        if week in BYE_WEEKS_2025:
            return team in BYE_WEEKS_2025[week]
        return False

    def will_score_zero_points(self, player_id: str, player_data: Dict, week: int) -> Tuple[bool, str]:
        """
        Check if a player will score zero points.

        Args:
            player_id: The player ID
            player_data: Player data from Sleeper API
            week: Week number to check

        Returns:
            Tuple of (will_score_zero, reason)
        """
        # Check if player has no team (free agent)
        team = player_data.get('team')
        if not team or team == 'FA':
            return True, "Free Agent - No Team"

        # Check if player is injured/out
        injury_status = (player_data.get('injury_status') or '').strip()
        if injury_status in ZERO_POINT_STATUSES:
            return True, f"Injury Status: {injury_status}"

        # Check if team is on bye
        if self.is_on_bye(team, week):
            return True, f"Team on Bye (Week {week})"

        return False, ""

    def check_roster_for_issues(
        self,
        roster: Dict,
        all_players: Dict,
        week: int,
        users: Dict[str, Dict]
    ) -> List[Dict]:
        """
        Check a roster for zero-point starters.

        Args:
            roster: Roster object
            all_players: All player data
            week: Week number
            users: User info dict

        Returns:
            List of issue dicts with player and reason
        """
        issues = []
        starters = roster.get('starters', [])
        owner_id = roster.get('owner_id')
        roster_id = roster.get('roster_id')

        # Get owner info
        owner = users.get(owner_id, {})
        team_name = owner.get('display_name', f"Team {roster_id}")

        for player_id in starters:
            # Skip empty roster spots
            if not player_id:
                continue

            # Get player data
            if player_id not in all_players:
                issues.append({
                    'player_id': player_id,
                    'player_name': 'Unknown Player',
                    'team': 'N/A',
                    'position': 'N/A',
                    'reason': 'Player not found in database',
                    'owner_id': owner_id,
                    'team_name': team_name,
                    'roster_id': roster_id
                })
                continue

            player = all_players[player_id]
            will_zero, reason = self.will_score_zero_points(player_id, player, week)

            if will_zero:
                issues.append({
                    'player_id': player_id,
                    'player_name': f"{player.get('first_name', '')} {player.get('last_name', '')}".strip(),
                    'team': player.get('team', 'FA'),
                    'position': player.get('position', 'N/A'),
                    'reason': reason,
                    'owner_id': owner_id,
                    'team_name': team_name,
                    'roster_id': roster_id
                })

        return issues

    def format_alert(self, team_issues: List[Dict], week: int) -> str:
        """
        Format an alert message for a team with zero-point starters.

        Args:
            team_issues: List of issue dicts for one team
            week: Week number

        Returns:
            Formatted alert message
        """
        if not team_issues:
            return ""

        team_name = team_issues[0]['team_name']
        msg = f"⚠️ **LINEUP ALERT - Week {week}**\n"
        msg += f"Team: **{team_name}**\n\n"
        msg += "The following starters are projected to score **ZERO POINTS**:\n\n"

        for issue in team_issues:
            msg += f"❌ **{issue['player_name']}** ({issue['team']} - {issue['position']})\n"
            msg += f"   Reason: {issue['reason']}\n\n"

        msg += "⏰ Please update your lineup before game time!"

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

    def check_lineups(self):
        """
        Main operation: check all lineups and post alerts for zero-point starters.
        """
        print(f"Checking lineups for league {self.league_id}...")

        # Check if this is the first run (data file doesn't exist)
        is_first_run = not self.alerts_file.exists()
        if is_first_run:
            print(f"Data file {self.alerts_file} does not exist - this is the first run")
            print("Will initialize tracking without sending alerts")

        # Load previously sent alerts
        seen_alerts = self.load_seen_alerts()

        # Get current week
        week = self.get_current_week()

        # Get league info
        league_info = self.get_league_info()
        league_name = league_info.get('name', 'Unknown League')
        print(f"League: {league_name}")

        # Get rosters
        print("Fetching rosters...")
        rosters = self.get_rosters()
        print(f"Found {len(rosters)} teams")

        # Get users
        print("Fetching users...")
        users = self.get_users()

        # Get all player data
        all_players = self.get_all_players()

        # Check each roster
        all_issues = []
        for roster in rosters:
            issues = self.check_roster_for_issues(roster, all_players, week, users)
            if issues:
                all_issues.extend(issues)

        # Group issues by team
        teams_with_issues = {}
        for issue in all_issues:
            roster_id = issue['roster_id']
            if roster_id not in teams_with_issues:
                teams_with_issues[roster_id] = []
            teams_with_issues[roster_id].append(issue)

        print(f"\nFound {len(teams_with_issues)} teams with lineup issues")
        print(f"Total zero-point starters: {len(all_issues)}")

        # Skip posting alerts on first run - just initialize the tracking
        if is_first_run:
            print("\n⚠ First run detected - initializing alert tracking without sending alerts")
            print(f"Found {len(all_issues)} lineup issues to track")
            # Initialize seen_alerts with all current issues
            for issue in all_issues:
                key = f"{week}_{issue['roster_id']}"
                if key not in seen_alerts:
                    seen_alerts[key] = set()
                seen_alerts[key].add(issue['player_id'])
        else:
            # Filter out alerts that have already been sent for this week/roster
            new_teams_with_issues = {}
            for roster_id, team_issues in teams_with_issues.items():
                key = f"{week}_{roster_id}"
                already_alerted = seen_alerts.get(key, set())

                # Only include issues for players we haven't alerted on yet
                new_issues = [issue for issue in team_issues if issue['player_id'] not in already_alerted]

                if new_issues:
                    new_teams_with_issues[roster_id] = new_issues
                    # Track these as alerted
                    if key not in seen_alerts:
                        seen_alerts[key] = set()
                    for issue in new_issues:
                        seen_alerts[key].add(issue['player_id'])

            # Post alerts for new issues
            if new_teams_with_issues:
                for roster_id, team_issues in new_teams_with_issues.items():
                    message = self.format_alert(team_issues, week)
                    print(f"\nPosting alert:\n{message}\n")

                    if self.chat_api_url and self.chat_api_key:
                        success = self.post_to_chat(message)
                        if success:
                            print("✓ Posted successfully")
                        else:
                            print("✗ Failed to post")
                    else:
                        print("⚠ Chat API not configured, skipping post")
            else:
                if teams_with_issues:
                    print("\n⚠ All lineup issues have already been alerted on - no new alerts to send")
                else:
                    print("\n✅ All teams have valid lineups - no alerts needed!")

        # Save updated alerts
        self.save_seen_alerts(seen_alerts)
        print(f"\nSaved alert tracking to {self.alerts_file}")
        print("Lineup check complete!")


def main():
    """Main entry point for the script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Check Sleeper fantasy football lineups for zero-point starters and post alerts to Token Bowl chat'
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
        '--week',
        type=int,
        help='Specific week to check (default: current NFL week)'
    )
    parser.add_argument(
        '--alerts-file',
        default='seen_alerts.json',
        help='Path to JSON file storing sent alerts (default: seen_alerts.json)'
    )

    args = parser.parse_args()

    chat_api_key = args.api_key

    # Run the lineup check
    checker = SleeperZeroPointsAlerts(
        league_id=args.league_id,
        chat_api_url=CHAT_API_URL,
        chat_api_key=chat_api_key,
        week=args.week,
        alerts_file=args.alerts_file
    )

    checker.check_lineups()


if __name__ == '__main__':
    main()
