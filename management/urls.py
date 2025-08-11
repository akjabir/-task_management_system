from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.routers import DefaultRouter
from .views import *
from django.conf import settings
from django.conf.urls.static import static

router = DefaultRouter()
router.register('authors', AuthorViewSet, basename='author')
router.register('categories', CategoryViewSet, basename='category')
router.register('books', BookViewSet, basename='book')

urlpatterns = [
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/login/', MyTokenObtainPairView.as_view(), name='custom_token_obtain_pair'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/borrow/', BorrowAPIView.as_view(), name='borrow'),
    path('api/return/', ReturnBookAPIView.as_view(), name='return-book'),
    path('api/users/<int:id>/penalties/', UserPenaltyPointsAPIView.as_view(), name='user-penalties'),
    path('send-due-notifications/', SendDueNotificationsView.as_view(), name='send_due_notifications'),

    path('api/', include(router.urls)),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
