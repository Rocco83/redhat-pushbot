#!/usr/bin/python3
"""
This is the Telegram poller, to interact with the users
"""
import logging
import time # needed for timeout on pushmessage
import timeout_decorator # needed for timeout on pushmessage
import telebot
import rhapi
import config
import db


# setup the bot
bot = telebot.TeleBot(config.TOKEN, threaded=False)

# define the log level on the console
logger = telebot.logger
#telebot.logger.setLevel(logging.INFO)
telebot.logger.setLevel(logging.DEBUG)
#telebot.logger.FileHandler('tickets-pushbot.log')


# Enable saving next step handlers to file "./.handlers-saves/step.save".
# Delay=2 means that after any change in next step handlers (e.g. calling register_next_step_handler())
# saving will hapen after delay 2 seconds.
bot.enable_save_next_step_handlers(delay=2)

# Load next_step_handlers from save file (default "./.handlers-saves/step.save")
# WARNING It will work only if enable_save_next_step_handlers was called!
bot.load_next_step_handlers()


@timeout_decorator.timeout(10, use_signals=False, timeout_exception=TimeoutError, exception_message="Timed out sending the message on Telegram")
def pushmessage(chat_id, msg):
    """
    Push the message sent from outside to the needed chat_id
    """
    bot.send_message(chat_id, msg, parse_mode="MarkdownV2")


@bot.message_handler(commands=['start'])
def start_command(message):
    """/start telegram command handler"""
    bot.send_message(
        message.chat.id,
        'This bot will help you out monitoring\n' +
        'Red Hat cases.\n' +
        'To get help press /help.'
    )

@bot.message_handler(commands=['help'])
def help_command(message):
    """/help telegram command handler"""
    bot.send_message(
        message.chat.id,
        'To setup the bot, run /setup\n' +
        'To list the current monitored caes, run /list\n' +
        'To add a case to monitor, run /add [casenumber]\n' +
        'To remove a case from monitor, run /remove [casenumber]\n' +
        'To change the notification kind, run /notification\n' +
        'To show your telegram ID, run /whoami. This is needed for debug.'
    )


@bot.message_handler(commands=['setup'])
def setup_command(message):
    """
    /setup telegram command handler
    create/update the user configuration
    expect to get: username
    next step: process_username_step
    """
    msg = bot.reply_to(message, """\
You need to introduce a valid Red Hat customer portal username and password.
It' recommended to make use of a service user, with read only grants for cases through the "Case Group" functionalities.
Provide now the username.
""")
    bot.register_next_step_handler(msg, process_username_step)


def process_username_step(message):
    """
    /setup telegram command handler
    create/update the user configuration
    expect to get: password
    next step: process_password_step
    """
    try:
        chat_id = str(message.chat.id)
        username = message.text
        # in this step, is allowed to not have the dict in place, let's create it
        if chat_id not in db.dictdb:
            db.dictdb[chat_id] = dict()
        if not "credentials" in db.dictdb[chat_id]:
            db.dictdb[chat_id]["credentials"] = dict()
        # configure the username
        db.dictdb[chat_id]["credentials"]["username"] = username
        # inform the user to provide the password
        msg = bot.reply_to(message, 'Thanks. Provide now the password')
        bot.register_next_step_handler(msg, process_password_step)
    except Exception as e:
        logger.exception(message.text + repr(e))
        bot.reply_to(message, 'oooops')


