#-------------------------------------------------------------------------------
# Name:        app
#
# Purpose:     TIGER Catalog is the catalog for Colorado College's collections.
#              It offers a simple web app interface to a Solr, Redis, Fedora
#              Commons, and MongoDB all components in semantic datastores in
#              the Catalog Pull Platform.
#
#
# Author:      Jeremy Nelson
#
# Created:     2014-03-04
# Copyright:   (c) Jeremy Nelson, Colorado College 2014
# Licence:     MIT
#-------------------------------------------------------------------------------
import os
import redis
import time

from bson import ObjectId
from solr_search.forms import BasicSearch
from flask import abort, Flask, g, jsonify, redirect, render_template, request
from flask import Response, url_for
from flask.ext.mongokit import Connection, MongoKit

from helpers.filters import get_facets
from helpers import metrics
from mongo_datastore import mongo_datastore, get_cover_art_image
from mongo_datastore import check_for_cover_art, get_item_details, get_work
from patron import patron, login_manager
from solr_search import solr, solr_search


app = Flask('tiger_catalog')
app.config.from_pyfile('catalog.cfg')
app.register_blueprint(mongo_datastore)
app.register_blueprint(patron)
app.register_blueprint(solr_search)



solr.init_app(app)
login_manager.init_app(app)

mongo_storage  = Connection(app.config["MONGODB_HOST"])

redis_ds = redis.StrictRedis(app.config['REDIS_HOST'],
                             app.config['REDIS_PORT'])


@app.template_filter('get_title')
def get_title(work_id):
    work = get_work(mongo_storage, work_id)
    if 'title' in work:
        return work.get('title')
    if 'headline' in work:
        return work.get('headline')
    if 'fields' in work:
        for row in work.get('fields'):
            if row.keys()[0] == '245':
                return ' '.join([y.values()[0] for y in row['245']['subfields'] if ['a','b'].count(y.keys()[0])])
    return 'No Title Found'

@app.template_filter('pretty_number')
def pretty_number(number):
    return "{:,}".format(number)

# This should be a new Extension, very manual right now but needs to be more
# flexible data collection for other cohort testing
@app.route("/feedback", methods=['GET', 'POST'])
def feedback():
    output = {'response': None}
    if request.method == 'POST':
        job = request.values.get('job')
        if job == 'auth_opts_test':
            patron_ip = request.remote_addr
            patron_ip_key = redis_ds.hget("auth-options-ip",
                                          patron_ip)
            timestamp = time.time()

            if not patron_ip_key:
                patron_ip_count = redis_ds.incr("global patron_ip")
                patron_ip_key = "patron_ip:{}".format(patron_ip_count)
                redis_ds.hset("auth-options-ip",
                              patron_ip,
                              patron_ip_key)
                redis_ds.hset(patron_ip_key, 'ip-addr', patron_ip)
            else:
                patron_ip_count = patron_ip_key.split(":")[-1]
            redis_ds.zadd("auth-options-log", timestamp, patron_ip_key)
            for name, value in request.values.iteritems():
                if name == 'job':
                    continue
                if value is not None:
                    redis_ds.setbit("auth-options-{}".format(name),
                                    patron_ip_count,
                                    1)
                    if name == 'other':
                        redis_ds.hset(patron_ip_key,
                                  'other-auth-option',
                                  value)
            output = {'response': 'ok',
                      'msg': 'Thanks for helping us out!',
                      'ip_key': patron_ip_key}
    return jsonify(output)

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

@app.route("/Work/<work_id>.json")
def work2json(work_id):
    return jsonify({'@id': work_id})

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