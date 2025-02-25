from django.core.management.base import BaseCommand
from app1.models import ParkingSlot

class Command(BaseCommand):
    help = 'Setup initial parking slots'

    def handle(self, *args, **kwargs):
        # Create car slots
        for i in range(3):
            ParkingSlot.objects.get_or_create(
                slot_number=i+1,
                defaults={
                    'vehicle_type': 'car',
                    'status': 'available',
                    'sensor_id': f'CAR_SENSOR_{i+1}'
                }
            )
            self.stdout.write(self.style.SUCCESS(f'Created car slot {i+1}'))

        # Create motorcycle slots
        for i in range(3):
            ParkingSlot.objects.get_or_create(
                slot_number=i+4,  # Start from 4 to avoid conflict with car slots
                defaults={
                    'vehicle_type': 'motorcycle',
                    'status': 'available',
                    'sensor_id': f'MOTO_SENSOR_{i+1}'
                }
            )
            self.stdout.write(self.style.SUCCESS(f'Created motorcycle slot {i+4}'))
