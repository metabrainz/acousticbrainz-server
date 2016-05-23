BEGIN;

CREATE INDEX data_metadata_audio_properties_md5_encoded_idx_lowlevel_json ON lowlevel_json USING gin ((data#>'{metadata,audio_properties,md5_encoded}'));

COMMIT;