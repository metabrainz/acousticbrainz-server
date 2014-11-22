acousticbrainz-server
=====================

The server components for the new AcousticBrainz project.

Requirements
------------

* [Python](https://www.python.org/) 2.7.x
* Python modules listed in `requirements.txt` (can be installed with `pip`, see below)
* [PostgreSQL](http://www.postgresql.org/) >=9.2 (needs the JSON data type)

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

After all this, you can run the site/server using `./acousticbrainz/server.py`.
Use `./acousticbrainz/server.py -h` to get a list of command-line switches
to further suit your local environment (e.g., port, listening address, ...).
