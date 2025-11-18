"""
URL routing for the sessions API.
"""

from django.urls import path
from .views import (
    RecurrencePatternListCreateView,
    RecurrencePatternDetailView,
    SessionOccurrenceListView,
    SessionOccurrenceDetailView,
    OccurrenceCompleteView,
)

urlpatterns = [
    path('patterns/', RecurrencePatternListCreateView.as_view(), name='pattern-list-create'),
    path('patterns/<int:pk>/', RecurrencePatternDetailView.as_view(), name='pattern-detail'),
    path('occurrences/', SessionOccurrenceListView.as_view(), name='occurrence-list-create'),
    path('occurrences/<int:pk>/', SessionOccurrenceDetailView.as_view(), name='occurrence-detail'),
    path('occurrences/<int:pk>/complete/', OccurrenceCompleteView.as_view(), name='occurrence-complete'),
]