def process_password_step(message):
    """
    /setup telegram command handler
    create/update the user configuration
    expect to get: nothing
    next step: setup completed or process_username_step if an exception on authentication is raised
    """
    try:
        chat_id = str(message.chat.id)
        password = message.text
        db.dictdb[chat_id]["credentials"]["password"] = password

        url = config.fqdn + "/rs/cases/"
        # verify if the username and password are valid
        rhapi.rhquery(db.dictdb[chat_id]["credentials"]["username"], db.dictdb[chat_id]["credentials"]["password"], url)

        msg = bot.reply_to(message, 'The account ' + db.dictdb[chat_id]["credentials"]["username"] + ' has been tested and registered successfully\nThe last update for this case will come sortly.')
        db.dictdb[chat_id]["configured"] = True
        db.savejson(config.dbfile, db.dictdb)

    except rhapi.HTTPLoginFailed as e:
        db.dictdb[chat_id]["configured"] = False
        msg = bot.reply_to(message, 'The account ' + db.dictdb[chat_id]["credentials"]["username"] + ' has failed with the provided password')
        bot.register_next_step_handler(msg, process_username_step)
        pass
    except Exception as e:
        logger.exception(repr(message) + repr(e))
        bot.reply_to(message, 'oooops')

@bot.message_handler(commands=['add'])
def add_command(message):
    """
    /add telegram command handler
    add a case to be monitored by the bot
    expect to get: case number
    next step: process_addcase_step
    """
    chat_id = str(message.chat.id)
    if not db.checkuserconfiguration(chat_id, db.dictdb):
        msg = bot.reply_to(message, "Proceed with /setup first, your account is not configured for id " + str(message.chat.id))
        logger.exception("db: " + repr(db.dictdb))
        return
    msg = bot.reply_to(message, """\
Specify the case number that you want to add to monitoring (only the case number, not the URL)
""")
    bot.register_next_step_handler(msg, process_addcase_step)


def process_addcase_step(message):
    """
    /add telegram command handler
    add a case to be monitored by the bot
    expect to get: nothing
    next step: case added or process_addcase_step if an exception is raised
    """
    try:
        chat_id = str(message.chat.id)
        case = message.text
        # verify that a number has been entered, otherwise get back to process_addcase_step
        if not case.isdigit():
            msg = bot.reply_to(message, 'The case must be a number. Please paste just the case number.')
            bot.register_next_step_handler(msg, process_addcase_step)
            return

        url = config.fqdn + "/rs/cases/" + case
        # verify if the username can access the case number specified
        rhapi.rhquery(db.dictdb[chat_id]["credentials"]["username"], db.dictdb[chat_id]["credentials"]["password"], url)

        # create the needed indexes if missing
        if not "cases" in db.dictdb[chat_id] or type(db.dictdb[chat_id]["cases"]) is not dict:
            db.dictdb[chat_id]["cases"] = dict()

        if not case in db.dictdb[chat_id]["cases"]:
            db.dictdb[chat_id]["cases"][case] = None
        else:
            bot.reply_to(message, 'The case ' + case + ' is already monitored')
            return
        db.savejson(config.dbfile, db.dictdb)

        bot.send_message(chat_id, 'The case ' + case + ' has been tested and registered successfully')

    except rhapi.HTTPLoginFailed as e:
        msg = bot.reply_to(message, 'The case ' + case + ' is not visible with the current account. Please enter a valid case')
        bot.register_next_step_handler(msg, process_addcase_step)
    except Exception as e:
        logger.exception(message.text + repr(e))
        bot.reply_to(message, 'oooops')


@bot.message_handler(commands=['remove'])
def remove_command(message):
    """
    /remove telegram command handler
    remove a case from the monitoring of the bot
    expect to get: case number
    next step: process_removecase_step
    """
    chat_id = str(message.chat.id)
    if not db.checkuserconfiguration(chat_id, db.dictdb):
        msg = bot.reply_to(message, "Proceed with /setup first, your account is not configured for id " + str(message.chat.id))
        logger.exception("db: " + repr(db.dictdb))
        return
    msg = bot.reply_to(message, """\
Specify the case number that you want to remove to monitoring (only the case number, not the URL)
""")
    bot.register_next_step_handler(msg, process_removecase_step)


