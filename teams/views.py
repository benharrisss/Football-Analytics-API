from datetime import datetime
from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count, Sum, Case, When, IntegerField, Min, Max
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Team
from .serializers import TeamSerializer
from matches.models import Match
from teams.services.team_dna import calculate_team_dna, parse_season

class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all().order_by('name')
    serializer_class = TeamSerializer

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
            Q(home_team__name=team.name) | 
            Q(away_team__name=team.name))

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
            Q(home_team__name=team.name, ft_result='H') | 
            Q(away_team__name=team.name, ft_result='A')
        ).count()

        draws = matches.filter(ft_result='D').count()

        losses = matches.filter(
            Q(home_team__name=team.name, ft_result='A') | 
            Q(away_team__name=team.name, ft_result='H')
        ).count()

        goals_scored = matches.aggregate(total_goals=Sum(Case(
            When(home_team__name=team.name, then='ft_home_goals'),
            When(away_team__name=team.name, then='ft_away_goals'),
            output_field=IntegerField(),
        )))['total_goals'] or 0

        goals_conceded = matches.aggregate(total_goals=Sum(Case(
            When(home_team__name=team.name, then='ft_away_goals'),
            When(away_team__name=team.name, then='ft_home_goals'),
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
                team1_name = Team.objects.get(id=team1_id).name
            if team2_id:
                team2_name = Team.objects.get(id=team2_id).name
        except Team.DoesNotExist:
            return Response({'error': 'One or both team IDs do not exist.'}, status=404)

        if not team1_name or not team2_name:
            return Response({'error': 'Please provide both team1 and team2 query parameters.'}, status=400)
        
        if not Team.objects.filter(name=team1_name).exists():
            return Response({'error': f'Team "{team1_name}" does not exist.'}, status=404)

        if not Team.objects.filter(name=team2_name).exists():
            return Response({'error': f'Team "{team2_name}" does not exist.'}, status=404)

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
            (Q(home_team__name=team1_name) & Q(away_team__name=team2_name)) |
            (Q(home_team__name=team2_name) & Q(away_team__name=team1_name))
        )

        # Apply league filter to see head-to-head for specific league
        if league:
            matches = matches.filter(league__code=league)

            # League filter validation
            if not matches.exists():
                return Response({'error': f'No matches found between {team1_name} and {team2_name} in league {league}.'}, status=400)

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
            Q(home_team__name=team1_name, ft_result='H') | 
            Q(away_team__name=team1_name, ft_result='A')
        ).count()

        team2_wins = matches.filter(
            Q(home_team__name=team2_name, ft_result='H') | 
            Q(away_team__name=team2_name, ft_result='A')
        ).count()

        draws = matches.filter(ft_result='D').count()

        team1_goals = matches.aggregate(total_goals=Sum(Case(
            When(home_team__name=team1_name, then='ft_home_goals'),
            When(away_team__name=team1_name, then='ft_away_goals'),
            output_field=IntegerField(),
        )))['total_goals'] or 0

        team2_goals = matches.aggregate(total_goals=Sum(Case(
            When(home_team__name=team2_name, then='ft_home_goals'),
            When(away_team__name=team2_name, then='ft_away_goals'),
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
            When(home_team__name=team1_name, then='home_red_cards'),
            When(away_team__name=team1_name, then='away_red_cards'),
            output_field=IntegerField(),
        )))['total_reds'] or 0

        team2_reds = matches.aggregate(total_reds=Sum(Case(
            When(home_team__name=team2_name, then='home_red_cards'),
            When(away_team__name=team2_name, then='away_red_cards'),
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

        # League filter validation
        if league:
            team_matches = Match.objects.filter(
                league__code=league).filter(
                Q(home_team=team) | Q(away_team=team)).exists()

            if not team_matches:
                return Response({'error': f'No matches found for {team.name} in league {league}.'}, status=status.HTTP_400_BAD_REQUEST)

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

        league_name = None
        if league:
            league_obj = Match.objects.filter(
                league__code=league).values('league__name').first()
            if league_obj:
                league_name = league_obj['league__name']

        return Response({
            "team": team.name,
            "filters": {
                "league": league_name if league else 'All Leagues',
                "season": season,
                "date_from": date_from,
                "date_to": date_to,
                "last_n": last_n,
            },
            "dna_profile": dna_profile
        })

    # Filtering options
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['league__code']

    # Text search
    search_fields = ['name']

    # Ordering options
    ordering_fields = ['name']

    ordering = ['name']  # Default ordering
