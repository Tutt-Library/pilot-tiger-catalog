#-------------------------------------------------------------------------------
# Name:        filters
# Purpose:     This module provides facets and other filters for the TIGER
#              catalog
#
# Author:      Jeremy Nelson
#
# Created:     2014-01-26
# Copyright:   (c) Jeremy Nelse 2014
# Licence:     Apache 2
#-------------------------------------------------------------------------------
import redis
from pymongo import MongoClient

TIGER_REDIS = redis.StrictRedis() # Uses Redis Datastore for filter access

class Filter(object):

    def __init__(self, **kwargs):
        self.name = kwargs.get('name', None)
        self.subfilters = kwargs.get('subfilters', [])


FACETS = [Access]

def main():
    pass

if __name__ == '__main__':
    main()
