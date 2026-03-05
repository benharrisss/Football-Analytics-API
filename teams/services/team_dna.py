from datetime import date
import re
from django.db.models import Q, Avg, Sum, F, Case, When, FloatField
from matches.models import Match
from teams.models import Team, Club


def get_season_date_range(season_start_year):
    start_date = date(season_start_year, 8, 1)
    end_date = date(season_start_year + 1, 5, 31)
    return start_date, end_date


def parse_season(season_str):
    match = re.match(r'(\d{2}|\d{4})[-/](\d{2}|\d{4})$', season_str)
    if match:
        start, end = match.groups()

        if len(start) == 2:
            start_year = int(start) + 2000
        else:
            start_year = int(start)
        
        if len(end) == 2:
            end_year = int(end) + 2000
        else:
            end_year = int(end)

        if end_year != start_year + 1:
            raise ValueError("Season end year must be exactly one year after start year.")

        return get_season_date_range(start_year)
    
    if season_str.isdigit() and len(season_str) in [2, 4]:
        if len(season_str) == 2:
            start_year = int(season_str) + 2000
        else:
            start_year = int(season_str)
        
        return get_season_date_range(start_year)
    
    raise ValueError("Invalid season format. Use 'YYYY-YYYY', 'YYYY/YYYY', 'YY-YY', 'YY/YY' or 'YYYY'.")


def get_filtered_matches(team, league=None, date_from=None, date_to=None, last_n=None):
    queryset = Match.objects.filter(
        Q(home_team__club=team.club) | Q(away_team__club=team.club)
    )
    if league:
        queryset = queryset.filter(league__code=league)

    if date_from:
        queryset = queryset.filter(match_date__gte=date_from)

    if date_to:
        queryset = queryset.filter(match_date__lte=date_to)

    queryset = queryset.order_by('-match_date')

    if last_n:
        queryset = queryset[:last_n]
    
    return queryset


def calculate_raw_stats(team, matches):
    if not matches.exists():
        return None
    aggregated = matches.aggregate(
        avg_shots=Avg(Case(
            When(home_team__club=team.club, then=F('home_shots')),
            When(away_team__club=team.club, then=F('away_shots')),
            output_field=FloatField()
        )),
        avg_corners=Avg(Case(
            When(home_team__club=team.club, then=F('home_corners')),
            When(away_team__club=team.club, then=F('away_corners')),
            output_field=FloatField()
        )),
        avg_fouls=Avg(Case(
            When(home_team__club=team.club, then=F('home_fouls')),
            When(away_team__club=team.club, then=F('away_fouls')),
            output_field=FloatField()
        )),
        avg_yellows=Avg(Case(
            When(home_team__club=team.club, then=F('home_yellow_cards')),
            When(away_team__club=team.club, then=F('away_yellow_cards')),
            output_field=FloatField()
        )),
        avg_reds=Avg(Case(
            When(home_team__club=team.club, then=F('home_red_cards')),
            When(away_team__club=team.club, then=F('away_red_cards')),
            output_field=FloatField()
        )),
        goals_scored=Sum(Case(
            When(home_team__club=team.club, then=F('ft_home_goals')),
            When(away_team__club=team.club, then=F('ft_away_goals')),
            output_field=FloatField()
        )),
        goals_conceded=Sum(Case(
            When(home_team__club=team.club, then=F('ft_away_goals')),
            When(away_team__club=team.club, then=F('ft_home_goals')),
            output_field=FloatField()
        )),
        shots_conceded=Sum(Case(
            When(home_team__club=team.club, then=F('away_shots')),
            When(away_team__club=team.club, then=F('home_shots')),
            output_field=FloatField()
        )),
        shots_on_target=Sum(Case(
            When(home_team__club=team.club, then=F('home_shots_on_target')),
            When(away_team__club=team.club, then=F('away_shots_on_target')),
            output_field=FloatField()
        )),
        avg_shot_difference=Avg(Case(
            When(home_team__club=team.club, then=F('home_shots') - F('away_shots')),
            When(away_team__club=team.club, then=F('away_shots') - F('home_shots')),
            output_field=FloatField()
        )),
        avg_corner_difference=Avg(Case(
            When(home_team__club=team.club, then=F('home_corners') - F('away_corners')),
            When(away_team__club=team.club, then=F('away_corners') - F('home_corners')),
            output_field=FloatField()
        )),
    )

    matches_played = matches.count()

    # Raw DNA stats
    avg_shots = aggregated['avg_shots'] or 0
    avg_corners = aggregated['avg_corners'] or 0
    avg_fouls = aggregated['avg_fouls'] or 0
    avg_yellows = aggregated['avg_yellows'] or 0
    avg_reds = aggregated['avg_reds'] or 0
    goals_scored = aggregated['goals_scored'] or 0
    goals_conceded = aggregated['goals_conceded'] or 0
    shots_conceded = aggregated['shots_conceded'] or 0
    shots_on_target = aggregated['shots_on_target'] or 0
    avg_shot_diff = aggregated['avg_shot_difference'] or 0
    avg_corner_diff = aggregated['avg_corner_difference'] or 0

    # Raw calculations
    pressure_raw = (avg_shots * 0.7) + (avg_corners * 0.3)

    if shots_on_target > 0:
        clinicality_raw = (goals_scored / shots_on_target)
    else:
        clinicality_raw = 0

    discipline_raw = ((avg_fouls * 0.5) + (avg_yellows * 2) + (avg_reds * 5))

    if matches_played > 0:
        defensive_stability_raw = ((goals_conceded * 0.8) + (shots_conceded * 0.2)) / matches_played
    else:
        defensive_stability_raw = 0

    control_raw = (avg_shot_diff * 0.7) + (avg_corner_diff * 0.3)

    return {
        'pressure': pressure_raw,
        'clinicality': clinicality_raw,
        'discipline': discipline_raw,
        'defensive_stability': defensive_stability_raw,
        'control': control_raw,
    }


