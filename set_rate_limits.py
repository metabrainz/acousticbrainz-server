#!/usr/bin/env python

import sys
from acousticbrainz import config
from brainzutils.ratelimit import set_rate_limits, ratelimit_per_token_key, ratelimit_per_ip_key, ratelimit_window_key 
from brainzutils import cache
import config

# Yes, I could use getoptgetargparsewtfbbw, but then I would spend 20 mimnutes re-learning the stupid syntax.
# Or, I could just do it myself in the space of seconds.
# Also, I tried to integrate this script with manage.py, but then I ended up wasting an hour trying
# to figure out how to do this. So, we have this script. If you want to see it part of manage.py, you'll
# have to do it.

cache.init(
    host=config['REDIS_HOST'],
    port=config['REDIS_PORT'],
    namespace=config['REDIS_NAMESPACE'],
    ns_versions_loc=config['REDIS_NS_VERSIONS_LOCATION'])

if len(sys.argv) < 4:
    print("Usage: %s <per ip limit> <per token limit> <window in s>" % (sys.argv[0]))
    print("Current values:")
    print("      Requests per ip: ", int(cache.get(ratelimit_per_ip_key) or -1))
    print("   Requests per token: ", int(cache.get(ratelimit_per_token_key) or -1))
    print("          window size: ", int(cache.get(ratelimit_window_key) or -1))
    sys.exit(-1)

try:
    per_ip = int(sys.argv[1])
except ValueError:
    print("Invalid per ip limit. Must be non zero integer.")
    sys.exit(-1)

if per_ip <= 0:
    print("Invalid per ip limit. Must be non zero integer.")


try:
    per_token = int(sys.argv[2])
except ValueError:
    print("Invalid per token limit. Must be non zero integer.")
    sys.exit(-1)

if per_token <= 0:
    print("Invalid per token limit. Must be non zero integer.")


try:
    window = int(sys.argv[3])
except ValueError:
    print("Invalid window size. Must be non zero integer.")
    sys.exit(-1)

if window <= 0:
    print("Invalid window size. Must be non zero integer.")

set_rate_limits(per_token, per_ip, window)
