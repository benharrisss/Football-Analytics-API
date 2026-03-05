from django.db import models

class Club(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class League(models.Model):
    code = models.CharField(max_length=2, unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} ({self.code})"

class Team(models.Model):
    name = models.CharField(max_length=100)
    club = models.ForeignKey(Club, related_name='teams', on_delete=models.CASCADE)
    league = models.ForeignKey(League, related_name='teams', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('name', 'league')

    def __str__(self):
        return self.name

