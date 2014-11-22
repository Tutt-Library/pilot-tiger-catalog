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
import sys
import time
import urllib

from search.forms import BasicSearch, FilterResults
from flask import abort, Flask, g, jsonify, redirect, render_template, request
from flask import Response, url_for

from flask_negotiate import produces
from flask.ext.elastic import Elastic

try:
    from flask_bfe import bfe
except ImportError:
    sys.path.append("E:\\2014\\flask-bfe")
    from flask_bfe import bfe
try:
    from flask_fedora_commons import Repository
except ImportError:
    sys.path.append("C:\\Users\\jernelson\\Development\\flask-fedora")
    from flask_fedora_commons import Repository

try:
    from bibframe_catalog.catalog.helpers.search import keyword_search, resource_search
except ImportError:
    sys.path.append("E:\\2014\\bibframe-catalog")
    from catalog.helpers.search import keyword_search, resource_search
##from helpers.filters import get_facets
##from helpers import metrics
##from patron import patron, login_manager
from rdflib import Graph

catalog = Flask(__name__)
catalog.config.from_pyfile('catalog.cfg')
catalog.register_blueprint(bfe, url_prefix='/bfe')
repository = Repository(catalog)
search = Elastic(catalog)
##catalog.register_blueprint(patron)

##redis_ds = redis.StrictRedis(catalog.config['REDIS_HOST'],
##                             catalog.config['REDIS_PORT'])

BF_NS = rdflib.Namespace('http://bibframe.org/vocab/')
SCHEMA_NS = rdflib.Namespace('http://schema.org/')
BF_GRAPH = rdflib.Graph().parse('http://bibframe.org/vocab/')

CONTEXT={
    "@vocab": "http://bibframe.org/vocab/",
##    "fcrepo": "http://fedora.info/definitions/v4/repository#",
##    "fedora": "http://fedora.info/definitions/v4/rest-api#",
    "@language": "en"}

@catalog.template_filter('generate_cover_art_img')
def generate_cover_art_img(entity_id):
    cover_art_result = search.search(
        index='bibframe',
        doc_type='CoverArt',
        body={
		"query": {
			"filtered": {
				"filter": {
					"term": {
						"bf:coverArtFor": entity_id
						}
					}
				}
			}
		}
	)
    if cover_art_result.get('hits').get('total') > 0:
        return """<img src="{}" class="img-responsive img-thumbnail">""".format(
            url_for('cover_art', cover_id=cover_art_result.get("_id")))
    return ''








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
        try:
            label = entity_rdf.value(subject=rdflib.URIRef(entity_id),
                                     predicate=namespace.label)
        except:
            if label is not None:
                return html.format(
                    relative_url,
                    label)
        try:
            title = entity_rdf.value(subject=rdflib.URIRef(entity_id),
                                     predicate=namespace.titleValue)
        except:
            title = None
        if title is not None:
            return html.format(
                relative_url,
                title)
    return relative_url


@catalog.template_filter('get_creators')
def get_creators(creators):
    output = ''
    if type(creators) == list:
        for creator in creators:
            if '@id' in creator:
                output += "{},".format(get_entity(creator.get('@id')))
            else:
                entity = search.get_source(id=creator, index='bibframe')
                output += "{},".format(get_heading(entity))
    if output.endswith(","):
        output = output[:-1]
    return output

@catalog.template_filter('get_heading')
def get_heading(entity):
    def get_value(entity_property):
        if type(entity_property) == list:
            # Return first item in the list
            return entity_property[0]
        elif type(entity_property) == str:
            return entity_property
        else:
            return str(entity_property)
    def get_subject_value(entity_property):
        title = str(entity_property)
        search_result = search.get(id=entity_property[0], index='bibframe')
        if search_result:
            title = search_result['_source'].get('bf:titleValue')[0]
            if 'bf:subtitle' in search_result['_source']:
                title += " {}".format(
                    search_result['_source'].get('bf:subtitle')[0])
        return title

    if 'bf:title' in entity:
        return get_value(entity['bf:title'])
    if 'bf:titleValue' in entity:
        return get_value(entity['bf:titleValue'])
    if 'bf:instanceTitle' in entity:
        return get_subject_value(entity['bf:instanceTitle'])
    if 'bf:workTitle' in entity:
        return get_subject_value(entity['bf:workTitle'])
    if 'bf:name' in entity:
        return get_value(entity['bf:name'])
    if 'bf:label' in entity:
        return get_value(entity['bf:label'])
    if 'bf:classificationNumber' in entity:
        return get_value(entity['bf:classificationNumber'])



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
    if search.exists(id=value, index='bibframe'):
        result = search.get_source(id=value, index='bibframe')
        return """<a href="{}">{}</a>""".format(
            url_for('uuid', uuid=value[0], ext='html'),
            get_heading(result)
        )
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
            try:
                entity_rdf = rdflib.Graph().parse(value.get('@id'))
            except ImportError:
                return """<a href="{0}">{0}</a>""".format(value.get('@id'))
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

def entity_output(graph):
    output = {}
    for key, value in graph.items():
        if not key.startswith("http://fedora") and\
        not key.startswith("@") and\
        not key.startswith("http://www.w3.org"):
            label = BF_GRAPH.value(
                subject=rdflib.URIRef("http://bibframe.org/vocab/{}".format(key)),
                predicate=rdflib.URIRef(
                'http://www.w3.org/2000/01/rdf-schema#label'))
            print(key, label)
            if label is not None:
                output[str(label)] = value
            else:
                output[key] = value
    output = OrderedDict(sorted(output.items()))
    return output

@catalog.route("/search", methods=['POST'])
def search_index():
    term = request.form['q']
    page = request.form['page']
    result = search.search(q=term, index='bibframe', doc_type='Instance', from_=int(page))
    if result['hits'].get('total') > 0:
        return jsonify({"hits": result['hits'], "page": int(page)})
    return jsonify()


@catalog.route("/<entity_class>/<entity_id>")
@catalog.route("/<entity_class>/<entity_id>.<ext>")
@produces('application/json', 'application/rdf+xml', 'text/html')
def entity(entity_class, entity_id, ext='html'):
    entity = None
    for workspace in catalog.config.get(
        "WORKSPACES",
        ["bibframe", "schema"]):
        entity_url = '/'.join([catalog.config["FEDORA_HOST"],
                               'rest',
                               workspace,
                               entity_class,
                               entity_id])
        try:
            entity = rdflib.Graph().parse(entity_url)
            break
        except urllib.error.HTTPError:
            pass
    # Try without a workspace
    if entity is None:
        entity_url = '/'.join([catalog.config["FEDORA_HOST"],
                               'rest',
                               entity_class,
                               entity_id])
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
                output = entity_output(graph)

    else:
        output = entity_output(entity_json)
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


@catalog.route('/<uuid>')
@catalog.route("/<uuid>.<ext>")
def uuid(uuid, ext='html'):
    entity = search.get_source(id=uuid, index='bibframe')
    if ext.startswith("htm"):
        return render_template('detail.html',
                               cover_art_url=None,#cover_art_url,
                               item=None,#get_item_details(work_id),
                               entity=entity,
                               search_form=BasicSearch())
    elif ext.startswith("js"):
        return jsonify(entity)
    else:
        return "Entity is\n{}".format(entity)

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