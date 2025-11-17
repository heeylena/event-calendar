"""
Management command to generate session occurrences from recurrence patterns.

This command should be run periodically (e.g., daily via cron) to ensure
future occurrences are always available.
"""

from django.core.management.base import BaseCommand
from sessions.services import OccurrenceGenerationService


class Command(BaseCommand):
    help = 'Generate session occurrences from active recurrence patterns'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--months',
            type=int,
            default=3,
            help='Number of months ahead to generate occurrences (default: 3)'
        )
    
    def handle(self, *args, **options):
        months_ahead = options['months']
        
        self.stdout.write(
            f'Generating occurrences for the next {months_ahead} months...'
        )
        
        total_created = OccurrenceGenerationService.generate_for_all_patterns(
            months_ahead=months_ahead
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully generated {total_created} new occurrence(s)'
            )
        )
