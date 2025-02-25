from django.core.management.base import BaseCommand
from django.conf import settings
from app1.models import ParkingSlot
import json
import logging
import sys
from django_redis import get_redis_connection

# Configure a logger specifically for this command
logger = logging.getLogger('populate_parking_cache')
logger.setLevel(logging.DEBUG)

# If no handlers exist, add a console handler
if not logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - PARKING_CACHE - %(levelname)s: %(message)s'
    ))
    logger.addHandler(console_handler)

class Command(BaseCommand):
    help = 'Populate parking slot cache for Server-Sent Events'

    def handle(self, *args, **kwargs):
        # Get Redis connection
        redis_client = get_redis_connection('parking_updates')
        
        # Fetch current parking slot statuses
        car_slots = ParkingSlot.objects.filter(vehicle_type='car')
        motorcycle_slots = ParkingSlot.objects.filter(vehicle_type='motorcycle')
        
        parking_updates = {
            'car_slots': [
                {
                    'slot_number': slot.slot_number,
                    'sensor_id': slot.sensor_id,
                    'status': slot.status
                } for slot in car_slots
            ],
            'motorcycle_slots': [
                {
                    'slot_number': slot.slot_number,
                    'sensor_id': slot.sensor_id,
                    'status': slot.status
                } for slot in motorcycle_slots
            ]
        }
        
        # Log details before setting cache
        logger.info(f"Parking Updates to Cache:")
        logger.info(f"Car Slots: {len(parking_updates['car_slots'])}")
        for slot in parking_updates['car_slots']:
            logger.info(f"Car Slot: {slot}")
        
        logger.info(f"Motorcycle Slots: {len(parking_updates['motorcycle_slots'])}")
        for slot in parking_updates['motorcycle_slots']:
            logger.info(f"Motorcycle Slot: {slot}")
        
        # Serialize updates
        serialized_updates = json.dumps(parking_updates)
        
        # Set cache with Redis
        try:
            # Set cache with expiration
            redis_client.set('latest_parking_updates', serialized_updates, ex=60)
            
            # Verify cache contents
            retrieved_value = redis_client.get('latest_parking_updates')
            
            if retrieved_value:
                # Decode bytes to string if needed
                retrieved_value = retrieved_value.decode('utf-8') if isinstance(retrieved_value, bytes) else retrieved_value
                logger.info(f"Retrieved Redis Cache: {retrieved_value}")
            else:
                logger.warning("No value retrieved from Redis cache")
        
        except Exception as e:
            logger.error(f"Redis cache update failed: {e}")
        
        self.stdout.write(self.style.SUCCESS('Completed parking slot cache population'))
