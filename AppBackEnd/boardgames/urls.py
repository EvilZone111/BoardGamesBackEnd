from rest_framework.routers import SimpleRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from boardgames import views
from django.urls import path

from boardgames.views import EventViewSet, ProfileViewSet, ScoresViewSet, ParticipationRequestsViewSet, \
    FriendshipStatusViewSet

router = SimpleRouter()
router.register(r'events', EventViewSet, basename='events')
router.register(r'profiles', ProfileViewSet)
# router.register(r'games', GameViewSet)
router.register(r'scores', ScoresViewSet)
router.register(r'requests', ParticipationRequestsViewSet)
router.register(r'friends', FriendshipStatusViewSet)



urlpatterns = [
    path('register/', views.RegisterAPIView.as_view(), name='register'),
    # path('login/', views.LoginAPIView.as_view(), name='login'),
    path('user/', views.AuthUserAPIView.as_view(), name='user'),
    # path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
]

urlpatterns += router.urls