#!/usr/bin/env bash
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

if ! command -v stripe &> /dev/null; then
    echo "Stripe CLI not found, installing..."
    curl -fsSL https://cli.stripe.com/install.sh | bash
    export PATH="$PATH:/home/user/.local/bin"
fi

python manage.py collectstatic --no-input

python manage.py makemigrations
python manage.py migrate

celery -A config worker --loglevel=info
