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
import redis

from forms import BasicSearch
from flask import abort, Flask, g, jsonify, redirect, render_template, request
from flask import url_for
from flask.ext.mongokit import MongoKit
from flask.ext.solrpy import FlaskSolrpy

from helpers.filters import get_facets
from helpers.mongodb import get_marc

app = Flask('tiger_catalog')
app.config.from_pyfile('tiger.cfg')

solr = FlaskSolrpy()
solr.init_app(app)

db = MongoKit(app)
redis_ds = redis.StrictRedis(app.config['REDIS_HOST'],
                             app.config['REDIS_PORT'])

@app.template_filter('pretty_number')
def pretty_number(number):
    return "{:,}".format(number)

@app.route('/search',
           methods=['GET', 'POST'])
def search():
    query = request.form.get('q')
    solr_result = g.solr.query(query)
    for row in solr_result.results:
        row['workURL'] = ''
        row['coverURL'] = ''
        row['instanceLocation'] = ''
        row['instanceDetail'] = ''
    return jsonify({'total': solr_result.numFound,
                    'instances': solr_result.results,
                    'result': "OK"})

@app.route('/')
def home():
    facets = get_facets(redis_ds=redis_ds,
                        mongo_collection=db.marc_records)
    return render_template('catalog.html',
                           facets=facets,
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
