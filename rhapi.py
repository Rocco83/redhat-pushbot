#!/usr/bin/python3
"""
This is the Red Hat Customer Portal API poller, to query for the cases
"""
import sys
import urllib.request
from pprint import pformat
import concurrent.futures
import logging
import time
import xmltodict
import bot
import config
import db

#logging.basicConfig(
#    format='%(asctime)s %(levelname)-8s %(message)s',
#    level=logging.DEBUG,
#    datefmt='%Y-%m-%d %H:%M:%S')
#logger = logging.getLogger(__name__)
logger = logging.getLogger('RedHatAPI')
formatter = logging.Formatter(
    '%(asctime)s (%(filename)s:%(lineno)d %(threadName)s) %(levelname)s - %(name)s: "%(message)s"'
)
console_output_handler = logging.StreamHandler(sys.stderr)
console_output_handler.setFormatter(formatter)
logger.addHandler(console_output_handler)

logger.setLevel(logging.ERROR)
logger.setLevel(logging.DEBUG)



class HTTPLoginFailed(Exception):
    """Declare the exception to be used outside of this module"""
    def __init__(self, username):
        self.username = username
        Exception.__init__(self, 'Wrong username or password exception for user %s' % username)


def casepoller(event):
    """
    Main class, iterate over the database.
    Open a thread for each user configured.
    Each thread will modify the database.
    A final version of the database will be written on the disk.
    """

    while True:
        try:
            logger.info("case poller started")
            if event.is_set():
                logger.info("event received, stopping the thread")
                break
            pollerthread = concurrent.futures.ProcessPoolExecutor()
            db.dictdb = dict(pollerthread.map(casesiterator, db.dictdb.items()))
            pollerthread.shutdown(wait=True)
            # race condition, what if we save a new user whike this function is running?
            db.savejson(config.dbfile, db.dictdb)
            logger.info("case poller standby for the next iteration, sleeping for " + str(config.rhpollertimeout) + " seconds")
            time.sleep(config.rhpollertimeout)
        except:
            e = sys.exc_info()[0]
            logger.error("error: " + e)

def casesiterator(chat_id_tuple):
    """
    Per user thread.
    The thread will be evaluated and for every case the parsing will be started
    """
    # the tuple must be splittted between the chat_id (user id in telegram) and the associated configuration dict
    chat_id, user_dict = chat_id_tuple
    logger.info("chatid: " + chat_id + ", parsing the following database\n" + pformat(chat_id_tuple, depth=3))
    # verify that the user has a valid configuration
    if not db.checkuserconfiguration(chat_id, db.dictdb):
        logger.info("chatid: " + chat_id + ", no valid configuration for the user")
    else:
        # if notify index is not set, assign the default value
        if not "notify" in user_dict:
            user_dict["notify"] = ["Associate"]
        # start the real parsing, checking if cases index is set
        # once a user add himself, the index is *not* set
        if "cases" in user_dict and user_dict["cases"] is not None:
            # extract the case number and the relative hash (xml dump) associated
            for casenumber, casedump in user_dict["cases"].items():
                logger.info("chatid: " + chat_id + ", case " + casenumber + ", a valid configuration has been found. The case parsing is going to be executed.")
                # case is an hash, the key is the case number, the value is an hash.
                # the hash has None value once added, the case xml afterward
                # parsecase function will be called for every case
                user_dict["cases"][casenumber] = parsecase(chat_id, casenumber, casedump, user_dict["credentials"], user_dict["notify"])
        else:
            logger.info("chatid: " + chat_id + ", no cases hash has been found for the user")

    # always return a value, which can be the original one or the modified one
    return str(chat_id), user_dict


