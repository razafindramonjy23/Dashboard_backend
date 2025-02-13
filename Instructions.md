reto serveur alefa aloha 


docker run -p 6379:6379 redis
celery -A api worker --loglevel=info --pool=solo
redis-sever na am docker de tih => docker run -p 6379:6379 redis 


python manage.py start_scheduler

#pour importer le base rehetra amin'ny alalan'ny sychro
python manage.py start_scheduler

#importer depuis expertsender
python manage.py expertsender
