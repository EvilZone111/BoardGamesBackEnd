from django.contrib.auth import authenticate
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import response, status, permissions
from rest_framework.decorators import action, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.generics import GenericAPIView, CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework_simplejwt.views import TokenObtainPairView

from boardgames.models import Event, Profile, UserScore, ParticipationRequest, FriendshipStatus
from boardgames.serializers import EventsSerializer, ProfilesSerializer, RegisterSerializer, LoginSerializer, \
    UserScoresSerializer, ParticipationRequestsSerializer, FriendshipStatusesSerializer, CustomTokenObtainPairSerializer
from boardgames.utils import serialize_data, serialize_single_obj_data
from django.utils.translation import activate


# TODO: рекомендательная система


class ProfileViewSet(ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfilesSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filter_fields = ['city']
    search_fields = ['first_name', 'last_name']

    # френдлист

    @action(detail=False, methods=['get'], url_path='friendlist/(?P<user_id>[^/.]+)')
    def get_friendlist(self, request, user_id):
        list1 = FriendshipStatusViewSet.queryset.filter(user1=user_id, isAccepted=True).values_list('user2',
                                                                                                    flat=True).distinct()
        list2 = FriendshipStatusViewSet.queryset.filter(user2=user_id, isAccepted=True).values_list('user1',
                                                                                    flat=True).distinct()
        qs1 = self.queryset.filter(pk__in=list1)
        qs2 = self.queryset.filter(pk__in=list2)
        return serialize_data(self, qs1.union(qs2))


# class GameViewSet(ReadOnlyModelViewSet):
#     queryset = Game.objects.all()
#     serializer_class = GamesSerializer
#     filter_backends = [DjangoFilterBackend, SearchFilter]
#     filter_fields = ['year']
#     search_fields = ['title']

@permission_classes([permissions.IsAuthenticated])
class EventViewSet(ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventsSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filter_fields = ['game', 'organizer', 'is_active']
    search_fields = ['game']

    # создание

    def perform_create(self, serializer):
        print(self.request.user.id)
        return serializer.save(organizer=self.request.user, is_active=True)

    # поиск по нескольким критериям: http://127.0.0.1: 8000 / api / events /?game_id = 2 & playersMax = 4

    # получения событий, организованных пользователем

    @action(detail=False, methods=['get'])
    def my_events(self, request):
        return serialize_data(self, self.queryset.filter(organizer=self.request.user))

    # получение прошлых мероприятий пользователя, активных мероприятий пользователя, PUT

    @action(detail=False, methods=['get'], url_path='by_user/(?P<org_id>[^/.]+)')
    def by_user(self, request, org_id):
        queryset = self.queryset.filter(organizer=org_id)
        serializer = self.serializer_class(queryset, many=True, read_only=True)
        return Response(serializer.data)


class ScoresViewSet(ModelViewSet):
    queryset = UserScore.objects.all()
    serializer_class = UserScoresSerializer

    # получение оценок игры
    @action(detail=False, methods=['get'], url_path='game/(?P<game_id>[^/.]+)')
    def scores_by_games(self, request, game_id):
        return serialize_data(self, self.queryset.filter(game=game_id))

    # получение оценок пользователя

    @action(detail=False, methods=['get'], url_path='user/(?P<user_id>[^/.]+)')
    def scores_by_users(self, request, user_id):
        return serialize_data(self, self.queryset.filter(user=user_id))

    # получение оценок текущего пользователя

    @action(detail=False, methods=['get'], url_path='my_score/(?P<game_id>[^/.]+)')
    def my_score(self, request, game_id):
        return serialize_single_obj_data(self, self.queryset.filter(user=self.request.user, game=game_id).first())

    # получение средней оценки

    @action(detail=False, methods=['get'], url_path='score/(?P<game_id>[^/.]+)')
    def my_scores(self, request, game_id):
        scores = self.queryset.filter(game=game_id)
        score_number = scores.count()
        if score_number == 0:
            return Response(status=status.HTTP_204_NO_CONTENT)
        score_value = 0
        for score_obj in scores:
            score_value += score_obj.score
        score_value /= score_number
        return Response({'score_value': score_value, 'score_number': score_number})

    # выставление или изменение оценки

    @action(detail=False, methods=['post'], url_path='rate/(?P<game_id>[^/.]+)')
    def rate(self, request, game_id):
        user_rate = self.queryset.filter(user=self.request.user, game=game_id).first()
        if user_rate is None:
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                serializer.save(user=self.request.user, game=game_id)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            score_obj = user_rate
            score_obj.score = request.data["score"]
            score_obj.save()
            serializer = self.serializer_class(score_obj)
            return Response(serializer.data)

    @action(detail=False, methods=['delete'], url_path='delete/(?P<game_id>[^/.]+)')
    def delete(self, request, game_id):
        user_rate = self.queryset.filter(user=self.request.user, game=game_id).first()
        if user_rate is not None:
            user_rate.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ParticipationRequestsViewSet(ModelViewSet):
    queryset = ParticipationRequest.objects.all()
    serializer_class = ParticipationRequestsSerializer

    # получение заявок на мероприятие

    @action(detail=False, methods=['get'], url_path='event/(?P<event_id>[^/.]+)')
    def requests_by_event(self, request, event_id):
        if Event.objects.get(id=event_id).organizer == self.request.user:
            return serialize_data(self, self.queryset.filter(event=event_id, isAccepted=False))

    # получение списка участников

    # получение исходящих заявок

    @action(detail=False, methods=['get'])
    def my_requests(self, request):
        return serialize_data(self, self.queryset.filter(user=self.request.user))

    # отправление заявки

    @action(detail=False, methods=['post'], url_path='participate/(?P<event_id>[^/.]+)')
    def participate(self, request, event_id):
        if self.queryset.filter(user=self.request.user, event=Event.objects.get(id=event_id)).first() is None:
            if Event.objects.get(id=event_id).organizer == self.request.user:
                return Response({'message': "Нельзя отправить заявку на участие в собственном мероприятии"},
                                status=status.HTTP_400_BAD_REQUEST)
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                serializer.save(user=self.request.user, event=Event.objects.get(id=event_id))
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'message': "Заявка уже отправлена"}, status=status.HTTP_400_BAD_REQUEST)

    # изменение заявки(ответ на заявку)

    def update(self, request, *args, **kwargs):
        user_rate = self.queryset.filter(user=self.request.user, game=request.data['game_id']).first()
        user_rate.message = request.data["message"]
        user_rate.answer = request.data["answer"]
        user_rate.isAccepted = request.data["isAccepted"]
        user_rate.save()
        serializer = self.serializer_class(user_rate)
        return Response(serializer.data)


