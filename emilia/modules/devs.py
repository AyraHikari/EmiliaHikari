import os
import sys
import traceback

from telegram.error import BadRequest, Unauthorized
from telegram import Message, Chat, Update, Bot, MessageEntity
from telegram import ParseMode
from telegram.ext import CommandHandler, run_async, Filters
from telegram.utils.helpers import escape_markdown, mention_html

from emilia import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, WHITELIST_USERS, BAN_STICKER, API_WEATHER, spamfilters
from emilia.__main__ import STATS, USER_INFO
from emilia.modules.disable import DisableAbleCommandHandler, DisableAbleRegexHandler
from emilia.modules.helper_funcs.extraction import extract_user
from emilia.modules.helper_funcs.filters import CustomFilters

from emilia.modules.helper_funcs.alternate import send_message


@run_async
def reboot(bot: Bot, update: Update):
	msg = update.effective_message
	chat_id = update.effective_chat.id
	send_message(update.effective_message, "Rebooting...", parse_mode=ParseMode.MARKDOWN)
	try:
		os.system("cd /home/ayra/emilia/ && python3.6 -m emilia &")
		os.system('kill %d' % os.getpid())
		send_message(update.effective_message, "Reboot Berhasil!", parse_mode=ParseMode.MARKDOWN)
	except:
		send_message(update.effective_message, "Reboot Gagal!", parse_mode=ParseMode.MARKDOWN)

@run_async
def executor(bot: Bot, update: Update):
	msg = update.effective_message
	if msg.text:
		args = msg.text.split(None, 1)
		code = args[1]
		chat = msg.chat.id
		try:
			exec(code)
		except:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			errors = traceback.format_exception(etype=exc_type, value=exc_obj, tb=exc_tb)
			send_message(update.effective_message, "**Execute**\n`{}`\n\n*Failed:*\n```{}```".format(code, "".join(errors)), parse_mode="markdown")


REBOOT_HANDLER = CommandHandler("emreboot", reboot, filters=Filters.user(OWNER_ID))
EXEC_HANDLER = CommandHandler("emil", executor, filters=Filters.user(OWNER_ID))

#dispatcher.add_handler(REBOOT_HANDLER)
dispatcher.add_handler(EXEC_HANDLER)
