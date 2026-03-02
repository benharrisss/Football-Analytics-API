import pandas as pd
from django.core.management.base import BaseCommand
from teams.models import League, Team
from matches.models import Match
from datetime import datetime

class Command(BaseCommand):
    help = 'Imports match data from matches.csv'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the matches.csv file')

    TEAM_NAME_NORMALISATION = {
        "Nott'm Forest": "Nottm Forest",
    }

    def normalise_team_name(self, name):
        return self.TEAM_NAME_NORMALISATION.get(name, name)

    def handle(self, *args, **options):
        file_path = options['csv_file']
        
        # 1. Load data and filter for English Leagues (E0, E1, E2, E3)
        self.stdout.write("Loading CSV...")
        df = pd.read_csv(file_path)
        english_divs = ['E0', 'E1', 'E2', 'E3']
        df = df[df['Division'].isin(english_divs)]

        # Map Division codes to Names
        league_map = {
            'E0': 'Premier League',
            'E1': 'Championship',
            'E2': 'League One',
            'E3': 'League Two'
        }

        self.stdout.write(f"Processing {len(df)} matches...")

        for index, row in df.iterrows():
            # 2. Get or Create League
            league_obj, _ = League.objects.get_or_create(
                code=row['Division'],
                defaults={'name': league_map.get(row['Division'], 'Unknown League')}
            )

            # 3. Get or Create Teams
            home_team_obj, _ = Team.objects.get_or_create(
                name=self.normalise_team_name(row['HomeTeam']),
                league=league_obj
            )
            away_team_obj, _ = Team.objects.get_or_create(
                name=self.normalise_team_name(row['AwayTeam']),
                league=league_obj
            )

            # 4. Create Match (using update_or_create to prevent duplicates)
            try:
                Match.objects.update_or_create(
                    league=league_obj,
                    match_date=row['MatchDate'],
                    home_team=home_team_obj,
                    away_team=away_team_obj,
                    defaults={
                        'match_time': row['MatchTime'] if pd.notna(row['MatchTime']) else None,
                        'ft_home_goals': row['FTHome'],
                        'ft_away_goals': row['FTAway'],
                        'ft_result': row['FTResult'],
                        'ht_home_goals': row['HTHome'] if pd.notna(row['HTHome']) else None,
                        'ht_away_goals': row['HTAway'] if pd.notna(row['HTAway']) else None,
                        'ht_result': row['HTResult'] if pd.notna(row['HTResult']) else None,
                        'home_shots': row['HomeShots'] if pd.notna(row['HomeShots']) else None,
                        'away_shots': row['AwayShots'] if pd.notna(row['AwayShots']) else None,
                        'home_shots_on_target': row['HomeTarget'] if pd.notna(row['HomeTarget']) else None,
                        'away_shots_on_target': row['AwayTarget'] if pd.notna(row['AwayTarget']) else None,
                        'home_fouls': row['HomeFouls'] if pd.notna(row['HomeFouls']) else None,
                        'away_fouls': row['AwayFouls'] if pd.notna(row['AwayFouls']) else None,
                        'home_corners': row['HomeCorners'] if pd.notna(row['HomeCorners']) else None,
                        'away_corners': row['AwayCorners'] if pd.notna(row['AwayCorners']) else None,
                        'home_yellow_cards': row['HomeYellow'] if pd.notna(row['HomeYellow']) else None,
                        'away_yellow_cards': row['AwayYellow'] if pd.notna(row['AwayYellow']) else None,
                        'home_red_cards': row['HomeRed'] if pd.notna(row['HomeRed']) else None,
                        'away_red_cards': row['AwayRed'] if pd.notna(row['AwayRed']) else None,
                        'home_elo_pre': row['HomeElo'] if pd.notna(row['HomeElo']) else None,
                        'away_elo_pre': row['AwayElo'] if pd.notna(row['AwayElo']) else None,
                        'home_form_5': row['Form5Home'] if pd.notna(row['Form5Home']) else None,
                        'away_form_5': row['Form5Away'] if pd.notna(row['Form5Away']) else None,
                        'home_win_odds': row['OddHome'] if pd.notna(row['OddHome']) else None,
                        'draw_odds': row['OddDraw'] if pd.notna(row['OddDraw']) else None,
                        'away_win_odds': row['OddAway'] if pd.notna(row['OddAway']) else None,
                        'over_2_5_odds': row['Over25'] if pd.notna(row['Over25']) else None,
                        'under_2_5_odds': row['Under25'] if pd.notna(row['Under25']) else None,
                    }
                )
            except Exception as e:
                self.stderr.write(f"Error at index {index}: {e}")

        self.stdout.write(self.style.SUCCESS('Successfully imported football data!'))