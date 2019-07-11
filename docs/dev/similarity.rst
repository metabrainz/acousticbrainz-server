Developing for Similarity
=========================

Setting up the environment
^^^^^^^^^^^^^^^^^^^^^^^^^^

Once your database and server are built, compute the static indices
for all indices at once using the cli command:

`./develop.sh run --rm webserver python2 manage.py similarity add-indices`

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