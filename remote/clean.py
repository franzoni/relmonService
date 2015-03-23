#!/usr/bin/env python
"""
Script for cleaning RelMon report generation products
"""

import os
import argparse
import httplib
import json
import shutil
from common import utils

# TODO: move hardcoded values to config file
RELMON_PATH = (
    "/afs/cern.ch/cms/offline/dqm/ReleaseMonitoring-TEST/jdaugalaSandbox/")
SERVICE_HOST = "188.184.185.27"

# parse arguments
parser = argparse.ArgumentParser()
parser.add_argument(dest="id", help="FIXME: id help")
args = parser.parse_args()

# get RelMon
status, data = utils.httpget(SERVICE_HOST, "/requests/" + args.id)
if (status != httplib.OK):
    # FIXME: solve this problem
    exit(1)
relmon_request = json.loads(data)

# do cleaning
if (os.path.exists("requests/" + args.id)):
    shutil.rmtree("requests/" + args.id)
if (not os.path.exists(RELMON_PATH + relmon_request["name"] + '/')):
    exit()
all_categories_removed = True
for category in relmon_request["categories"]:
    cat_report_path = (
        RELMON_PATH + relmon_request["name"] + '/' + category["name"])
    if (category["name"] == "Generator" or category["HLT"] != "only"):
        if (os.path.exists(cat_report_path)):
            if (len(category["lists"]["target"]) > 0):
                shutil.rmtree(cat_report_path)
            else:
                all_categories_removed = False
    if (category["HLT"] != "no" and category["name"] != "Generator"):
        cat_report_path += "_HLT"
        if (os.path.exists(cat_report_path)):
            if (len(category["lists"]["target"]) > 0):
                shutil.rmtree(cat_report_path)
            else:
                all_categories_removed = False
if (all_categories_removed):
    shutil.rmtree(RELMON_PATH + relmon_request["name"] + '/')
