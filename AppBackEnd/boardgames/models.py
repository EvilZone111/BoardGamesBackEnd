from datetime import datetime, timedelta

import jwt
from django.contrib.auth.models import User, AbstractUser, PermissionsMixin
from django.db import models

from boardgames.managers import ProfileManager
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class Profile(AbstractUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    bio = models.TextField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=30, null=True, blank=True)
    sexOptions = (
        ('M', 'Мужской'),
        ('F', 'Женский'),
        ('U', 'Не указан'),
    )
    sex = models.CharField(max_length=1, choices=sexOptions, default='U')
    profilePicture = models.ImageField(null=True, blank=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    objects = ProfileManager()
    date_of_birth = models.DateField(blank=True, null=True)
    friends = models.ManyToManyField('self', through='FriendshipStatus')

    # scores = models.ManyToManyField('Game', through='UserScore')
    def get_full_name(self):
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    full_name = property(get_full_name)

    # def __str__(self):
    #     return self.email

    @property
    def token(self):
        token = jwt.encode(
            {'username': self.email,
             'email': self.email,
             'exp': datetime.utcnow() + timedelta(hours=24)},
            settings.SECRET_KEY, algorithm='HS256')
        return token


class Event(models.Model):
    name = models.CharField(max_length=50)
    address = models.TextField()
    address_additional_info = models.TextField(blank=True, null=True)
    min_play_time = models.IntegerField(blank=True, null=True)
    max_play_time = models.IntegerField(blank=True, null=True)
    min_players = models.IntegerField(blank=True, null=True)
    max_players = models.IntegerField(blank=True, null=True)
    date = models.DateField()
    time = models.TimeField()
    description = models.TextField(max_length=400, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    game = models.IntegerField()
    # game = models.ForeignKey('Game', on_delete=models.CASCADE, related_name='related_events')
    organizer = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='organized_events')
    participators = models.ManyToManyField(Profile, through='ParticipationRequest')


class ParticipationRequest(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='user_requests')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='participation_requests')
    message = models.TextField(max_length=200, null=True, blank=True)
    isAccepted = models.BooleanField(default=False)
    answer = models.TextField(max_length=200, null=True, blank=True)


# class Game(models.Model):
#     title = models.CharField(max_length=50)
#     year = models.IntegerField()
#     BGGScore = models.DecimalField(max_digits=3, decimal_places=1)
#     score = models.DecimalField(max_digits=2, decimal_places=2, default=0, blank=True, null=True)
#     gameTimeMin = models.IntegerField(blank=True, null=True)
#     gameTimeMax = models.IntegerField(blank=True, null=True)
#     playersMin = models.IntegerField(blank=True, null=True)
#     playersMax = models.IntegerField(blank=True, null=True)
#     description = models.TextField(max_length=3000)
#     BGGUrl = models.CharField(max_length=100)
#     pictureUrl = models.CharField(blank=True, max_length=1000, null=True)


class UserScore(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='user_scores')
    game = models.IntegerField()
    # game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='game_scores')
    score = models.IntegerField()


class FriendshipStatus(models.Model):
    user1 = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='user1')
    user2 = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='user2')
    message = models.TextField(max_length=200, null=True, blank=True)
    isAccepted = models.BooleanField(default=False)
