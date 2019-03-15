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

UPDATE model SET mappings = '{
        "alternative": "alternative",
        "blues": "blues",
        "electronic": "electronic",
        "folkcountry": "folk_country",
        "funksoulrnb": "funk_soul_rnb",
        "jazz": "jazz",
        "pop": "pop",
        "raphiphop": "rap_hiphop",
        "rock": "rock"
    }'::jsonb WHERE model.model = 'genre_dortmund';

UPDATE model SET mappings = '{
        "ambient": "ambient",
        "dnb": "drum_and_bass",
        "house": "house",
        "techno": "techno",
        "trance": "trance"
    }'::jsonb WHERE model.model = 'genre_electronic';

UPDATE model SET mappings = '{
        "cla": "classical",
        "dan": "dance",
        "hip": "hiphop",
        "jaz": "jazz",
        "pop": "pop",
        "rhy": "rhythm",
        "roc": "rock",
        "spe": "speech"
    }'::jsonb WHERE model.model = 'genre_rosamerica';

UPDATE model SET mappings = '{
        "blu": "blues",
        "cla": "classical",
        "cou": "country",
        "dis": "disco",
        "hip": "hiphop",
        "jaz": "jazz",
        "met": "metal",
        "pop": "pop",
        "reg": "reggae",
        "roc": "rock"
    }'::jsonb WHERE model.model = 'genre_tzanetakis';
    
COMMIT;
