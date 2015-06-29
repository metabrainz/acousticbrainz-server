from __future__ import with_statement
from fabric.api import local
from fabric.colors import green, yellow
from acousticbrainz import create_app, cache


def git_pull():
    local("git pull origin")
    print(green("Updated local code.", bold=True))


def install_requirements():
    local("pip install -r requirements.txt")
    print(green("Installed requirements.", bold=True))


def compile_styling():
    """Compile main.less into main.css.
    This command requires Less (CSS pre-processor). More information about it can be
    found at http://lesscss.org/.
    """
    style_path = "static/css/"
    local("lessc --clean-css %smain.less > %smain.css" % (style_path, style_path))
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


def test(coverage=True):
    """Run all tests.

    It will also create code coverage report, unless specified otherwise. It
    will be located in cover/index.html file.
    """
    if coverage:
        local("nosetests --exe --with-coverage --cover-package=acousticbrainz --cover-erase --cover-html")
        print(yellow("Coverage report can be found in cover/index.html file.", bold=True))
    else:
        local("nosetests --exe")
