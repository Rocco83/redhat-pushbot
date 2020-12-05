#!/usr/bin/python3
"""
Manage the database for the application
"""
import os
import json
import logging


#logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(level=logging.INFO)

# declare the global variable
dictdb = None


def checkuserconfiguration(chat_id, dictdb):
    """Verify if the configuration for the user is valid"""
    if dictdb is None:
        logging.error("chat_id " + chat_id + " is None")
        return False
    if chat_id not in dictdb:
        logging.info("chat_id " + chat_id + " not in db")
        return False
    if not "configured" in dictdb[chat_id]:
        logging.info("chat_id " + chat_id + " user not configure, dictdb[chat_id][configured] not in db")
        return False
    if dictdb[chat_id]["configured"] is False:
        logging.info("chat_id " + chat_id + " user has a wrong configuration, dictdb[chat_id][configured] is False")
        return False
    return True


def loadjson(dbfile):
    """Load the db file into memory"""
    if os.path.exists(dbfile):
        try:
            with open(dbfile, 'r') as dbfile_p:
                dictdb = json.load(dbfile_p)
        except json.decoder.JSONDecodeError as e:
            # TODO add debug messages, for the wrong file loaded
            dictdb = dict()
    else:
        dictdb = dict()
    return dictdb


def savejson(dbfile, dictdb):
    """Save the db memory back into file"""
    with open(dbfile, 'w') as dbfile_p:
        json.dump(dictdb, dbfile_p)
