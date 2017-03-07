# AcousticBrainz contributing guidelines

Our contributing guidelines are an extension of the MetaBrainz guidelines, which can be found
at https://github.com/metabrainz/guidelines.

When working on AcousticBrainz please keep these guidelines in mind. If you do not follow these
guidelines we may direct you to them before accepting your contribution.

## Community/Discussion

If you want to discuss something, join us in the [#metabrainz](irc://irc.freenode.net/metabrainz)
IRC channel on irc.freenode.net. More info is available at https://wiki.musicbrainz.org/Communication.
Alternatively, you can post something in the [AcousticBrainz category](https://community.metabrainz.org/c/acousticbrainz)
of the MetaBrainz forums.

Create tickets in [the bug tracker](http://tickets.musicbrainz.org/browse/AB).


## Development workflow

Keep these points in mind when making changes to the AcousticBrainz codebase. If anything is unclear or
contradictory, raise an issue in the bug tracker or talk to us on IRC.

### Code layout and separation

The AcousticBrainz server has two main modules of code.

`db` contains methods which read and write data to and from the database

`webserver` contains the Flask application which serves the AcousticBrainz website and API

TODO: API/website separation, Javascript

####  Data flow

When at all possible, we should have very little logic code in the webservice module.

A view should read data from the client, validate the input, call a processing method and
then return the status.

You can assume that inputs given to a processing method (e.g. a database method) are valid.

TODO: Result format of API: Lists, Objects, error/status fields.

### Python style

Please read the [Python guidelines](https://github.com/metabrainz/guidelines/blob/master/Python.md)
on the MetaBrainz site for information about

 * Coding style
 * Documentation
 * Tests

## Git workflow

We use a git workflow similar to that proposed by github: https://guides.github.com/activities/forking/

Ensure that you [write good commit messages](http://robots.thoughtbot.com/5-useful-tips-for-a-better-commit-message).

Once you have made your changes, create [a new pull request](https://github.com/metabrainz/acousticbrainz-server/compare).