def parsecase(chat_id, casenumber, storedcase, credentials, notify):
    """
    case parser.
    The online case will be extracted and compared with the saved case.
    If there is a new comment matching the requirements, this will be sent.
    In any case return the dict to replace the current value.
    """
    logger.debug("chatid: " + chat_id + ", case " + casenumber + ", parsing started.")

    # extract the last comment dict
    onlinecase = loadcase(casenumber, credentials, notify)
    # check if there is a comment
    if onlinecase is None:
        # there are still no comments, continue
        logger.info("chatid: " + chat_id + ", case " + casenumber + ", no comment has been made in the case. Skipping further checks.")
        return None
    # lastModifiedDate must be of the comment, not of the case. Otherwise every comment will trigger a notification.
    if storedcase is not None and 'lastcomment' in storedcase and onlinecase["lastcomment"].get('lastModifiedDate') == storedcase["lastcomment"].get('lastModifiedDate'):
        # if the comment retireve is the same stored, just continue to the next case
        logger.info("chatid: " + chat_id + ", case " + casenumber + ", the saved comment is the same as the latest comment in the Customer Portal")
        return storedcase

    if "text" in onlinecase['lastcomment']:
        caseupdate = onlinecase['lastcomment'].get("text")
        logger.info(caseupdate)
        logger.info("chatid: " + chat_id + ", case " + casenumber + ", sending update via telegram")
        caseupdatestrip = (caseupdate[:1000] + '\n[...]') if len(caseupdate) > 1000 else caseupdate
        # notify the user via telegram
        bot.pushmessage(chat_id, "Case " + onlinecase.get('@caseNumber') + "\n" + onlinecase.get('summary') + "\n"  + onlinecase.get('status') + "\n```\n" + caseupdatestrip + "\n```")
        logger.debug("chatid: " + chat_id + ", case " + casenumber + ", the update has been sent via telegram")
    else:
        # TODO throw an exception
        return None

    # return the updated case dict
    return onlinecase


def loadcase(case, credentials, notify):
    """
    Load the case from Red Hat Customer Portal and parse it according to the user configuration
    """
    # set the url for the case retrieval
    url = config.fqdn + "/rs/cases/" + case

    # request the updated online configuration
    res_body = rhquery(credentials["username"], credentials["password"], url)

    # create a dict from the XML
    case_dict = xmltodict.parse(res_body.decode('utf-8'))
    logger.debug("loadcase() case: " + case + ", case_dict\n" + pformat(case_dict))

    # if ["comments"]["comment"] key does not exist, the first reply is still missing
    if case_dict['case']['comments'] is None or not "comment" in case_dict['case']['comments']:
        # return None to continue the parsing without this case number
        return None

    # extract the comments from the structure
    # the expected output is a list of OrderedDict in ['case']['comments']['comment']
    # the order is newer to older comments
    comments = case_dict['case']['comments']['comment']

    # if only one element is found, an OrderedDict is returned.
    # if more then one element is found, a List is returned.
    # fixing the type always to list.
    if(type(comments) is not list):
        comments = list([comments])

    # initialize the return value for the iteration
    lastcomment = dict()
    # create an iterator -- next is needed to get the first index
    commentsiter = iter(comments)

    # iterate over the retrieved dict
    try:
        while True:
            # extract the next comment from the structure
            lastcomment = next(commentsiter)
            # check if we have a real comment, on the first iteration no
            if lastcomment.get('@id') is None:
                logger.info("case " + case + ", empty")
                continue
            # notify is a list, default value ["Associate"]
            # check if the Type that posted the comment is matching the deired one
            if lastcomment.get('createdByType') in notify:
                # the comment is matching, exiting from the loop
                logger.info("case " + case + ", found comment id " + lastcomment["@id"])
                break
            else:
                # extract the next comment from the structure and restart the loop
                logger.debug("case " + case + ", NOT suitable comment id " + lastcomment["@id"])
    # This exception means that there are no further comments in the iter
    except StopIteration:
        logger.info("case " + case + ", no suitable comments has been found, exiting from the function")
        return None
    # a general exception handler
    except Exception as e:
        logger.error("case " + case + ", Exception parsing the comments, error:\n" + repr(e) + "\ncomments array:\n" + repr(comments) + "\nlastcomment parsed:\n" + repr(lastcomment))

    # create the return value
    complete_case = case_dict['case']
    complete_case['lastcomment'] = lastcomment

    return complete_case


def rhquery(auth_user, auth_pass, url):
    """
    Do the effective query to Red Hat Customer Portal, and retrieve the output
    The result xml will be returned
    """
    # If you would like to request Authorization header for Digest Authentication,
    # replace HTTPBasicAuthHandler object to HTTPDigestAuthHandler
    passman = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    passman.add_password(None, url, auth_user, auth_pass)
    authhandler = urllib.request.HTTPBasicAuthHandler(passman)
    opener = urllib.request.build_opener(authhandler)
    urllib.request.install_opener(opener)

    # get the case xml
    try:
        res = urllib.request.urlopen(url)
    except urllib.error.HTTPError as e:
        raise HTTPLoginFailed(auth_user)
    res_body = res.read()

    return res_body
