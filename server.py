#!/usr/bin/env python

from webserver import create_app
import argparse

application = create_app()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='AcousticBrainz server')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Turn on debugging mode to see stack traces on '
                             'the error pages. This overrides DEBUG value '
                             'in config file.')
    parser.add_argument('-h', default='0.0.0.0', type=str,
                        help='which interface to listen on. Default: 0.0.0.0')
    parser.add_argument('-p', '--port', default=8080, type=int,
                        help='which port to listen on. Default: 8080')
    args = parser.parse_args()
    application.run(debug=True if args.debug else None,
                    host=args.host, port=args.port)
