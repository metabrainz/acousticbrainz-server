# AcousticBrainz contribution guidelines

Our contributing guidelines are an extension of the MetaBrainz guidelines, which can be found
at https://github.com/metabrainz/guidelines.

When working on AcousticBrainz please keep these guidelines in mind. If you do not follow these
guidelines we may direct you to them before accepting your contribution.

## Community/Discussion

If you want to discuss something, join us in the [#metabrainz](ircs://irc.libera.chat:6697/metabrainz)
IRC channel on irc.libera.chat. More info is available at https://wiki.musicbrainz.org/Communication.
Alternatively, you can post something in the [AcousticBrainz category](https://community.metabrainz.org/c/acousticbrainz)
of the MetaBrainz forums.

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

## Bug tracking and issues

Tickets can be created or resolved via [the bug tracker](https://tickets.metabrainz.org/projects/AB/issues/).

### Ticketing basics

 * You can assign yourself to a ticket if you wish to start working on it. 
 * Set the ticket status to "in progress" when you begin.
 * Follow our [git workflow](#git-workflow) to begin making changes and create a pull request.
 * The project maintainer will change a ticket status to "resolved" when the related pull request is merged.

## Git workflow

We use a git workflow similar to that proposed by github: https://guides.github.com/activities/forking/

Some key steps to follow:

1. Create a new branch in your fork and _give it a meaningful name_.
    * For example, if you are fixing the issue AB-101, the branch could be named ab-101.
2. Write [good commit messages](http://robots.thoughtbot.com/5-useful-tips-for-a-better-commit-message) when you commit your changes.
3. Once you have made your changes, create [a new pull request](https://github.com/metabrainz/acousticbrainz-server/compare).
    * When solving more than one issue, split them into multiple pull requests. This makes it easier to review and merge patches.
4. If you get feedback and need to make changes to a pull request, [use git rebase](https://help.github.com/en/articles/using-git-rebase-on-the-command-line) instead of adding more commits.

