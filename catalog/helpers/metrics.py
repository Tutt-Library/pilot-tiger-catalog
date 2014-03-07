#-------------------------------------------------------------------------------
# Name:        metrics
# Purpose:     This module provides data analytic tools for the Catalog Pull
#              Platform.
#
# Author:      Jeremy Nelson
#
# Created:     2014-02-19
# Copyright:   (c) Jeremy Nelson, Colorado College 2014
# Licence:     MIT
#-------------------------------------------------------------------------------
import datetime
import os
import re
import redis
import urlparse

from flask import Blueprint, Config, flash, g, jsonify, request, render_template
from flask import session, url_for
from flask_bibframe.models import CoverArt

blueprint_folder = os.path.abspath(os.path.dirname(__file__))
app_folder = os.path.split(blueprint_folder)[0]


metrics_config = Config(app_folder)
metrics_config.from_pyfile('catalog.cfg')

redis_ds = redis.StrictRedis(metrics_config.get('REDIS_HOST'))


def parse_logfile(log_path, redis_ds=redis_ds, tz='-0700'):
    """Takes a nginx access log, opens the file, and parses through and creates
    metrics for use by other Blueprints and apps.

    Parameters
    ----------
    log_path : str
        Full path and filename of the nginx access log
    redis_ds : StrictRedis instance
        defaults to Redis datastore for CPP's metrics
    tz : str
        Timezone offset, defaults to -0700
    """
    if not os.path.exists(log_path):
        return
    with open(log_path, 'rb') as log_file:
        access_log = log_file.readlines()
    date_pattern = "%d/%b/%Y:%H:%M:%S {}".format(tz)
    log_re = (r''
              '(\d+.\d+.\d+.\d+)\s-\s-\s' #IP address
              '\[(.+)\]\s' #datetime
              '"GET\s(.+)\s\w+/.+"\s\d+\s' #requested file
              '\d+\s"(.+)"\s' #referrer
              '"(.+)"' #user agent
             )
    for row in access_log:
        log = re.findall(log_re, row)
        if len(log) < 1:
            continue
        ip = log[0][0]
        logged_on = datetime.datetime.strptime(log[0][1],
                                               date_pattern)
        request_path = urlparse.parse_qsl(log[0][2])