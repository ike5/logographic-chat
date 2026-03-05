#!/bin/bash

# Optional startup script that Railway might be looking for
# The main deployment command is in railway.json

echo "Starting logographic-chat backend..."
cd backend
python manage.py migrate --noinput
daphne -b 0.0.0.0 -p $PORT logographic_chat.asgi:application