from django.shortcuts import render
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import F, Q, Sum, Max, Count, Case, When, IntegerField
from rest_framework import viewsets, status
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Match
from teams.models import Club
from .serializers import MatchSerializer
from .filters import MatchFilter
from teams.services.team_dna import parse_season
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

class MatchViewSet(viewsets.ModelViewSet):
    queryset = Match.objects.all().order_by('-match_date')
    serializer_class = MatchSerializer
    

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'league_table', 'biggest_upsets']:
            return [AllowAny()]
        return [IsAuthenticated()]


    @extend_schema(
        parameters=[
            OpenApiParameter(name='league', description='Filter by league code e.g E0, E1, E2, E3)', required=False, type=OpenApiTypes.STR),
            OpenApiParameter(name='season', description='Season format e.g. 20/21, 2023-2024 etc.', required=False, type=OpenApiTypes.STR),
            OpenApiParameter(name='elo_diff', description='Minimum ELO difference to consider a match an upset', required=False, type=OpenApiTypes.FLOAT),
            OpenApiParameter(name='limit', description='Number of matches to return', required=False, type=OpenApiTypes.INT),])
    @action(detail=False, methods=['get'])
    def upsets(self, request):
        league = request.query_params.get('league')
        season = request.query_params.get('season')
        elo_diff_threshold = float(request.query_params.get('elo_diff', 200))
        limit = int(request.query_params.get('limit', 20))

        matches = Match.objects.all()

        if league:
            matches = matches.filter(league__code=league)
        
        if season:
            date_from, date_to = parse_season(season)
            matches = matches.filter(match_date__gte=date_from, match_date__lte=date_to)

        upsets = []
        for match in matches:
            home_elo = match.home_elo_pre
            away_elo = match.away_elo_pre

            if home_elo is None or away_elo is None:
                continue

            diff = abs(home_elo - away_elo)

            if diff < elo_diff_threshold:
                continue

            # determine winner
            if match.ft_home_goals > match.ft_away_goals:
                winner = 'home'
            elif match.ft_home_goals < match.ft_away_goals:
                winner = 'away'
            else:
                continue  # skip draws

            if winner == 'home' and home_elo < away_elo:
                upsets.append(match)
            elif winner == 'away' and away_elo < home_elo:
                upsets.append(match)

        upsets = sorted(upsets, key=lambda m: abs(m.home_elo_pre - m.away_elo_pre), reverse=True)[:limit]
        serializer = self.get_serializer(upsets, many=True)

        return Response(serializer.data)

    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='league', description='Filter by league code e.g E0, E1, E2, E3)', required=False, type=OpenApiTypes.STR),
            OpenApiParameter(name='season', description='Season format e.g. 20/21, 2023-2024 etc.', required=False, type=OpenApiTypes.STR),
            OpenApiParameter(name='min_odds', description='Minimum odds to consider a match an upset', required=False, type=OpenApiTypes.FLOAT),
            OpenApiParameter(name='limit', description='Number of matches to return', required=False, type=OpenApiTypes.INT),])
    @action(detail=False, methods=['get'])
    def upsets_by_odds(self, request):
        league = request.query_params.get('league')
        season = request.query_params.get('season')
        min_odds = float(request.query_params.get('min_odds', 8.0))
        limit = int(request.query_params.get('limit', 20))

        matches = Match.objects.all()

        if league:
            matches = matches.filter(league__code=league)
        
        if season:
            date_from, date_to = parse_season(season)
            matches = matches.filter(match_date__gte=date_from, match_date__lte=date_to)

        upsets = []
        for match in matches:
            if match.ft_home_goals > match.ft_away_goals:
                if match.home_win_odds and match.home_win_odds >= min_odds:
                    upsets.append(match)
            
            elif match.ft_home_goals < match.ft_away_goals:
                if match.away_win_odds and match.away_win_odds >= min_odds:
                    upsets.append(match)
            
        upsets = sorted(upsets, key=lambda m: max(m.home_win_odds or 0, m.away_win_odds or 0), reverse=True)[:limit]
        serializer = self.get_serializer(upsets, many=True)

        return Response(serializer.data)


    @extend_schema(
        parameters=[
            OpenApiParameter(name='limit', description='Number of matches to return', required=False, type=OpenApiTypes.INT),])
    @action(detail=False, methods=['get'])
    def biggest_upsets(self, request):
        limit = int(request.query_params.get('limit', 20))
        
        matches = Match.objects.filter(home_elo_pre__isnull=False, away_elo_pre__isnull=False)

        upsets = []
        for match in matches:
            home_elo = match.home_elo_pre
            away_elo = match.away_elo_pre

            diff = abs(home_elo - away_elo)

            if match.ft_home_goals > match.ft_away_goals and home_elo < away_elo:
                upsets.append(match)
            elif match.ft_home_goals < match.ft_away_goals and away_elo < home_elo:
                upsets.append(match)

        upsets = sorted(upsets, key=lambda m: abs(m.home_elo_pre - m.away_elo_pre), reverse=True)[:limit]
        serializer = self.get_serializer(upsets, many=True)

        return Response(serializer.data)

    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='league', description='Filter by league code e.g E0, E1, E2, E3)', required=True, type=OpenApiTypes.STR),
            OpenApiParameter(name='season', description='Season format e.g. 20/21, 2023-2024 etc.', required=False, type=OpenApiTypes.STR),])
    @action(detail=False, methods=['get'])
    def league_table(self, request):
        league_code = request.query_params.get('league')
        season = request.query_params.get('season')

        if not league_code:
            return Response({"error": "League code is required"}, status=status.HTTP_400_BAD_REQUEST)

        if league_code not in ['E0', 'E1', 'E2', 'E3']:
            return Response({"error": "Invalid league code. Valid options are E0, E1, E2, E3."}, status=status.HTTP_400_BAD_REQUEST)

        matches = Match.objects.filter(league__code=league_code)

        if not matches.exists():
            return Response({"error": f"No matches found for the specified league {league_code}"}, status=status.HTTP_404_NOT_FOUND)

        # Optional season filtering for specific league tables
        if season:
            try:
                date_from, date_to = parse_season(season)
                matches = matches.filter(match_date__gte=date_from, match_date__lte=date_to)
            except ValueError:
                return Response({"error": "Invalid season format."}, status=status.HTTP_400_BAD_REQUEST)
            
            if not matches.exists():
                return Response({"error": f"No matches found for the specified league {league_code} in season {season}"}, status=status.HTTP_404_NOT_FOUND)

        table = []

        clubs = Club.objects.filter(
            Q(teams__home_matches__in=matches) | Q(teams__away_matches__in=matches)
        ).distinct()

        for club in clubs:
            club_matches = matches.filter(
                Q(home_team__club=club) | Q(away_team__club=club)
            )

            played = club_matches.count()
            if played == 0:
                continue
            
            wins = club_matches.filter(
                Q(home_team__club=club, ft_result='H') | Q(away_team__club=club, ft_result='A')
            ).count()

            draws = club_matches.filter(ft_result='D').count()

            losses = club_matches.filter(
                Q(home_team__club=club, ft_result='A') | Q(away_team__club=club, ft_result='H')
            ).count()

            goals_for = club_matches.aggregate(total=Sum(
                Case(
                    When(home_team__club=club, then='ft_home_goals'),
                    When(away_team__club=club, then='ft_away_goals'),
                    output_field=IntegerField()
                )
            ))['total'] or 0

            goals_against = club_matches.aggregate(total=Sum(
                Case(
                    When(home_team__club=club, then='ft_away_goals'),
                    When(away_team__club=club, then='ft_home_goals'),
                    output_field=IntegerField()
                )
            ))['total'] or 0

            goal_difference = goals_for - goals_against
            points = (wins * 3) + draws

            table.append({
                "team": club.name,
                "played": played,
                "wins": wins,
                "draws": draws,
                "losses": losses,
                "goals_for": goals_for,
                "goals_against": goals_against,
                "goal_difference": goal_difference,
                "points": points
            })

        table = sorted(table, key=lambda x: (-x['points'], -x['goal_difference'], -x['goals_for'], x['team']))

        new_table = []

        for index, team in enumerate(table, start=1):
            new_table.append({
                "position": index,
                "team": team['team'],
                "played": team['played'],
                "wins": team['wins'],
                "draws": team['draws'],
                "losses": team['losses'],
                "goals_for": team['goals_for'],
                "goals_against": team['goals_against'],
                "goal_difference": team['goal_difference'],
                "points": team['points'],
            })
        
        return Response(new_table)


    @extend_schema(
        parameters=[
            OpenApiParameter(name='league', description='Filter by league code e.g E0, E1, E2, E3)', required=True, type=OpenApiTypes.STR),
            OpenApiParameter(name='season', description='Season format e.g. 20/21, 2023-2024 etc.', required=False, type=OpenApiTypes.STR),])
    @action(detail=False, methods=['get'])
    def league_stats(self, request):
        league_code = request.query_params.get('league')
        season = request.query_params.get('season')

        if not league_code:
            return Response({"error": "League code is required"}, status=status.HTTP_400_BAD_REQUEST)

        if league_code not in ['E0', 'E1', 'E2', 'E3']:
            return Response({"error": "Invalid league code. Valid options are E0, E1, E2, E3."}, status=status.HTTP_400_BAD_REQUEST)

        matches = Match.objects.filter(league__code=league_code)
        league_name = matches.values_list('league__name', flat=True).first()

        if season:
            try:
                date_from, date_to = parse_season(season)
                matches = matches.filter(match_date__gte=date_from, match_date__lte=date_to)
            except ValueError:
                return Response({"error": "Invalid season format."}, status=status.HTTP_400_BAD_REQUEST)

        total_matches = matches.count()

        if total_matches == 0:
            return Response({"error": f"No matches found for the specified league {league_code} in season {season}"}, status=status.HTTP_404_NOT_FOUND)

        total_goals = matches.aggregate(total=Sum(F('ft_home_goals') + F('ft_away_goals')))['total'] or 0
        total_shots = matches.aggregate(total=Sum(F('home_shots') + F('away_shots')))['total'] or 0
        total_corners = matches.aggregate(total=Sum(F('home_corners') + F('away_corners')))['total'] or 0
        
        total_yellow_cards = matches.aggregate(total=Sum(F('home_yellow_cards') + F('away_yellow_cards')))['total'] or 0
        total_red_cards = matches.aggregate(total=Sum(F('home_red_cards') + F('away_red_cards')))['total'] or 0
        total_fouls = matches.aggregate(total=Sum(F('home_fouls') + F('away_fouls')))['total'] or 0

        home_wins = matches.filter(ft_result='H').count()
        away_wins = matches.filter(ft_result='A').count()
        draws = matches.filter(ft_result='D').count()

        highest_scoring_match = matches.aggregate(max_goals=Max(F('ft_home_goals') + F('ft_away_goals')))['max_goals'] or 0

        clean_sheet_matches = matches.filter(
            Q(ft_home_goals=0) | Q(ft_away_goals=0)
        ).count()

        response_data = {
            "league": league_code,
            "league_name": league_name,
            "season": season if season else "All Time",
            "matches_played": total_matches,
            "average_goals_per_match": round(total_goals / total_matches, 2),
            "average_shots_per_match": round(total_shots / total_matches, 2),
            "average_corners_per_match": round(total_corners / total_matches, 2),
            "average_yellow_cards_per_match": round(total_yellow_cards / total_matches, 2),
            "average_red_cards_per_match": round(total_red_cards / total_matches, 2),
            "average_fouls_per_match": round(total_fouls / total_matches, 2),
            "home_win_percentage": round((home_wins / total_matches) * 100, 2),
            "away_win_percentage": round((away_wins / total_matches) * 100, 2),
            "draw_percentage": round((draws / total_matches) * 100, 2),
            "most_goals_in_a_match": highest_scoring_match,
            "clean_sheet_percentage": round((clean_sheet_matches / total_matches) * 100, 2),
        }

        return Response(response_data)


    # Filtering options
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = MatchFilter

    # Text search
    search_fields = [
        'home_team__name',
        'away_team__name',
    ]

    # Ordering options
    ordering_fields = [
        'match_date',
        'ft_home_goals',
        'ft_away_goals',
        'home_elo_pre',
        'away_elo_pre',
    ]

    ordering = ['-match_date']  # Default ordering


