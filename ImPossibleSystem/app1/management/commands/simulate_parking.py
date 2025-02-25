from django.core.management.base import BaseCommand
from app1.models import ParkingSlot
from django.utils import timezone
from datetime import timedelta, datetime
import random

class Command(BaseCommand):
    help = 'Simulates parking events over a period of time'

    def get_hourly_probability(self, hour):
        # Early morning (midnight to 5 AM)
        if 0 <= hour < 5:
            return 0.2
        # Morning rush (6 AM to 9 AM)
        elif 5 <= hour < 7:
            return 0.4 + (hour - 5) * 0.15  # Gradually increasing
        elif 7 <= hour < 9:
            return 0.7
        # Work hours (9 AM to 4 PM)
        elif 9 <= hour < 16:
            return 0.6
        # Evening rush (4 PM to 7 PM)
        elif 16 <= hour < 19:
            return 0.75
        # Evening wind-down (7 PM to midnight)
        else:
            return 0.4 - (hour - 19) * 0.05  # Gradually decreasing

    def handle(self, *args, **options):
        slots = list(ParkingSlot.objects.all())
        if not slots:
            self.stdout.write(self.style.ERROR('No parking slots found. Please run setup_parking_slots first.'))
            return

        self.stdout.write('Starting parking simulation...')
        now = timezone.now()

        # Reset analytics data
        for slot in slots:
            # Initialize counters
            slot.total_occupancy_time = timedelta()
            slot.total_occupancy_count = 0
            slot.last_24h_occupancy_count = 0
            slot.last_24h_occupancy_time = timedelta()
            
            # Simulate a full day with hourly changes
            current_time = now - timedelta(hours=24)
            is_occupied = False
            occupation_start = None
            
            while current_time <= now:
                hour = current_time.hour
                prob = self.get_hourly_probability(hour)
                
                if not is_occupied and random.random() < prob:
                    # Vehicle arrives
                    is_occupied = True
                    occupation_start = current_time
                    slot.total_occupancy_count += 1
                    slot.last_24h_occupancy_count += 1
                
                elif is_occupied and random.random() < 0.3:  # 30% chance to leave each hour if occupied
                    # Vehicle leaves
                    is_occupied = False
                    duration = current_time - occupation_start
                    slot.total_occupancy_time += duration
                    slot.last_24h_occupancy_time += duration
                    occupation_start = None
                
                current_time += timedelta(hours=1)
            
            # Handle currently occupied slot
            if is_occupied and occupation_start:
                duration = now - occupation_start
                slot.total_occupancy_time += duration
                slot.last_24h_occupancy_time += duration
                slot.status = 'occupied'
                slot.current_distance = 20.0
                slot.occupation_start = occupation_start
            else:
                slot.status = 'available'
                slot.current_distance = 150.0
                slot.occupation_start = None
            
            slot.save()
            
            self.stdout.write(
                f'Slot {slot.slot_number}: {slot.total_occupancy_count} events, '
                f'total time {slot.total_occupancy_time.total_seconds()/3600:.1f} hours, '
                f'current status: {slot.status}'
            )

        self.stdout.write(self.style.SUCCESS('Successfully simulated parking events'))
