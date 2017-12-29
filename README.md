acousticbrainz-server
=====================

The server components for the new AcousticBrainz project.

Please report issues here: http://tickets.musicbrainz.org/browse/AB


## Installation

### Vagrant VM

The easiest way to start is to setup ready-to-use [Vagrant](https://www.vagrantup.com/)
VM. To do that [download](https://www.vagrantup.com/downloads.html) and install
Vagrant for your OS. Then copy two config files:

1. `custom_config.py.example` to `custom_config.py` *(you don't need to modify this file)*
2. `profile.conf.in.sample` to `profile.conf.in` in the `./hl_extractor/` directory
*(in this file you need to set `models_essentia_git_sha` value)*

After that you can spin up the VM and start working with it:

    $ vagrant up
    $ vagrant ssh

There are some environment variables that you can set to affect the
provisioning of the virtual machine.

 * `AB_NCPUS`: Number of CPUs to put in the VM (default 1, 2 makes
               compilation faster)
 * `AB_MEM`:   Amount of memory (default 1024mb)
 * `AB_MIRROR`: ubuntu mirror (default archive.ubuntu.com)
 * `AB_NOHL`: If set, don't compile the highlevel calculation tools
              (not needed for regular server development)


There are some shortcuts defined using fabric to perform commonly used
commands:

 * `fab vpsql`: Load a psql session. Requires a local psql client
 * `fab vssh`: Connect to the VM more efficiently, saving the settings
               so that you don't need to run vagrant each time you ssh.

### Manually

Full installation instructions are available in [INSTALL.md](https://github.com/metabrainz/acousticbrainz-server/blob/master/INSTALL.md) file. After installing, continue the following steps.

## Configuration and development

### Building static files

We use Gulp as our JavaScript/CSS build system.
node.js dependencies. Calling `gulp` on its own will build everything necessary
to access the server in a web browser:

    ./node_modules/.bin/gulp

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

    python manage.py add_admin <your user>

You should now be able to access the admin section at http://localhost:8080/admin


## Running

Before starting the server you will need to build static files:

    $ cd acousticbrainz-server
    $ fab build_static

*Keep in mind that you'll need to rebuild static files after you modify
JavaScript or CSS.*

You can start the web server (will be available at http://localhost:8080/):

    $ cd acousticbrainz-server
    $ python manage.py runserver

the high-level data extractor:

    $ cd acousticbrainz-server/hl_extractor
    $ python hl_calc.py

the dataset evaluator:

    $ cd acousticbrainz-server/dataset_eval
    $ python evaluate.py


## Working with data

### Importing

AcousticBrainz provides data dumps that you can import into your own server.
Latest database dump is available at http://acousticbrainz.org/download. You
need to download full database dump from this page and use it during database
initialization:

    $ python manage.py init_db path_to_the_archive

you can also easily remove existing database before initialization using
`--force` option:

    $ python manage.py init_db --force path_to_the_archive

or import archive after database is created:

    $ python manage.py import_data path_to_the_archive

*You can also import dumps that you created yourself. This process is described
below (see `dump full_db` command).*

### Exporting

There are several ways to export data out of AcousticBrainz server. You can
create full database dump or export only low-level and high-level data in JSON
format. Both ways support incremental dumping.

#### Examples

**Full database dump:**

    $ python manage.py dump full_db

**JSON dump:**

    $ python manage.py dump json

*Creates two separate full JSON dumps with low-level and high-level data.*

**Incremental dumps:**

    $ python manage.py dump incremental

*Creates new incremental dump in three different formats: usual database dump,
low-level and high-level JSON.*

**Previous incremental dumps:**

    $ python manage.py dump incremental --id 42

*Same as another one, but recreates previously created incremental dump.*
