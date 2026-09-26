# Academic Information Management System (AcadStack)

## Background

This system is meant for managing the academics information about the courses as they run in a university. Typically, a university offers several degree **programs** such as BSc, MSc, BTech, MTech, PhD. Each program requires the students to credit certain number of courses. Courses can be of elective or mandatory, and may be offered in specific academic sessions of the year. Certain minimum attendance of students in lectures may be required. Thus, the attendance data also may be required to be captured.

This application AcadStack to efficiently manage information about various **courses**, the **offerings** of those courses by various **instructors**, the **students** and course **enrollment** in those course offerings. Capturing all this informat allows deriving useful, actionable analytics about the university's academics.


## Docker based deployment

You can deploy the application using docker. Make sure that docker is installed
on the machine on which you will run the following steps. Please see this https://docs.docker.com/engine/install/
for the instructions about how to install docker engine on your machine.

1. On the target host, create a directory from where you will be deploying. E.g. by running `mkdir $HOME/acadstack-docker`
1. Change directories into that folder: `cd $HOME/acadstack-docker`
1. Copy the `docker-compose.yml` and `app_env_vars.env.example` to `$HOME/acadstack-docker` folder.
1. Copy `app_env_vars.env.example` to `app_env_vars.env` and edit it if needed. For simple demo you can leave it unchanged (except for the port number 
if it collides with something already running on your host). For anything beyond a throwaway demo, set
`SECRET_KEY` (see the comment in the file): without it every restart logs all users out.
1. Run `docker compose --env-file app_env_vars.env up -d` to launch the containers.
1. Run `docker ps | grep acadstack` to verify that the containers are up. You may see something like the following:
```bash
$ docker ps | grep acadstack
2f1cd5e70109   sodhix/acadstack-backend:v.01             "python main.py"         20 minutes ago   Up 19 minutes         0.0.0.0:5300->5300/tcp, [::]:5300->5300/tcp            acadstack_backend
5109005ae0bc   postgres:17                          "docker-entrypoint.s…"   20 minutes ago   Up 19 minutes         0.0.0.0:5432->5432/tcp, [::]:5432->5432/tcp            acadstack_postgres
e0875d9fd10e   sodhix/acadstack-frec-service:v.01        "python run.py"          20 minutes ago   Up 19 minutes         0.0.0.0:5060->5060/tcp, [::]:5060->5060/tcp             frec_svc
```
1. Run `docker exec -it acadstack_backend /bin/bash` to open a shell into the backend container. You should see:
```bash
$ docker exec -it acadstack_backend /bin/bash
root@2f1cd5e70109:/app# 
```
1. In the above container shell, run the following to create the demo data:
`python demo_data.py config.json`. `config.json` here is the copy baked into the image at
build time (it is not mounted from the host), so it already has DB credentials matching
`app_env_vars.env`; if you changed the DB password in `app_env_vars.env` you must edit
`config.json` inside this same container shell to match before running the command. You
should see something like the following:
```bash
$ docker exec -it acadstack_backend /bin/bash
root@2f1cd5e70109:/app# python demo_data.py config.json 
========== Setting up DEMO database ==========
Dropping the schema: acadstack_db
Creating the schema: acadstack_db
Database 'acadstack_db' initialized.
Created DB tables.
Created academic sessions
Creating users...
Added 290 users. Password for each user is: abcd1234
Creating courses...
Added 28 courses.
Creating course offerings and enrolling students...
Added 100 offerings, each with 46 students.
Creating course offerings and enrolling students...
...
...
Added 100 offerings, each with 60 students.
Done adding demo data.
root@2f1cd5e70109:/app#
```
1. Open the browser at `http://localhost:5300/acadstack/` and login 
using ID `acad.user` and password `abcd1234`. 
You may have to change the port (5300 is default) and the password
if you altered the one in `app_env_vars.env` and `config.json`.