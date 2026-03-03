from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count, Sum, Case, When, IntegerField
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Team
from .serializers import TeamSerializer
from matches.models import Match

class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all().order_by('name')
    serializer_class = TeamSerializer

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        team = self.get_object()
        league_code = request.query_params.get('league', None)

        matches = Match.objects.filter(Q(home_team__name=team.name) | Q(away_team__name=team.name))

        # Apply league filter to see stats for specific league
        if league_code:
            matches = matches.filter(league__code=league_code)

        matches_played = matches.count()

        wins = matches.filter(Q(
            home_team__name=team.name, ft_result='H') | Q(away_team__name=team.name, ft_result='A')
        ).count()

        draws = matches.filter(ft_result='D').count()

        losses = matches.filter(Q(
            home_team__name=team.name, ft_result='A') | Q(away_team__name=team.name, ft_result='H')
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

        return Response({
            'team': team.name,
            'league': league_code if league_code else 'All Leagues',
            'matches_played': matches_played,
            'wins': wins,
            'draws': draws,
            'losses': losses,
            'goals_scored': goals_scored,
            'goals_conceded': goals_conceded,
            'goal_difference': goal_difference,
            'win_percentage': win_percentage,
        })


    # Filtering options
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['league__code']

    # Text search
    search_fields = ['name']

    # Ordering options
    ordering_fields = ['name']

    ordering = ['name']  # Default ordering
