"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from api.views import GameViewSet, QuestionTypeViewSet, RoundViewSet,QuestionViewSet,MediaViewSet
from django.conf import settings
from django.urls import re_path
from django.views.static import serve as static_serve

router = DefaultRouter()
router.register(r'games', GameViewSet,basename='games')
router.register(r'rounds', RoundViewSet,basename='rounds')
router.register(r'questions', QuestionViewSet,basename='questions')
router.register(r'questiontypes', QuestionTypeViewSet,basename='questiontypes')
router.register(r'media', MediaViewSet, basename='media')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),
    re_path(r'^media/(?P<path>.*)$', static_serve, {'document_root': settings.MEDIA_ROOT}),
]
