acousticbrainz-server
=====================

The server components for the AcousticBrainz project.

Please report issues here: http://tickets.musicbrainz.org/browse/AB


## Installation and Running

### Docker

You can use [docker](https://www.docker.com/) and [docker-compose](https://docs.docker.com/compose/) to run the AcousticBrainz server. Make sure docker and docker-compose are installed.
Then copy two config files:

1. `custom_config.py.example` to `custom_config.py` *(you don't need to modify this file)*
2. `profile.conf.in.sample` to `profile.conf.in` in the `./hl_extractor/` directory
  In `profile.conf.in` you need to set the `models_essentia_git_sha` value.
  Unless you know what you are doing, this value should be **v2.1_beta1**

#### Running `docker-compose` commands

For convenience, we provide a script `develop.sh` which does the same as running:

    docker-compose -f docker/docker-compose.yml -p acousticbrainz-server <args>

Then, in order to download all the software and build and start the containers needed to run AcousticBrainz, use the following command:

#### Build

    ./develop.sh up --build

The first time you install acousticbrainz, you will need to initialize the AcousticBrainz database:

    ./develop.sh run --rm  webserver python2 manage.py init_db

In order to load a psql session, use the following command:

    ./develop.sh run --rm db psql -U acousticbrainz -h db

### Setup the MusicBrainz Server

MusicBrainz database containing all the MusicBrainz metadata is needed for
setting up your application. The ``mbdump.tar.bz2`` is the core MusicBrainz
archive which includes the tables for artist, release_group etc.
The ``mbdump-derived.tar.bz2`` archive contains annotations, user tags and search indexes.
These archives include all the data required for setting up an instance of
AcousticBrainz.

You can import the database dumps by downloading and importing the data in
a single command:

    docker-compose -f docker/docker-compose.dev.yml run musicbrainz_db

**Note**

One can also manually download the dumps and then import it:-

  1. For this, you have to download the dumps ``mbdump.tar.bz2`` and ``mbdump-derived.tar.bz2``
     from http://ftp.musicbrainz.org/pub/musicbrainz/data/fullexport/.

       **Warning**

       Make sure to get the latest dumps

  2. Then the environment variable ``DUMPS_DIR`` must be set to the path of the
     folders containing the dumps. This can be done by:

         export DUMPS_DIR="Path of the folder containing the dumps"

     You can check that the variable ``DUMPS_DIR`` has been succesfully assigned or not by:

         echo $DUMPS_DIR

      This must display the path of your folder containing the database dumps. The folder must contain at least the file    ``mbdump.tar.bz2``.

  3. Then import the database dumps by this command:

         docker-compose -f docker/docker-compose.dev.yml run -v $DUMPS_DIR:/home/musicbrainz/dumps \
         -v $PWD/data/mbdata:/var/lib/postgresql/data/pgdata musicbrainz_db

**Note**

  You can also use the smaller sample dumps available at http://ftp.musicbrainz.org/pub/musicbrainz/data/sample/
  to set up the MusicBrainz database. However, note that these dumps are .tar.xz
  dumps while AcousticBrainz currently only supports import of .tar.bz2 dumps.
  So, a decompression of the sample dumps and recompression into .tar.bz2 dumps
  will be needed. This can be done using the following command:

     xzcat mbdump-sample.tar.xz | bzip2 > mbdump.tar.bz2

**Warning**

Keep in mind that this process is very time consuming, so make sure that you don't delete the ``data/mbdata`` directory accidently. Also make sure that you have about 25GB of free space to keep the MusicBrainz data.

Initialization of AcousticBrainz database is also required:

    ./develop.sh run --rm  webserver python2 manage.py init_db

Then you can start all the services:

    ./develop.sh up --build

### Manually

Full installation instructions are available in [INSTALL.md](https://github.com/metabrainz/acousticbrainz-server/blob/master/INSTALL.md) file. After installing, continue the following steps.

## Configuration and development

### Building static files

We use Gulp as our JavaScript/CSS build system.

#### First-time installation
For development, the first time that you install acousticbrainz you must install
node packages in your local directory.

    ./develop.sh run --rm --user `id -u`:`id -g` -e HOME=/tmp webserver npm install

This has the effect of creating a `node_modules` directory in your local code checkout.
The `--user` and `-e` flags are needed on a Linux host to make this directory owned
by your local user.

To build stylesheets and javascript bundles, run gulp:

    ./develop.sh run --rm webserver ./node_modules/.bin/gulp

*You will need to rebuild static files after you modify JavaScript or CSS.*

### Login

To use the dataset tools you need to configure OAuth with MusicBrainz.
Log in to your MusicBrainz account (or create one if needed) and create
[a new application](https://musicbrainz.org/account/applications).

Choose a name (for example, "AcousticBrainz development"), set Type to "Web Application"
and set the Callback URL to http://localhost:8080/login/musicbrainz/post

Copy the OAuth Client ID and OAuth Client Secret values to
`custom_config.py` as `MUSICBRAINZ_CLIENT_ID` and `MUSICBRAINZ_CLIENT_SECRET`.

You should now be able to use the menu in the top corner of your AcousticBrainz server
to log in.

### Admin interface

Once you have logged in, you can make your user an admin, by running

    ./develop.sh run --rm webserver python2 manage.py add_admin <your user>

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

    ./develop.sh run --rm webserver python2 manage.py dump full_db

**JSON dump:**

    ./develop.sh run --rm webserver python2 manage.py dump json

*Creates two separate full JSON dumps with low-level and high-level data.*

**Incremental dumps:**

    ./develop.sh run --rm webserver python2 manage.py dump incremental

*Creates new incremental dump in three different formats: usual database dump,
low-level and high-level JSON.*

**Previous incremental dumps:**

    ./develop.sh run --rm webserver python2 manage.py dump incremental --id 42

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
