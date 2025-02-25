from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
from .models import ParkingSlot, UserProfile

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
@api_view(['POST'])
def update_sensor_reading(request):
    """
    Endpoint for Arduino to send sensor readings
    Expected JSON format:
    {
        "sensor_id": "SENSOR_1",
        "distance": 45.5,
        "is_occupied": true
    }
    """
    try:
        sensor_id = request.data.get('sensor_id')
        distance = request.data.get('distance')
        is_occupied = request.data.get('is_occupied')

        if not all([sensor_id, distance is not None]):
            return Response(
                {'error': 'Missing required fields: sensor_id, distance'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get the parking slot associated with this sensor
        try:
            parking_slot = ParkingSlot.objects.get(sensor_id=sensor_id)
        except ParkingSlot.DoesNotExist:
            return Response(
                {'error': f'No parking slot found for sensor {sensor_id}'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Convert distance to float and determine occupancy if not provided
        distance = float(distance)
        if is_occupied is None:
            # If distance is less than threshold, consider it occupied
            threshold = 50 if parking_slot.vehicle_type == 'motorcycle' else 100
            is_occupied = distance < threshold

        # Update the parking slot
        parking_slot.update_sensor_reading(distance, is_occupied)

        return Response({
            'status': 'success',
            'slot_number': parking_slot.slot_number,
            'current_status': parking_slot.status,
            'distance': distance
        }, status=status.HTTP_200_OK)

    except ValueError as e:
        return Response(
            {'error': 'Invalid distance value'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['GET'])
def get_parking_analytics(request):
    """
    Get analytics for all parking slots
    """
    try:
        slots = ParkingSlot.objects.all()
        analytics_data = {
            'total_slots': len(slots),
            'occupied_slots': sum(1 for slot in slots if slot.status == 'occupied'),
            'maintenance_slots': sum(1 for slot in slots if slot.status == 'maintenance'),
            'slots_data': [{
                'slot_number': slot.slot_number,
                'vehicle_type': slot.vehicle_type,
                'status': slot.status,
                'analytics': slot.analytics if slot.analytics else {},
                'last_maintenance': slot.maintenance_history[-1] if slot.maintenance_history else None
            } for slot in slots]
        }
        return Response(analytics_data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['POST'])
def log_maintenance(request):
    """
    Log maintenance for a parking slot
    Expected JSON format:
    {
        "slot_number": 1,
        "issue": "Sensor calibration required",
        "notes": "Scheduled maintenance"
    }
    """
    try:
        slot_number = request.data.get('slot_number')
        issue = request.data.get('issue')
        notes = request.data.get('notes')

        try:
            parking_slot = ParkingSlot.objects.get(slot_number=slot_number)
        except ParkingSlot.DoesNotExist:
            return Response(
                {'error': f'No parking slot found with number {slot_number}'},
                status=status.HTTP_404_NOT_FOUND
            )

        parking_slot.log_maintenance(issue, notes)

        return Response({
            'status': 'success',
            'message': f'Maintenance logged for slot {slot_number}'
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
