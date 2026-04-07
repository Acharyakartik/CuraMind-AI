from django.urls import path

from . import views

app_name = "appointments"

urlpatterns = [
    path("new/", views.schedule_appointment, name="schedule"),
]