class FriendshipStatusViewSet(ModelViewSet):
    queryset = FriendshipStatus.objects.all()
    serializer_class = FriendshipStatusesSerializer

    # входящие заявки в друзья
    @action(detail=False, methods=['get'])
    def my_requests(self, request):
        return serialize_data(self, self.queryset.filter(user2=self.request.user, isAccepted=False))

    # исходящие заявки в друзья
    @action(detail=False, methods=['get'])
    def sent_requests(self, request):
        return serialize_data(self, self.queryset.filter(user1=self.request.user, isAccepted=False))

    # отправление заявки

    @action(detail=False, methods=['post'], url_path='add/(?P<user2_id>[^/.]+)')
    def send_request(self, request, user2_id):
        if self.queryset.filter(user1=self.request.user, user2=Profile.objects.get(id=user2_id)).first() is None:
            if Profile.objects.get(id=user2_id) == self.request.user:
                return Response({'message': "Нельзя отправить заявку самому себе"},
                                status=status.HTTP_400_BAD_REQUEST)
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                serializer.save(user1=self.request.user, user2=Profile.objects.get(id=user2_id))
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'message': "Заявка уже отправлена"}, status=status.HTTP_400_BAD_REQUEST)

    # принятие заявки(для отклонения-удалить запись )
    @action(detail=False, methods=['put'], url_path='accept/(?P<user1_id>[^/.]+)')
    def accept_request(self, request, user1_id):
        friendship = self.queryset.filter(user2=self.request.user, user1=Profile.objects.get(id=user1_id)).first()
        friendship.isAccepted = True
        friendship.message = None
        friendship.save()
        serializer = self.serializer_class(friendship)
        return Response(serializer.data)


class RegisterAPIView(GenericAPIView):
    authentication_classes = []
    serializer_class = RegisterSerializer
    activate('ru')

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        print(serializer.initial_data)
        if serializer.initial_data['password'] != serializer.initial_data['confirm_password']:
            return response.Response(data={'confirm_password': ['Пароли не совпадают']},
                                     status=status.HTTP_400_BAD_REQUEST)
        if serializer.is_valid():
            # serializer.
            serializer.save()
            return response.Response(serializer.data, status=status.HTTP_201_CREATED)
        return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginAPIView(GenericAPIView):
    authentication_classes = []

    serializer_class = LoginSerializer

    def post(self, request):
        email = request.data.get('email', None)
        password = request.data.get('password', None)

        user = authenticate(username=email, password=password)
        print(user.token)

        if user:
            serializer = self.serializer_class(user)
            return response.Response(serializer.data, status=status.HTTP_200_OK)
        return response.Response({'message': "Неверный логин или пароль"}, status=status.HTTP_400_BAD_REQUEST)


class AuthUserAPIView(GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        user = request.user
        serializer = RegisterSerializer(user)
        return response.Response({'user': serializer.data})


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
