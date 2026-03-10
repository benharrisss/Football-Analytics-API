from datetime import datetime
from django.shortcuts import render
from django.db.models import Q, Count, Sum, Case, When, IntegerField, Min, Max, Avg, ExpressionWrapper, F, FloatField
from django.db.models.functions import Coalesce, Cast
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Team, Club
from .serializers import TeamSerializer
from matches.models import Match
from teams.services.team_dna import calculate_team_dna, parse_season, get_filtered_matches
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all().order_by('name')
    serializer_class = TeamSerializer
    

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'stats', 'head_to_head']:
            return [AllowAny()]
        return [IsAuthenticated()]


    @extend_schema(
        parameters=[
            OpenApiParameter(name='league', description='Filter by league code e.g E0, E1, E2, E3)', required=False, type=OpenApiTypes.STR),
            OpenApiParameter(name='date_from', description='Start date for stats in YYYY-MM-DD format', required=False, type=OpenApiTypes.STR),
            OpenApiParameter(name='date_to', description='End date for stats in YYYY-MM-DD format', required=False, type=OpenApiTypes.STR),])
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        team = self.get_object()
        league = request.query_params.get('league', None)
        date_from = request.query_params.get('date_from', None)
        date_to = request.query_params.get('date_to', None)

        try:
            if date_from:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            if date_to:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)

        matches = Match.objects.filter(
            Q(home_team__club=team.club) | 
            Q(away_team__club=team.club))

        # Apply league filter to see stats for specific league
        if league:
            matches = matches.filter(league__code=league)

            # League filter validation
            if not matches.exists():
                return Response({'error': f'No matches found for {team.name} in league {league}.'}, status=400)

        # Apply date range filter
        if date_from:
            matches = matches.filter(match_date__gte=date_from)
        if date_to:
            matches = matches.filter(match_date__lte=date_to)

        # If no date range provided, get earliest and latest match dates
        date_bounds = matches.aggregate(
            earliest=Min('match_date'),
            latest=Max('match_date')
        )

        if not date_from:
            date_from = date_bounds['earliest']
        if not date_to:
            date_to = date_bounds['latest']

        matches_played = matches.count()

        wins = matches.filter(
            Q(home_team__club=team.club, ft_result='H') | 
            Q(away_team__club=team.club, ft_result='A')
        ).count()

        draws = matches.filter(ft_result='D').count()

        losses = matches.filter(
            Q(home_team__club=team.club, ft_result='A') | 
            Q(away_team__club=team.club, ft_result='H')
        ).count()

        goals_scored = matches.aggregate(total_goals=Sum(Case(
            When(home_team__club=team.club, then='ft_home_goals'),
            When(away_team__club=team.club, then='ft_away_goals'),
            output_field=IntegerField(),
        )))['total_goals'] or 0

        goals_conceded = matches.aggregate(total_goals=Sum(Case(
            When(home_team__club=team.club, then='ft_away_goals'),
            When(away_team__club=team.club, then='ft_home_goals'),
            output_field=IntegerField(),
        )))['total_goals'] or 0

        goal_difference = goals_scored - goals_conceded

        if matches_played > 0:
            win_percentage = (wins / matches_played) * 100
        else:
            win_percentage = 0.0

        league_name = None
        if league:
            league_obj = Match.objects.filter(
                league__code=league).values('league__name').first()
            if league_obj:
                league_name = league_obj['league__name']

        return Response({
            'team': team.name,
            'league': league_name if league else 'All Leagues',
            'date_from': date_from,
            'date_to': date_to,
            'matches_played': matches_played,
            'wins': wins,
            'draws': draws,
            'losses': losses,
            'goals_scored': goals_scored,
            'goals_conceded': goals_conceded,
            'goal_difference': goal_difference,
            'win_percentage': win_percentage,
        })


    @extend_schema(
        parameters=[
            OpenApiParameter(name='team1_id', description='ID of the first team', required=False, type=OpenApiTypes.INT),
            OpenApiParameter(name='team2_id', description='ID of the second team', required=False, type=OpenApiTypes.INT),
            OpenApiParameter(name='team1', description='Name of the first team (alternative to team1_id)', required=False, type=OpenApiTypes.STR),
            OpenApiParameter(name='team2', description='Name of the second team (alternative to team2_id)', required=False, type=OpenApiTypes.STR),
            OpenApiParameter(name='league', description='Filter by league code e.g E0, E1, E2, E3)', required=False, type=OpenApiTypes.STR),
            OpenApiParameter(name='date_from', description='Start date for head-to-head in YYYY-MM-DD format', required=False, type=OpenApiTypes.STR),
            OpenApiParameter(name='date_to', description='End date for head-to-head in YYYY-MM-DD format', required=False, type=OpenApiTypes.STR),]
    )
    @action(detail=False, methods=['get'])
    def head_to_head(self, request):
        team1_id = request.query_params.get('team1_id', None)
        team2_id = request.query_params.get('team2_id', None)
        team1_name = request.query_params.get('team1', None)
        team2_name = request.query_params.get('team2', None)
        league = request.query_params.get('league', None)
        date_from = request.query_params.get('date_from', None)
        date_to = request.query_params.get('date_to', None)

        # Team name validation
        try:
            if team1_id:
                team1 = Team.objects.get(id=team1_id)
            elif team1_name:
                team1 = Team.objects.filter(name=team1_name).first()
            else:
                return Response({'error': 'Please provide either team1_id or team1 query parameter.'}, status=400)

            if team2_id:
                team2 = Team.objects.get(id=team2_id)
            elif team2_name:
                team2 = Team.objects.filter(name=team2_name).first()
            else:
                return Response({'error': 'Please provide either team2_id or team2 query parameter.'}, status=400)
            
        except Team.DoesNotExist:
            return Response({'error': 'One or both team IDs do not exist.'}, status=404)

        if not team1 or not team2:
            return Response({'error': 'One or both team names could not be found.'}, status=404)

        club1 = team1.club
        club2 = team2.club

        # Date validation
        try:
            if date_from:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            if date_to:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)

        if date_from and date_to and date_from > date_to:
            return Response({'error': 'date_from cannot be after date_to.'}, status=400)

        matches = Match.objects.filter(
            (Q(home_team__club=club1) & Q(away_team__club=club2)) |
            (Q(home_team__club=club2) & Q(away_team__club=club1))
        )

        # Apply league filter to see head-to-head for specific league
        if league:
            matches = matches.filter(league__code=league)

            # League filter validation
            if not matches.exists():
                return Response({'error': f'No matches found between {team1.name} and {team2.name} in league {league}.'}, status=400)

        # Apply date range filter
        if date_from:
            matches = matches.filter(match_date__gte=date_from)
        if date_to:
            matches = matches.filter(match_date__lte=date_to)

        # If no date range provided, get earliest and latest match dates
        date_bounds = matches.aggregate(
            earliest=Min('match_date'),
            latest=Max('match_date')
        )

        if not date_from:
            date_from = date_bounds['earliest']
        if not date_to:
            date_to = date_bounds['latest']
        
        matches = matches.order_by('-match_date')

        total_matches = matches.count()

        team1_wins = matches.filter(
            Q(home_team__club=club1, ft_result='H') | 
            Q(away_team__club=club1, ft_result='A')
        ).count()

        team2_wins = matches.filter(
            Q(home_team__club=club2, ft_result='H') | 
            Q(away_team__club=club2, ft_result='A')
        ).count()

        draws = matches.filter(ft_result='D').count()

        team1_goals = matches.aggregate(total_goals=Sum(Case(
            When(home_team__club=club1, then='ft_home_goals'),
            When(away_team__club=club1, then='ft_away_goals'),
            output_field=IntegerField(),
        )))['total_goals'] or 0

        team2_goals = matches.aggregate(total_goals=Sum(Case(
            When(home_team__club=club2, then='ft_home_goals'),
            When(away_team__club=club2, then='ft_away_goals'),
            output_field=IntegerField(),
        )))['total_goals'] or 0

        goal_difference = team1_goals - team2_goals

        if total_matches > 0:
            team1_win_percentage = (team1_wins / total_matches) * 100
            team2_win_percentage = (team2_wins / total_matches) * 100
        else:
            team1_win_percentage = 0.0
            team2_win_percentage = 0.0
            
        team1_reds = matches.aggregate(total_reds=Sum(Case(
            When(home_team__club=club1, then='home_red_cards'),
            When(away_team__club=club1, then='away_red_cards'),
            output_field=IntegerField(),
        )))['total_reds'] or 0

        team2_reds = matches.aggregate(total_reds=Sum(Case(
            When(home_team__club=club2, then='home_red_cards'),
            When(away_team__club=club2, then='away_red_cards'),
            output_field=IntegerField(),
        )))['total_reds'] or 0

        league_name = None
        if league:
            league_obj = Match.objects.filter(
                league__code=league).values('league__name').first()
            if league_obj:
                league_name = league_obj['league__name']

        return Response({
            'team1': team1_name,
            'team2': team2_name,
            'league': league_name if league else 'All Leagues',
            'date_from': date_from,
            'date_to': date_to,
            'total_matches': total_matches,
            'team1_wins': team1_wins,
            'team1_win_percentage': team1_win_percentage,
            'team2_wins': team2_wins,
            'team2_win_percentage': team2_win_percentage,
            'draws': draws,
            'team1_goals': team1_goals,
            'team2_goals': team2_goals,
            'goal_difference': goal_difference,
            'team1_red_cards': team1_reds,
            'team2_red_cards': team2_reds,
        })

    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='league', description='Filter by league code e.g E0, E1, E2, E3)', required=False, type=OpenApiTypes.STR),
            OpenApiParameter(name='season', description='Season format e.g. 20/21, 2023-2024 etc.', required=False, type=OpenApiTypes.STR),
            OpenApiParameter(name='date_from', description='Start date for DNA calculation in YYYY-MM-DD format (overrides season if both provided)', required=False, type=OpenApiTypes.STR),
            OpenApiParameter(name='date_to', description='End date for DNA calculation in YYYY-MM-DD format (overrides season if both provided)', required=False, type=OpenApiTypes.STR),
            OpenApiParameter(name='last_n', description='Calculate DNA based on last N matches instead of date range or season', required=False, type=OpenApiTypes.INT),
        ]
    )
    @action(detail=True, methods=['get'])
    def dna(self, request, pk=None):
        team = self.get_object()
        league = request.query_params.get('league', None)
        season = request.query_params.get('season', None)
        date_from = request.query_params.get('date_from', None)
        date_to = request.query_params.get('date_to', None)
        last_n = request.query_params.get('last_n', None)

        # Season parsing and validation
        if season:
            try:
                date_from, date_to = parse_season(season)
            except ValueError:
                return Response({'error': 'Invalid season format. Use "YYYY-YYYY", "YYYY/YYYY", "YY-YY", "YY/YY" or "YYYY".'}, status=status.HTTP_400_BAD_REQUEST)

        # Date validation (only if season is not provided)
        if date_from and not season:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Invalid date_from format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if date_to and not season:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Invalid date_to format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        if date_from and date_to and date_from > date_to:
            return Response({'error': 'date_from cannot be after date_to.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # last_n validation
        if last_n:
            try:
                last_n = int(last_n)
                if last_n <= 0:
                    raise ValueError
            except ValueError:
                return Response({'error': 'last_n must be a positive integer.'}, status=status.HTTP_400_BAD_REQUEST)

        matches = get_filtered_matches(team=team, league=league, date_from=date_from, date_to=date_to, last_n=last_n)

        if not matches.exists():
            return Response({'error': 'No matches found for the given filters to calculate DNA.'}, status=status.HTTP_400_BAD_REQUEST)

        league_qs = matches.values_list('league__name', flat=True).distinct()

        # League filter validation
        if league:
            team_matches = Match.objects.filter(
                league__code=league).filter(
                Q(home_team__club=team.club) | Q(away_team__club=team.club)).exists()

            if not team_matches:
                return Response({'error': f'No matches found for {team.name} in league {league}.'}, status=status.HTTP_400_BAD_REQUEST)

            display_league = matches.first().league.name
        elif league_qs.count() == 1:
            display_league = league_qs.first()
        else:
            display_league = 'All Leagues'    

        # Calculate Team DNA using the service function
        dna_profile = calculate_team_dna(
            team=team,
            league=league,
            date_from=date_from,
            date_to=date_to,
            last_n=last_n
        )

        if not dna_profile:
            return Response({'error': 'No matches found for the given filters to calculate DNA.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "team": team.name,
            "filters": {
                "league": display_league,
                "season": season,
                "date_from": date_from,
                "date_to": date_to,
                "last_n": last_n,
            },
            "dna_profile": dna_profile
        })


    @extend_schema(
        parameters=[
            OpenApiParameter(name='league', description='Filter by league code e.g E0, E1, E2, E3)', required=False, type=OpenApiTypes.STR),
            OpenApiParameter(name='season', description='Season format e.g. 20/21, 2023-2024 etc.', required=False, type=OpenApiTypes.STR),
            OpenApiParameter(name='limit', description='Number of teams to return', required=False, type=OpenApiTypes.INT),
            OpenApiParameter(name='min_games', description='Minimum number of games played to be included in the ranking', required=False, type=OpenApiTypes.INT),])
    @action(detail=False, methods=['get'])
    def best_attack(self, request):
        league = request.query_params.get('league')
        season = request.query_params.get('season')
        limit = int(request.query_params.get('limit', 10))

        if season:
            default_min_games = 20
        else:
            default_min_games = 100

        min_games = int(request.query_params.get('min_games', default_min_games))

        matches = Match.objects.all()

        if league:
            matches = matches.filter(league__code=league)

        if season:
            date_from, date_to = parse_season(season)
            matches = matches.filter(match_date__range=(date_from, date_to))

        results = []

        for club in Club.objects.all():

            home_stats = matches.filter(home_team__club=club).aggregate(
                games=Count('id'),
                goals=Coalesce(Sum('ft_home_goals'), 0),
                shots=Coalesce(Sum('home_shots'), 0)
            )

            away_stats = matches.filter(away_team__club=club).aggregate(
                games=Count('id'),
                goals=Coalesce(Sum('ft_away_goals'), 0),
                shots=Coalesce(Sum('away_shots'), 0)
            )

            games = home_stats["games"] + away_stats["games"]

            if games == 0:
                continue

            if games < min_games:
                continue

            goals = home_stats["goals"] + away_stats["goals"]
            shots = home_stats["shots"] + away_stats["shots"]

            goals_per_game = goals / games
            shots_per_game = shots / games

            attack_score = (goals_per_game * 0.8) + (shots_per_game * 0.2)

            results.append({
                "club": club.name,
                "games": games,
                "goals_per_game": round(goals_per_game, 2),
                "shots_per_game": round(shots_per_game, 2),
                "attack_score": round(attack_score, 2)
            })

        results = sorted(results, key=lambda x: x['attack_score'], reverse=True)[:limit]

        return Response(results)

    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='league', description='Filter by league code e.g E0, E1, E2, E3)', required=False, type=OpenApiTypes.STR),
            OpenApiParameter(name='season', description='Season format e.g. 20/21, 2023-2024 etc.', required=False, type=OpenApiTypes.STR),
            OpenApiParameter(name='limit', description='Number of teams to return', required=False, type=OpenApiTypes.INT),
            OpenApiParameter(name='min_games', description='Minimum number of games played to be included in the ranking', required=False, type=OpenApiTypes.INT),])
    @action(detail=False, methods=['get'])
    def best_defence(self, request):
        league = request.query_params.get('league')
        season = request.query_params.get('season')
        limit = int(request.query_params.get('limit', 10))

        if season:
            default_min_games = 20
        else:
            default_min_games = 100

        min_games = int(request.query_params.get('min_games', default_min_games))

        matches = Match.objects.all()

        if league:
            matches = matches.filter(league__code=league)

        if season:
            date_from, date_to = parse_season(season)
            matches = matches.filter(match_date__range=(date_from, date_to))

        results = []

        for club in Club.objects.all():

            home_stats = matches.filter(home_team__club=club).aggregate(
                games=Count('id'),
                goals_conceded=Coalesce(Sum('ft_away_goals'), 0),
                shots_conceded=Coalesce(Sum('away_shots'), 0)
            )

            away_stats = matches.filter(away_team__club=club).aggregate(
                games=Count('id'),
                goals_conceded=Coalesce(Sum('ft_home_goals'), 0),
                shots_conceded=Coalesce(Sum('home_shots'), 0)
            )

            games = home_stats["games"] + away_stats["games"]

            if games == 0:
                continue

            if games < min_games:
                continue

            goals_conceded = home_stats["goals_conceded"] + away_stats["goals_conceded"]
            shots_conceded = home_stats["shots_conceded"] + away_stats["shots_conceded"]

            goals_conceded_per_game = goals_conceded / games
            shots_conceded_per_game = shots_conceded / games

            defence_score = 1 / ((goals_conceded_per_game * 0.8) + (shots_conceded_per_game * 0.2))

            results.append({
                "club": club.name,
                "games": games,
                "goals_conceded_per_game": round(goals_conceded_per_game, 2),
                "shots_conceded_per_game": round(shots_conceded_per_game, 2),
                "defence_score": round(defence_score, 2)
            })

        results = sorted(results, key=lambda x: x['defence_score'], reverse=True)[:limit]

        return Response(results)


    @extend_schema(
        parameters=[
            OpenApiParameter(name='league', description='Filter by league code e.g E0, E1, E2, E3)', required=False, type=OpenApiTypes.STR),
            OpenApiParameter(name='season', description='Season format e.g. 20/21, 2023-2024 etc.', required=False, type=OpenApiTypes.STR),
            OpenApiParameter(name='limit', description='Number of teams to return', required=False, type=OpenApiTypes.INT),])
    @action(detail=False, methods=['get'])
    def over_under_performing(self, request):
        league = request.query_params.get('league')
        season = request.query_params.get('season')
        limit = int(request.query_params.get('limit', 24))

        if not league:
            return Response({'error': 'League code is required'}, status=status.HTTP_400_BAD_REQUEST)

        matches = Match.objects.filter(league__code=league)

        if season:
            try:
                date_from, date_to = parse_season(season)
                matches = matches.filter(match_date__range=(date_from, date_to))
            except ValueError:
                return Response({'error': 'Invalid season format. Use "YYYY-YYYY", "YYYY/YYYY", "YY-YY", "YY/YY" or "YYYY".'}, status=status.HTTP_400_BAD_REQUEST)

        if not matches.exists():
            return Response({'error': 'No matches found for the given filters.'}, status=status.HTTP_404_NOT_FOUND)

        results = []
        clubs = Club.objects.filter(Q(teams__home_matches__in=matches) | Q(teams__away_matches__in=matches)).distinct()

        for club in clubs:
            club_matches = matches.filter(Q(home_team__club=club) | Q(away_team__club=club))
            total_matches = club_matches.count()
            elo_matches_used = 0

            actual_points = 0
            expected_points = 0
            goals_for = 0
            goals_against = 0

            for match in club_matches:
                if match.home_elo_pre is None or match.away_elo_pre is None:
                    continue
                
                elo_matches_used += 1

                if match.home_team.club == club:
                    team_elo = match.home_elo_pre
                    opponent_elo = match.away_elo_pre
                    goals_for += match.ft_home_goals
                    goals_against += match.ft_away_goals

                    if match.ft_result == 'H':
                        actual_points += 3
                    elif match.ft_result == 'D':
                        actual_points += 1
                
                else:
                    team_elo = match.away_elo_pre
                    opponent_elo = match.home_elo_pre
                    goals_for += match.ft_away_goals
                    goals_against += match.ft_home_goals

                    if match.ft_result == 'A':
                        actual_points += 3
                    elif match.ft_result == 'D':
                        actual_points += 1
                
                expected_win_prob = 1 / (1 + 10 ** ((opponent_elo - team_elo) / 400))
                expected_points += expected_win_prob * 3

            if total_matches == 0:
                continue
            
            coverage_percentage = (elo_matches_used / total_matches) * 100
            # Need at least 50% of matches with ELO data to consider evaluating performance vs expectations
            if coverage_percentage < 50:
                continue

            results.append({
                "team": club.name,
                "actual_points": actual_points,
                "expected_points": round(expected_points, 2),
                "goal_difference": goals_for - goals_against,
                "elo_coverage_percentage": round(coverage_percentage, 2)
            })

        if not results:
            return Response({'error': 'insufficient ELO data to evaluate performance for teams in this league/season.'}, status=status.HTTP_404_NOT_FOUND)

        # Actual table position
        actual_sorted = sorted(results, key=lambda x: (-x['actual_points'], -x['goal_difference'], x['team']))

        for index, team in enumerate(actual_sorted, start=1):
            team['actual_position'] = index

        # Expected table position
        expected_sorted = sorted(actual_sorted, key=lambda x: (-x['expected_points'], x['team']))

        final_results = []

        for index, team in enumerate(expected_sorted, start=1):
            performance_diff = team['actual_points'] - team['expected_points']

            # +/1 point threshold for over/under performing
            if abs(performance_diff) <= 1:
                performance = 'Performing as Expected'
            elif performance_diff > 1:
                performance = 'Overperforming'
            else:
                performance = 'Underperforming'

            final_results.append({
                "team": team['team'],
                "expected_position": index,
                "actual_position": team['actual_position'],
                "actual_points": team['actual_points'],
                "expected_points": team['expected_points'],
                "goal_difference": team['goal_difference'],
                "performance_diff": round(performance_diff, 2),
                "performance": performance,
                "elo_coverage_percentage": team['elo_coverage_percentage']
            })
        
        return Response(final_results[:limit])


    # Filtering options
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['league__code']

    # Text search
    search_fields = ['name']

    # Ordering options
    ordering_fields = ['name']

    ordering = ['name']  # Default ordering
