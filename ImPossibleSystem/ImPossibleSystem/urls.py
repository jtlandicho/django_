"""
URL configuration for ImPossibleSystem project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from django.urls import path
from app1 import views, api
urlpatterns = [
    path("admin/", admin.site.urls),
    path("register/", views.SignUpPage, name="signup"),
    path("", views.LoginPage, name="login"),
    path("home/", views.HomePage, name="home"),
    path("logout/", views.LogoutPage, name="logout"),
    path("slots/", views.parking_slots, name="slots"),
    path("analytics/", views.analytics, name="analytics"),
    path("tools/", views.tools, name="tools"),    
    # API endpoints
    path("api/sensor-reading/", api.update_sensor_reading, name="update_sensor_reading"),
    path("api/analytics/", api.get_parking_analytics, name="get_parking_analytics"),
    path("api/log-maintenance/", api.log_maintenance, name="log_maintenance"),
    path('sse/parking-updates/', views.parking_slot_updates, name='parking_slot_updates'),
    path('sse/public-slots/', views.public_slots_updates, name='public_slots_updates'),
    path("disagree/", views.disagree, name="disagree"),   


]

