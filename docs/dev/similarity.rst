Developing for Similarity
=========================

Setting up the environment
^^^^^^^^^^^^^^^^^^^^^^^^^^

**NOTE:** If there is no submitted data in the lowlevel table, similarity
cannot be initialized.

Once your database and server are built, there are a few steps required to
initialize the similarity engine. These steps can be run completed altogether
using the following cli command:

``./develop.sh run --rm webserver python2 manage.py similarity init``

As seen below, they may also be applied separately for more control.

Compute all required statistics over the lowlevel table:

``./develop.sh run --rm webserver python2 manage.py similarity compute-stats``

Compute all metrics for all recordings in the lowlevel table:

``./develop.sh run --rm webserver python2 manage.py similarity add-metrics``

This command can be run again at any time to compute the metrics for a number of
newly submitted recordings. It will not recompute metrics for recordings that
already exist in the similarity.similarity table.

Finally, compute all static indices at once:

``./develop.sh run --rm webserver python2 manage.py similarity add-indices``

It is possible to alter the index parameters using additional arguments.

Index parameters
^^^^^^^^^^^^^^^^

Indices take a number of parameters when being built. We are currently evaluating
them ourselves and have developed a set of base indices, but you may want to
experiment with different parameters. 

Queries to an index become more precise when the index is built with a higher 
number of trees, but they will also take longer to build. Indices can also vary
in the method used to calculate distance between recordings. Limitations of
parameter selection can be found in the `Annoy documentation`_ and our codebase_

.. _Annoy documentation: https://github.com/spotify/annoy
.. _codebase: https://github.com/metabrainz/acousticbrainz-server/master/tree/similarity/index_model.py