Web API
=======

The AcousticBrainz server provides a Web API for getting and submitting data.

**Base URL**: ``https://acousticbrainz.org``

Endpoint Reference
------------------

Core data
^^^^^^^^^

.. autoflask:: webserver:create_app_sphinx()
   :blueprints: api_v1_core
   :include-empty-docstring:
   :undoc-static:

Datasets
^^^^^^^^

.. autoflask:: webserver:create_app_sphinx()
   :blueprints: api_v1_datasets
   :include-empty-docstring:
   :undoc-static:

Similarity
^^^^^^^^^^

.. autoflask:: webserver:create_app_sphinx()
   :blueprints: api_v1_similarity
   :include-empty-docstring:
   :undoc-static:

Rate limiting
^^^^^^^^^^^^^

The AcousticBrainz API is rate limited via the use of rate limiting headers that
are sent as part of the HTTP response headers. Each call will include the
following headers:

- **X-RateLimit-Limit**: Number of requests allowed in given time window

- **X-RateLimit-Remaining**: Number of requests remaining in current time
  window

- **X-RateLimit-Reset-In**: Number of seconds when current time window expires
  (*recommended*: this header is resilient against clients with incorrect
  clocks)

- **X-RateLimit-Reset**: UNIX epoch number of seconds (without timezone) when
  current time window expires [#]_

We typically set the limit to 10 queries every 10 seconds per IP address,
but these values may change. Make sure you check the response headers
if you want to know the specific values.

Rate limiting is automatic and the client must use these headers to determine
the rate to make API calls. If the client exceeds the number of requests
allowed, the server will respond with error code ``429: Too Many Requests``.
Requests that provide the *Authorization* header with a valid user token may
receive higher rate limits than those without valid user tokens.

.. [#] Provided for compatibility with other APIs, but we still recommend using
   ``X-RateLimit-Reset-In`` wherever possible

Constants
^^^^^^^^^

Constants that are relevant to using the API:

.. autodata:: webserver.views.api.v1.core.MAX_ITEMS_PER_BULK_REQUEST
.. autodata:: webserver.views.api.v1.core.LOWLEVEL_INDIVIDUAL_FEATURES
.. autodata:: similarity.metrics.BASE_METRIC_NAMES
