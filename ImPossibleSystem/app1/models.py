from django.contrib.auth.models import User
from djongo import models
from django.utils import timezone

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_admin = models.BooleanField(default=False)
    preferences = models.JSONField(default=dict)  # Store user preferences as JSON

    class Meta:
        db_table = 'user_profiles'

class SensorReading(models.Model):
    timestamp = models.DateTimeField(default=timezone.now)
    distance = models.FloatField()
    is_occupied = models.BooleanField()
    sensor_status = models.CharField(max_length=50)

    class Meta:
        abstract = True

class MaintenanceLog(models.Model):
    timestamp = models.DateTimeField(default=timezone.now)
    issue = models.CharField(max_length=200)
    resolved = models.BooleanField(default=False)
    notes = models.TextField(null=True)

    class Meta:
        abstract = True

class Analytics(models.Model):
    daily_occupancy_rate = models.FloatField(default=0)
    peak_hours = models.JSONField(default=list)
    average_parking_duration = models.IntegerField(default=0)  # in minutes
    last_calculated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

from django.utils import timezone
from datetime import timedelta

class ParkingSlot(models.Model):
    VEHICLE_TYPES = [
        ('car', 'Car'),
        ('motorcycle', 'Motorcycle'),
    ]
    
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('reserved', 'Reserved'),
        ('maintenance', 'Under Maintenance'),
    ]
    
    # Basic slot information
    slot_number = models.IntegerField(unique=True)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    sensor_id = models.CharField(max_length=50, unique=True)
    last_updated = models.DateTimeField(auto_now=True)
    current_distance = models.FloatField(default=150.0)  # Default to empty slot distance
    # Add this line:
    is_occupied = models.BooleanField(default=False)
    # Analytics fields
    occupation_start = models.DateTimeField(null=True, blank=True)
    total_occupancy_time = models.DurationField(default=timedelta)
    total_occupancy_count = models.IntegerField(default=0)
    last_24h_occupancy_count = models.IntegerField(default=0)
    last_24h_occupancy_time = models.DurationField(default=timedelta)

    class Meta:
        db_table = 'parking_slots'

    def __str__(self):
        return f"{self.get_vehicle_type_display()} Slot {self.slot_number}"

    def update_sensor_reading(self, distance, is_occupied):
        now = timezone.now()
        old_status = self.status
        
        # Update basic info
        self.current_distance = distance
        self.status = 'occupied' if is_occupied else 'available'
        
        # Handle analytics
        if is_occupied and old_status != 'occupied':
            # Vehicle just parked
            self.occupation_start = now
            self.total_occupancy_count += 1
            self.last_24h_occupancy_count += 1
            
        elif not is_occupied and old_status == 'occupied' and self.occupation_start:
            # Vehicle just left
            occupancy_duration = now - self.occupation_start
            self.total_occupancy_time += occupancy_duration
            self.last_24h_occupancy_time += occupancy_duration
            self.occupation_start = None
            
        # Clean up old 24h data
        cutoff_time = now - timedelta(hours=24)
        if self.last_updated < cutoff_time:
            self.last_24h_occupancy_count = 0
            self.last_24h_occupancy_time = timedelta()
        
        # Record history
        total_slots = ParkingSlot.objects.count()
        occupied_slots = ParkingSlot.objects.filter(status='occupied').count()
        occupancy_rate = (occupied_slots / total_slots * 100) if total_slots > 0 else 0
        
        duration = timedelta()
        if self.status == 'occupied' and self.occupation_start:
            duration = now - self.occupation_start
        
        ParkingHistory.objects.create(
            slot=self,
            timestamp=now,
            status=self.status,
            duration=duration,
            occupancy_rate=occupancy_rate,
            occupied_count=occupied_slots
        )
            
        self.save()
        
    @property
    def average_occupancy_duration(self):
        if self.total_occupancy_count == 0:
            return timedelta()
        return self.total_occupancy_time / self.total_occupancy_count
    
    @property
    def utilization_rate_24h(self):
        """Returns the utilization rate as a percentage over the last 24 hours"""
        total_time = timedelta(hours=24)
        if self.last_24h_occupancy_time > total_time:
            return 100.0
        return (self.last_24h_occupancy_time.total_seconds() / total_time.total_seconds()) * 100

    def update_analytics(self):
        # Implementation for calculating analytics
        pass

class ParkingHistory(models.Model):
    slot = models.ForeignKey(ParkingSlot, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=ParkingSlot.STATUS_CHOICES)
    duration = models.DurationField(default=timedelta)
    occupancy_rate = models.FloatField(default=0)
    occupied_count = models.IntegerField(default=0)

    class Meta:
        db_table = 'parking_history'
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['slot', 'timestamp'])
        ]

    @classmethod
    def record_snapshot(cls):
        """Record current parking state for historical analysis"""
        now = timezone.now()
        total_slots = ParkingSlot.objects.count()
        occupied_slots = ParkingSlot.objects.filter(status='occupied').count()
        occupancy_rate = (occupied_slots / total_slots * 100) if total_slots > 0 else 0

        # Record data for each slot
        for slot in ParkingSlot.objects.all():
            # Calculate duration if slot is occupied
            duration = timedelta()
            if slot.status == 'occupied' and slot.occupation_start:
                duration = now - slot.occupation_start

            cls.objects.create(
                slot=slot,
                timestamp=now,
                status=slot.status,
                duration=duration,
                occupancy_rate=occupancy_rate,
                occupied_count=occupied_slots
            )
