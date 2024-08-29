#!/usr/bin/env bash
set -o errexit

if ! command -v stripe &> /dev/null
then
    echo "Stripe CLI не найден, установка..."
    curl -fsSL https://cli.stripe.com/install.sh | bash
    export PATH="$PATH:/home/user/.local/bin"
fi

pip install -r requirements.txt

python manage.py collectstatic --no-input

python manage.py makemigrations

python manage.py migrate

