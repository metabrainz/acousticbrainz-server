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

or high level data extractor:

    # cd /high-level
    # python hl_calc.py


### The Usual Way

**Requirements:**

* [Python](https://www.python.org/) 2.7.x
* Python modules listed in `requirements.txt` (can be installed with `pip`, see below)
* [PostgreSQL](http://www.postgresql.org/) >=9.2 (needs the JSON data type)
* [pxz](http://manpages.ubuntu.com/manpages/trusty/man1/pxz.1.html)
* `streaming_extractor_music_svm` which is a part of the [Essentia library](http://essentia.upf.edu/)

If you have the latest Ubuntu install, this command will install your pre-requisites:

   sudo apt-get install build-essential git-core python-dev python-virtualenv postgresql-9.3 
                postgresql-client-9.3 postgresql-server-dev-9.3 pxz

It is recommended, although optional, to first set up a virtual environment and
activate it:

    virtualenv venv
    . ./venv/bin/activate

Then use `pip` to install the required Python dependencies:

    pip install -r requirements.txt

Then copy over `config.py.sample` to `config.py` in the `acousticbrainz/` folder
and edit its content to fit your environment.

(Something about setting up PostgreSQL could go go here...)

After all this, you can run the site/server using `./server.py`.
Use `./server.py -h` to get a list of command-line switches
to further suit your local environment (e.g., port, listening address, ...).


## Working with data

### Exporting

There are several ways to export data out of AcousticBrainz server. You can
create full database dump or export only low level and high level data in JSON
format. Both ways support incremental dumping.

#### Examples

**Full database dump:**

    $ python manage.py dump full_db

**JSON dump:**

    $ python manage.py dump json

*Creates two separate full JSON dumps with low level and high level data.*

**Incremental dumps:**

    $ python manage.py dump incremental

*Creates new incremental dump in three different formats: usual database dump,
low level and high level JSON.*

**Previous incremental dumps:**

    $ python manage.py dump incremental -i=42

*Same as the previous but recreates previous incremental dump.*
