#-------------------------------------------------------------------------------
# Name:        mongodb
# Purpose:     Module provides access to a MongoDB server
#
# Author:      Jeremy Nelson
#
# Created:     2014-01-22
# Copyright:   (c) Jeremy Nelson, Colorado College 2014
# Licence:     MIT
#-------------------------------------------------------------------------------

from bson.objectid import ObjectId
from pymongo.errors import InvalidId

def get_marc(db, marc_id):
    """
    Function takes a MongoDB instance and a marc_id, returns Null or Dictionary
    of the MARC record.

    :param db: Flask-MongoKit DB
    :param marc_id: Mongo ID of MARC record, can take either string of hash or
                    ObjectId
    """
    marc_records = db.marc_records
    try:
        if type(marc_id) != ObjectId:
            marc_id = ObjectId(marc_id)
        return marc_records.find_one({'_id': marc_id})
    except InvalidId, e:
        return

