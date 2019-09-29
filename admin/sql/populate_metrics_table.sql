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

INSERT INTO similarity.eval_params (metric, distance_type, n_trees) VALUES ('mfccs', 'angular', 10);
INSERT INTO similarity.eval_params (metric, distance_type, n_trees) VALUES ('mfccsw', 'angular', 10);
INSERT INTO similarity.eval_params (metric, distance_type, n_trees) VALUES ('gfccs', 'angular', 10);
INSERT INTO similarity.eval_params (metric, distance_type, n_trees) VALUES ('gfccsw', 'angular', 10);
INSERT INTO similarity.eval_params (metric, distance_type, n_trees) VALUES ('key', 'angular', 10);
INSERT INTO similarity.eval_params (metric, distance_type, n_trees) VALUES ('bpm', 'angular', 10);
INSERT INTO similarity.eval_params (metric, distance_type, n_trees) VALUES ('onsetrate', 'angular', 10);
INSERT INTO similarity.eval_params (metric, distance_type, n_trees) VALUES ('moods', 'angular', 10);
INSERT INTO similarity.eval_params (metric, distance_type, n_trees) VALUES ('instruments', 'angular', 10);
INSERT INTO similarity.eval_params (metric, distance_type, n_trees) VALUES ('dortmund', 'angular', 10);
INSERT INTO similarity.eval_params (metric, distance_type, n_trees) VALUES ('rosamerica', 'angular', 10);
INSERT INTO similarity.eval_params (metric, distance_type, n_trees) VALUES ('tzanetakis', 'angular', 10);

COMMIT;
