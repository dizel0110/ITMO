# Graph

## Table of Contents
+ [About](#about)
    + [Prerequisites](#prerequisites)
+ [Getting Started](#getting-started)
    + [Quickstart with docker-compose](#quickstart)
    + [Testing](#testing)
+ [Management commands](#management-commands)

## About <a name = "about"></a>
  Graph backend server

### Prerequisites <a name = "prerequisites"></a>
```
Python 3.11.3
Postgres (inside container)
Redis (inside container)
Celery (inside container)
```
```
docker v20+
docker-compose v1.27+
```

## Getting Started <a name = "getting-started"></a>
These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Download from s3 <a name = "download"></a>
You need to download files from "s3_path" and put them in the folder "work_path" .

### Quickstart with docker-compose <a name = "quickstart"></a>

- Start conteinerized services
```bash
docker-compose up -d
```
- Installing dependencies
```bash
# Do it for the first time
pip install poetry

# Do it each time you would like to setup dependencies
poetry shell
poetry install
pre-commit install
```
- Copying configs
```
cp example.env .env
```
- Start migrations
```
python manage.py migrate
```
- Create createsuperuser
```
python manage.py createsuperuser
```
- Compile translations

```
make translate_compile
```
- Init neo4j models
```
python manage.py install_labels
```
- Load data
```
python3 manage.py load_init_data
python3 manage.py get_annoy_indexes
```
- Start development server
```
python manage.py runserver
```
or run command
```
make run
```

Server will start on localhost:8000


## Management commands <a name = "management-commands"></a>

## Command-helpers for local development

- `make help` - display available commands
- `make run` - run local developer server
- `make qa` - run tests
- `make fmt` - run code auto-formatting
- `make lint` - run static code analyzers
- `make worker` - run celery workers with auto reload
- `make scheduler` - run celery beat scheduler
