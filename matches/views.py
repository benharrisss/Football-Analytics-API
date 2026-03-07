from django.shortcuts import render
from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import F
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Match
from .serializers import MatchSerializer
from .filters import MatchFilter
from teams.services.team_dna import parse_season

class MatchViewSet(viewsets.ModelViewSet):
    queryset = Match.objects.all().order_by('-match_date')
    serializer_class = MatchSerializer

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


