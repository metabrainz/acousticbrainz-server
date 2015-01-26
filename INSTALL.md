Installing AcousticBrainz Server
================================

Prerequisites
-------------

* [Python](https://www.python.org/) 2.7.x
* [PostgreSQL](http://www.postgresql.org/) >=9.2 (needs the JSON data type)
* [pxz](http://manpages.ubuntu.com/manpages/trusty/man1/pxz.1.html)
* `streaming_extractor_music_svm` which is a part of the [Essentia library](http://essentia.upf.edu/)
    \+ *svm_models* which are available at http://essentia.upf.edu/documentation/svm_models/

For example in the latest Ubuntu, this command will install your pre-requisites:

    $ sudo apt-get install build-essential git-core python-dev python-virtualenv \
        postgresql-9.3 postgresql-client-9.3 postgresql-server-dev-9.3 pxz

Virtual environment
-------------------

It is recommended, although optional, to first set up a virtual environment and
activate it:

    $ virtualenv venv
    $ . ./venv/bin/activate

Python dependencies
-------------------

Then use `pip` to install the required Python dependencies:

    $ pip install -r requirements.txt

Configuration
-------------

Copy over `config.py.sample` to `config.py` in the `acousticbrainz/` folder
and edit its content to fit your environment.

Creating the database
---------------------

After you tweak configuration file, database needs to be created:

    $ cd admin
    $ ./init_db.sh

Starting the server
-------------------

After all this, you can run the site/server using `./server.py`.
Use `./server.py -h` to get a list of command-line switches
to further suit your local environment (e.g., port, listening address, ...).
