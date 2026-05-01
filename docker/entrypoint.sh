#!/bin/sh
set -e

python -c "import os, time\nhost=os.environ.get('POSTGRES_HOST')\nif host:\n  import socket\n  port=int(os.environ.get('POSTGRES_PORT','5432'))\n  for _ in range(30):\n    try:\n      s=socket.create_connection((host, port), timeout=1)\n      s.close()\n      break\n    except OSError:\n      time.sleep(1)\n"

python manage.py migrate --noinput
python manage.py runserver 0.0.0.0:8000

