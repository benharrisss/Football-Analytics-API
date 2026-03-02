from rest_framework import serializers
from .models import Match

class MatchSerializer(serializers.ModelSerializer):
    league = serializers.StringRelatedField()
    home_team = serializers.StringRelatedField()
    away_team = serializers.StringRelatedField()
    
    class Meta:
        model = Match
        fields = '__all__'