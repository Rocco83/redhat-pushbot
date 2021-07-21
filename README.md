# tickets-pushbot
:warning: **This project is not supported or backed by Red Hat&reg;**

Did you get tired of managing tons of vendor email notification for the support tickets?
Have you disabled the email notification fully for your mobile?
Do you want to monitor just a couple of cases with priorities?
Are you managing a very high priority case and you don't want to waste time in refreshing the browser?

So, get bot notification on your $device just for the vendor ticket that you prefer.

As of today, some limitations apply (as in every project starting from scratch):
- the only poller supported is Red Hat&reg; Customer Portal.
- the only notification method is limited to Telegram.


## Some use cases in details
- You have too many cases open with red hat, and you get too many email
- You have a business email without custom filters, and you can't filter manually some cases only to your inbox
- You need to have the push notification for cases in escalation
- You need to keep an eye only on some cases
- You simply prefer to use Telegram over the email for the notifications


## Setup
### Minimum setup to start woring with the bot
This step is shared among all the following setup type.
You need a valid login in the Red Hat&reg; Customer Portal, of course.
We definitely recommend to setup a "service user" (a non-human user) to leverage on the automation.
The username and password of the user will be written in the configuration file.

We also recommend to implement in the Customer Portal the "Case Groups", allowing only the "read" permission on the needed groups.
This configuration will provide a limited view of the user that you will configure
More information can be found at the following links
[What are Case Groups and how do I create one?](https://access.redhat.com/solutions/777833)
[Portal Case Management User Guide](https://access.redhat.com/articles/2390851)


### On premise usage
#### Installation
Pull the repository, and setup the needed modules. 
We recommend to install the modules in a virtual environment (e.g.: `python3 -m venv venv`).

This bot works with python3 (will likely not work with python2) and need the following modules:
- PyTelegramBotAPI
- xmltodict
Pull the repository, and setup the needed modules.
You can use `$ pip install -r requirements.txt` to help you out with the dependencies.

#### Setup your bot
Chat with `@BotFather` and create a new bot. Save the bot username and the token.
In your repository, copy the config.py-sample in config.py and customize the token in config.py
Start the daemon with `python3 wrapper.py`
Proceed with Cloud usage chapter, replacing the bot name that you are going to use.

#### Some more technical details for the On premise setup
The data will be written into `db.json`.
The bot as of today does not need any inbound connection, as this bot poll telegram and redhat customer portal.


### Cloud usage
IMPORTANT: read the chapter "Customer portal limitations and security concearns" below
You need to chat with `@TicketNotificationBot` with Telegram.
Just follow the instruction from the bot, `/help` is available.
The basic step needed in `/setup`
After setting up the user, among the other actions, you can decide if to get from the bot only the Customer notifications, the Associate (Red Hat&reg;) notifications, or both. The default is "Associate".

You can (warning: not tested) add the bot into a group, to get a number of users notified.

### Customer portal limitations and security concearns
Clearly, saving the password in clear text and allowing a "full read" permission over the cases can be "too much" if you don't control the telegram bot.
So we encourage you to setup your telegram bot on premise, where you know that you data will be safe.

This limitations are introduced by the Customer Portal limitations, for which the following Request for Enahncement has been filed.
As soon as some public bugzilla will be available, the link will be shared.
You are encouraged anyway to open a case to Red Hat&reg; to request the same functionalities, as the most users request it, the most probable is that the function will be introduced

#### [RFE] ability to create a token in place of username & password
```
Currently, the only authentication method that i have found is via username and password.
What i wish to have is a token, to avoid creating tons of users in the customer portal, and being able to remove the authentication (or rotating it) upon needing.
```

#### [RFE] Add granularity for User Groups in the Customer Portal
```
Currently, the granularity that User Groups allows in the customer portal is "read" and "write".
What i would like to request is to add other granularity settings, restricting further the "read" permission.
I would suggest to add:
* read updates only: read only the updates, and avoid to read attachments (where more sensitive informations are disclosed)
* read summary only: don't disclose at all the "text" field of the xml. This would allow to have the notification without disclosing *any* sensitive information outside of the title of the case and the last update time.
```



## Detailed information
If you wish to add some code, refer to testcase.xml for a sample anonymized output of the xml from the customer portal.
You can see also another same here below (anonymized)

A sample case is pasted here below
```
GET https://api.access.redhat.com/rs/cases/00000000/comments
```
```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?><comments xmlns="http://www.redhat.com/gss/strata"><comment caseNumber="00000000" id="a00000000000000000"><createdBy>CustomerSurname, CustomerName</createdBy><createdDate>2020-09-22T17:07:10Z</createdDate><lastModifiedBy>CustomerSurname, CustomerName</lastModifiedBy><lastModifiedDate>2020-09-22T17:07:09Z</lastModifiedDate><text>Hi Milan,[...]</text><draft>false</draft><publishedDate>2020-09-22T17:07:09Z</publishedDate><createdByType>Customer</createdByType>
```

### Reference guide
The reference documentation for the customer portal used is the following
[Red Hat&reg; API guide](https://access.redhat.com/documentation/en-us/red_hat_customer_portal/1/html/customer_portal_integration_guide/index)
TODO implement a token from Red Hat: https://access.redhat.com/articles/3626371


## TODO
Here the list of what has been suggested so far, and due to lack of time has been not implemented.
PR are more then welcome.
* implement lock file (to avoid json concurrent write)
* don't post the full reply from redhat, limit it to X charactes (configurable)
* add a quick reply button to get the latest comment for a case
* add a brief "end message" for uploaded cases
* add timestamps in the logs
* add slack support (and have the application multi notification then)
* add stack trace via telegram -- for debugging

