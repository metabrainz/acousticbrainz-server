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

Full installation instructions are available in [INSTALL.md](https://github.com/metabrainz/acousticbrainz-server/blob/master/INSTALL.md) file.
