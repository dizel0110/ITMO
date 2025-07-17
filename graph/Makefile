.PHONY: all help clean line_code migrate migrate_app run pep8 qa flush

# target: all - Default target. Does nothing.
all:
	@clear
	@echo "Hello $(LOGNAME), nothing to do by default"
	@echo "Try 'make help'"

# target: help - Display callable targets.
help:
	@clear
	@egrep "^# target:" [Mm]akefile

# target: clean - Delete pycache
clean:
	echo "### Cleaning *.pyc and .DS_Store files "
	find . -name '*.pyc' -exec rm -f {} \;
	find . -name '.DS_Store' -exec rm -f {} \;
	find . -name "__pycache__" -type d -exec rm -rf {} +

# target: line_code - counting lines of code
line_code:
	echo "### Counting lines of code within the project"
	echo "# Python:" ; find . -name '*.py' -type f -exec cat {} + | wc -l
	echo "# JavaScript:" ; find . -name '*.js' -type f -exec cat {} + | wc -l
	echo "# HTML:" ; find . -name '*.html' -type f -exec cat {} + | wc -l
	echo "# CSS:" ; find . -name '*.css' -type f -exec cat {} + | wc -l

# target: migrate - Makemigrations and migration
migrate:
	python3 manage.py makemigrations && python3 manage.py migrate

# target: migrate - Makemigrations application and migration
migrate_app:
	python3 manage.py makemigrations $(APP) && python3 manage.py migrate

# target: run - Run server
run:
	python3 manage.py runserver 0.0.0.0:8000

# target: mypy - Run static typing
mypy:
	mypy --config-file=mypy.ini akcent_graph

# target: pylint - Checks for errors, enforces a coding standard, looks for code smells.
pylint:
	pylint akcent_graph

# target: pep8 - Run code style test
pep8:
	flake8 akcent_graph

# target: isort - Sorts imports
isort:
	isort akcent_graph

# target: black - Code formatting
black:
	black akcent_graph

# target: all in one formatters
fmt: isort black

# target: all in one lints
lint: black mypy pylint pep8

# target: qa - Run tests
qa:
	pytest

# target: flush - clean database
flush:
	python3 manage.py flush

# target: translate - generate translations
translate:
	python3 manage.py makemessages --locale=ru --ignore=venv/* --ignore=volumes/* --no-wrap

# target: translate_compile - compile translations binary
translate_compile:
	python3 manage.py compilemessages --locale=ru

# target: worker - Run celery worker with auto reload
worker:
	watchmedo auto-restart --directory=./ --pattern=*.py --recursive -- celery -A akcent_graph worker -l INFO --autoscale=10,2 --purge

# target: scheduler - Run celery worker scheduler
scheduler:
	watchmedo auto-restart --directory=./ --pattern=*.py --recursive -- celery -A akcent_graph beat -l INFO --pidfile= --scheduler django_celery_beat.schedulers:DatabaseScheduler

# target: shell - Get into a shell inside app container
shell:
	docker-compose exec app sh -c "python3 manage.py shell_plus"

# target: check migrations
check_migrations:
	python manage.py lintmigrations

# target: sentry generate key to pass info env file
sentry_gen_key:
	docker-compose -f docker-compose-sentry.yml run --rm sentry-base config generate-secret-key

# target: upgrade db to init all migrations needed to run sentry
sentry_db_init:
	docker-compose -f docker-compose-sentry.yml run --rm sentry-base upgrade

# target: up all sentry containers
sentry_run:
	docker-compose -f docker-compose-sentry.yml up -d
