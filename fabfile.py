from __future__ import with_statement
from fabric.api import local
from fabric.colors import green, yellow, red
from db import cache
import config

import os


def vpsql():
    """Connect to the acousticbrainz database running on vagrant."""
    local("psql -h localhost -p 15432 -U postgres acousticbrainz")


def vssh():
    """SSH to a running vagrant host."""
    curdir = os.path.dirname(os.path.abspath(__file__))
    configfile = os.path.join(curdir, '.vagrant', 'ssh_config')
    if not os.path.exists(configfile):
        local('vagrant ssh-config acousticbrainz > .vagrant/ssh_config')

    local("ssh -F .vagrant/ssh_config -o 'ControlMaster auto' -o 'ControlPath ~/.ssh/ab_vagrant_control' -o 'ControlPersist 4h' acousticbrainz")


def git_pull():
    local("git pull origin")
    print(green("Updated local code.", bold=True))


def install_requirements():
    local("pip install -r requirements.txt")
    print(green("Installed requirements.", bold=True))


def build_static():
    local("./node_modules/.bin/gulp")


def clear_memcached():
    try:
        cache.init(config.MEMCACHED_SERVERS)
        cache.flush_all()
        print(green("Flushed everything from memcached.", bold=True))
    except AttributeError as e:
        print(red("Failed to clear memcached! Check your config file.\nError: %s" % e))


def deploy():
    git_pull()
    install_requirements()
    build_static()
    clear_memcached()


def test(coverage=True):
    """Run all tests.

    It will also create code coverage report, unless specified otherwise. It
    will be located in cover/index.html file.
    """
    if coverage:
        local("nosetests --exe --with-coverage --cover-erase --cover-html "
              "--cover-package=db,webserver,hl_extractor,dataset_eval")
        print(yellow("Coverage report can be found in cover/index.html file.", bold=True))
    else:
        local("nosetests --exe")
