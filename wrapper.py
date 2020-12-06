#!/usr/bin/python3
"""
Main file to run the Bot and the Red Hat API poller
"""
import concurrent.futures
import threading
import time
import bot
import rhapi
import config
import db

# global variable
db.dictdb = db.loadjson(config.dbfile)

if __name__ == "__main__":
    event = threading.Event()
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # start the Telegram Bot thread
            botthread = executor.submit(bot.run)
            # start the Red Hat API thread
            pollerthread = executor.submit(rhapi.casepoller, event)
            # TODO must be able to catch ctrl+c
            while (not (botthread.done() and pollerthread.done())):
                time.sleep(10)
                if(pollerthread.done()):
                    print("pollerthread closed, exiting botthread")
                    event.set() # set the event to be catched in the threads
                    botthread.cancel()
                if(botthread.done()):
                    print("botthread closed, exiting pollerthread")
                    event.set() # set the event to be catched in the threads
                    pollerthread.cancel()
    except KeyboardInterrupt:
        event.set() # set the event to be catched in the threads
        botthread.cancel()
        pollerthread.cancel()

# TODO implement stack trace from threads, to quit/restart the daemon
