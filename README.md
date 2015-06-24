acousticbrainz-server
=====================

The server components for the new AcousticBrainz project.

Please report issues here: http://tickets.musicbrainz.org/browse/AB


## Installation

### Vagrant VM

The easiest way to start is to setup ready-to-use [Vagrant](https://www.vagrantup.com/)
VM. To do that [download](https://www.vagrantup.com/downloads.html) and install
Vagrant for your OS. Then copy two config files:

1. `config.py.sample` to `config.py` in the `acousticbrainz/` directory *(you
don't need to modify this file)*
2. `profile.conf.in.sample` to `profile.conf.in` in the `high-level/` directory
*(in this file you need to set `models_essentia_git_sha` value)*

After that you can spin up the VM and start working with it:

    $ vagrant up
    $ vagrant ssh
    $ sudo su && cd /vagrant

You can start the web server (will be available at http://127.0.0.1:8080/):

    # python server.py

or high-level data extractor:

    # cd /high-level
    # python hl_calc.py

### The Usual Way

Full installation instructions are available in [INSTALL.md](https://github.com/metabrainz/acousticbrainz-server/blob/master/INSTALL.md) file.


## Working with data

### Importing

AcousticBrainz provides data dumps that you can import into your own server.
Latest database dump is available at http://acousticbrainz.org/download. You
need to download full database dump from this page and use it during database
initialization:

    $ python manage.py init_db -a <path_to_the_archive>

you can also easily remove existing database before initialization using
`--force` option:

    $ python manage.py init_db -a <path_to_the_archive> --force

or import archive after database is created:

    $ python manage.py import_data -a <path_to_the_archive>

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

    $ python manage.py dump incremental -i=42

*Same as another one, but recreates previously created incremental dump.*
