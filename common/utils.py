"""
Helper functions for relmon request service.
"""

import fractions
import re
import requests
import json
import paramiko
import threading
import relmon_shared

# TODO: move hardcoded values to config file
DQM_ROOT_URL = "https://cmsweb.cern.ch/dqm/relval/data/browse/ROOT/"
HYPERLINK_REGEX = re.compile(r"href=['\"]([-./\w]*)['\"]")
CERTIFICATE_PATH = "/afs/cern.ch/user/j/jdaugala/.globus/usercert.pem"
KEY_PATH = "/afs/cern.ch/user/j/jdaugala/.globus/userkey.pem"
CMSWEB_URL = "https://cmsweb.cern.ch"
DATATIER_CHECK_URL =\
    "https://cmsweb.cern.ch/reqmgr/reqMgr/outputDatasetsByRequestName/"
CREDENTIALS_PATH = "/afs/cern.ch/user/j/jdaugala/private/credentials"
REMOTE_WORK_DIR = "/build/jdaugala/relmon"
DOWNLOADER_CMD = "cd " + REMOTE_WORK_DIR + "; ./download_DQM_ROOT.py "
REPORT_GENERATOR_CMD = ("cd /build/jdaugala/CMSSW_7_4_0_pre8\n" +
                        " eval `scramv1 runtime -sh`\n" +
                        "cd " + REMOTE_WORK_DIR +
                        "\n ./compare.py ")

credentials = {}
with open(CREDENTIALS_PATH) as cred_file:
    credentials = json.load(cred_file)


# str:CMSSW -- version . E.g. "CMSSW_7_2_"
# bool:MC -- True -> Monte Carlo, False -> data
def get_ROOT_file_urls(CMSSW, category_name):
    url = DQM_ROOT_URL
    if (category_name == "Data"):
        url += "RelValData/"
    else:
        url += "RelVal/"
    CMSSW = re.search("CMSSW_\d_\d_", CMSSW)
    # TODO: handle this error
    if (CMSSW is None):
        return None
    url += CMSSW.group() + "x/"
    r = requests.get(url,
                     verify=False,
                     cert=(CERTIFICATE_PATH, KEY_PATH))
    # TODO: handle failure
    if (r.status_code != requests.codes.ok):
        return None
    hyperlinks = HYPERLINK_REGEX.findall(r.text)[1:]
    for u_idx, url in enumerate(hyperlinks):
        hyperlinks[u_idx] = CMSWEB_URL + url
    return hyperlinks


# Given sample name returns DQMIO dataset status. If given sample
# produces DQMIO dataset then the second object of the returned
# tuple is the name of that DQMIO dataset
def get_DQMIO_status(sample_name):
    r = requests.get(DATATIER_CHECK_URL + sample_name,
                     verify=False,
                     cert=(CERTIFICATE_PATH, KEY_PATH))
    # TODO: handle request failure
    if (r.status_code == requests.codes.ok):
        if ("DQMIO" in r.text):
            rjson = json.loads(r.text.replace('\'', '\"'))
            DQMIO_string = [i for i in rjson if "DQMIO" in i][0]
            if ("None" in DQMIO_string):
                return ("waiting", None)
            return ("DQMIO", DQMIO_string)
        return ("NoDQMIO", None)
    return ("waiting", None)


def get_ROOT_name_part(DQMIO_string):
    if (DQMIO_string):
        parts = DQMIO_string.split('/')[1:]
        DS = parts[0]
        CMSSW = parts[1].split('-')[0]
        PS = parts[1].split('-')[1]
        return DS + "__" + CMSSW + '-' + PS + '-'


def sample_fraction_by_status(relmon_request, status, ignore):
    not_ignored = 0
    with_status = 0
    for category in relmon_request["categories"]:
        for sample_list in category["lists"].itervalues():
            for sample in sample_list:
                if (sample["status"] in ignore):
                    continue
                if (sample["status"] in status):
                    with_status += 1
                not_ignored += 1
    if (not_ignored == 0):
        return fractions.Fraction(0)
    return fractions.Fraction(with_status, not_ignored)


class SSHThread(threading.Thread):
    def __init__(self, command):
        threading.Thread.__init__(self)
        self.command = command

    def run(self):
        print("SSHThread")
        print(self.command)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect("cmsdev04.cern.ch",
                    username=credentials["user"],
                    password=credentials["pass"])
        (stdin, stdout, stderr) = ssh.exec_command(self.command)
        print (stdout.readlines())
        print (stderr.readlines())
        ssh.close()


def is_downloader_alive(request_id):
    return (request_id in relmon_shared.downloaders and
            relmon_shared.downloaders[request_id].isAlive())


def is_reporter_alive(request_id):
    return (request_id in relmon_shared.reporters and
            relmon_shared.reporters[request_id].isAlive())


def is_terminator_alive(request_id):
    return (request_id in relmon_shared.terminators and
            relmon_shared.terminators[request_id].isAlive())


def start_downloader(request_id):
    if (is_downloader_alive(request_id)):
        return None
    downloader = SSHThread(
        DOWNLOADER_CMD + str(request_id))
    relmon_shared.downloaders[request_id] = downloader
    downloader.start()
    return downloader


def start_reporter(request_id):
    if (is_reporter_alive(request_id)):
        return None
    reporter = SSHThread(
        REPORT_GENERATOR_CMD + str(request_id))
    relmon_shared.reporters[request_id] = reporter
    reporter.start()
    return reporter
