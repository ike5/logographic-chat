#!/usr/bin/env python
"""
Comprehensive deployment test suite
"""
import os
import sys
import subprocess
import time
import requests

def test_environment():
    """Test if required environment variables are set"""
    print("Testing environment variables...")

    required_vars = ["DJANGO_SECRET_KEY", "DATABASE_URL", "PORT"]
    missing_vars = []

    for var in required_vars:
        if var not in os.environ or not os.environ[var]:
            missing_vars.append(var)
        else:
            print(f"✓ {var} = {'***' if 'SECRET' in var else os.environ[var]}")

    if missing_vars:
        print("✗ Missing environment variables:", missing_vars)
        return False

    print("✓ All required environment variables are set")
    return True

def test_migration():
    """Test database migrations"""
    print("\nTesting database migrations...")

    try:
        result = subprocess.run(
            ["python", "manage.py", "migrate", "--noinput", "--plan"],
            capture_output=True,
            text=True,
            cwd="backend"
        )

        if result.returncode == 0:
            print("✓ Migration check successful")
            print("Migration plan:")
            for line in result.stdout.split('\n'):
                if line.strip():
                    print(f"  {line.strip()}")
            return True
        else:
            print(f"✗ Migration check failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Migration test exception: {e}")
        return False

def test_asgi_start():
    """Test if ASGI application can start"""
    print("\nTesting ASGI application startup...")

    # Set Django settings
    os.environ["DJANGO_SETTINGS_MODULE"] = "logographic_chat.settings"

    try:
        # Add backend to Python path
        sys.path.insert(0, 'backend')

        # Import Django
        import django
        django.setup()
        print("✓ Django setup successful")

        # Import ASGI application
        from logographic_chat.asgi import application
        print("✓ ASGI application imported successfully")

        return True
    except Exception as e:
        print(f"✗ ASGI application failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_daphne_start():
    """Test if Daphne can start the ASGI server"""
    print("\nTesting Daphne startup...")

    port = os.environ.get("PORT", "8000")

    try:
        # Start Daphne in background
        proc = subprocess.Popen(
            [
                "daphne",
                "-b", "0.0.0.0",
                "-p", port,
                "logographic_chat.asgi:application"
            ],
            cwd="backend",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Give it time to start
        time.sleep(3)

        # Check if process is running
        if proc.poll() is not None:
            stdout, stderr = proc.communicate()
            print(f"✗ Daphne failed to start: {stderr.decode() if stderr else 'Unknown error'}")
            return False

        # Try to connect to the server
        try:
            response = requests.get(f"http://localhost:{port}/api/rooms/", timeout=5)
            print(f"✓ Server responded with status: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"✗ Could not connect to server: {e}")
            proc.terminate()
            return False

        # Clean up
        proc.terminate()
        return True

    except Exception as e:
        print(f"✗ Daphne test exception: {e}")
        return False

def test_static_files():
    """Test if static files are properly collected"""
    print("\nTesting static files...")

    static_dir = "backend/staticfiles"

    if os.path.exists(static_dir) and os.listdir(static_dir):
        print(f"✓ Static files directory exists with {len(os.listdir(static_dir))} files")
        return True
    else:
        print("✗ Static files directory missing or empty")
        return False

def main():
    print("Running comprehensive deployment tests...")
    print("=" * 60)

    tests = [
        ("Environment Variables", test_environment),
        ("Static Files", test_static_files),
        ("Database Migration", test_migration),
        ("ASGI Application", test_asgi_start),
        ("Daphne Server", test_daphne_start),
    ]

    results = {}
    for name, test_func in tests:
        print(f"\n{'='*20} {name} {'='*20}")
        results[name] = test_func()

    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY:")

    all_passed = True
    for name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n✓ All tests passed! Deployment should work.")
        return 0
    else:
        print("\n✗ Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    # Set minimal environment for testing
    if "DJANGO_SECRET_KEY" not in os.environ:
        os.environ["DJANGO_SECRET_KEY"] = "test-key-12345"
    if "DATABASE_URL" not in os.environ:
        os.environ["DATABASE_URL"] = "sqlite:///test.db"
    if "PORT" not in os.environ:
        os.environ["PORT"] = "8000"

    sys.exit(main())