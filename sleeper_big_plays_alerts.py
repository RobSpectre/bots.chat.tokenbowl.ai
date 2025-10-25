#!/usr/bin/env python3
"""
Sleeper Big Plays Alerts Bot

This script monitors player performances during games and posts alerts to the
Token Bowl group chat when players from league rosters achieve significant
scoring milestones (big plays). Tracks high-scoring performances in real-time
during game days.
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

# Scoring thresholds for alerts (PPR scoring)
# These represent significant fantasy performances
SCORING_THRESHOLDS = {
    20: {'emoji': '🔥', 'label': 'HOT PERFORMANCE'},
    30: {'emoji': '💥', 'label': 'EXPLOSIVE GAME'},
    40: {'emoji': '🚀', 'label': 'MONSTER PERFORMANCE'},
    50: {'emoji': '👑', 'label': 'LEGENDARY GAME'}
}


class SleeperBigPlaysAlerts:
    """Handles checking for big plays and posting alerts."""

    def __init__(
        self,
        league_id: str,
        chat_api_url: str,
        chat_api_key: str,
        week: int = None,
        big_plays_file: str = "seen_big_plays.json"
    ):
        """
        Initialize the big plays alerts.

        Args:
            league_id: The Sleeper league ID
            chat_api_url: The Token Bowl chat API URL
            chat_api_key: The API key for authentication
            week: Specific week to check (if None, uses current week)
            big_plays_file: Path to JSON file storing alerted big plays
        """
        self.league_id = league_id
        self.chat_api_url = chat_api_url
        self.chat_api_key = chat_api_key
        self.target_week = week
        self.big_plays_file = Path(big_plays_file)
        self.league = League(league_id)
        self.players_api = Players()

    def load_seen_big_plays(self) -> Dict[str, Dict[str, int]]:
        """
        Load previously alerted big plays from JSON file.

        Returns:
            Dict mapping "week_player_id" to dict of {threshold: timestamp}
        """
        if not self.big_plays_file.exists():
            return {}

        try:
            with open(self.big_plays_file, 'r') as f:
                data = json.load(f)
                return data.get('big_plays', {})
        except json.JSONDecodeError:
            print(f"Warning: Could not parse {self.big_plays_file}, starting fresh")
            return {}

    def save_seen_big_plays(self, big_plays: Dict[str, Dict[str, int]]):
        """
        Save alerted big plays to JSON file.

        Args:
            big_plays: Dict mapping "week_player_id" to dict of thresholds
        """
        data = {
            'big_plays': big_plays,
            'last_updated': datetime.now().isoformat()
        }

        with open(self.big_plays_file, 'w') as f:
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

    def get_league_rosters(self) -> List[Dict]:
        """
        Get all rosters in the league.

        Returns:
            List of roster objects
        """
        return self.league.get_rosters()

    def get_league_player_ids(self, rosters: List[Dict]) -> Set[str]:
        """
        Get all player IDs on league rosters.

        Args:
            rosters: List of roster objects

        Returns:
            Set of player IDs in the league
        """
        player_ids = set()
        for roster in rosters:
            if roster.get('players'):
                player_ids.update(roster['players'])
            if roster.get('reserve'):
                player_ids.update(roster['reserve'])
        return player_ids

    def get_matchups(self, week: int) -> List[Dict]:
        """
        Get matchup data for the specified week.

        Args:
            week: Week number

        Returns:
            List of matchup objects with player points
        """
        try:
            matchups = self.league.get_matchups(week)
            return matchups if matchups else []
        except Exception as e:
            print(f"Error fetching matchups for week {week}: {e}")
            return []

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

    def get_player_scores(self, matchups: List[Dict]) -> Dict[str, float]:
        """
        Extract player scores from matchups data.

        Args:
            matchups: List of matchup objects

        Returns:
            Dict mapping player_id to points scored
        """
        player_scores = {}
        for matchup in matchups:
            # Get player points from matchup
            player_points = matchup.get('players_points', {})
            for player_id, points in player_points.items():
                # Use the highest score if player appears in multiple matchups
                if player_id not in player_scores or points > player_scores[player_id]:
                    player_scores[player_id] = points

        return player_scores

    def find_big_plays(
        self,
        player_scores: Dict[str, float],
        league_player_ids: Set[str],
        all_players: Dict,
        week: int,
        seen_big_plays: Dict[str, Dict[str, int]]
    ) -> List[Dict]:
        """
        Find players who have crossed scoring thresholds.

        Args:
            player_scores: Dict of player_id to points
            league_player_ids: Set of player IDs in the league
            all_players: All player data
            week: Current week
            seen_big_plays: Previously alerted big plays

        Returns:
            List of dicts with big play information
        """
        new_big_plays = []

        for player_id, points in player_scores.items():
            # Only check players on league rosters
            if player_id not in league_player_ids:
                continue

            # Skip players with no points
            if points <= 0:
                continue

            # Get player info
            if player_id not in all_players:
                continue

            player = all_players[player_id]
            player_name = f"{player.get('first_name', '')} {player.get('last_name', '')}".strip()
            team = player.get('team', 'FA')
            position = player.get('position', 'N/A')

            # Check which thresholds have been crossed
            key = f"{week}_{player_id}"
            alerted_thresholds = seen_big_plays.get(key, {})

            # Check each threshold from highest to lowest
            for threshold in sorted(SCORING_THRESHOLDS.keys(), reverse=True):
                # If player has crossed this threshold and we haven't alerted yet
                if points >= threshold and str(threshold) not in alerted_thresholds:
                    new_big_plays.append({
                        'player_id': player_id,
                        'player_name': player_name,
                        'team': team,
                        'position': position,
                        'points': points,
                        'threshold': threshold,
                        'emoji': SCORING_THRESHOLDS[threshold]['emoji'],
                        'label': SCORING_THRESHOLDS[threshold]['label']
                    })

                    # Mark this threshold as alerted
                    if key not in seen_big_plays:
                        seen_big_plays[key] = {}
                    seen_big_plays[key][str(threshold)] = datetime.now().isoformat()

                    # Only alert for the highest threshold crossed
                    break

        return new_big_plays

    def format_big_play_alert(self, big_play: Dict, week: int) -> str:
        """
        Format a big play alert message.

        Args:
            big_play: Big play info dict
            week: Week number

        Returns:
            Formatted alert message
        """
        emoji = big_play['emoji']
        label = big_play['label']
        name = big_play['player_name']
        team = big_play['team']
        position = big_play['position']
        points = big_play['points']

        msg = f"{emoji} **{label}** {emoji}\n"
        msg += f"**{name}** ({team} - {position})\n"
        msg += f"Week {week}: **{points:.1f} points**\n"

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

    def check_big_plays(self):
        """
        Main operation: check for big plays and post alerts.
        """
        print(f"Checking for big plays in league {self.league_id}...")

        # Check if this is the first run (data file doesn't exist)
        is_first_run = not self.big_plays_file.exists()
        if is_first_run:
            print(f"Data file {self.big_plays_file} does not exist - this is the first run")
            print("Will initialize tracking without sending alerts")

        # Load previously alerted big plays
        seen_big_plays = self.load_seen_big_plays()

        # Get current week
        week = self.get_current_week()

        # Get league info
        league_info = self.get_league_info()
        league_name = league_info.get('name', 'Unknown League')
        print(f"League: {league_name}")
        print(f"Week: {week}")

        # Get league rosters
        print("Fetching league rosters...")
        rosters = self.get_league_rosters()
        league_player_ids = self.get_league_player_ids(rosters)
        print(f"Tracking {len(league_player_ids)} players on league rosters")

        # Get matchups (contains player scores)
        print(f"Fetching matchups for week {week}...")
        matchups = self.get_matchups(week)
        if not matchups:
            print("No matchup data available yet for this week")
            print("This is normal before games start or if the week hasn't begun")
            return

        print(f"Found {len(matchups)} matchups")

        # Extract player scores from matchups
        player_scores = self.get_player_scores(matchups)
        print(f"Found scores for {len(player_scores)} players")

        # Get all player data for names/details
        all_players = self.get_all_players()

        # Find big plays
        new_big_plays = self.find_big_plays(
            player_scores,
            league_player_ids,
            all_players,
            week,
            seen_big_plays
        )

        print(f"Found {len(new_big_plays)} new big plays")

        # Skip posting alerts on first run - just initialize the tracking
        if is_first_run:
            print("\n⚠ First run detected - initializing big plays tracking without sending alerts")
            print(f"Found {len(new_big_plays)} performances to track")
        else:
            # Post big play alerts
            if new_big_plays:
                # Sort by points (highest first)
                new_big_plays.sort(key=lambda x: x['points'], reverse=True)

                for big_play in new_big_plays:
                    message = self.format_big_play_alert(big_play, week)
                    print(f"\nPosting big play alert:\n{message}")

                    if self.chat_api_url and self.chat_api_key:
                        success = self.post_to_chat(message)
                        if success:
                            print("✓ Posted successfully")
                        else:
                            print("✗ Failed to post")
                    else:
                        print("⚠ Chat API not configured, skipping post")
            else:
                print("No new big plays to report")

        # Save updated big plays tracking
        self.save_seen_big_plays(seen_big_plays)
        print(f"\nSaved big plays tracking to {self.big_plays_file}")
        print("Big plays check complete!")


def main():
    """Main entry point for the script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Monitor Sleeper fantasy football games for big plays and post alerts to Token Bowl chat'
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
        '--big-plays-file',
        default='seen_big_plays.json',
        help='Path to JSON file storing alerted big plays (default: seen_big_plays.json)'
    )

    args = parser.parse_args()

    chat_api_key = args.api_key

    # Run the big plays check
    checker = SleeperBigPlaysAlerts(
        league_id=args.league_id,
        chat_api_url=CHAT_API_URL,
        chat_api_key=chat_api_key,
        week=args.week,
        big_plays_file=args.big_plays_file
    )

    checker.check_big_plays()


if __name__ == '__main__':
    main()
