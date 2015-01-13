acousticbrainz-server
=====================

The server components for the new AcousticBrainz project.

Please report issues here: http://tickets.musicbrainz.org/browse/AB

Requirements
------------

* [Python](https://www.python.org/) 2.7.x
* Python modules listed in `requirements.txt` (can be installed with `pip`, see below)
* [PostgreSQL](http://www.postgresql.org/) >=9.2 (needs the JSON data type)

If you have the latest Ubuntu install, this command will install your pre-requisites:

   sudo apt-get install build-essential git-core python-dev python-virtualenv postgresql-9.3 
                postgresql-client-9.3 postgresql-server-dev-9.3 pxz


Install
-------

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
