# acousticbrainz-server

The server components for the new AcousticBrainz project.

Please report issues here: http://tickets.musicbrainz.org/browse/AB


## Installation

**Requirements:**

* [Python](https://www.python.org/) 2.7.x
* [PostgreSQL](http://www.postgresql.org/) >=9.2 (needs the JSON data type)
* [pxz](http://manpages.ubuntu.com/manpages/trusty/man1/pxz.1.html)

For example in the latest Ubuntu, this command will install your pre-requisites:

    $ sudo apt-get install build-essential git-core python-dev python-virtualenv
                postgresql-9.3 postgresql-client-9.3 postgresql-server-dev-9.3 pxz

It is recommended, although optional, to first set up a virtual environment and
activate it:

    $ virtualenv venv
    $ . ./venv/bin/activate

Then use `pip` to install the required Python dependencies:

    $ pip install -r requirements.txt

Then copy over `config.py.sample` to `config.py` in the `acousticbrainz/` folder
and edit its content to fit your environment.

After you tweak configuration file, database needs to be created:

    $ cd admin
    $ ./init_db.sh

After all this, you can run the site/server using `./server.py`.
Use `./server.py -h` to get a list of command-line switches
to further suit your local environment (e.g., port, listening address, ...).


## Exporting data

There are several ways to export data out of AcousticBrainz server. You can
create full database dump or export only low level and high level data in JSON
format. Both ways support incremental dumping.

### Examples

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
