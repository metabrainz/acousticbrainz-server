# AcousticBrainz contribution guidelines

## Community/Discussion
If you want to discuss something, go to the [#metabrainz](irc://irc.freenode.net/metabrainz)
IRC channel on irc.freenode.net. More info is available at https://wiki.musicbrainz.org/Communication.
Alternatively, you can post something in the [AcousticBrainz category](https://community.metabrainz.org/c/acousticbrainz)
of the MetaBrainz forums.

Create ticket in [the bug tracker](http://tickets.musicbrainz.org/browse/AB). Try to provide a good description.


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

### Documentation

Include docstrings in functions. This should say *what* the function does, its *inputs*,
and *outputs* or possible *failure states* (exceptions).

In the `webserver` module, docstrings are turned into [API Documentation](http://acousticbrainz.readthedocs.io/)
and so should be formatted to include query format and an example of the response:

    """Get low-level data for many recordings at once.

    **Example response**:

    .. sourcecode:: json

       {"mbid1": {"some": "json"}}

    :query recording_ids: *Required.* A list of recording MBIDs to retrieve

      Takes the form `mbid[:offset];mbid[:offset]`. Offsets are optional, and should
      be >= 0
    :resheader Content-Type: *application/json*
    """

The format of a non-api docstring should be
```python
def frob(foo, bar=None):
    """Frob a foo, with an optional bar operation
       Args:
           foo: the foo to be frobbed
           bar: if set, a callback to a bar operation to be applied after
                the foo is frobbed
       Returns:
           The new foo, after frobbing and baring
```

### Style

Note: While this is section describes an ideal style, we know that parts of the AcousticBrainz
codebase do not follow these guidelines exactly. We are pragmatic in our application of the
guidelines and try our best to follow them, but there will be deviations. When in doubt, follow
the guidelines rather than copying existing code.

We mostly follow PEP-8 style guidelines. We have a pylintrc file which can be used to check code
for style compliance. Run

    pylint --rcfile=pylintrc

to check code for compliance.


*SQL statements*
For SQL statements we use sqlalchemy.text to write prepared statements. SQL keywords
should be in upper-case and right aligned. For example:

    query = text("""
        SELECT id
             , name
          FROM table
         WHERE id = :myid""")
    result = connection.execute(query, {"id": 1})

It is preferred to assign the query to a separate variable and not include it inside the
`execute` call.

### Tests

You should write tests for all new methods that you write. If you update a method, make sure that
tests for that method still pass, and write/remove tests as necessary for the change in functionality.

Tests for a module (`package/module.py`) go in a `test` subdirectory - `package/test/test_module.py`

Database tests (for modules in `db`) can use the database. Inherit from `db.testing.DatabaseTestCase`
to automatically reset the database at the end of each testcase.

Try and isolate tests as much as possible. If you have a utility function which transforms or validates
and input, you can test this in isolation.

Webserver tests don't need to write data to the database. Instead, you can use a mock to verify
that the call to the database was made:

```python
@mock.patch("db.data.load_high_level")
def test_hl_numerical_offset(self, hl):
    hl.return_value = {}
    resp = self.client.get("/api/v1/%s/high-level?n=3" % self.uuid)
    self.assertEqual(200, resp.status_code)
    hl.assert_called_with(self.uuid, 3)
```

TODO: Integration tests to make sure that data is correctly passed from webserver to database?

## Git workflow

We use a git workflow similar to that proposed by github: https://guides.github.com/activities/forking/

Ensure that you [write good commit messages](http://robots.thoughtbot.com/5-useful-tips-for-a-better-commit-message).

Once you have made your changes, create [a new pull request](https://github.com/metabrainz/acousticbrainz-server/compare).

