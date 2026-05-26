web: python manage.py collectstatic --noinput && python manage.py migrate --noinput && gunicorn config.wsgi
release: python manage.py migrate