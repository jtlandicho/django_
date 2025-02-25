from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from pymongo import MongoClient
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Cleanup old parking records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to retain records'
        )

    def handle(self, *args, **options):
        try:
            retention_days = options['days']
            cutoff_date = timezone.now() - timedelta(days=retention_days)
            
            # Connect to MongoDB directly
            client = MongoClient('localhost', 27017)
            db = client['parksense_db']
            collection = db['parking_history']  # Using the actual collection name from MongoDB
            
            # Delete old records
            result = collection.delete_many({'timestamp': {'$lt': cutoff_date}})
            deleted_count = result.deleted_count
            
            client.close()
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully deleted {deleted_count} old parking records')
            )
            return deleted_count
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error cleaning up records: {str(e)}')
            )
            logger.error(f'Error in cleanup_old_records: {str(e)}')
            return -1
