import os.path
import json

STATIC_BUILD_PATH = os.path.join(os.path.dirname(__file__), "static", "build")
MANIFEST_PATH = os.path.join(STATIC_BUILD_PATH, "manifest.json")

manifest_content = {}


def read_manifest():
    if os.path.isfile(MANIFEST_PATH):
        with open(MANIFEST_PATH) as manifest_file:
            global manifest_content
            manifest_content = json.load(manifest_file)


def manifest_get_static_path(resource_name):
    """Find the public URL of a static file in production.
    Assets built by webpack for deployment have a hash component in the filename. The manifest file
    maps entrypoint filenames to filenames on disk. If a filename doesn't exist in the manifest file,
    it's just a regular static file on disk.
    """
    if resource_name not in manifest_content:
        return "/static/%s" % resource_name
    return manifest_content[resource_name]


def development_get_static_path(resource_name):
    """Find the public URL of a static file during development.
    Assets that are built with webpack during development don't have any hash components, and
    so we just look for them in the build directory.
    """
    build_path = os.path.join(STATIC_BUILD_PATH, resource_name)
    if os.path.exists(build_path):
        return "/static/build/%s" % resource_name
    else:
        return "/static/%s" % resource_name
