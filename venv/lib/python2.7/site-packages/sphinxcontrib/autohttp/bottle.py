"""
    sphinxcontrib.autohttp.bottle
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    The sphinx.ext.autodoc-style HTTP API reference builder (from Bottle)
    for sphinxcontrib.httpdomain.

    :copyright: Copyright 2012 by Jameel Al-Aziz
    :license: BSD, see LICENSE for details.

"""

import re
import six

from docutils import nodes
from docutils.parsers.rst import directives
from docutils.statemachine import ViewList

from sphinx.util import force_decode
from sphinx.util.compat import Directive
from sphinx.util.nodes import nested_parse_with_titles
from sphinx.util.docstrings import prepare_docstring
from sphinx.pycode import ModuleAnalyzer

from sphinxcontrib import httpdomain
from sphinxcontrib.autohttp.common import http_directive, import_object


def translate_bottle_rule(app, rule):
    buf = six.StringIO()
    if hasattr(app.router, "parse_rule"):
        iterator = app.router.parse_rule(rule)  # bottle 0.11
    else:
        iterator = app.router._itertokens(rule)  # bottle 0.12
    for name, filter, conf in iterator:
        if filter:
            buf.write('(')
            buf.write(name)
            if (filter != app.router.default_filter and filter != 'default')\
                    or conf:
                buf.write(':')
                buf.write(filter)
            if conf:
                buf.write(':')
                buf.write(conf)
            buf.write(')')
        else:
            buf.write(name)
    return buf.getvalue()


def get_routes(app):
    for route in app.routes:
        path = translate_bottle_rule(app, route.rule)
        yield route.method, path, route


class AutobottleDirective(Directive):

    has_content = True
    required_arguments = 1
    option_spec = {'endpoints': directives.unchanged,
                   'undoc-endpoints': directives.unchanged,
                   'include-empty-docstring': directives.unchanged}

    @property
    def endpoints(self):
        endpoints = self.options.get('endpoints', None)
        if not endpoints:
            return None
        return frozenset(re.split(r'\s*,\s*', endpoints))

    @property
    def undoc_endpoints(self):
        undoc_endpoints = self.options.get('undoc-endpoints', None)
        if not undoc_endpoints:
            return frozenset()
        return frozenset(re.split(r'\s*,\s*', undoc_endpoints))

    def make_rst(self):
        app = import_object(self.arguments[0])
        for method, path, target in get_routes(app):
            endpoint = target.name or target.callback.__name__
            if self.endpoints and endpoint not in self.endpoints:
                continue
            if endpoint in self.undoc_endpoints:
                continue
            view = target.callback
            docstring = view.__doc__ or ''
            if not isinstance(docstring, six.text_type):
                analyzer = ModuleAnalyzer.for_module(view.__module__)
                docstring = force_decode(docstring, analyzer.encoding)
            if not docstring and 'include-empty-docstring' not in self.options:
                continue
            docstring = prepare_docstring(docstring)
            for line in http_directive(method, path, docstring):
                yield line

    def run(self):
        node = nodes.section()
        node.document = self.state.document
        result = ViewList()
        for line in self.make_rst():
            result.append(line, '<autobottle>')
        nested_parse_with_titles(self.state, result, node)
        return node.children


def setup(app):
    if 'http' not in app.domains:
        httpdomain.setup(app)
    app.add_directive('autobottle', AutobottleDirective)

