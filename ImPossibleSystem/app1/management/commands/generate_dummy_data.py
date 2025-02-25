from django.core.management.base import BaseCommand
from django.utils import timezone
from app1.models import ParkingSlot, ParkingHistory
from datetime import timedelta
import random

class Command(BaseCommand):
    help = 'Generate dummy parking history data for testing'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get all parking slots
        slots = ParkingSlot.objects.all()
        if not slots:
            self.stdout.write(self.style.ERROR('No parking slots found. Please create parking slots first.'))
            return
            
        # Generate 20 random parking records for today
        for _ in range(20):
            # Pick a random slot
            slot = random.choice(slots)
            
            # Generate random start time between start of day and now
            max_start = int((now - start_of_day).total_seconds())
            random_seconds = random.randint(0, max_start)
            timestamp = start_of_day + timedelta(seconds=random_seconds)
            
            # Generate random duration between 30 minutes and 4 hours
            duration = timedelta(minutes=random.randint(30, 240))
            
            # Create parking record
            ParkingHistory.objects.create(
                slot=slot,
                timestamp=timestamp,
                status='occupied',
                duration=duration
            )
            
            # Update slot analytics
            slot.total_occupancy_count += 1
            slot.total_occupancy_time += duration
            if timestamp >= (now - timedelta(hours=24)):
                slot.last_24h_occupancy_count += 1
                slot.last_24h_occupancy_time += duration
            slot.save()
            
        self.stdout.write(self.style.SUCCESS('Successfully generated 20 dummy parking records'))
