#-------------------------------------------------------------------------------
# Name:        filters
# Purpose:     This module provides filter functionality for searching in the
#              TIGER catalog
#
# Author:      Jeremy Nelson
#
# Created:     2014-01-31
# Copyright:   (c) Jeremy Nelson 2014
# Licence:     MIT
#-------------------------------------------------------------------------------
from solr_functions import __get_fields_subfields__
from tutt_maps import *
import datetime
import re


def slugify(value):
    """
    Converts to lowercase, removes non-word characters (alphanumerics and
    underscores) and converts spaces to hyphens. Also strips leading and
    trailing whitespace.
    """
    value = re.sub('[^\w\s-]', '', value).strip().lower()
    return re.sub('[-\s]+', '-', value)

def access_facet(**kwargs):
    set_key = kwargs.get('set_key', None)
    redis_ds = kwargs.get('redis_ds')
    mongo_collection = kwargs.get('mongo_collection')
    lib_count = mongo_collection.count()
    if set_key:
        filter_key = access_filter(set_key, redis_ds)
        online_count = redis_ds.scard(filter_key)
        lib_count = int(redis_ds.scard(set_key)) - online_count
    else:
        filter_key = "filter:access:online"
        online_count = redis_ds.scard(filter_key)
    facet =  [{"label": "In the Library",
               "icon": "glyphicon glyphicon-home",
                "count": lib_count-online_count},
              {"label": "Online",
               "icon": "glyphicon glyphicon-globe",
              "count": online_count}]
    return facet


def access_filter(set_key, redis_ds):
    """
    Function returns the redis key of intersection between the set of ids and the
    *filter:access:online* set

    :param set_key: Redis key made up of ids
    :param redis_ds: Redis Datastore
    """
    intersection_key = "{}:filter:access:online".format(set_key)
    redis_ds.sinsertstore(intersection_key, set_key, 'filter:access:online')
    return intersection_key

def classify_marc21_schema(record):
    "Classifies a MARC21 record as specific Work class based on BIBFRAME website"
    leader = record.leader
    field007 = record['007']
    field336 = record['336']
    work_class = None
    if leader[6] == 'a':
        if field007 is not None:
            test_value = field007.data[0]
            if test_value == 'a' or test_value == 'd':
                work_class = 'Map' # http://schema.org/Map
            elif test_value == 'h': # Microfilm
                work_class = 'Photograph' # http://schema.org/Photograph
            elif ['m', 'v'].count(test_value) > 0:
                work_class = 'VideoObject' # http://schema.org/VideoObject
        else:
            # Book is the default for Language Material
            work_class =  'Book'
    elif leader[6] == 'e' or leader[6] == 'f':
        # Map is the default
        work_class = 'Map'
        if field007 is not None:
            if field007.data[0] == 'r':
                work_class = 'Dataset'
    elif leader[6] == 'g':
        work_class = 'Photograph'
    elif leader[6] == 'i':
        work_class = 'AudioObject' # http://schema.org/AudioObject
    elif leader[6] == 'j':
        work_class = 'MusicRecording'
    elif leader[6] == 'k':
        work_class = 'Photograph'
    elif leader[6] == 'm':
        work_class = 'SoftwareApplication'
    if work_class is None:
        work_class = 'CreativeWork'
    return work_class


def get_facets(**kwargs):
    facets = [{"name":"Access",
               "items": access_facet(**kwargs)},
              {"name": "Location",
               "items": location_facet(**kwargs)},
              {"name": "Topics",
               "items": topic_facet(**kwargs)}]
    return facets

def sub_location_facet(**kwargs):
    """
    Function iterates through Music Library, Government Documents, and Special
    Collections to create a location subcodes.
    """
    facet = []
    total_count = 0
    facet_count = {}
    # Should be GovDocs, MusicLibrary, or SpecialCollections
    sub_collection_name = kwargs.get('name')
    redis_ds = kwargs.get('redis_ds')
    location_set_key = "filter:location:{}".format(sub_collection_name)
    location_label_key = "filter:location:{}:labels".format(sub_collection_name)
    for location_key in redis_ds.smembers(location_set_key):
        count = redis_ds.scard(location_key)
        label = redis_ds.hget(location_label_key, location_key)
        if label in facet_count:
            facet_count[label] += count
        else:
            facet_count[label] = count
    for row in facet_count.keys():
        total_count += facet_count[row]
        facet.append({"label": row,
                      "count": facet_count[row]})
    return facet, total_count

