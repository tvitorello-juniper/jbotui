PR_PASSPHRASE="$(date +%N | sha256sum | base64 | head -c 64)"
PR_CA_PASSPHRASE="$(date +%N%N | sha256sum | base64 | head -c 64)"
MYHOSTNAME="$(hostname -I)"
expect generate_certificate.exp $PR_PASSPHRASE $PR_CA_PASSPHRASE $MYHOSTNAME
python manage.py secretkeygen 
rabbitmq-server start -detached 
celery -A jbotserv worker -l info --loglevel=INFO --concurrency=16 --detach 
uwsgi djan.ini            