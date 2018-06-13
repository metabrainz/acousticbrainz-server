BEGIN;

CREATE INDEX artist_idx_begin_area ON musicbrainz.artist (begin_area);
CREATE INDEX artist_idx_end_area ON musicbrainz.artist (end_area);
 
CREATE UNIQUE INDEX area_type_idx_gid ON musicbrainz.area_type (gid);
 
CREATE UNIQUE INDEX medium_format_idx_gid ON musicbrainz.medium_format (gid);

CREATE UNIQUE INDEX release_status_idx_gid ON musicbrainz.release_status (gid);

CREATE UNIQUE INDEX language_idx_iso_code_2b ON musicbrainz.language (iso_code_2b);
CREATE UNIQUE INDEX language_idx_iso_code_2t ON musicbrainz.language (iso_code_2t);
CREATE UNIQUE INDEX language_idx_iso_code_1 ON musicbrainz.language (iso_code_1);
CREATE UNIQUE INDEX language_idx_iso_code_3 ON musicbrainz.language (iso_code_3);

CREATE UNIQUE INDEX release_packaging_idx_gid ON musicbrainz.release_packaging (gid);

CREATE UNIQUE INDEX script_idx_iso_code ON musicbrainz.script (iso_code);

CREATE UNIQUE INDEX gender_idx_gid ON musicbrainz.gender (gid);

CREATE UNIQUE INDEX artist_type_idx_gid ON musicbrainz.artist_type (gid);

COMMIT;
