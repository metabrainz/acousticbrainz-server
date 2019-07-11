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
**Metric**			 **Hybrid**	  **Category**
==================== ============ ====================
MFCCs				 False	      Timbre
==================== ============ ====================
MFCCs (Weighted)	 False	      Timbre
==================== ============ ====================
GFCCs				 False	      Timbre
==================== ============ ====================
GFCCs (Weighted)	 False	      Timbre
==================== ============ ====================
Key					 False	      Rhythm (Key/Scale)
==================== ============ ====================
BPM					 False	      Rhythm
==================== ============ ====================
OnsetRate			 False	      Rhythm
==================== ============ ====================
Moods				 False	      High-Level
==================== ============ ====================
Instruments			 False	      High-Level
==================== ============ ====================
Dortmund			 False	      High-Level (Genre)
==================== ============ ====================
Rosamerica			 False	      High-Level (Genre)
==================== ============ ====================
Tzanetakis			 False	      High-Level (Genre)
==================== ============ ====================

Note: Hybrid metrics are combinations of multiple metrics. In the future, 
we hope to integrate more metrics that combine low-level features for a 
more holistic approach to similarity.

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

.. _API endpoints: https://acousticbrainz.readthedocs.io/api.html
.. _Annoy: https://github.com/spotify/annoy
.. _developer reference: https://acousticbrainz.readthedocs.io/dev/similarity.html