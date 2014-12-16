#!/usr/bin/env python
from acousticbrainz import create_app
import argparse

application = create_app()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='AcousticBrainz dev server')
    parser.add_argument("-d", "--debug", help="Turn on debugging mode to see stack traces in the error pages", default=True, action='store_true')
    parser.add_argument("-t", "--host", help="Which interfaces to listen on. Default: 0.0.0.0", default="0.0.0.0", type=str)
    parser.add_argument("-p", "--port", help="Which port to listen on. Default: 8080", default="8080", type=int)
    args = parser.parse_args()
    application.run(debug=True, host=args.host, port=args.port)
