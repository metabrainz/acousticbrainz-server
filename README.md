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

    ./develop.sh build

The first time you install acousticbrainz, you will need to initialize the AcousticBrainz database:

    ./develop.sh run --rm  webserver python2 manage.py init_db

In order to load a psql session, use the following command:

    ./develop.sh run --rm db psql -U acousticbrainz -h db

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

    ./develop.sh run --rm --user `id -u`:`id -g` webserver ./node_modules/.bin/gulp

*You will need to rebuild static files after you modify JavaScript or CSS.*

## Running

You can start the web server (will be available at http://localhost:8080/):

    ./develop.sh run --rm webserver runserver

the high-level data extractor:

    ./develop.sh run --rm webserver hl_calc

the dataset evaluator:

    ./develop.sh run --rm webserver dataset_eval


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

    ./develop.sh run --rm webserver flask add_admin <your user>

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
initialization. We provide a Flask CLI for this purpose. In order to use it,
first log in to the vagrant server and set the environment variable `FLASK_APP`
to `manage.py`:

    $ cd acousticbrainz-server
    $ export FLASK_APP=manage.py

You can then import the downloaded database dump during database initialization:

    ./develop.sh run --rm webserver flask init_db path_to_the_archive

You can also easily remove existing database before initialization using
`--force` option:

    ./develop.sh run --rm webserver flask init_db --force path_to_the_archive

or import archive after database is created:

    ./develop.sh run --rm webserver flask import_data path_to_the_archive

*You can also import dumps that you created yourself. This process is described
below (see `dump full_db` command).*

### Exporting

There are several ways to export data out of AcousticBrainz server. You can
create full database dump or export only low-level and high-level data in JSON
format. Both ways support incremental dumping. As usual, log in to the vagrant server and
set the `FLASK_APP` environment variable to `manage.py` before using the examples
that follow.

    $ cd acousticbrainz-server
    $ export FLASK_APP=manage.py

#### Examples

**Full database dump:**

    ./develop.sh run --rm webserver flask dump full_db

**JSON dump:**

    ./develop.sh run --rm webserver flask dump json

*Creates two separate full JSON dumps with low-level and high-level data.*

**Incremental dumps:**

    ./develop.sh run --rm webserver flask dump incremental

*Creates new incremental dump in three different formats: usual database dump,
low-level and high-level JSON.*

**Previous incremental dumps:**

    ./develop.sh run --rm webserver flask dump incremental --id 42

*Same as another one, but recreates previously created incremental dump.*

## Test your changes with unit tests

Unit tests are an important part of AcousticBrainz. It helps make it easier for
developers to test changes and help prevent easily avoidable mistakes later on.
Before commiting new code or making a pull request, run the unit tests on your code.

    ./test.sh

This builds and runs the containers needed for the tests.
