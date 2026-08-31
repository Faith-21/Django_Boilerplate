.PHONY: help install run migrations migrate superuser test coverage lint format check clean

help:  ## Show the available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:  ## Create a virtualenv and install dependencies
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements-dev.txt
	test -f .env || cp .env.example .env

run:  ## Start the development server
	.venv/bin/python manage.py runserver

migrations:  ## Create migrations for model changes
	.venv/bin/python manage.py makemigrations

migrate:  ## Apply migrations
	.venv/bin/python manage.py migrate

superuser:  ## Create an administrator account
	.venv/bin/python manage.py createsuperuser

test:  ## Run the test suite
	.venv/bin/python manage.py test --settings=config.test_settings

coverage:  ## Run tests with a coverage report
	.venv/bin/coverage run manage.py test --settings=config.test_settings
	.venv/bin/coverage report

lint:  ## Check formatting and lint rules
	.venv/bin/ruff check .
	.venv/bin/ruff format --check .

format:  ## Auto-format the code
	.venv/bin/ruff format .
	.venv/bin/ruff check --fix .

check:  ## Run Django's deployment checks
	.venv/bin/python manage.py check --deploy

clean:  ## Remove caches and build artefacts
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .ruff_cache .coverage htmlcov staticfiles
