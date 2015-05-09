from __future__ import with_statement
from fabric.api import local
from fabric.colors import green
from acousticbrainz import create_app, cache


def git_pull():
    local("git pull origin")
    print(green("Updated local code.", bold=True))


def install_requirements():
    local("pip install -r requirements.txt")
    print(green("Installed requirements.", bold=True))


def compile_styling():
    """Compile styles.less into styles.css.
    This command requires Less (CSS pre-processor). More information about it can be
    found at http://lesscss.org/.
    """
    style_path = "static/css/"
    local("lessc --clean-css %sstyles.less > %sstyles.css" % (style_path, style_path))
    print(green("Style sheets have been compiled successfully.", bold=True))


def clear_memcached():
    with create_app().app_context():
        cache.flush_all()
    print(green("Flushed everything from memcached.", bold=True))


def deploy():
    git_pull()
    install_requirements()
    compile_styling()
    clear_memcached()
