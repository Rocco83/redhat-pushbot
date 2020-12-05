#!/usr/bin/python3
"""
Main file to run the Bot and the Red Hat API poller
"""
import concurrent.futures
import time
import bot
import rhapi
import config
import db

# global variable
db.dictdb = db.loadjson(config.dbfile)

if __name__ == "__main__":
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # start the Telegram Bot thread
            botthread = executor.submit(bot.run)
            # start the Red Hat API thread
            pollerthread = executor.submit(rhapi.casepoller)
            # must be able to catch ctrl+c
            while (not (botthread.done() and pollerthread.done())):
                time.sleep(10)
                if(pollerthread.done()):
                    print("pollerthread closed, exiting botthread")
                    botthread.cancel()
                if(botthread.done()):
                    print("botthread closed, exiting pollerthread")
                    pollerthread.cancel()
    except KeyboardInterrupt:
        botthread.cancel()
        pollerthread.cancel()

# TODO implement stack trace from threads, to quit/restart the daemon
