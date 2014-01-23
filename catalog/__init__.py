#-------------------------------------------------------------------------------
# Name:        TIGER Catalog
#
# Purpose:     TIGER Catalog is the next generation catalog for Colorado College.
#              It offers a simple web app interface to a Solr, Redis, Fedora
#              Commons, and MongoDB all components in semantic datastores in
#              the Catalog Pull Platform.
#
#
# Author:      Jeremy Nelson
#
# Created:     2014-01-22
# Copyright:   (c) Jeremy Nelson, Colorado College 2014
# Licence:     MIT
#-------------------------------------------------------------------------------

from forms import BasicSearch
from flask import Flask, render_template
from flask.ext.mongokit import MongoKit

from mongodb_helpers import get_marc

app = Flask('tiger_catalog')
app.config.from_pyfile('tiger.cfg')

db = MongoKit(app)

@app.route('/')
def home():
    return render_template('catalog.html',
                           search_form=BasicSearch(),
                           patron=None)

def main(dev=False):
    host = '0.0.0.0'
    port = 8000
    if dev:
        app.run(
            host=host,
            port=port,
            debug=True)
    else:
        app.run(
            host=host,
            port=port)

if __name__ == '__main__':
    main(True)