def location_facet(**kwargs):
    set_key = kwargs.get('set_key', None)
    redis_ds = kwargs.get('redis_ds')
    mongo_collection = kwargs.get('mongo_collection')
    sub_locations = ["GovDocs", "MusicLibrary", "SpecialCollections"]
    facet = []
    special_collect_facet, special_collect_count = sub_location_facet(
        name="SpecialCollections",
        redis_ds=redis_ds)
    facet.append({"label": "Special Collections",
                  "count": special_collect_count,
                  "children": special_collect_facet})
    gov_docs_facet, gov_docs_count = sub_location_facet(name="GovDocs",
                                                        redis_ds=redis_ds)
    facet.append({"label": "Government Documents",
                  "count": gov_docs_count,
                  "children": gov_docs_facet})
    music_lib_facet, music_lib_count = sub_location_facet(name="MusicLibrary",
                                                          redis_ds=redis_ds)
    facet.append({"label": "Music Library",
                  "count": music_lib_count,
                  "children": music_lib_facet})
    for location_key in redis_ds.hkeys("filter:location:labels"):
        if redis_ds.sismember("filter:location:GovDocs",
                              location_key):
            continue
        if redis_ds.sismember("filter:location:MusicLibrary",
                              location_key):
            continue
        if redis_ds.sismember("filter:location:SpecialCollections",
                              location_key):
            continue
        if redis_ds.scard(location_key) > 20:
            facet.append({"label": redis_ds.hget("filter:location:labels",
                                                 location_key),
                          "count": redis_ds.scard(location_key)})

    facet = sorted(facet, key=lambda x: x.get('count'), reverse=True)
    return facet


def location_filter(set_key, redis_ds):
    return []

def topic_facet(**kwargs):
    facet = []
    redis_ds = kwargs.get('redis_ds')
    start = kwargs.get('start', 0)
    end = kwargs.get('end', 24)
    top_25 = redis_ds.zrevrange("filter:subjects:sorted",
                                start,
                                end,
                                withscores=True)
    for row in top_25:
        filter_key = row[0]
        facet.append({"label": redis_ds.hget("filter:subjects:labels",
                                             filter_key),
                      "count": int(row[1])})
    return facet


def create_access_filter(mongo_db,
                         redis_ds):
    """
    Function creates a set of records that create an Access filter,
    currently only creates online access filter. Stores results in
    the redis key *filter:access:online*.

    :param mongo_db: Mongo Collection
    :param redis_ds: Redis Datastore
    """
    tutt_records = mongo_db.records
    all_online = tutt_records.find(
    {
        "fields.994.subfields.a": { "$in": ["ewww", "ewwwd", "ewwwp", "ewwwn"] }
    },
    {
        "_id"
    })
    for rec in all_online:
        mongo_id = str(rec.get('_id'))
        if not redis_ds.sismember('filter:access:online', mongo_id):
            redis_ds.sadd('filter:access:online', mongo_id)


def create_location_filter(mongo_collection,
                           redis_ds):
    for i,row in enumerate(mongo_collection.find()):
        mongo_id = str(row.get('_id'))
        output = __get_fields_subfields__(row, ['994'], ['a'])
        if not i%100:
            sys.stderr.write(".")
        if not i%1000:
            sys.stderr.write(str(i))
        for location_code in output:
            label = FULL_CODE_MAP.get(location_code)
            if type(label) != str:
                not_found.append({"{} code unknown for {}".format(
                    location_code,
                    mongo_id)})
                continue
            location_key = "filter:location:{}".format(slugify(label))
            if not redis_ds.sismember(location_key, mongo_id):
                redis_ds.sadd(location_key, mongo_id)
            if not redis_ds.hexists("filter:location:codes",
                                    location_code):
                redis_ds.hset("filter:location:codes",
                              location_code,
                              location_key)
            if not redis_ds.hexists("filter:location:labels",
                                    location_key):
                redis_ds.hset("filter:location:labels",
                              location_key,
                              label)