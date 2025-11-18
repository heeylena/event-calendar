"""
Management command to generate session occurrences from recurrence patterns.

This command should be run periodically (e.g., daily via cron) to ensure
future occurrences are always available.
"""

from django.core.management.base import BaseCommand
from sessions import services


class Command(BaseCommand):
    help = 'Generate session occurrences from active recurrence patterns'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days ahead to generate occurrences (default: 7)'
        )
    
    def handle(self, *args, **options):
        days_ahead = options['days']
        
        self.stdout.write(
            f'Generating occurrences for the next {days_ahead} days...'
        )
        
        total_created = services.generate_occurrences_for_all_patterns(
            days_ahead=days_ahead
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully generated {total_created} new occurrence(s)'
            )
        )
