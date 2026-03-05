#!/usr/bin/env python
"""
Check if Django can start with production settings
"""
import os
import sys

# Set production environment
os.environ["DJANGO_SETTINGS_MODULE"] = "logographic_chat.settings"
os.environ["DEBUG"] = "False"

# Mock Railway environment variables if not set
if "DJANGO_SECRET_KEY" not in os.environ:
    os.environ["DJANGO_SECRET_KEY"] = "fake-production-key-for-testing-only"

if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "sqlite:///test.db"  # Fallback for testing

if "REDIS_URL" not in os.environ:
    os.environ["REDIS_URL"] = ""  # Empty Redis URL should trigger in-memory mode

try:
    print("Testing Django production configuration...")

    # Import Django settings
    from django.conf import settings
    print("✓ Settings imported successfully")

    # Test channel layers
    from channels.layers import get_channel_layer
    channel_layer = get_channel_layer()
    print("✓ Channel layer configured successfully")

    # Test database connection
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        print("✓ Database connection successful")

    # Test ASGI application
    from logographic_chat.asgi import application
    print("✓ ASGI application loads successfully")

    print("All checks passed! Production configuration is valid.")
    sys.exit(0)

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)