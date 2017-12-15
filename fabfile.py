from __future__ import with_statement

import os

from fabric.api import local
from fabric.colors import green


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


def deploy():
    git_pull()
    install_requirements()
    build_static()
    local("python manage.py clear_cache")
