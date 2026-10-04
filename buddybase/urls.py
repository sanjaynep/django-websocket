from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from hub import views as hub_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('hub.urls')),
    path('login/', auth_views.LoginView.as_view(template_name='hub/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),
    path('register/', hub_views.register, name='register'),
]