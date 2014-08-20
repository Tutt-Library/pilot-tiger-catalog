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
import json
import os
import redis
import rdflib
import time
import urllib
import uuid

from bson import ObjectId
from bson.errors import InvalidId
from collections import OrderedDict
from search.forms import BasicSearch, FilterResults

from flask import abort, Flask, g, jsonify, redirect, render_template, request
from flask import Response, url_for
##from flask.ext.mongokit import Connection, MongoKit
from flask_negotiate import produces
##from helpers.filters import get_facets
##from helpers import metrics
##from mongo_datastore import mongo_datastore, get_cover_art_image
##from mongo_datastore import check_for_cover_art, get_item_details, get_work
##from patron import patron, login_manager
from rdflib import Graph

##from solr_search import solr, solr_search

catalog = Flask(__name__)
##catalog = Flask('tiger_catalog')
catalog.config.from_pyfile('catalog.cfg')
##catalog.register_blueprint(mongo_datastore)
##catalog.register_blueprint(patron)
##catalog.register_blueprint(solr_search)



##solr.init_app(catalog)
##login_manager.init_app(catalog)

##mongo_storage  = Connection(catalog.config["MONGODB_HOST"])

##redis_ds = redis.StrictRedis(catalog.config['REDIS_HOST'],
##                             catalog.config['REDIS_PORT'])

BF_NS = rdflib.Namespace('http://bibframe.org/vocab/')
SCHEMA_NS = rdflib.Namespace('http://schema.org/')

CONTEXT={
    "@vocab": "http://bibframe.org/vocab/",
##    "fcrepo": "http://fedora.info/definitions/v4/repository#",
##    "fedora": "http://fedora.info/definitions/v4/rest-api#",
    "@language": "en"}


def get_entity(entity_id):
    entity_rdf = rdflib.Graph().parse(entity_id)
    relative_url = urllib.parse.urlsplit(entity_id).path
    if relative_url.startswith("/rest"):
        relative_url = relative_url.split("/rest")[-1]
    html = """<a href="{}">{}</a>"""
    for namespace in [
        BF_NS,
        SCHEMA_NS,
        rdflib.RDFS,
        rdflib.RDF]:
        label = entity_rdf.value(subject=rdflib.URIRef(entity_id),
                                  predicate=namespace.label)
        if label is not None:
            return html.format(
                relative_url,
                label)
        title = entity_rdf.value(subject=rdflib.URIRef(entity_id),
                                 predicate=namespace.titleValue)
        if title is not None:
            return html.format(
                relative_url,
                title)
    return relative_url


@catalog.template_filter('get_creators')
def get_creators(creators):
    output = ''
    if type(creators) == dict and '@id' in creators:
        return get_entity(creators.get('@id'))
    elif type(creators) == list:
        for creator in creators:
            if '@id' in creator:
                output += "{},".format(get_entity(creator.get('@id')))
    if output.endswith(","):
        output = output[:-1]
    return output

@catalog.template_filter('get_heading')
def get_heading(entity):
    if 'title' in entity:
        if type(entity['title']) == list:
            return entity['title'][0]
        elif type(entity['title']) == str:
            return entity['title']
        else:
            return str(entity['title'])
    if 'name' in entity:
        if type(entity['name']) == list:
            return entity['name'][0]
        else:
            return entity['name']




##    work = get_work(mongo_storage, work_id)
##    if 'creator' in work:
##        creators = []
##        for mongo_id in work.get('creator', []):
##            print(mongo_storage.database_names())
##            creator = mongo_storage.schema_org.Person.find_one(
##                {"_id": ObjectId(mongo_id)},
##                {"name"})
##            if creator:
##                creators.append(creator)
##        return ','.join(
##            ["""<a href="/Person/{0}">{1}</a>""".format(creator.get('_id'),
##                                                        creator.get('name')) for creator in creators])
##    if 'fields' in work:
##        for row in work.get('fields'):
##            if row.keys()[0] == '100':
##                return ' '.join([y.values()[0] for y in row['100']['subfields'] if ['a','b'].count(y.keys()[0])])




@catalog.template_filter('get_organization')
def get_organization(org_str):
    # test to if org string is an object id
    try:
        org_id = ObjectId(org_str)
        organization = mongo_storage.schema_org.Organization.find_one({
        "_id": ObjectId(org_id)})
        if organization is not None:
            return organization.get('name')
    except InvalidId:
        return org_str


@catalog.template_filter('process_value')
def process_value(value):
    output = ''
    if type(value) == str or type(value) == bool:
        return value
    if type(value) == list:
        for val in value:
            if '@id' in val:
                output += "{}<br>".format(get_entity(val['@id']))
            else:
                output += "{}<br>".format(val)
    if type(value) == dict:
        if '@id' in value:
            entity_rdf = rdflib.Graph().parse(value.get('@id'))
##            except rdflib.plugin.PluginException:
##                entity_rdf = rdflib.Graph()
            relative_url = urllib.parse.urlsplit(value.get('@id')).path
            if relative_url.startswith("/rest"):
                relative_url = relative_url.split("/rest")[-1]
            if value.get('@id').startswith("http://id.loc.gov"):
                relative_url = value.get('@id')
            for namespace in [
                BF_NS,
                SCHEMA_NS,
                rdflib.RDFS]:
                label = entity_rdf.value(
                    subject=rdflib.URIRef(value.get('@id')),
                    predicate=namespace.label)
            output += """<a href="{}">{}</a><br>""".format(
                    relative_url, label)
    return output


