import sys
import traceback

from functools import wraps
from typing import Optional

from telegram import User, Chat, ChatMember, Update, Bot
from telegram import error

from emilia import DEL_CMDS, SUDO_USERS, WHITELIST_USERS

from emilia.modules import languages


def send_message(message, text,  *args,**kwargs):
	try:
		return message.reply_text(text, *args,**kwargs)
	except error.BadRequest as err:
		if str(err) == "Reply message not found":
			try:
				return message.reply_text(text, quote=False, *args,**kwargs)
			except error.BadRequest as err:
				print("ERROR: {}".format(err))
