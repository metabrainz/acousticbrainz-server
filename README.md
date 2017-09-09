acousticbrainz-server
=====================

The server components for the new AcousticBrainz project.

Please report issues here: http://tickets.musicbrainz.org/browse/AB


## Installation and Running

### Vagrant VM

You can use [docker](https://www.docker.com/) and [docker-compose](https://docs.docker.com/compose/) to run the AcousticBrainz server. Make sure docker and docker-compose are installed.
Then copy two config files:

1. `custom_config.py.example` to `custom_config.py` *(you don't need to modify this file)*
2. `profile.conf.in.sample` to `profile.conf.in` in the `./hl_extractor/` directory
*(in this file you need to set `models_essentia_git_sha` value)*

Then, in order to download all the software and build and start the containers needed to run AcousticBrainz, use the following command:

`docker-compose -f docker/docker-compose.dev.yml up --build`

The first time you do that, you will then need to initialize the AcousticBrainz database:

`docker-compose -f docker/docker-compose.dev.yml run webserver python2 manage.py init_db --skip-create-db`

In order to load a psql session, use the following command:

`docker-compose -f docker/docker-compose.dev.yml run webserver psql -U acousticbrainz -h db`

### Manually

Full installation instructions are available in [INSTALL.md](https://github.com/metabrainz/acousticbrainz-server/blob/master/INSTALL.md) file. After installing, continue the following steps.

## Configuration and development

### Building static files

We use Gulp as our JavaScript/CSS build system.
node.js dependencies.
After you started development versions of containers with `docker-compose`, connect to the main container:

`docker-compose -f docker/docker-compose.dev.yml run webserver run /bin/bash`

Calling `gulp` on its own will build everything necessary
to access the server in a web browser:

    root@<container_id>:/code# npm install
    root@<container_id>:/code# ./node_modules/.bin/gulp

*Keep in mind that you'll need to rebuild static files after you modify
JavaScript or CSS.*

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

    docker-compose -f docker-compose.dev.yml run webserver python2 manage.py add_admin <your user>

You should now be able to access the admin section at http://localhost:8080/admin


## Working with data

### Importing

AcousticBrainz provides data dumps that you can import into your own server.
Latest database dump is available at http://acousticbrainz.org/download. You
need to download full database dump from this page and use it during database
initialization:

    $ docker-compose -f docker/docker-compose.dev.yml run webserver python2 manage.py init_db path_to_the_archive

you can also easily remove existing database before initialization using
`--force` option:

    $ docker-compose -f docker/docker-compose.dev.yml run webserver python2 manage.py init_db --force path_to_the_archive

or import archive after database is created:

    $ docker-compose -f docker/docker-compose.dev.yml run webserver python2 manage.py import_data path_to_the_archive

*You can also import dumps that you created yourself. This process is described
below (see `dump full_db` command).*

### Exporting

There are several ways to export data out of AcousticBrainz server. You can
create full database dump or export only low-level and high-level data in JSON
format. Both ways support incremental dumping.

#### Examples

**Full database dump:**

    $ docker-compose -f docker/docker-compose.dev.yml run webserver python2 manage.py dump full_db

**JSON dump:**

    $ docker-compose -f docker/docker-compose.dev.yml run webserver python2 manage.py dump json

*Creates two separate full JSON dumps with low-level and high-level data.*

**Incremental dumps:**

    $ docker-compose -f docker/docker-compose.dev.yml run webserver python2 manage.py dump incremental

*Creates new incremental dump in three different formats: usual database dump,
low-level and high-level JSON.*

**Previous incremental dumps:**

    $ docker-compose -f docker/docker-compose.dev.yml run webserver python2 manage.py dump incremental --id 42

*Same as another one, but recreates previously created incremental dump.*
