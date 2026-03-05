#!/usr/bin/env python
"""
Test script that simulates Railway deployment environment
"""
import os
import sys

# Add backend to Python path for imports
sys.path.insert(0, 'backend')

# Set Railway-like environment
os.environ["DJANGO_SETTINGS_MODULE"] = "logographic_chat.settings"
os.environ["DEBUG"] = "False"

# Railway provides these via environment variables
# For testing, we'll simulate missing ones
if "DJANGO_SECRET_KEY" not in os.environ:
    os.environ["DJANGO_SECRET_KEY"] = "fake-key-for-railway-test-12345"

if "DATABASE_URL" not in os.environ:
    # Railway should provide this - use SQLite fallback for testing
    os.environ["DATABASE_URL"] = "sqlite:///railway_test.db"

if "REDIS_URL" not in os.environ:
    # Leave empty to test in-memory fallback
    os.environ["REDIS_URL"] = ""

def test_settings():
    """Test if Django settings can load"""
    try:
        from django.conf import settings
        print("✓ Django settings loaded")
        print(f"  DEBUG = {settings.DEBUG}")
        print(f"  Database = {settings.DATABASES['default']['ENGINE']}")
        return True
    except Exception as e:
        print(f"✗ Django settings failed: {e}")
        return False

def test_database():
    """Test database connectivity"""
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        print("✓ Database connection successful")
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False

def test_asgi():
    """Test ASGI application"""
    try:
        from logographic_chat.asgi import application
        print("✓ ASGI application created successfully")
        return True
    except Exception as e:
        print(f"✗ ASGI application failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_urls():
    """Test URL patterns"""
    try:
        from django.urls import get_resolver
        resolver = get_resolver()
        patterns = resolver.url_patterns
        print(f"✓ URL resolver loaded with {len(patterns)} patterns")
        return True
    except Exception as e:
        print(f"✗ URL resolver failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing Railway deployment configuration...")
    print("=" * 50)

    tests = [
        ("Settings", test_settings),
        ("Database", test_database),
        ("ASGI", test_asgi),
        ("URLs", test_urls),
    ]

    all_passed = True
    for name, test_func in tests:
        print(f"\n{name}:")
        if not test_func():
            all_passed = False

    print("=" * 50)
    if all_passed:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)