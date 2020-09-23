Developing for Similarity
=========================

Setting up the environment
--------------------------

**NOTE:** If there is no submitted data in the lowlevel table, similarity
cannot be initialized.

Once your database and server are built, there are a few steps required to
initialize the similarity engine. These steps can be run completed altogether
using the following cli command:

``./develop.sh manage similarity init``

Environment subcommands
^^^^^^^^^^^^^^^^^^^^^^^

The ``init`` similarity command runs each of these sub-commands in order. They can be run
individually to perform a specific step.

Compute required statistics over the lowlevel table:

``./develop.sh manage similarity compute-stats``

Extract data values for all recordings in the lowlevel table:

``./develop.sh manage similarity add-metrics``

This command can be run again at any time to extract values for recordings that have been added
since the last time that this command was run.

Finally, build the annoy indices:

``./develop.sh manage similarity add-indices``

This command will rebuild an index from scratch, reading from the metrics that were extracted from
the ``add-metrics`` command. This should be run each time after ``add-metrics`` to rebuild the
similarity indexes.

It is possible to alter the index parameters using additional arguments.


Similarity implementation details
---------------------------------

Metrics list
^^^^^^^^^^^^
We store a list of metrics in the *similarity.similarity_metrics* database table.
A definition of these each of these metrics is stored in the ``similarity.metrics`` python module.
These definitions describe which database field to load the metric from, and any preprocessing
that has to be performed before adding it to the index.

Statistics
^^^^^^^^^^
Some features (Weighted MFCCs, Weighted GFCCs) require a mean and standard deviation value to
perform normalisation.
We can't compute the mean of all items in the database as this would take too long, so
instead we take a random sample (by default ``similarity.manage.NORMALIZATION_SAMPLE_SIZE``, 10000) of items
and compute the mean and SD on those items. In our experiments this gave a good tradeoff of accuracy vs
computation speed.

Speed of database access and indexing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Reading all items directly from the database (*lowlevel_json* table) is too slow to do every time
the annoy index needs to be updated. Because of this, we split the import process into two steps.
The ``add-metrics`` subcommand extracts data from the lowlevel table into a new summary table
(*similarity.similarity*) that includes only the specific numerical feature necessary for the similarity index.

The ``add-indices`` subcommand reads from the *similarity.similarity* table and builds an Annoy index. We build
this index from scratch each time the command is run due to technical requirements in Annoy, and the fact that
this operation doesn't take too long to complete.

Adding a new feature
^^^^^^^^^^^^^^^^^^^^
(todo: fill in with more detail)

* Add new metric to ``admin/sql/populate_metrics_table.sql``
* Add new metric class to ``similarity.metrics``
* Add this class to ``similarity.metrics.BASE_METRICS``
* Extract new data if necessary in ``db.similarity.get_batch_data``
* alter *similarity.similarity* table to include new column for this feature

  * todo: should we be able to fill in just this column, or do we recreate *similarity.similarity*?

Index parameters
----------------

Indices take a number of parameters when being built. We are currently evaluating
them ourselves and have developed a set of base indices, but you may want to
experiment with different parameters. 

Queries to an index become more precise when the index is built with a higher 
number of trees, but they will also take longer to build. Indices can also vary
in the method used to calculate distance between recordings. Limitations of
parameter selection can be found in the `Annoy documentation`_ and our codebase_

.. _Annoy documentation: https://github.com/spotify/annoy
.. _codebase: https://github.com/metabrainz/acousticbrainz-server/master/tree/similarity/index_model.py