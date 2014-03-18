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

from catalog.mongo_datastore.ingesters import mods2ds

RECORD_CONSTANTS = {'source': u'CoCCC',
                    'msg': u'From Colorado College MODS record'}

def add_oral_history(mods, client):
    schema_org = client.schema_org
    bibframe = client.bibframe
    base_mods = mods2ds.add_base(mods, client, RECORD_CONSTANTS)


PUB_INFO_RE = re.compile(r"v. (\w*) no. (\w*)")
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
        ObjectId: Mongo DB ObjectId for the schema.org Thesis
    """
    bibframe = client.bibframe
    schema_org = client.schema_org
    periodical_id = mods2ds.add_periodical(mods, client, RECORD_CONSTANTS)
    title = mods.find("{{{0}}}titleInfo/{{{0}}}title".format(mods2ds.MODS_NS))
    if PUB_INFO_RE.search(title.text):
        publication_volume, publication_issue = None, None
        volume, issue = PUB_INFO_RE.search(title.text).groups()
        if volume:
            publication_volume = mods2ds.add_publication_volume(mods,
                client,
                volume,
                RECORD_CONSTANTS)
            schema_org.CreativeWork.update({"_id": periodical_id},
                {"$push": {"hasPart": str(publication_volume)}})
        if issue:
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

def insert_mods(db, mods_xml, redis_ds):
    """Inserts a MODS XML datastream to MongoDB schema_org and bibframe
    collections.

    Args:
        db: Flask-MongoKit Database
        mods_xml: Raw MODS XML
        redis_ds: Redis Datastore
        record_constants: Dictionary of

    Returns:
        None

    Raises:
        None
    """
    mods = etree.XML(mods_xml)
    genre = mods.find("{{{0}}}genre".format(MODS_NS))

    if genre is None:
        # Try genre subject
        genre = mods.find("{{{0}}}subject/{{{0}}}genre".format(MODS_NS))
    if ['Audio recording', 'Personal narratives'].count(genre.text) > -1:
        return add_oral_history(mods, db)
    if genre.text.startswith('newspaper'):
        return add_publication(mods, db, RECORD_CONSTANTS)
    if genre.text.startswith('theses'):
        return add_thesis(mods, db, RECORD_CONSTANTS )

def main():
    pass

if __name__ == '__main__':
    main()
