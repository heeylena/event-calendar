"""
Admin configuration for the sessions app.
"""

from django.contrib import admin
from .models import Session, SessionException


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    """Admin interface for Session model."""
    
    list_display = ['title', 'session_type', 'start_datetime', 'recurrence_day', 'duration_minutes']
    list_filter = ['session_type', 'recurrence_day', 'created_at']
    search_fields = ['title', 'description']
    date_hierarchy = 'start_datetime'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'session_type')
        }),
        ('Schedule', {
            'fields': ('start_datetime', 'duration_minutes', 'recurrence_day')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']


@admin.register(SessionException)
class SessionExceptionAdmin(admin.ModelAdmin):
    """Admin interface for SessionException model."""
    
    list_display = ['session', 'exception_date', 'is_cancelled', 'modified_datetime']
    list_filter = ['is_cancelled', 'created_at']
    search_fields = ['session__title']
    date_hierarchy = 'exception_date'
    
    fieldsets = (
        ('Exception Details', {
            'fields': ('session', 'exception_date', 'is_cancelled', 'modified_datetime')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at']
