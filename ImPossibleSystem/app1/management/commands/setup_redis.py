from django.core.management.base import BaseCommand
from django.conf import settings
from django_redis import get_redis_connection
from distutils.version import LooseVersion
import redis
import sys
import subprocess
import time
import platform
import os
import re

class Command(BaseCommand):
    help = 'Sets up Redis and verifies the connection for ParkSense'

    def handle(self, *args, **kwargs):
        self.stdout.write('Setting up Redis...')
        
        # Basic Redis connection test
        try:
            # Try to connect to Redis directly
            test_connection = redis.Redis(host='localhost', port=6379, db=0)
            info = test_connection.info()
            
            # Extract version from info
            version = info.get('redis_version', '0.0.0')
            self.stdout.write(self.style.SUCCESS(f'Redis server version: {version}'))
            
            # Version compatibility check
            if LooseVersion(version) < LooseVersion('3.0.0'):
                self.stdout.write(self.style.ERROR(f'Redis version {version} is too old. Minimum required version is 3.0.0'))
                sys.exit(1)
                
            if LooseVersion(version) < LooseVersion('7.0.0'):
                self.stdout.write(self.style.WARNING(
                    f'Redis version {version} is older than recommended version 7.0.0.\n'
                    'Some advanced features might not be available, but basic functionality will work.'
                ))
            
            self.stdout.write(self.style.SUCCESS('Redis server is running'))
            
        except redis.ConnectionError as e:
            self.stdout.write(self.style.ERROR('Redis server is not running.'))
            
            if platform.system().lower() == 'windows':
                self.stdout.write(self.style.WARNING('Please start Redis server using the Redis Windows Service'))
                self.stdout.write('1. Open Services (services.msc)')
                self.stdout.write('2. Find Redis service')
                self.stdout.write('3. Right-click and select Start')
            else:
                self.stdout.write(self.style.WARNING('Attempting to start Redis server...'))
                try:
                    if platform.system().lower() == 'darwin':  # macOS
                        subprocess.run(['brew', 'services', 'start', 'redis'])
                    else:  # Linux
                        subprocess.run(['sudo', 'service', 'redis-server', 'start'])
                    time.sleep(2)
                except Exception as start_error:
                    self.stdout.write(self.style.ERROR(f'Failed to start Redis server: {start_error}'))
            sys.exit(1)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error connecting to Redis: {e}'))
            sys.exit(1)

        # Verify Redis connection and configuration
        try:
            # Test basic Redis operations that work in Redis 3.0
            test_connection.set('test_key', 'test_value')
            test_value = test_connection.get('test_key')
            test_connection.delete('test_key')
            
            if test_value != b'test_value':
                raise Exception('Basic Redis operations failed')
                
            self.stdout.write(self.style.SUCCESS('Basic Redis operations working correctly'))

            # Display cache configuration
            self.stdout.write('\nCache Configuration:')
            try:
                default_cache = settings.CACHES.get('default', {})
                parking_cache = settings.CACHES.get('parking_updates', {})
                
                if not default_cache or not parking_cache:
                    self.stdout.write(self.style.WARNING(
                        'Cache configuration is missing in settings.py. Please add the following configuration:\n\n'
                        'CACHES = {\n'
                        '    "default": {\n'
                        '        "BACKEND": "django_redis.cache.RedisCache",\n'
                        '        "LOCATION": "redis://127.0.0.1:6379/1",\n'
                        '        "OPTIONS": {\n'
                        '            "CLIENT_CLASS": "django_redis.client.DefaultClient",\n'
                        '            "IGNORE_EXCEPTIONS": True\n'
                        '        }\n'
                        '    },\n'
                        '    "parking_updates": {\n'
                        '        "BACKEND": "django_redis.cache.RedisCache",\n'
                        '        "LOCATION": "redis://127.0.0.1:6379/2",\n'
                        '        "OPTIONS": {\n'
                        '            "CLIENT_CLASS": "django_redis.client.DefaultClient",\n'
                        '            "IGNORE_EXCEPTIONS": True,\n'
                        '            "MAX_ENTRIES": 100\n'
                        '        }\n'
                        '    }\n'
                        '}\n'
                    ))
                else:
                    self.stdout.write(f'Default cache location: {default_cache.get("LOCATION", "Not configured")}')
                    self.stdout.write(f'Parking updates cache location: {parking_cache.get("LOCATION", "Not configured")}')
                    self.stdout.write(f'Parking slot cache timeout: {getattr(settings, "PARKING_SLOT_CACHE_TIMEOUT", "Not configured")} seconds')

                # Clear existing cache (optional)
                clear = input('\nDo you want to clear existing cache? (y/n): ').lower()
                if clear == 'y':
                    # Use FLUSHDB command directly for Redis 3.0 compatibility
                    test_connection.execute_command('SELECT', '1')
                    test_connection.execute_command('FLUSHDB')
                    test_connection.execute_command('SELECT', '2')
                    test_connection.execute_command('FLUSHDB')
                    self.stdout.write(self.style.SUCCESS('Cache cleared successfully'))

            except AttributeError:
                self.stdout.write(self.style.ERROR('CACHES setting is not defined in settings.py'))

        except redis.ConnectionError as e:
            self.stdout.write(self.style.ERROR(f'Failed to connect to Redis: {e}'))
            self.stdout.write('Please check if Redis is running and the configuration is correct')
            sys.exit(1)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'An error occurred: {e}'))
            sys.exit(1)

        self.stdout.write(self.style.SUCCESS('\nRedis setup completed successfully!'))
