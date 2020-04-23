acousticbrainz-server
=====================

The server components for the AcousticBrainz project.

Please report issues here: http://tickets.musicbrainz.org/browse/AB


## Installation and Running

### Docker

We use [docker](https://www.docker.com/) and [docker-compose](https://docs.docker.com/compose/) to run the AcousticBrainz server.
Ensure that you have these tools installed, [following the installation instructions](https://docs.docker.com/engine/install/).

### Configuration

Copy the following two configuration files:

1. `config.py.example` to `config.py`
2. `profile.conf.in.sample` to `profile.conf.in` in the `./hl_extractor/` directory
  In `profile.conf.in` you need to set the `models_essentia_git_sha` value.
  Unless you know what you are doing, this value should be **v2.1_beta1**

#### Running `docker-compose` commands

For convenience, we provide a script `develop.sh` which calls `docker-compose`. We also have some additional
subcommands for commonly used commands. Some of these subcommands take no arguments:

    ./develop.sh bash   # open a bash shell in a new container in the webserver service
    ./develop.sh psql   # run psql, connecting to the database
    ./develop.sh shell  # run a flask shell in ipython

And some subcommands take arguments, passing them to the underlying program:

    ./develop.sh npm    # run npm in a new container in the webserver service
    ./develop.sh manage # run python manage.py in a new container in the webserver service
    ./develop.sh ...    # run docker-compose

If you want to run `docker-compose` yourself you are welcome to do so, however keep in
mind that we call it in the following way, to standardise the project name:

    docker-compose -f docker/docker-compose.dev.yml -p acousticbrainz-server <args>

### Build and initial configuration

Build the docker containers needed for AcousticBrainz by running the following:

    ./develop.sh build

### Running 

Start the webserver and other required services with:

    ./develop.sh up

The first time you install AcousticBrainz, you will need to initialize the AcousticBrainz database.
Run in a separate terminal:

    ./develop.sh manage init_db
    
You will be able to view your local AcousticBrainz server at http://localhost:8080

## Development notes

### Database

In order to load a psql session, use the following command:

    ./develop.sh psql

### Building static files

We use webpack as our JavaScript/CSS build system.

#### First-time npm setup
For development, the first time that you install acousticbrainz you must install
node packages in your local directory.

    ./develop.sh npm install

This has the effect of creating a `node_modules` directory in your local code checkout.

To build stylesheets and javascript bundles, run webpack:

    ./develop.sh npm run build:dev

You will need to rebuild static files after you modify JavaScript or CSS. If you want to rebuild
these source files as you change them then you can run webpack in watch mode:

    ./develop.sh npm run build:dev -- --watch

### Login

To use the dataset tools you need to configure OAuth with MusicBrainz.
Log in to your MusicBrainz account (or create one if needed) and create
[a new application](https://musicbrainz.org/account/applications).

Choose a name (for example, "AcousticBrainz development"), set Type to "Web Application"
and set the Callback URL to http://localhost:8080/login/musicbrainz/post

Copy the OAuth Client ID and OAuth Client Secret values to
`config.py` as `MUSICBRAINZ_CLIENT_ID` and `MUSICBRAINZ_CLIENT_SECRET`.

You should now be able to use the menu in the top corner of your AcousticBrainz server
to log in.

### Admin interface

Once you have logged in, you can make your user an admin, by running

    ./develop.sh manage add_admin <your user>

You should now be able to access the admin section at http://localhost:8080/admin


## Working with data

### Importing

> Before you import or export data, make sure you understand how
[docker bind mounts](https://docs.docker.com/engine/admin/volumes/bind-mounts/) work.
The following commands will work if you specify paths in the current directory, but
if you want to specify paths somewhere else (e.g. a Downloads or tmp directory) you
must specify an additional `--mount` flag.

AcousticBrainz provides data dumps that you can import into your own server.
Latest database dump is available at http://acousticbrainz.org/download. You
need to download full database dump from this page and use it during database
initialization:

    ./develop.sh run --rm webserver python2 manage.py init_db path_to_the_archive

you can also easily remove existing database before initialization using
`--force` option:

    ./develop.sh run --rm webserver python2 manage.py init_db --force path_to_the_archive

or import archive after database is created:

    ./develop.sh run --rm webserver python2 manage.py import_data path_to_the_archive

*You can also import dumps that you created yourself. This process is described
below (see `dump full_db` command).*

### Exporting

There are several ways to export data out of AcousticBrainz server. You can
create full database dump or export only low-level and high-level data in JSON
format. Both ways support incremental dumping.

#### Examples

**Full database dump:**

    ./develop.sh manage dump full_db

**JSON dump:**

    ./develop.sh manage dump json

*Creates two separate full JSON dumps with low-level and high-level data.*

**Incremental dumps:**

    ./develop.sh manage dump incremental

*Creates new incremental dump in three different formats: usual database dump,
low-level and high-level JSON.*

**Previous incremental dumps:**

    ./develop.sh manage dump incremental --id 42

*Same as another one, but recreates previously created incremental dump.*

## Test your changes with unit tests

Unit tests are an important part of AcousticBrainz. It helps make it easier for
developers to test changes and help prevent easily avoidable mistakes later on.
Before commiting new code or making a pull request, run the unit tests on your code.

    ./test.sh

This will start a set of docker containers separate to your development environment,
run the tests, and then stop and remove the containers. To run tests more rapidly
without having to bring up and take down containers all the time, you can run
each step individually. To bring up containers in the background:

    ./test.sh -u

Then run your tests when you need with:

    ./test.sh [optional arguments to pass to py.test]

Stop the test containers with:

    ./test.sh -s

This will stop but not delete the containers. You can delete the containers with:

    ./test.sh -d

We use the `-p` flag to `docker-compose` to start the test containers as a new
project, `acousticbrainztest` so that containers don't conflict with
already running development containers. You can access containers directly
while they are running (e.g. with `docker exec`) with this name (e.g. `acousticbrainztest_db_1`)

The database has no separate volume for data, this means that any data
in the test database will disappear when the containers are
deleted (at the end of standalone `./test.sh`, or after `./test.sh -d`)

We forward the port from postgres to `localhost:15431`, so you can connect to it
with `psql` on your host if you want to inspect the contents of the database.
