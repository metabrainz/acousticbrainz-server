BEGIN;

INSERT INTO model (model, model_version, date, status) VALUES ('danceability', 'v2.1_beta1', now(), 'show');
INSERT INTO model (model, model_version, date, status) VALUES ('gender', 'v2.1_beta1', now(), 'show');
INSERT INTO model (model, model_version, date, status) VALUES ('genre_dortmund', 'v2.1_beta1', now(), 'show');
INSERT INTO model (model, model_version, date, status) VALUES ('genre_electronic', 'v2.1_beta1', now(), 'show');
INSERT INTO model (model, model_version, date, status) VALUES ('genre_rosamerica', 'v2.1_beta1', now(), 'show');
INSERT INTO model (model, model_version, date, status) VALUES ('genre_tzanetakis', 'v2.1_beta1', now(), 'show');
INSERT INTO model (model, model_version, date, status) VALUES ('ismir04_rhythm', 'v2.1_beta1', now(), 'show');
INSERT INTO model (model, model_version, date, status) VALUES ('mood_acoustic', 'v2.1_beta1', now(), 'show');
INSERT INTO model (model, model_version, date, status) VALUES ('mood_aggressive', 'v2.1_beta1', now(), 'show');
INSERT INTO model (model, model_version, date, status) VALUES ('mood_electronic', 'v2.1_beta1', now(), 'show');
INSERT INTO model (model, model_version, date, status) VALUES ('mood_happy', 'v2.1_beta1', now(), 'show');
INSERT INTO model (model, model_version, date, status) VALUES ('mood_party', 'v2.1_beta1', now(), 'show');
INSERT INTO model (model, model_version, date, status) VALUES ('mood_relaxed', 'v2.1_beta1', now(), 'show');
INSERT INTO model (model, model_version, date, status) VALUES ('mood_sad', 'v2.1_beta1', now(), 'show');
INSERT INTO model (model, model_version, date, status) VALUES ('moods_mirex', 'v2.1_beta1', now(), 'show');
INSERT INTO model (model, model_version, date, status) VALUES ('timbre', 'v2.1_beta1', now(), 'show');
INSERT INTO model (model, model_version, date, status) VALUES ('tonal_atonal', 'v2.1_beta1', now(), 'show');
INSERT INTO model (model, model_version, date, status) VALUES ('voice_instrumental', 'v2.1_beta1', now(), 'show');

COMMIT;
