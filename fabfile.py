from fabric.api import local
from fabric.colors import green


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
