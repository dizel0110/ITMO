# Env

ML and AI module

## Table of Contents
+ [About](#about)
    + [Prerequisites](#prerequisites)
+ [Getting Started](#getting-started)
    + [Quickstart with docker-compose](#quickstart)
    + [Testing](#testing)
+ [Management commands](#management-commands)
+ [Production deploy](#production-deploy)

## About <a name = "about"></a>
ML and AI module backend server

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

### Quickstart with docker-compose <a name = "quickstart"></a>

- Start conteinerized services
```
docker-compose up -d
```
- Installing dependencies
```bash
# Do it for the first time
pip install poetry

# Do it each time you would like to setup dependencies
poetry shell (or any other venv provider like Conda or other)
poetry install --no-root
poetry install --with dev
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
python manage.py createsuperadmin
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
- `make pep8` - run linter
- `make worker` - run celery workers with auto reload
- `make scheduler` - run celery beat scheduler

## Production deploy <a name = "production-deploy"></a>

## Getting correct OS
-- Ubuntu 22.04 with latest CUDA 12.6, then run commands
```
sudo apt install python3 python3-pip
pip3 install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu115
```
### Other options to install PyTorch locally
```
https://pytorch.org/get-started/locally/
```

### Installing the NVIDIA Container Toolkit
-- Installing with Apt

## Configure the production repository:
```
 curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
  && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
```
## Optionally, configure the repository to use experimental packages:
```
 sed -i -e '/experimental/ s/^#//g' /etc/apt/sources.list.d/nvidia-container-toolkit.list
```
## Update the packages list from the repository:
```
 sudo apt-get update
```
## Install the NVIDIA Container Toolkit packages:
```
 sudo apt-get install -y nvidia-container-toolkit
```
-- Configuring Docker
## Configure the container runtime by using the nvidia-ctk command:
```
 sudo nvidia-ctk runtime configure --runtime=docker
```
## The nvidia-ctk command modifies the /etc/docker/daemon.json file on the host. The file is updated so that Docker can use the NVIDIA Container Runtime.

## Restart the Docker daemon:
```
 sudo systemctl restart docker
```
## Installing CUDA
```
 wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-keyring_1.1-1_all.deb
 sudo dpkg -i cuda-keyring_1.1-1_all.deb
 sudo apt-get update
 sudo apt-get -y install cuda-toolkit-12-6
```
## Installing Docker Compose v2
```
https://docs.docker.com/compose/install/linux/
```
## Provide access to models source files
- Vikhr-Llama3.1-8B-Instruct-R-21-09-24.Q5_K_M files must be available on "path_to_s3"
- ai-forever/sbert_large_mt_nlu_ru files must be available on "path_to_s3"