def get_league_baselines(teams_raw_stats):
    if not teams_raw_stats:
        return None
    baselines = {}

    for stat in ['pressure', 'clinicality', 'discipline', 'defensive_stability', 'control']:
        stat_values = [team[stat] for team in teams_raw_stats]
        baselines[stat] = {'min': min(stat_values), 'max': max(stat_values)}

    return baselines


def normalise_stats(value, min_value, max_value, invert=False):
    # Neutral baseline if all teams have the same value
    if max_value == min_value:
        return 50

    scaled = (value - min_value) / (max_value - min_value)

    if invert:
        scaled = 1 - scaled

    score = round(scaled * 100, 2)
    
    return max(0, min(score, 100))


def calculate_team_dna(team, league=None, date_from=None, date_to=None, last_n=None):
    matches = get_filtered_matches(team, league, date_from, date_to, last_n)
    raw_stats = calculate_raw_stats(team, matches)

    if not raw_stats:
        return None

    relevant_clubs = Club.objects.all()

    teams_raw = []
    for club in relevant_clubs:
        representative_team = club.teams.first()
        if not representative_team:
            continue

        t_matches = get_filtered_matches(representative_team, league, date_from, date_to, last_n)
        t_raw_stats = calculate_raw_stats(representative_team, t_matches)
        
        if t_raw_stats and t_matches.exists():
            teams_raw.append(t_raw_stats)

    baselines = get_league_baselines(teams_raw)

    if not baselines:
        baselines = {stat: {'min': 0, 'max': max(raw_stats[stat], 1)} for stat in raw_stats.keys()}

    dna_profile = {
        'pressure': normalise_stats(raw_stats['pressure'], 
            baselines['pressure']['min'], baselines['pressure']['max']
        ),
        'clinicality': normalise_stats(raw_stats['clinicality'], 
            baselines['clinicality']['min'], baselines['clinicality']['max']
        ),
        'discipline': normalise_stats(raw_stats['discipline'], 
            baselines['discipline']['min'], baselines['discipline']['max'], invert=True
        ),
        'defensive_stability': normalise_stats(raw_stats['defensive_stability'], 
            baselines['defensive_stability']['min'], baselines['defensive_stability']['max'], invert=True
        ),
        'control': normalise_stats(raw_stats['control'], 
            baselines['control']['min'], baselines['control']['max']
        ),
    }

    return dna_profile

    