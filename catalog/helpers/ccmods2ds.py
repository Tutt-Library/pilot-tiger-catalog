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
import re
import xml.etree.ElementTree as etree

from catalog.mongo_datastore.ingesters import mods2ds
from copy import deepcopy
from flask_fedora_commons.lib.util import RequestFailed
from gridfs import GridFS


RECORD_CONSTANTS = {'source': u'CoCCC',
                    'msg': u'From Colorado College MODS record'}

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
    if ['audio recording',
        'personal narratives'].count(genre.text.lower()) > 0:
        return add_oral_history(mods, db)
    if ['newspaper', 'periodical'].count(genre.text.lower()) > 0:
        return add_publication(mods, db)
    if genre.text.lower().startswith('history'):
        return mods2ds.get_or_add_article(mods, db, RECORD_CONSTANTS)
    if genre.text.lower().startswith('photo'):
        return mods2ds.get_or_add_photograph(mods, db, RECORD_CONSTANTS)
    if genre.text.lower().startswith('pict'):
        return mods2ds.get_or_add_photograph(mods, db, RECORD_CONSTANTS)
    if genre.text.lower().startswith('thes'):
        return add_thesis(mods, db, RECORD_CONSTANTS)
    if genre.text.lower().startswith('videorecord'):
        return mods2ds.get_or_add_video(mods, db, RECORD_CONSTANTS)
    # Next try using type_of_resource value to guess type
    type_of_resource = mods.find(
        "{{{0}}}typeOfResource".format(mods2ds.MODS_NS))
    if type_of_resource.text.startswith('sound'):
        return mods2ds.get_or_add_audio(mods, client, RECORD_CONSTANTS)
    if type_of_resource.text.startswith('still image'):
        return get_or_add_photograph(mods, db, RECORD_CONSTANTS)
    if type_of_resource.text.startswith("text"):
        series = mods.find(
            "{{{0}}}relatedItem[@type='series']/{{{0}}}titleInfo/{{{0}}}title".format(
            ccmods2ds.mods2ds.MODS_NS))
        if series is not None:
            series_id = add_series(series, client, RECORD_CONSTANTS)
            article_id = mods2ds.get_or_add_article(mods, db, RECORD_CONSTANTS)
            db.schema_org.update(
                {"_id": article_id},
                {"$set": {"isPartOf": str(series_id)}})
            return ariticle_id

def process_pid(pid, client, repo):
    """Takes a PID, queries Fedora Commons repository and adds to MongoDB
    bibframe database.

    Args:
        pid: String of pid
        client: Flask-MongoKit Client
        repo: Fedora Commons repository

    Returns:
        primary_key: MongoDB id for pid
    """
    bibframe = client.bibframe
    schema_org = client.schema_org
    mods = etree.XML(repo.api.getDatastreamDissemination(pid, 'MODS')[0])
    try:
        raw_thumbnail = repo.api.getDatastreamDissemination(pid, 'TN')[0]
    except RequestFailed:
        raw_thumbnail = None
    cover_art_grid = GridFS(bibframe)
    mongo_id = insert_mods(mods, client)
    if raw_thumbnail is not None:
        image_id = cover_art_grid.put(raw_thumbnail)
        cover_art = bf_models.CoverArt(
            annotates=str(mongo_id),
            annotationSource='http://dacc.coalliance.org/fedora/{}'.format(pid),
            assertionDate=datetime.datetime.utcnow().isoformat(),
            coverArtThumb=image_id)
        setattr(cover_art,
                'recordInfo',
                generate_record_info(
                    RECORD_CONSTANTS.get('source'),
                    RECORD_CONSTANTS.get('msg')))
    return mongo_id













def main():
    pass

if __name__ == '__main__':
    main()