@catalog.template_filter('get_title')
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

@catalog.template_filter('pretty_number')
def pretty_number(number):
    return "{:,}".format(number)

@catalog.template_filter('show_schema')
def show_schema(entity):
    if '@type' in entity:
        # Is native schema.org in datastore
        if [u'AudioObject', u'Photograph', u'VideoObject',
            u'Periodical', u'Article', u'CreativeWork'].count(
            entity['@type']) > -1:
            work = OrderedDict()
            for key in sorted(entity.keys()):
                if key.startswith('@'):
                    continue

                if ['contributor', 'copyrightHolder', 'creator'].count(key) > 0:
                    mongo_id = entity['_id']
                    named_entity = mongo_storage.schema_org.Person.find_one(
                        {"_id": ObjectId(mongo_id)})
                    if named_entity is None:
                        named_entity = mongo_storage.schema_org.Organization.find_one(
                        {"_id": ObjectId(mongo_id)})
                    if named_entity is not None:
                        work[key] = named_entity.name
                    else:
                        work[key] = mongo_id
                else:
                    work[key] = entity[key]








# This should be a new Extension, very manual right now but needs to be more
# flexible data collection for other cohort testing
@catalog.route("/feedback", methods=['GET', 'POST'])
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

@catalog.route('/CoverArt/<cover_id>')
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

@catalog.route("/<entity_class>/<entity_id>")
@catalog.route("/<entity_class>/<entity_id>.<ext>")
@produces('application/json', 'application/rdf+xml', 'text/html')
def entity(entity_class, entity_id, ext='html'):
    entity_url = urllib.parse.urljoin(
        catalog.config["FEDORA_HOST"],
        "rest/{}/{}".format(entity_class, entity_id))
    try:
        entity = rdflib.Graph().parse(entity_url)
    except urllib.error.HTTPError:
        abort(404)
    entity_json = json.loads(entity.serialize(
        format='json-ld',
        context=CONTEXT).decode('utf-8'))
    output = {}
    if '@graph' in entity_json:

        for graph in entity_json['@graph']:
            if '@type' in graph and entity_class in graph['@type']:
                for key, value in graph.items():
                    if not key.startswith("http://fedora") and\
                    not key.startswith("@") and\
                    not key.startswith("http://www.w3.org"):
                        output[key] = value
    else:
        for key, value in entity_json.items():
            if not key.startswith("http://fedora") and\
                    not key.startswith("@") and\
                    not key.startswith("http://www.w3.org"):
                        output[key] = value
    if ext.startswith('html'):
        return render_template('detail.html',
                           cover_art_url=None,#cover_art_url,
                           item=None,#get_item_details(work_id),
                           entity=output,
                           search_form=BasicSearch())
    elif ext.startswith('json'):
        return jsonify(entity_json)
    elif ext.startswith('turtle'):
        return entity.serialize(format='turtle')
    elif ['xml', 'rdf'].count(ext) > -1:
        return work_rdf.serialize()



def person_content(person_id, ext='html'):
##    marc_db = getattr(mongo_storage,
##                      catalog.config["MONGODB_DATABASE"])
##    bibframe_db = mongo_storage.bibframe
##    schema_org_db = mongo_storage.schema_org
##    person_id = ObjectId(person_id)
##    # Try schema org
##    person = schema_org_db.Person.find_one(
##        {"_id": person_id})
##    if person is None:
##        person = bibframe_db.find_one(
##            {"_id": person_id})
##    if person is None:
##        abort(404)
##    person['works'] = []
##    for result in schema_org_db.CreativeWork.find(
##        {'creator': str(person_id)},
##        {'headline', 'name'}):
##            person['works'].append(result)
    person_url = urllib.parse.urljoin(
        catalog.config["FEDORA_HOST"],
        "rest/Person/{}".format(person_id))
    person_rdf = rdflib.Graph().parse(person_url)
    if ext == 'html':
        return render_template('person.html',
            person=person,
            search_form=BasicSearch())


@catalog.route("/Person/<person_id>", methods=['GET', 'POST'])
@produces('application/json', 'application/rdf+xml', 'text/html')
def person(person_id):
    if 'application/json' in request.headers['Accept']:
        return person_content(person_id, 'json')
    elif 'application/rdf+xml' in request.headers['Accept']:
        return person_content(person_id, 'xml')
    else:
        return person_content(person_id)

##@catalog.route("/Work/<work_id>", methods=['GET', 'POST'])
##@produces('application/json', 'application/rdf+xml', 'text/html')
##def work(work_id):
##    if 'application/json' in request.headers['Accept']:
##        return work_content(work_id, 'json')
##    elif 'application/rdf+xml' in request.headers['Accept']:
##        return work_content(work_id, 'xml')
##    else:
##        return work_content(work_id)


@catalog.route('/')
def home():
##    marc_db = getattr(mongo_storage,
##                      catalog.config["MONGODB_DATABASE"])
##    facets = get_facets(redis_ds=redis_ds,
##                        mongo_collection=marc_db.marc_records)
    facets = []
    return render_template('catalog.html',
                           facets=facets,
                           search_form=BasicSearch(),
                           patron=None)

def main(dev=False):
    host = '0.0.0.0'
    port = 8000
    if dev:
        catalog.run(
            host=host,
            port=port,
            debug=True)
    else:
        catalog.run(
            host=host,
            port=port)

if __name__ == '__main__':
    main(True)