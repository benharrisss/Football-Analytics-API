from django.urls import reverse
from rest_framework import status
from django.contrib.auth.models import User
from teams.models import Team, Club, League
from matches.models import Match
from datetime import datetime
from rest_framework.test import APITestCase

class MatchAPITests(APITestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(username='testuser', password='testpass123')

        # Create test data
        self.league = League.objects.create(code='E0', name='Premier League')
        self.club1 = Club.objects.create(name='Liverpool')
        self.team1 = Team.objects.create(name='Liverpool 23/24', club=self.club1, league=self.league)

        self.club2 = Club.objects.create(name='Chelsea')
        self.team2 = Team.objects.create(name='Chelsea 23/24', club=self.club2, league=self.league)

        self.match = Match.objects.create(
            league=self.league,
            home_team=self.team1,
            away_team=self.team2,
            match_date=datetime(2023, 8, 10),
            ft_home_goals=2,
            ft_away_goals=1,
            ft_result='H',
            home_elo_pre=1500, 
            away_elo_pre=1600
        )
    
    # Public endpoints
    def test_match_list_public(self):
        url = reverse('match-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_league_table_success(self):
        url = reverse('match-league-table') + '?league=E0&season=23/24'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(isinstance(response.data, list))

    def test_league_table_missing_league(self):
        url = reverse('match-league-table') + '?season=23/24'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_league_table_invalid_league(self):
        url = reverse('match-league-table') + '?league=INVALID&season=23/24'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    
    # Protected/Authenticated endpoints
    def test_league_stats_requires_authentication(self):
        url = reverse('match-league-stats') + '?league=E0&season=23/24'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_league_stats_success(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('match-league-stats') + '?league=E0&season=23/24'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_league_stats_missing_league(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('match-league-stats')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_league_stats_invalid_league(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('match-league-stats') + '?league=INVALID&season=23/24'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upsets_requires_authentication(self):
        url = reverse('match-upsets')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_upsets_success(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('match-upsets') + '?league=E0&season=23/24'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_biggest_upsets_success(self):
        url = reverse('match-biggest-upsets')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

