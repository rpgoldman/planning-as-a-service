![logo100](https://github.com/AI-Planning/planning-as-a-service/assets/861782/90f1a948-d5dd-4092-8cb1-2065abe6cfb7) Planning as a service (PaaS) provides an extendable API to deploy planners online in local or cloud servers. The service
provides a queue manager to control a set of workers, which
can easily be extended with one of several planners available
in PLANUTILS.

# Getting Started


## Docker Build & Launch

1. Get sources

```bash
git clone https://github.com/AI-Planning/planning-as-a-service
cd planning-as-a-service/server
```

2. Create an .env file in the server folder:

Please create a new environment file called .env, and set up the following variable. You can reference the provided `.env.example` file.

* FLOWER_USERNAME=username #Flower Moinitor Username
* FLOWER_PASSWORD=password #Flower Moinitor Password
* MAX_MEMORY_PER_DOCKER_WORKER=4096M #Max memory each Celery worker/container can consume
* WORKER_NUMBERS=12 #Number of Celery worker/containers
* TIME_LIMIT=30 #Time limit per celery task in seconds
* MYSQL_USER=user #Metadata DB user
* MYSQL_PASSWORD=password
* MYSQL_ROOT_PASSWORD=password
* CELERY_RESULT_EXPIRE=86400 #Time for when after stored task results will be deleted on Redis
* FLOWER_MONITOR_MAX_TASKS=10000 # Maximum tasks log that will be kept on Flower

3. Start Docker:

```bash
# make sure you are in the server folder to run the makefile
cd server
sudo make
```

1. This will build the latest Planutils Image and install all the selected solvers. You can edit the Dockerfile to update the available solvers.

2. Then it will expose the Flask application's endpoints on port `5001` as well as a [Flower](https://github.com/mher/flower) server for monitoring workers on port `5555`

To add more workers:

```bash
docker compose up -d --scale worker=5 --no-recreate
```

To shut down:

```bash
docker compose down
```
To change the endpoints, update the code in [api/app.py](api/app.py)

Task changes should happen in [queue/tasks.py](celery-queue/tasks.py)


## Compatibility Issues
Please be aware that the current Singularity docker image is not compatible with the new Mac M1 CPU.


## API

- Planning solver: [localhost:5001/solver/](http://localhost:5001/solver/)
- Queue Monitor: [localhost:5555](http://localhost:5555)
- Package API: `http://localhost:5001/package/{package_name}/{package_service}`
- Manifest API: The required arguments for the POST request are defined in the Planutils package manifests, and can be easily viewed at: `http://localhost:5001/docs/{package_name}`

## Local Dev

Assuming you are in the `server/` directory.

```bash
sudo apt-get install redis-server
sudo service redis-server start
virtualenv env
pip install -r requirements.txt
```

### Run server

New terminal (If you are using vscode, do ```CTRL+SHIFT+` ``` to open a new terminal)

Run Flask:

```bash
source env/bin/activate
cd api
python app.py
```

New terminal and start celery:

```bash
source env/bin/activate
cd celery-queue
celery -A tasks worker --loglevel=info
```

New Terminal and start flower (queue monitoring):

```bash
source env/bin/activate
cd celery-queue
flower -A tasks --port=5555 --broker=redis://localhost:6379/0
```

### Debug

Go to `server` folder and open `vscode`. Install vscode first. Note that this assumes you have started celery and flower as instructed above.

```bash
cd server
code . &
```

Go to the debug symbol add breakpoints and debug as shown below:
![image](https://github.com/AI-Planning/planning-as-a-service/blob/master/docs/videos/debug.gif)


### Example use

A simple python script to send a POST request to the lama-first planner, getting back stdout, stderr, and the generated plan:

```python
import requests
import time
from pprint import pprint

req_body = {
"domain":"(define (domain BLOCKS) (:requirements :strips) (:predicates (on ?x ?y) (ontable ?x) (clear ?x) (handempty) (holding ?x) ) (:action pick-up :parameters (?x) :precondition (and (clear ?x) (ontable ?x) (handempty)) :effect (and (not (ontable ?x)) (not (clear ?x)) (not (handempty)) (holding ?x))) (:action put-down :parameters (?x) :precondition (holding ?x) :effect (and (not (holding ?x)) (clear ?x) (handempty) (ontable ?x))) (:action stack :parameters (?x ?y) :precondition (and (holding ?x) (clear ?y)) :effect (and (not (holding ?x)) (not (clear ?y)) (clear ?x) (handempty) (on ?x ?y))) (:action unstack :parameters (?x ?y) :precondition (and (on ?x ?y) (clear ?x) (handempty)) :effect (and (holding ?x) (clear ?y) (not (clear ?x)) (not (handempty)) (not (on ?x ?y)))))",
"problem":"(define (problem BLOCKS-4-0) (:domain BLOCKS) (:objects D B A C ) (:INIT (CLEAR C) (CLEAR A) (CLEAR B) (CLEAR D) (ONTABLE C) (ONTABLE A) (ONTABLE B) (ONTABLE D) (HANDEMPTY)) (:goal (AND (ON D C) (ON C B) (ON B A))) )"
}

# Send job request to solve endpoint
solve_request_url=requests.post("http://localhost:5001/package/lama-first/solve", json=req_body).json()

# Query the result in the job
celery_result=requests.post('http://localhost:5001' + solve_request_url['result'])

print('Computing...')
while celery_result.json().get("status","")== 'PENDING':

    # Query the result every 0.5 seconds while the job is executing
    celery_result=requests.post('http://localhost:5001' + solve_request_url['result'])
    time.sleep(0.5)

pprint(celery_result.json())
```

This python code will run a POST solve request on the lama-first solver, and return the link to access the result from the celery queue. In the meantime, the program 
polls for the task to be completed, and prints out the returned json when it is. 

If you want to use an [adaptor](https://github.com/AI-Planning/planning-as-a-service/blob/master/server/api/adaptor) to parse the returned plan files, you can specify the arguments when processing the job result:

```python
# Query the result in the job
celery_result=requests.post('http://localhost:5001' + solve_request_url['result'], json={"adaptor":"planning_editor_adaptor"}  )
```

* Note: This script needs to be run in the same environment as the docker container

## Adding new Planners

Install a planner available in planutils by adding the installation line in the [worker dockerfile](https://github.com/AI-Planning/planning-as-a-service/blob/master/server/Dockerfile).

```dockerfile
RUN planutils install -f -y dual-bfws-ffparser
```
To learn how to setup a new planner in planutils, see the information in [planuitls github repo](https://github.com/AI-Planning/planutils#5-add-a-new-package)

## Troubleshooting

### Worker failures

These would manifest themselves as the worker(s) repeatedly restarting.  You can see this in `docker compose logs worker`.

One possible explanation is out of memory errors.  To investigate this: use `docker container list` to find the identifier of the docker container for the worker.  Invoke `docker inspect <docker-container-id>` and look for something like this:
```
        "State": {
            "Status": "restarting",
            "Running": true,
            "Paused": false,
            "Restarting": true,
            "OOMKilled": true,    <----------------
            "Dead": false,
            "Pid": 0,
            "ExitCode": 137,
            "Error": "",
            "StartedAt": "2025-05-08T17:44:23.979871719Z",
            "FinishedAt": "2025-05-08T17:44:28.22886954Z"
        },
```

If this is the problem, try setting the environment variable `MAX_MEMORY_PER_DOCKER_WORKER` to a larger value before invoking `make` to start the system.

## Editor.Planning.Domains plugin

If you want to edit the plugin exposing the service to the online editor, take a look at the [plugin codebase](https://github.com/AI-Planning/planning-as-a-service-plugin)

## Docker Flask Celery Redis

A basic [Docker Compose](https://docs.docker.com/compose/) template for orchestrating a [Flask](http://flask.pocoo.org/) application & a [Celery](http://www.celeryproject.org/) queue with [Redis](https://redis.io/)

---

Docker structure adapted from [https://github.com/mattkohl/docker-flask-celery-redis](https://github.com/mattkohl/docker-flask-celery-redis)
