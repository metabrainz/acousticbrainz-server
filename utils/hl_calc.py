import hashlib

import yaml


class HighLevelConfigurationError(Exception):
    """Indicates an error configuring the highlevel extractor on startup,
    before processing items"""


def create_profile(in_file, out_file, sha1):
    """Prepare a profile file for use with essentia. Sanity check to make sure
    important values are present.
    """

    try:
        with open(in_file, 'r') as f:
            doc = yaml.load(f, Loader=yaml.SafeLoader)
    except IOError as e:
        raise HighLevelConfigurationError(u"Cannot read profile {}: {}".format(in_file, e))

    try:
        models_ver = doc['mergeValues']['metadata']['version']['highlevel']['models_essentia_git_sha']
    except KeyError:
        models_ver = None

    if not models_ver:
        raise HighLevelConfigurationError("{} needs to have mergeValues.metadata.version.highlevel."
                                          "models_essentia_git_sha defined".format(in_file))

    doc['mergeValues']['metadata']['version']['highlevel']['essentia_build_sha'] = sha1

    try:
        with open(out_file, 'w') as yaml_file:
            yaml.dump(doc, yaml_file, default_flow_style=False)
    except IOError as e:
        raise HighLevelConfigurationError(u"Cannot write profile {}: {}".format(out_file, e))


def get_build_sha1(binary):
    """Calculate the SHA1 of the binary we're using."""
    try:
        with open(binary, "rb") as fp:
            contents = fp.read()
    except IOError as e:
        raise HighLevelConfigurationError("Cannot calculate the SHA1 of the high-level extractor binary: {}".format(e))

    return hashlib.sha1(contents).hexdigest()