def process_removecase_step(message):
    """
    /remove telegram command handler
    remove a case from the monitoring of the bot
    expect to get: nothing
    next step: case removed or process_removecase_step if an exception is raised
    """
    chat_id = str(message.chat.id)
    case = message.text
    # verify that a number has been entered, otherwise get back to process_removecase_step
    if not case.isdigit():
        msg = bot.reply_to(message, 'The case must be a number. Please paste just the case number.')
        bot.register_next_step_handler(msg, process_removecase_step)
        return

    # create the index if missing
    if not "cases" in db.dictdb[chat_id]:
        db.dictdb[chat_id]["cases"] = dict()

    if case in db.dictdb[chat_id]["cases"]:
        db.dictdb[chat_id]["cases"].pop(case)
    else:
        bot.reply_to(message, 'The case ' + case + ' was not monitored')
        return
    db.savejson(config.dbfile, db.dictdb)

    bot.send_message(chat_id, 'The case ' + case + ' has been removed successfully')


@bot.message_handler(commands=['list'])
def listcase_command(message):
    """
    /list telegram command handler
    list the cases monitored by the bot
    expect to get: nothing
    next step: nothing
    """
    chat_id = str(message.chat.id)
    if not db.checkuserconfiguration(chat_id, db.dictdb):
        msg = bot.reply_to(message, "Proceed with /setup first, your account is not configured for id " + str(message.chat.id))
        logger.exception("db: " + repr(db.dictdb))
        return
    if not "cases" in db.dictdb[chat_id] or len(db.dictdb[chat_id]["cases"]) == 0:
        msg = bot.reply_to(message, "No cases are monitored, add it via /add")
        return
    cases = "\n".join(db.dictdb[chat_id]["cases"])
    msg = bot.reply_to(message, "The following cases are monitored by the tool for you:\n" + cases)


@bot.message_handler(commands=['whoami'])
def whoami_command(message):
    """
    /whoami telegram command handler
    print the chat_id of the user
    expect to get: nothing
    next step: nothing
    """
    chat_id = str(message.chat.id)
    msg = bot.reply_to(message, "Your chat_id is " + chat_id)

@bot.message_handler(commands=['notification'])
def notification_command(message):
    """
    /notification telegram command handler
    change the notifiaction Type for the current user
    expect to get: Type to be monitored (Associate, Customer or Both)
    next step: process_notification_step
    """
    chat_id = str(message.chat.id)
    if not db.checkuserconfiguration(chat_id, db.dictdb):
        msg = bot.reply_to(message, "Proceed with /setup first, your account is not configured for id " + str(message.chat.id))
        logger.exception("db: " + repr(db.dictdb))
        return
    msg = bot.reply_to(message, """\
This setting let you define which kind of update you want to receive.
Please pick between 'Both', 'Associate' and 'Customer' (default: Associate)
""")
    bot.register_next_step_handler(msg, process_notification_step)


def process_notification_step(message):
    """
    /notification telegram command handler
    change the notifiaction Type for the current user
    expect to get: nothing
    next step: notification change for the user or process_notification_step if an exception is raised
    """
    chat_id = str(message.chat.id)
    notify = message.text

    # create the index if missing
    if not "cases" in db.dictdb[chat_id]:
        db.dictdb[chat_id]["cases"] = dict()

    xmlvalues = ["Both", "Associate", "Customer"]
    if notify in xmlvalues:
        if notify == "Both":
            notify = ["Associate", "Customer"]
        else:
            notify = [notify]
    else:
        msg = bot.reply_to(message, "Wrong input '" + notify + "', acceptable values are Both, Associate, Customer")
        bot.register_next_step_handler(message, process_notification_step)
        return None


    db.dictdb[chat_id]["notify"] = notify

    db.savejson(config.dbfile, db.dictdb)
    bot.send_message(chat_id, 'The notification setting has been set to ' + repr(notify))


def run(event):
    """
    Main class, iterate over the bot.
    The bot will be initialized and will iterate forever.
    """
    # TODO implement event
    global bot
    try:
        bot.polling(none_stop=True, timeout=60)
    except Exception as e:
        logger.exception(repr(message) + repr(e))
