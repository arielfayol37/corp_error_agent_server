from django.urls import path
from .views import EnvView, BeaconView, SuggestView

urlpatterns = [
    path("env", EnvView.as_view()),
    path("beacon", BeaconView.as_view()),
    path("suggest", SuggestView.as_view()),
]
