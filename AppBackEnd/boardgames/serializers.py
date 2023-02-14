from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from boardgames.models import Event, Profile, UserScore, FriendshipStatus, ParticipationRequest


class EventsSerializer(ModelSerializer):
    class Meta:
        model = Event
        # fields = ('name', 'location', 'playersMin', 'playersMax', 'date', 'time', 'game')
        fields = '__all__'
        read_only_fields = ('organizer',)


# class GamesSerializer(ModelSerializer):
#     class Meta:
#         model = Game
#         fields = '__all__'


class ProfilesSerializer(ModelSerializer):
    class Meta:
        model = Profile
        fields = '__all__'


class UserScoresSerializer(ModelSerializer):
    class Meta:
        model = UserScore
        fields = '__all__'
        read_only_fields = ('user', 'game')


class FriendshipStatusesSerializer(ModelSerializer):
    class Meta:
        model = FriendshipStatus
        fields = '__all__'
        read_only_fields = ('user1', 'user2', 'isAccepted')


class ParticipationRequestsSerializer(ModelSerializer):
    class Meta:
        model = ParticipationRequest
        fields = '__all__'
        read_only_fields = ('user', 'event')


class RegisterSerializer(ModelSerializer):
    password = serializers.CharField(max_length=128, min_length=6, write_only=True, required=True,
                                     validators=[validate_password])
    confirm_password = serializers.CharField(max_length=128, min_length=6, write_only=True, required=True)

    class Meta:
        model = Profile
        fields = ('email', 'password', 'confirm_password', 'first_name', 'last_name')

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        validated_data['username'] = validated_data['email']
        return Profile.objects.create_user(**validated_data)


class LoginSerializer(ModelSerializer):
    password = serializers.CharField(max_length=128, min_length=6, write_only=True)

    class Meta:
        model = Profile
        fields = ('email', 'username', 'password', 'token')
        # fields = '__all__'
        read_only_fields = ['token']


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super(CustomTokenObtainPairSerializer, self).validate(attrs)
        data.update({'id': self.user.id})
        return data
