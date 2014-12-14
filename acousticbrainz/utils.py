import json
import os

UNSURE = "unsure"

_whitelist_file = os.path.join(os.path.dirname(__file__), "tagwhitelist.json")
_whitelist_tags = set(json.load(open(_whitelist_file)))

SANITY_CHECK_KEYS = [
    ['metadata', 'version', 'essentia'],
    ['metadata', 'version', 'essentia_git_sha'],
    ['metadata', 'version', 'extractor'],
    ['metadata', 'version', 'essentia_build_sha'],
    ['metadata', 'audio_properties', 'length'],
    ['metadata', 'audio_properties', 'bit_rate'],
    ['metadata', 'audio_properties', 'codec'],
    ['metadata', 'audio_properties', 'lossless'],
    ['metadata', 'tags', 'file_name'],
    ['metadata', 'tags', 'musicbrainz_recordingid'],
    ['lowlevel'],
    ['rhythm'],
    ['tonal'],
]


def _has_key(dictionary, key):
    """Checks if muti-level dictionary contains in item referenced by a
    specified key.

    Args:
        dictionary: Multi-level dictionary that needs to be checked.
        keys: List of keys that will be checked. For example, key
            ['metadata', 'tags'] represents dictionary['metadata']['tags'].
    Returns:
        True if dictionary contains item with a specified key, False if it
        wasn't found.
    """
    for part in key:
        if part not in dictionary:
            return False
        dictionary = dictionary[part]
    return True


def sanity_check_data(data):
    """Checks if data about the track contains all required keys.

    Args:
        data: Dictionary that contains information about the track.
    Returns:
        First key that is missing or None if everything is in place.
    """
    for key in SANITY_CHECK_KEYS:
        if not _has_key(data, key):
            return key
    return None


def clean_metadata(data):
    """Check that tags are in our whitelist. If not, throw them away."""
    tags = data["metadata"]["tags"]
    for tag in tags.keys():
        tag = tag.lower()
        if tag not in _whitelist_tags:
            del tags[tag]
    data["metadata"]["tags"] = tags
    return data


def _interpret(text, data, threshold):
    if data['probability'] >= threshold:
        return text, data['value'].replace("_", " "), "%.3f" % data['probability']
    return text, UNSURE,"%.3f" %  data['probability']


def interpret_high_level(hl):
    genres = []
    genres.append(_interpret("Genre - tzanetakis' method", hl['highlevel']['genre_tzanetakis'], .6))
    genres.append(_interpret("Genre - electronic classification", hl['highlevel']['genre_electronic'], .6))
    genres.append(_interpret("Genre - dortmund method", hl['highlevel']['genre_dortmund'], .6))
    genres.append(_interpret("Genre - rosamerica method", hl['highlevel']['genre_rosamerica'], .6))

    moods = []
    moods.append(_interpret("Mood - electronic", hl['highlevel']['mood_electronic'], .6))
    moods.append(_interpret("Mood - party", hl['highlevel']['mood_party'], .6))
    moods.append(_interpret("Mood - aggressive", hl['highlevel']['mood_aggressive'], .6))
    moods.append(_interpret("Mood - acoustic", hl['highlevel']['mood_acoustic'], .6))
    moods.append(_interpret("Mood - happy", hl['highlevel']['mood_happy'], .6))
    moods.append(_interpret("Mood - sad", hl['highlevel']['mood_sad'], .6))
    moods.append(_interpret("Mood - relaxed", hl['highlevel']['mood_relaxed'], .6))
    moods.append(_interpret("Mood - mirex method", hl['highlevel']['moods_mirex'], .6))

    other = []
    other.append(_interpret("Voice", hl['highlevel']['voice_instrumental'], .6))
    other.append(_interpret("Gender", hl['highlevel']['gender'], .6))
    other.append(_interpret("Danceability", hl['highlevel']['danceability'], .6))
    other.append(_interpret("Tonal", hl['highlevel']['tonal_atonal'], .6))
    other.append(_interpret("Timbre", hl['highlevel']['timbre'], .6))
    other.append(_interpret("ISMIR04 Rhythm", hl['highlevel']['ismir04_rhythm'], .6))

    return genres, moods, other
