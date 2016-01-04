Installing AcousticBrainz Server
================================

AcousticBrainz Server consists of two parts: web server that powers
acousticbrainz.org website and high-level data extractor that processes
incoming low-level information about recordings.

Prerequisites
-------------

* [Python](https://www.python.org/) 2.7.x
* [PostgreSQL](http://www.postgresql.org/) >=9.2 (needs the JSON data type)
* [Node.js](http://memcached.org/)
* [memcached](http://memcached.org/)
* [pxz](http://manpages.ubuntu.com/manpages/trusty/man1/pxz.1.html) for
exporting and importing the data

For example in the latest Ubuntu, this command will install pre-requisites:

    $ sudo apt-get install python-dev python-virtualenv memcached pxz \
        postgresql-9.3 postgresql-client-9.3 postgresql-server-dev-9.3


Web Server
----------

It is recommended, although optional, to first set up a virtual environment and
activate it:

    $ virtualenv venv
    $ . ./venv/bin/activate

### Python dependencies

Then use `pip` to install the required Python dependencies:

    $ pip install -r requirements.txt

### Configuration

Copy over `config.py.sample` to `config.py` and edit its content to fit your
environment.

#### Configuring MusicBrainz OAuth

You need to create [a new application](https://musicbrainz.org/account/applications)
and set two variables: `MUSICBRAINZ_CLIENT_ID` and `MUSICBRAINZ_CLIENT_SECRET`.
On MusicBrainz set Callback URL to `http://<host>/login/musicbrainz/post`.

### Creating the database

After you tweak configuration file, database needs to be created:

    $ python manage.py init_db

*Optional:* You might want to create a database that will be used by tests:

    $ python manage.py init_test_db
    
### Node.js dependencies

Node.js dependencies are managed using `npm`. To install these dependencies run
the following command:

    $ npm install
    
### Building static files

We use Gulp as our JavaScript/CSS build system. It should be installed with
node.js dependencies. Calling `gulp` on its own will build everything necessary
to access the server in a web browser:

    ./node_modules/.bin/gulp
    
*Keep in mind that you'll need to rebuild static files after you modify
JavaScript or CSS.*

### Starting the server

After all this, you can run the site/server using `./server.py`.
Use `./server.py -h` to get a list of command-line switches
to further suit your local environment (e.g., port, listening address, ...).


High-level Data Extractor
-------------------------

To run high-level data extractor you'll need two things:

1. `streaming_extractor_music_svm` which is a part of the [Essentia library](http://essentia.upf.edu/)
2. *svm_models* which are available at http://essentia.upf.edu/documentation/svm_models/

### Building `streaming_extractor_music_svm`

To build the extractor binary you'll need to get [Gaia](https://github.com/MTG/gaia)
and [Essentia](https://github.com/MTG/essentia) libraries. Generally, you should
use installation instructions provided with them, but to save you some time
here's a set of steps that you can follow:

1. `git clone` Gaia and install it without using additional options during the
configuration step

2. `git clone` Essentia and configure it like this:

        $ ./waf configure --mode=release --with-gaia --with-example=streaming_extractor_music_svm

3. Build Essentia and copy `streaming_extractor_music_svm` binary from *build/src/examples/*
directory into *./hl_extractor/* in the project root.

### Installing SVM models

Download archive from http://essentia.upf.edu/documentation/svm_models/, extract
it, and move contents of *svm_models* directory into */hl_extractor/svm_models*
in the project root.

### Starting the extractor

    $ cd high-level
    $ python hl_calc.py
