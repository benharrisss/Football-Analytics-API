from django.db import models
from teams.models import Team, League

class Match(models.Model):
    RESULT_CHOICES = [
        ('H', 'Home Win'),
        ('A', 'Away Win'),
        ('D', 'Draw'),
    ]

    # Basic Match Info
    league = models.ForeignKey(League, related_name='matches', on_delete=models.CASCADE)
    match_date = models.DateField()
    match_time = models.TimeField(null=True, blank=True)
    home_team = models.ForeignKey(Team, related_name='home_matches', on_delete=models.CASCADE)
    away_team = models.ForeignKey(Team, related_name='away_matches', on_delete=models.CASCADE)

    # Goals & Results
    ft_home_goals = models.IntegerField()
    ft_away_goals = models.IntegerField()
    ft_result = models.CharField(max_length=1, choices=RESULT_CHOICES)

    ht_home_goals = models.IntegerField(null=True, blank=True)
    ht_away_goals = models.IntegerField(null=True, blank=True)
    ht_result = models.CharField(max_length=1, choices=RESULT_CHOICES, null=True, blank=True)

    # Match Statistics
    home_shots = models.IntegerField(null=True, blank=True)
    away_shots = models.IntegerField(null=True, blank=True)

    home_shots_on_target = models.IntegerField(null=True, blank=True)
    away_shots_on_target = models.IntegerField(null=True, blank=True)

    home_fouls = models.IntegerField(null=True, blank=True)
    away_fouls = models.IntegerField(null=True, blank=True)

    home_corners = models.IntegerField(null=True, blank=True)
    away_corners = models.IntegerField(null=True, blank=True)

    home_yellow_cards = models.IntegerField(null=True, blank=True)
    away_yellow_cards = models.IntegerField(null=True, blank=True)

    home_red_cards = models.IntegerField(null=True, blank=True)
    away_red_cards = models.IntegerField(null=True, blank=True)

    # Elo & Form
    home_elo_pre = models.FloatField(null=True, blank=True)
    away_elo_pre = models.FloatField(null=True, blank=True)

    home_form_5 = models.IntegerField(null=True, blank=True)
    away_form_5 = models.IntegerField(null=True, blank=True)

    # Betting Odds
    home_win_odds = models.FloatField(null=True, blank=True)
    draw_odds = models.FloatField(null=True, blank=True)
    away_win_odds = models.FloatField(null=True, blank=True)

    over_2_5_odds = models.FloatField(null=True, blank=True)
    under_2_5_odds = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = ('league', 'match_date', 'home_team', 'away_team')

    def __str__(self):
        return f"{self.home_team} vs {self.away_team} on {self.match_date}"



