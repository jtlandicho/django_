from django.core.management.base import BaseCommand
from pymongo import MongoClient
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Reset analytics counters for parking slots'

    def handle(self, *args, **options):
        try:
            # Connect to MongoDB directly
            client = MongoClient('localhost', 27017)
            db = client['parksense_db']
            
            # Reset parking slots analytics
            slots_collection = db['parking_slots']
            slots_result = slots_collection.update_many(
                {},  # match all documents
                {
                    '$set': {
                        'total_occupancy_time': 0,
                        'total_occupancy_count': 0,
                        'utilization_rate_24h': 0,
                        'average_occupancy_duration': 0,
                        'peak_hour_count': 0,
                        'peak_hour': None,
                        'last_24h_occupancy_count': 0,
                        'last_24h_occupancy_time': 0
                    }
                }
            )
            
            # Clear parking history
            history_collection = db['parking_history']
            history_result = history_collection.delete_many({})
            
            modified_count = slots_result.modified_count
            deleted_count = history_result.deleted_count
            client.close()
            
            msg = f'Successfully reset analytics for {modified_count} parking slots and deleted {deleted_count} parking history records'
            self.stdout.write(self.style.SUCCESS(msg))
            return msg
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error resetting analytics: {str(e)}')
            )
            logger.error(f'Error in reset_analytics: {str(e)}')
            return -1
