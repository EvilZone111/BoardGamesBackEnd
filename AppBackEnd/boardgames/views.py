from django.contrib.auth import authenticate
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import response, status, permissions
from rest_framework.decorators import action, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.generics import GenericAPIView, CreateAPIView, get_object_or_404
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
    filter_fields = {
        'game': ['exact'],
        'organizer': ['exact'],
        'is_active': ['exact'],
        'city': ['exact'],
        'date': ['gte', 'lte', ]
    }
    search_fields = ['game']

    # создание

    def perform_create(self, serializer):
        serializer.save(organizer=self.request.user, is_active=True)
        return Response(serializer.data)

    # поиск по нескольким критериям: http://127.0.0.1: 8000 / api / events /?game_id = 2 & playersMax = 4

    # получение событий, организованных пользователем

    @action(detail=False, methods=['get'])
    def my_events(self, request):
        return serialize_data(self, self.queryset.filter(organizer=self.request.user))

    # получение прошлых мероприятий пользователя, активных мероприятий пользователя, PUT

    @action(detail=False, methods=['get'], url_path='by_user/(?P<org_id>[^/.]+)')
    def by_user(self, request, org_id):
        queryset = self.queryset.filter(organizer=org_id)
        serializer = self.serializer_class(queryset, many=True, read_only=True)
        return Response(serializer.data)

    # изменение мероприятия
    @action(detail=False, methods=['put'], url_path='(?P<event_id>[^/.]+)/edit')
    def edit(self, request, event_id):
        print(self.request.data)
        instance = get_object_or_404(Event.objects.all(), pk=event_id)
        if self.request.data['organizer'] == self.request.user.id:
            serializer = self.serializer_class(instance, data=self.request.data)
            if serializer.is_valid():
                serializer.save(organizer=self.request.user)
                return Response(serializer.data)
            return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_403_FORBIDDEN)
        # if self.request.user=
        # friendship = self.queryset.filter(user2=self.request.user, user1=Profile.objects.get(id=user1_id)).first()
        # friendship.isAccepted = True
        # friendship.message = None
        # friendship.save()
        # serializer = self.serializer_class(friendship)
        # return Response(serializer.   data)


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

    # удаление оценки

    @action(detail=False, methods=['delete'], url_path='delete/(?P<game_id>[^/.]+)')
    def delete(self, request, game_id):
        user_rate = self.queryset.filter(user=self.request.user, game=game_id).first()
        if user_rate is not None:
            user_rate.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ParticipationRequestsViewSet(ModelViewSet):
    queryset = ParticipationRequest.objects.all()
    serializer_class = ParticipationRequestsSerializer

    # получение нерассмотренных заявок на мероприятие

    @action(detail=False, methods=['get'], url_path='event/(?P<event_id>[^/.]+)/unhandled_requests')
    def unhandled_requests_by_event(self, request, event_id):
        if Event.objects.get(id=event_id).organizer == self.request.user:
            return serialize_data(self, self.queryset.filter(event=event_id, is_handled=False))

    # получение списка участников

    @action(detail=False, methods=['get'], url_path='event/(?P<event_id>[^/.]+)/participators')
    def participators_of_event(self, request, event_id):
        return serialize_data(self, self.queryset.filter(event=event_id, is_accepted=True))

    # получение всех заявок на участие

    @action(detail=False, methods=['get'], url_path='event/(?P<event_id>[^/.]+)/requests')
    def requests_by_event(self, request, event_id):
        if Event.objects.get(id=event_id).organizer == self.request.user:
            return serialize_data(self, self.queryset.filter(event=event_id))

    # получение статуса моей заявки
    @action(detail=False, methods=['get'], url_path='event/(?P<event_id>[^/.]+)/my_request')
    def my_request_status(self, request, event_id):
        if Event.objects.get(id=event_id).organizer != self.request.user:
            return serialize_data(self, self.queryset.filter(event=event_id))
        return Response(status=status.HTTP_204_NO_CONTENT)

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
                serializer.save(user=self.request.user, event=Event.objects.get(id=event_id), is_accepted=False)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'message': "Заявка уже отправлена"}, status=status.HTTP_400_BAD_REQUEST)

    # изменение заявки(ответ на заявку)

    @action(detail=False, methods=['patch'], url_path='respond/(?P<event_id>[^/.]+)/(?P<user_id>[^/.]+)')
    def respond(self, request, event_id, user_id):
        user_request = self.queryset.filter(user=user_id, event=event_id).first()
        user_request.answer = request.data['answer']
        user_request.is_accepted = request.data['is_accepted']
        user_request.is_handled = True
        user_request.save()
        serializer = self.serializer_class(user_request)
        return Response(serializer.data)
        # if(user_request.or):
        #
        #     # user_rate.message = request.data["message"]
        #     user_rate.answer = request.data["answer"]
        #     user_rate.is_accepted = request.data["is_accepted"]
        #     user_rate.save()
        #     serializer = self.serializer_class(user_rate)
        #     return Response(serializer.data)

    # удаление заявки

    @action(detail=False, methods=['delete'], url_path='delete/(?P<event_id>[^/.]+)')
    def delete(self, request, event_id):
        user_request = self.queryset.filter(user=self.request.user, event=event_id).first()
        if user_request is not None:
            user_request.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # получение статуса заявки


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

    # # принятие заявки(для отклонения-удалить запись )
    # @action(detail=False, methods=['put'], url_path='accept/(?P<user1_id>[^/.]+)')
    # def accept_request(self, request, user1_id):
    #     friendship = self.queryset.filter(user2=self.request.user, user1=Profile.objects.get(id=user1_id)).first()
    #     friendship.isAccepted = True
    #     friendship.message = None
    #     friendship.save()
    #     serializer = self.serializer_class(friendship)
    #     return Response(serializer.data)


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
