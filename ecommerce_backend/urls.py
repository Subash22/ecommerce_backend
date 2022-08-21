"""the_fashion_fit URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
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
from django.urls import re_path as url
from django.contrib import admin
from django.urls import path, include
from users import views as user_views
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from filebrowser.sites import site
from django.views.static import serve 
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from django.conf.urls.static import static
from users.views import get_tokens_for_user, LogoutView, UpdateProfileView

urlpatterns = [
    url(r'^media/(?P<path>.*)$', serve,{'document_root': settings.MEDIA_ROOT}), 
    url(r'^static/(?P<path>.*)$', serve,{'document_root': settings.STATIC_ROOT}), 
    # url(r'^chaining/', include('smart_selects.urls')),
    url(r"^admin/filebrowser/", site.urls),
    path('tinymce/', include('tinymce.urls')),
    path('admin/', admin.site.urls),
     
    path('login/', get_tokens_for_user, name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='token_obtain_pair'),

    path('register/', user_views.register, name='user-register'),
    path('forgot/', user_views.forgot, name='forgot-password'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='users/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name="users/password_reset_confirm.html"), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='users/password_reset_complete.html'), name='password_reset_complete'), 
    
    path('update-profile/', UpdateProfileView.as_view(), name='update_profile_view'),

    path('', include('main.urls')),
]

# urlpatterns += static(settings.MEDIA_URL,document_root = settings.MEDIA_ROOT)
# urlpatterns += static(settings.STATIC_URL,document_root = settings.STATIC_ROOT)

admin.site.site_header = 'The Fashion Fit'
admin.site.site_title = 'The Fashion Fit'

