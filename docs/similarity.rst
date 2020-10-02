Recording Similarity
====================

An emerging feature in AcousticBrainz is recording similarity.

We compute similarity between recordings based on a selection of 
high and low-level features [metrics]. 

Similarity metrics for each recording should be computed on submission. 
When the metrics for a recording have been added to static index files, 
we can query for track-track similarity based on our choice of feature. 

This dataset is made available through a set of `API endpoints`_, and 
distribution of the static index files for more flexibility.

Similarity Metrics
^^^^^^^^^^^^^^^^^^

Similarity metrics are methods of applying a vectorized measurement to
one, or many features of high and low-level data.

Thus far, the following metrics can be used to assess similarity:

==================== ============ ====================
**Metric**           **Hybrid**   **Category**
==================== ============ ====================
MFCCs                False        Timbre
MFCCs (Weighted)     False        Timbre
GFCCs                False        Timbre
GFCCs (Weighted)     False        Timbre
Key                  False        Rhythm (Key/Scale)
BPM                  False        Rhythm
OnsetRate            False        Rhythm
Moods                False        High-Level
Instruments          False        High-Level
Dortmund             False        High-Level (Genre)
Rosamerica           False        High-Level (Genre)
Tzanetakis           False        High-Level (Genre)
==================== ============ ====================

Note: Hybrid metrics are combinations of multiple metrics. In the future, 
we hope to integrate more metrics that combine low-level features for a 
more holistic approach to similarity.

Similarity Statistics
^^^^^^^^^^^^^^^^^^^^^

Some of our metrics are normalized using the mean and standard deviation
of their features from the lowlevel table. We must compute the statistics
for such metrics prior to computing the metrics themselves. To do so, we
collect a sample of the lowlevel table and use it to approximate the mean
and standard deviation. Currently, the metrics that require statistics are
the following:

- MFCCs
- Weighted MFCCs
- GFCCs
- Weighted GFCCs

Indexing
^^^^^^^^

Metric vectors for each recording are added to static indices, created with 
the Annoy_ library. An individual index exists for each of the metrics
available. An index uses a nearest neighbours approach for queries.

Note that computing an index takes time, and thus it cannot happen each time
a recording is submitted. Indices are recomputed, including new submissions,
on a time interval.

More can be read about indices and contributing to similarity work in the
`developer reference`_.

Evaluation
^^^^^^^^^^

The similarity engine is an ongoing project, and its results are still largely
experimental. While we tune different index parameters (described in the
`developer reference`_), we'd like to gather feedback from the community.

As such, we've made an evaluation available to the public. When viewing the
summary data for a recording, you may access similar recordings organized by
metric. Recordings are organized from most similar to least similar. Alongside
the list of the most similar recordings, you may provide input:

- Rate whether the recording should be higher or lower on the list of similarity,
  or whether this result seems accurate.
- Provide additional suggestions related to a specific similar recording, or in
  general.

Feel free to provide as much or as little feedback as you wish when browsing.
We appreciate your help in improving similarity at AcousticBrainz!

.. _API endpoints: https://acousticbrainz.readthedocs.io/api.html
.. _Annoy: https://github.com/spotify/annoy
.. _developer reference: https://acousticbrainz.readthedocs.io/dev/similarity.html