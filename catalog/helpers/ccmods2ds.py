#-------------------------------------------------------------------------------
# Name:        ccmods2ds
# Purpose:     Colorado College MODS custom functions to Schema.org and BIBFRAME
#              Linked Data
#
# Author:      Jeremy Nelson
#
# Created:     2014/03/11
# Copyright:   (c) Jeremy Nelson, Colorado College 2014
# Licence:     GPL2
#-------------------------------------------------------------------------------
import datetime
import re
import xml.etree.ElementTree as etree

from catalog.mongo_datastore import generate_record_info
from catalog.mongo_datastore.ingesters import mods2ds
from catalog.solr_search import index_mods
from copy import deepcopy
from flask_fedora_commons.lib.util import RequestFailed
from flask_schema_org.models import CreativeWork
from gridfs import GridFS
import flask_bibframe.models as bf_models

RECORD_CONSTANTS = {'source': u'CoCCC',
                    'msg': u'From Colorado College MODS record',
                    'location': 'dacc'}

def add_podcast(mods, client):
    schema_org = client.schema_org
    bibframe = client.bibframe
    base_mods = mods2ds.add_base(mods, client, RECORD_CONSTANTS)



def add_oral_history(mods, client):
    schema_org = client.schema_org
    bibframe = client.bibframe
    base_mods = mods2ds.add_base(mods, client, RECORD_CONSTANTS)



PUB_INFO_VOL_RE = re.compile(r"v. (\w*)")
PUB_INFO_ISSUE_RE = re.compile(r"no. (\w*)")
PUB_INFO_ALL_RE = re.compile(r"(\[.*\])")
def add_publication(mods, client):
    """Takes a MODS etree and adds a Periodical and related PublicationIssue
    and PublicationVolume to the Mongo Datastore

    Function takes a MODS etree and based on regex matches, creates related
    PublicationIssue and PublicationVolume classes that are descendents from
    schema:CreativeWork using a regex on the title following the practice at
    CC of putting the volume and number in the title for specific values.

    Args:
        mods: MODS XML etree
        client: Mongo DB Client

    Returns:
        ObjectId: Mongo DB ObjectId for the schema.org Publication
    """
    bibframe = client.bibframe
    schema_org = client.schema_org
    title = mods.find("{{{0}}}titleInfo/{{{0}}}title".format(mods2ds.MODS_NS))
    org_title = deepcopy(title.text)
    title.text = PUB_INFO_ALL_RE.sub('', title.text).strip()
    periodical_id = mods2ds.add_periodical(mods, client, RECORD_CONSTANTS)
    publication_volume, publication_issue = None, None
    if PUB_INFO_VOL_RE.search(org_title):
        volume = PUB_INFO_VOL_RE.search(org_title).groups()[0]
        if volume is not None:
            title.text = u"{0} [v. {1}]".format(title.text, volume)
            publication_volume = mods2ds.add_publication_volume(mods,
                client,
                volume,
                RECORD_CONSTANTS)
            schema_org.CreativeWork.update({"_id": periodical_id},
                {"$push": {"hasPart": str(publication_volume)}})
    if PUB_INFO_ISSUE_RE.search(title.text):
        issue = PUB_INFO_ISSUE_RE.search(title.text).groups()[0]
        if issue is not None:
            title.text = org_title
            publication_issue = mods2ds.add_publication_issue(mods,
                client,
                issue,
                RECORD_CONSTANTS)
            if publication_volume:
                schema_org.CreativeWork.update(
                    {"_id": publication_issue},
                    {"$set": {"isPartOf": str(publication_volume)}})
                schema_org.CreativeWork.update(
                    {"_id": publication_volume},
                    {"$push": {"hasPart": str(publication_issue)}})
            else:
                schema_org.CreativeWork.update(
                    {"_id": publication_issue},
                    {"$set": {"isPartOf": str(periodical_id)}})
                schema_org.CreativeWork.update(
                    {"_id": periodical_id},
                    {"$push": {"hasPart": str(publication_volume)}})

def add_series(mods, client):
    bibframe = client.bibframe
    schema_org = client.schema_org
    series_mods = etree.Element("{{{}}}mods".format(mods2ds.MODS_NS))
    title_info = etree.Element("{{{}}}titleInfo".format(mods2ds.MODS_NS))
    title = etree.Element("{{{}}}title".format(mods2ds.MODS_NS))
    title.text = mods.text
    title_info.append(title)
    series_mods.append(title_info)
    return mods2ds.get_or_add_periodical(series_mods, client, RECORD_CONSTANTS)

