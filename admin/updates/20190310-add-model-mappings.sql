BEGIN;

ALTER TABLE model ADD COLUMN mappings JSONB;
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
        "hip": "hip_hop",
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