from django.shortcuts import render
from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Match
from .serializers import MatchSerializer
from .filters import MatchFilter

class MatchViewSet(viewsets.ModelViewSet):
    queryset = Match.objects.all().order_by('-match_date')
    serializer_class = MatchSerializer

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


