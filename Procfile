web: python manage.py collectstatic --noinput && python manage.py migrate --noinput && gunicorn config.wsgi
web: gunicorn config.wsgi --log-file -
release: python manage.py migrate