def insert_mods(mods_xml, client):
    """Inserts a MODS XML datastream to MongoDB schema_org and bibframe
    collections.

    Args:
        mods_xml: Raw MODS XML
        client: Mongo Client

    Returns:
        None

    Raises:
        None
    """
    mods = etree.XML(mods_xml)
    genre = mods.find("{{{0}}}genre".format(mods2ds.MODS_NS))

    if genre is None:
        # Try genre subject
        genre = mods.find("{{{0}}}subject/{{{0}}}genre".format(mods2ds.MODS_NS))
    if genre is not None and genre.text is not None:
        if ['audio recording',
            'interview',
            'personal narratives'].count(genre.text.lower()) > 0:
            return mods2ds.get_or_add_audio(mods, client, RECORD_CONSTANTS)
        if ['newspaper', 'periodical'].count(genre.text.lower()) > 0:
            return mods2ds.get_or_add_periodical(mods, client, RECORD_CONSTANTS)
        if genre.text.lower().startswith('history'):
            return mods2ds.get_or_add_article(mods, client, RECORD_CONSTANTS)
        if genre.text.lower().startswith('photo'):
            return mods2ds.get_or_add_photograph(mods, client, RECORD_CONSTANTS)
        if genre.text.lower().startswith('pict'):
            return mods2ds.get_or_add_photograph(mods, client, RECORD_CONSTANTS)
        if genre.text.lower().startswith('thes') or \
        genre.text.lower().startswith('essay'):
            return mods2ds.add_thesis(mods, client, RECORD_CONSTANTS)
        if genre.text.lower().startswith('videorecord'):
            return mods2ds.get_or_add_video(mods, client, RECORD_CONSTANTS)

    # Next try using type_of_resource value to guess type
    type_of_resource = mods.find(
        "{{{0}}}typeOfResource".format(mods2ds.MODS_NS))
    if type_of_resource is not None and type_of_resource.text is not None:
        if type_of_resource.text.startswith('sound'):
            return mods2ds.get_or_add_audio(mods, client, RECORD_CONSTANTS)
        if type_of_resource.text.startswith('still image'):
            return mods2ds.get_or_add_photograph(mods, client, RECORD_CONSTANTS)
        if type_of_resource.text.startswith("text"):
            series = mods.find(
                "{{{0}}}relatedItem[@type='series']/{{{0}}}titleInfo/{{{0}}}title".format(
                mods2ds.MODS_NS))
            if series is not None and series.text is not None:
                series_id = add_series(series, client)
                article_id = mods2ds.get_or_add_article(mods, client, RECORD_CONSTANTS)
                client.schema_org.CreativeWork.update(
                    {"_id": article_id},
                    {"$set": {"isPartOf": str(series_id)}})
                return article_id
    # No matches, create a generic CreativeWork
    work = CreativeWork(**mods2ds.add_base(mods, client, RECORD_CONSTANTS))
    work_id = client.schema_org.CreativeWork.insert(work.as_dict())
    return work_id



def process_pid(pid, client, repository, solr_connection):
    """Takes a PID, queries Fedora Commons repository and adds to MongoDB
    bibframe database.

    Args:
        pid: String of pid
        client: Flask-MongoKit Client
        repository: Fedora Commons repository
        solr_connection: Solr connection

    Returns:
        primary_key: MongoDB id for pid
    """
    bibframe = client.bibframe
    schema_org = client.schema_org
    raw_mods = repository.api.getDatastreamDissemination(pid, 'MODS')[0]
    try:
        raw_thumbnail = repository.api.getDatastreamDissemination(pid, 'TN')[0]
    except RequestFailed:
        raw_thumbnail = None
    cover_art_grid = GridFS(bibframe)
    mongo_id = insert_mods(raw_mods, client)
    schema_org.CreativeWork.update(
        {"_id": mongo_id},
        {"$set": {"identifiers": {"pid": pid}}})
    schema_org.CreativeWork.update(
        {"_id": mongo_id},
        {"$set": {'availableAtOrFrom': 'dacc'}})
    if raw_thumbnail is not None:
        image_id = cover_art_grid.put(raw_thumbnail)
        cover_art = bf_models.CoverArt(
            annotates=str(mongo_id),
            annotationSource='http://dacc.coalliance.org/fedora/{}'.format(pid),
            assertionDate=datetime.datetime.utcnow().isoformat(),
            coverArtThumb=image_id)
        bibframe.CoverArt.insert(cover_art.as_dict())
    schema_record = schema_org.CreativeWork.find_one({"_id": mongo_id})
    index_mods(solr_connection, schema_record, raw_mods)
    return mongo_id



def get_active_pids(repository):
    """Function queries Coalliance repository and extracts all active pids

    Args:
        repository - Fedora Commons Repository

    Returns:
        list - List of active PIDS
    """
    all_pids = []











def main():
    pass

if __name__ == '__main__':
    main()
