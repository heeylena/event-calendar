"""
Admin configuration for the sessions app.
"""

from django.contrib import admin
from .models import RecurrencePattern, SessionOccurrence


@admin.register(RecurrencePattern)
class RecurrencePatternAdmin(admin.ModelAdmin):
    """Admin interface for RecurrencePattern model."""
    
    list_display = ['title', 'weekday_name', 'time', 'start_date', 'end_date', 'is_active']
    list_filter = ['is_active', 'weekday', 'frequency', 'created_at']
    search_fields = ['title', 'description']
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'is_active')
        }),
        ('Recurrence Rules', {
            'fields': ('frequency', 'weekday', 'time', 'duration_minutes')
        }),
        ('Pattern Boundaries', {
            'fields': ('start_date', 'end_date')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']


@admin.register(SessionOccurrence)
class SessionOccurrenceAdmin(admin.ModelAdmin):
    """Admin interface for SessionOccurrence model."""
    
    list_display = ['title', 'start_datetime', 'duration_minutes', 'status', 'is_exception', 'recurrence_pattern']
    list_filter = ['status', 'is_exception', 'recurrence_pattern', 'created_at']
    search_fields = ['title', 'description']
    date_hierarchy = 'start_datetime'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'recurrence_pattern')
        }),
        ('Schedule', {
            'fields': ('start_datetime', 'duration_minutes')
        }),
        ('Status', {
            'fields': ('status', 'is_exception')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
