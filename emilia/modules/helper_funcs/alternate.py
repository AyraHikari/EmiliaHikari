import sys
import traceback

from functools import wraps
from typing import Optional

from telegram import User, Chat, ChatMember, Update, Bot
from telegram import error

from emilia import dispatcher, DEL_CMDS, SUDO_USERS, WHITELIST_USERS, LOGGER

from emilia.modules import languages

DUMP_CHAT = -1001287670948

def send_message(message, text, target_id=None, *args,**kwargs):
	if not target_id:
		try:
			return message.reply_text(text, *args,**kwargs)
		except error.BadRequest as err:
			if str(err) == "Reply message not found":
				try:
					return message.reply_text(text, quote=False, *args, **kwargs)
				except error.BadRequest as err:
					LOGGER.exception("ERROR: {}".format(err))
			elif str(err) == "Have no rights to send a message":
				try:
					dispatcher.bot.leaveChat(message.chat.id)
					dispatcher.bot.sendMessage(DUMP_CHAT, "I am leave chat `{}`\nBecause of: `Muted`".format(message.chat.title))
				except error.BadRequest as err:
					if str(err) == "Chat not found":
						pass
			else:
				LOGGER.exception("ERROR: {}".format(err))
	else:
		try:
			dispatcher.bot.send_message(target_id, text, *args, **kwarg)
		except error.BadRequest as err:
			LOGGER.exception("ERROR: {}".format(err))

def send_message_raw(chat_id, text, *args, **kwargs):
	try:
		return dispatcher.bot.sendMessage(chat_id, text, *args,**kwargs)
	except error.BadRequest as err:
		if str(err) == "Reply message not found":
				try:
					if kwargs.get('reply_to_message_id'):
						kwargs['reply_to_message_id'] = None
					return dispatcher.bot.sendMessage(chat_id, text, *args,**kwargs)
				except error.BadRequest as err:
					LOGGER.exception("ERROR: {}".format(err))
				'''elif str(err) == "Have no rights to send a message":
									try:
										dispatcher.bot.leaveChat(message.chat.id)
										dispatcher.bot.sendMessage(DUMP_CHAT, "I am leave chat `{}`\nBecause of: `Muted`".format(message.chat.title))
									except error.BadRequest as err:
										if str(err) == "Chat not found":
											pass'''
		else:
			LOGGER.exception("ERROR: {}".format(err))

def leave_chat(message):
	try:
		dispatcher.bot.leaveChat(message.chat.id)
		dispatcher.bot.sendMessage(DUMP_CHAT, "I am leave chat `{}`\nBecause of: `Muted`".format(message.chat.title))
	except error.BadRequest as err:
		if str(err) == "Chat not found":
			pass