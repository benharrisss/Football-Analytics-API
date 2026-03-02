import django_filters
from .models import Match

class MatchFilter(django_filters.FilterSet):
    # Date range filter
    date_from = django_filters.DateFilter(field_name='match_date', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='match_date', lookup_expr='lte')

    class Meta:
        model = Match
        fields = [
            'league__code',
            'home_team__name',
            'away_team__name',
            'match_date',
            'ft_result',
        ]