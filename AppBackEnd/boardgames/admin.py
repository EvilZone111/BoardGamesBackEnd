from django.contrib import admin

from boardgames.models import Profile, Event,ParticipationRequest, UserScore, FriendshipStatus

admin.site.register(Profile)
admin.site.register(Event)
# admin.site.register(Game)
admin.site.register(ParticipationRequest)
admin.site.register(UserScore)
admin.site.register(FriendshipStatus)
