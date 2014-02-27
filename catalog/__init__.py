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
import os
import redis

from bson import ObjectId
from solr_search.forms import BasicSearch
from flask import abort, Flask, g, jsonify, redirect, render_template, request
from flask import Response, url_for
from flask.ext.mongokit import Connection, MongoKit

from helpers.filters import get_facets
from mongo_datastore import mongo_datastore, get_cover_art_image
from mongo_datastore import check_for_cover_art, get_item_details
from patron import patron, login_manager
from solr_search import solr, solr_search

app = Flask('tiger_catalog')
app.config.from_pyfile('tiger.cfg')
app.register_blueprint(mongo_datastore)
app.register_blueprint(patron)
app.register_blueprint(solr_search)


solr.init_app(app)
login_manager.init_app(app)

mongo_storage  = Connection(app.config["MONGODB_HOST"])

redis_ds = redis.StrictRedis(app.config['REDIS_HOST'],
                             app.config['REDIS_PORT'])

@app.template_filter('pretty_number')
def pretty_number(number):
    return "{:,}".format(number)

@app.route('/CoverArt/<cover_id>')
def cover_art(cover_id):
    entity_id, ext = os.path.splitext(cover_id)
    if ext.startswith(".jpg"):
        mimetype = 'image/jpg'
    else:
        mimetype = 'image/png'
    raw_image = get_cover_art_image(entity_id,
                                    mongo_storage.bibframe)
    if not raw_image:
        abort(404)
    return Response(raw_image, mimetype=mimetype)

@app.route("/Work/<work_id>")
def work(work_id):
    # Searches various MongoDB and Redis hashes for work_id match
    marc_db = getattr(mongo_storage,
                      app.config["MONGODB_DATABASE"])
    creative_work = marc_db.marc_records.find_one(
        {"_id": ObjectId(work_id)})
    if check_for_cover_art(work_id):
        cover_art_url = url_for('cover_art',
                                cover_id=work_id)
    else:
        cover_art_url =  url_for('solr_search.static',
                                 filename='img/no-cover.png')
    return render_template('detail.html',
                           cover_art_url=cover_art_url,
                           item=get_item_details(work_id),
                           work=creative_work,
                           search_form=BasicSearch())

@app.route('/')
def home():
    marc_db = getattr(mongo_storage,
                      app.config["MONGODB_DATABASE"])
    facets = get_facets(redis_ds=redis_ds,
                        mongo_collection=marc_db.marc_records)
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
