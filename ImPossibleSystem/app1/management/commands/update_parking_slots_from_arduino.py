import logging
import re
import time
import sys
import glob
import serial
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from django.core.cache import caches
from app1.models import ParkingSlot, ParkingHistory
from collections import defaultdict
import json
from datetime import datetime

# Configure a logger specifically for this command
logger = logging.getLogger('arduino_update_command')
logger.setLevel(logging.INFO)

# If no handlers exist, add a console handler
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - ARDUINO_UPDATE - %(levelname)s: %(message)s'
    ))
    logger.addHandler(console_handler)

def datetime_serializer(obj):
    """
    Custom JSON serializer for datetime objects
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

class Command(BaseCommand):
    help = 'Update parking slot status from Arduino serial data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--port', 
            type=str, 
            help='Serial port of Arduino (e.g., /dev/ttyACM0 or /dev/ttyUSB0)', 
            default=None
        )
        parser.add_argument(
            '--baud', 
            type=int, 
            help='Baud rate of serial connection', 
            default=9600
        )

    def handle(self, *args, **options):
        # Logging setup
        import os
        from pathlib import Path

        # Create logs directory in the project root if it doesn't exist
        log_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))) / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / 'arduino_parking_sensor.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filename=str(log_file)
        )
        logger = logging.getLogger('arduino_parking_sensor')

        # Port detection
        port = options['port']
        baud_rate = options['baud']

        # Detailed port diagnostics
        self.print_port_diagnostics(logger)

        # If no port specified, try to auto-detect
        if not port:
            port = self.find_arduino_port(logger)
            if not port:
                self.stderr.write(self.style.ERROR('No Arduino port found. Please specify a port manually.'))
                logger.error('No Arduino port found.')
                sys.exit(1)

        logger.info(f'Using Arduino port: {port}')
        self.stdout.write(f'Using Arduino port: {port}')

        # Slot update tracking
        slot_updates = defaultdict(lambda: {
            'current_distance': None,
            'status': None,
            'last_updated': None,
            'occupation_start': None,
            'total_occupancy_count': 0,
            'last_24h_occupancy_count': 0
        })
        last_bulk_update_time = time.time()

        while True:
            try:
                with serial.Serial(port, baud_rate, timeout=1) as ser:
                    logger.info(f'Successfully connected to Arduino on {port} at {baud_rate} baud')
                    self.stdout.write(f'Successfully connected to Arduino on {port} at {baud_rate} baud')

                    while True:
                        try:
                            # Read a line from serial
                            line = ser.readline().decode('utf-8').strip()
                            
                            if line and ('Car' in line or 'Motorcycle' in line):
                                # Parse the line
                                match = re.match(r'(\w+)\s+(\d+):\s+([\d.]+)\s+cm\s+-\s+(\w+)', line)
                                
                                if match:
                                    vehicle_type = match.group(1).lower()
                                    arduino_slot_number = int(match.group(2))
                                    distance = float(match.group(3))
                                    status = match.group(4).lower()

                                    # Map Arduino slot numbers to database slot numbers
                                    if vehicle_type == 'motorcycle':
                                        slot_number = arduino_slot_number + 3
                                    else:  # car
                                        slot_number = arduino_slot_number

                                    # Track slot updates
                                    now = timezone.now()
                                    slot_key = f"{vehicle_type}_{slot_number}"
                                    
                                    slot_updates[slot_key]['current_distance'] = distance
                                    slot_updates[slot_key]['status'] = 'occupied' if status == 'occupied' else 'available'
                                    slot_updates[slot_key]['last_updated'] = now

                            # Check if it's time for a bulk update (every 5 seconds)
                            current_time = time.time()
                            if current_time - last_bulk_update_time >= 5:
                                # Log the collected updates before bulk update
                                logger.info("Collected Updates:")
                                for key, update in slot_updates.items():
                                    logger.info(f"{key}: {update}")
                                
                                if slot_updates:  # Only update if there are changes
                                    # Collect all updates before bulk update
                                    final_updates = dict(slot_updates)
                                    
                                    # Perform bulk update with ALL collected updates
                                    self.bulk_update_slots(final_updates)
                                
                                last_bulk_update_time = current_time
                                slot_updates.clear()

                            # Small sleep to prevent tight looping
                            time.sleep(0.1)
                        
                        except UnicodeDecodeError:
                            logger.warning(f'Could not decode line: {line}')
                        
                        except Exception as e:
                            logger.error(f'Error processing serial data: {e}')
                            break
                
            except serial.SerialException as e:
                logger.error(f'Serial connection error: {e}')
                self.stderr.write(f'Could not open serial port {port}: {e}')
                
                # Try to find a new port if the previous one failed
                port = self.find_arduino_port(logger)
                if not port:
                    self.stderr.write(self.style.ERROR('No Arduino port found. Retrying...'))
                    logger.error('No Arduino port found.')
                    time.sleep(10)
                    continue
            
            except Exception as e:
                logger.error(f'Unexpected error: {e}')
                self.stdout.write(f'Unexpected error: {e}')
                time.sleep(10)
            
            # Wait before attempting to reconnect
            logger.info('Waiting 10 seconds before attempting to reconnect...')
            time.sleep(10)

    def bulk_update_slots(self, slot_updates):
        """
        Perform comprehensive bulk update of all parking slots in a single transaction
        
        Ensures all slot updates are processed together and cache is updated once
        """
        # Validate input
        if not slot_updates:
            logger.warning("No slot updates received")
            return

        try:
            # Get Redis connection for cache updates
            from django_redis import get_redis_connection
            redis_client = get_redis_connection('parking_updates')

            with transaction.atomic():
                # Prepare comprehensive update structure
                parking_updates = {
                    'car_slots': [],
                    'motorcycle_slots': [],
                    'timestamp': time.time()
                }

                # Collect all slot updates
                now = timezone.now()
                processed_slots = {}

                # First, validate all incoming updates
                for slot_key, update_data in slot_updates.items():
                    try:
                        vehicle_type, slot_number = slot_key.split('_')
                        slot_number = int(slot_number)

                        # Find the corresponding ParkingSlot
                        slot = ParkingSlot.objects.get(
                            vehicle_type=vehicle_type, 
                            slot_number=slot_number
                        )

                        # Update slot status and distance
                        old_status = slot.status
                        new_status = update_data['status']

                        if new_status != old_status:
                            # Track occupation history
                            if new_status == 'occupied':
                                slot.occupation_start = now
                                slot.total_occupancy_count += 1
                                slot.last_24h_occupancy_count += 1
                            else:
                                # Calculate total occupation time
                                if slot.occupation_start:
                                    occupation_duration = now - slot.occupation_start
                                    slot.total_occupancy_time += occupation_duration
                                    slot.last_24h_occupancy_time += occupation_duration
                                    slot.occupation_start = None

                        # Update slot attributes
                        slot.status = new_status
                        slot.current_distance = update_data['current_distance']
                        slot.last_updated = now
                        slot.save()

                        # Create parking history record
                        ParkingHistory.objects.create(
                            slot=slot,
                            timestamp=now,
                            status=new_status,
                            duration=timezone.timedelta(seconds=0)  # Placeholder
                        )

                        # Prepare update for cache
                        slot_update = {
                            'slot_number': slot.slot_number,
                            'sensor_id': slot.sensor_id,
                            'status': slot.status,
                            'current_distance': slot.current_distance,
                            'last_updated': slot.last_updated.isoformat()
                        }

                        # Categorize slots
                        if vehicle_type == 'car':
                            parking_updates['car_slots'].append(slot_update)
                        elif vehicle_type == 'motorcycle':
                            parking_updates['motorcycle_slots'].append(slot_update)

                    except ParkingSlot.DoesNotExist:
                        logger.warning(f"No slot found for {slot_key}")
                    except Exception as e:
                        logger.error(f"Error processing slot {slot_key}: {e}")

                # Prepare cache data
                try:
                    # Serialize updates with custom datetime handling
                    cache_data = json.dumps(
                        parking_updates, 
                        default=lambda obj: obj.isoformat() if hasattr(obj, 'isoformat') else str(obj)
                    )

                    # Update Redis cache
                    redis_client.set('latest_parking_updates', cache_data, ex=60)
                    
                    # Log cache update details
                    logger.info("Redis Cache Update:")
                    logger.info(f"Car Slots: {len(parking_updates['car_slots'])}")
                    logger.info(f"Motorcycle Slots: {len(parking_updates['motorcycle_slots'])}")
                    
                    # Verify cache contents
                    retrieved_cache = redis_client.get('latest_parking_updates')
                    if retrieved_cache:
                        retrieved_cache = retrieved_cache.decode('utf-8') if isinstance(retrieved_cache, bytes) else retrieved_cache
                        logger.info(f"Retrieved Cache: {retrieved_cache}")
                    else:
                        logger.warning("No cache retrieved after setting")

                except Exception as cache_error:
                    logger.error(f"Cache update error: {cache_error}")

        except Exception as e:
            logger.error(f"Error in bulk slot update: {e}")
            raise

    def find_arduino_port(self, logger=None):
        """
        Automatically detect Arduino serial port
        Tries common port patterns
        """
        if logger is None:
            logger = logging.getLogger('arduino_parking_sensor')

        possible_ports = [
            '/dev/ttyACM*',   # Arduino Uno, Leonardo
            '/dev/ttyUSB*',   # Arduino with USB-to-Serial adapter
            '/dev/tty.usbserial*',  # Mac OS X
            '/dev/tty.usbmodem*',   # Mac OS X
        ]
        
        arduino_ports = []
        for pattern in possible_ports:
            pattern_matches = glob.glob(pattern)
            logger.info(f"Checking pattern {pattern}: {pattern_matches}")
            arduino_ports.extend(pattern_matches)
        
        logger.info(f"Found possible Arduino ports: {arduino_ports}")
        
        # Try to open each port
        for port in arduino_ports:
            try:
                logger.info(f"Attempting to open port: {port}")
                ser = serial.Serial(port, 9600, timeout=1)
                ser.close()
                logger.info(f"Successfully tested port: {port}")
                return port
            except (OSError, serial.SerialException) as e:
                logger.warning(f"Could not open port {port}: {e}")
                continue
        
        return None

    def print_port_diagnostics(self, logger=None):
        """
        Print detailed diagnostics about available serial ports
        """
        if logger is None:
            logger = logging.getLogger('arduino_parking_sensor')

        try:
            import serial.tools.list_ports

            logger.info("Serial Port Diagnostics:")
            ports = list(serial.tools.list_ports.comports())
            
            if not ports:
                logger.error("No serial ports found.")
                self.stdout.write("No serial ports found.")
                return

            for port, desc, hwid in ports:
                logger.info(f"Port: {port}")
                logger.info(f"Description: {desc}")
                logger.info(f"Hardware ID: {hwid}")
                self.stdout.write(f"Port: {port}")
                self.stdout.write(f"Description: {desc}")
                self.stdout.write(f"Hardware ID: {hwid}")
                self.stdout.write("---")

        except ImportError:
            logger.error("serial.tools.list_ports module not available")
            self.stdout.write("Could not import serial port diagnostics module")
