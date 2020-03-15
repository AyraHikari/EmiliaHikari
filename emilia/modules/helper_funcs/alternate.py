import sys
import traceback

from functools import wraps
from typing import Optional

from telegram import User, Chat, ChatMember, Update, Bot
from telegram import error

from emilia import dispatcher, DEL_CMDS, SUDO_USERS, WHITELIST_USERS

from emilia.modules import languages


def send_message(message, text, target_id=None, *args,**kwargs):
	if not target_id:
		try:
			return message.reply_text(text, *args,**kwargs)
		except error.BadRequest as err:
			if str(err) == "Reply message not found":
				try:
					return message.reply_text(text, quote=False, *args, **kwargs)
				except error.BadRequest as err:
					print("ERROR: {}".format(err))
	else:
		try:
			dispatcher.bot.send_message(target_id, text, *args, **kwarg)
		except error.BadRequest as err:
			print("ERROR: {}".format(err))
