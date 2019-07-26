BEGIN;

-- Add base metrics when db is initialized, before similarity stats are computed
INSERT INTO similarity.similarity_metrics (metric, is_hybrid, description, category) VALUES ('mfccs', 'FALSE', 'MFCCs', 'timbre');
INSERT INTO similarity.similarity_metrics (metric, is_hybrid, description, category) VALUES ('mfccsw', 'FALSE', 'MFCCs (weighted)', 'timbre');
INSERT INTO similarity.similarity_metrics (metric, is_hybrid, description, category) VALUES ('gfccs', 'FALSE', 'GFCCs', 'timbre');
INSERT INTO similarity.similarity_metrics (metric, is_hybrid, description, category) VALUES ('gfccsw', 'FALSE', 'GFCCs (weighted)', 'timbre');
INSERT INTO similarity.similarity_metrics (metric, is_hybrid, description, category) VALUES ('key', 'FALSE', 'Key/Scale', 'rhythm');
INSERT INTO similarity.similarity_metrics (metric, is_hybrid, description, category) VALUES ('bpm', 'FALSE', 'BPM', 'rhythm');
INSERT INTO similarity.similarity_metrics (metric, is_hybrid, description, category) VALUES ('onsetrate', 'FALSE', 'OnsetRate', 'timbre');
INSERT INTO similarity.similarity_metrics (metric, is_hybrid, description, category) VALUES ('moods', 'FALSE', 'Moods', 'high-level');
INSERT INTO similarity.similarity_metrics (metric, is_hybrid, description, category) VALUES ('instruments', 'FALSE', 'Instruments', 'high-level');
INSERT INTO similarity.similarity_metrics (metric, is_hybrid, description, category) VALUES ('dortmund','FALSE', 'Genre (dortmund model)', 'high-level');
INSERT INTO similarity.similarity_metrics (metric, is_hybrid, description, category) VALUES ('rosamerica', 'FALSE', 'Genre (rosamerica model)', 'high-level');
INSERT INTO similarity.similarity_metrics (metric, is_hybrid, description, category) VALUES ('tzanetakis', 'FALSE', 'Genre (tzanetakis model)', 'high-level');

COMMIT;