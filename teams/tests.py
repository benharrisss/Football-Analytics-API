from django.urls import reverse
from rest_framework import status
from django.contrib.auth.models import User
from teams.models import Team, Club, League
from matches.models import Match
from datetime import datetime
from rest_framework.test import APITestCase

class TeamAPITests(APITestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(username='testuser', password='testpass123')

        # Create test data
        self.league = League.objects.create(code='E0', name='Premier League')
        self.club = Club.objects.create(name='Liverpool')
        self.team = Team.objects.create(name='Liverpool 23/24', club=self.club, league=self.league)

        self.opponent_club = Club.objects.create(name='Manchester United')
        self.opponent_team = Team.objects.create(name='Manchester United 23/24', club=self.opponent_club, league=self.league)

        self.match = Match.objects.create(
            league=self.league,
            home_team=self.team,
            away_team=self.opponent_team,
            match_date=datetime(2023, 8, 10),
            ft_home_goals=2,
            ft_away_goals=1,
            ft_result='H'
        )

    # Public endpoints
    def test_team_list_public(self):
        url = reverse('team-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_team_stats_public(self):
        url = reverse('team-stats', kwargs={'pk': self.team.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['wins'], 1)

    def test_head_to_head_success(self):
        url = reverse('team-head-to-head') + f'?team1_id={self.team.id}&team2_id={self.opponent_team.id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_matches'], 1)

    def test_head_to_head_invalid_teams(self):
        url = reverse('team-head-to-head') + '?team1_id=9999&team2_id=8888'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


    # Protected/Authenticated endpoints
    def test_dna_requires_authentication(self):
        url = reverse('team-dna', kwargs={'pk': self.team.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_dna_authenticated(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('team-dna', kwargs={'pk': self.team.pk})
        response = self.client.get(url)
        self.assertIn(response.status_code, [200, 400])

    def test_best_attack_requires_authentication(self):
        url = reverse('team-best-attack') + '?league=E0'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_best_attack_authenticated(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('team-best-attack') + '?league=E0'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(isinstance(response.data, list))

    def test_best_defence_requires_authentication(self):
        url = reverse('team-best-defence') + '?league=E0'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_best_defence_authenticated(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('team-best-defence') + '?league=E0'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(isinstance(response.data, list))

    def test_over_under_performing_requires_authentication(self):
        url = reverse('team-over-under-performing') + '?league=E0'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_over_under_performing_missing_league(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('team-over-under-performing')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_over_under_performing_invalid_league(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('team-over-under-performing') + '?league=INVALID'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)