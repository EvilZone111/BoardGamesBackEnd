from rest_framework.authentication import get_authorization_header, BaseAuthentication
from rest_framework import exceptions

import jwt

from django.conf import settings

from boardgames.models import Profile


class JWTAuthentication(BaseAuthentication):

    def authenticate(self, request):

        authHeader = get_authorization_header(request)

        authData = authHeader.decode('utf-8')

        authToken = authData.split(' ')

        if len(authToken) != 2:
            raise exceptions.AuthenticationFailed('Token not valid')

        token = authToken[1]


        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms='HS256')

            username = payload['username']

            user = Profile.objects.get(username=username)

            return user, token

        except jwt.ExpiredSignatureError as ex:
            raise exceptions.AuthenticationFailed('Token is expired, login again')

        except jwt.DecodeError as ex:
            raise exceptions.AuthenticationFailed('Token is invalid')

        except "Profile".DoesNotExist as no_user:
            raise exceptions.AuthenticationFailed('No such user')