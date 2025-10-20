#!/bin/bash
set -e
alembic upgrade head
python -m app.scripts.admin_seed
exec "$@"