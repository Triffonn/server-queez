from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AdminGameViewSet

router = DefaultRouter()
router.register(r'games', AdminGameViewSet, basename='admin-games')

urlpatterns = [
    path('', include(router.urls)),
]