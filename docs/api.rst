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

Constants
^^^^^^^^^

Constants that are relevant to using the API:

.. autodata:: webserver.views.api.v1.core.MAX_ITEMS_PER_BULK_REQUEST
