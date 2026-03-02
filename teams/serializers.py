from rest_framework import serializers
from .models import Team

class TeamSerializer(serializers.ModelSerializer):
    league = serializers.StringRelatedField()
    
    class Meta:
        model = Team
        fields = '__all__'