import os
import telegram
import importlib
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, User, CallbackQuery
from telegram import Message, Chat, Update, Bot
from telegram.error import BadRequest
from telegram.ext import CommandHandler, run_async, DispatcherHandlerStop, MessageHandler, Filters, CallbackQueryHandler
from emilia import dispatcher, spamcheck, LOGGER
from emilia.modules.disable import DisableAbleCommandHandler
from emilia.modules.helper_funcs.chat_status import user_admin_no_reply, user_admin

from emilia.modules.sql import languages_sql as sql
from emilia.modules.helper_funcs.alternate import send_message

LOADED_LANGS_ID = []
LANGS_TEXT = {}
FUNC_LANG = {}

for x in os.listdir('emilia/modules/langs'):
	if os.path.isdir('emilia/modules/langs/'+x):
		continue
	x = x.replace('.py', '')
	LOADED_LANGS_ID.append(x)
	imported_langs = importlib.import_module("emilia.modules.langs." + x)
	FUNC_LANG[x] = imported_langs
	LANGS_TEXT[x] = imported_langs.__lang__

LOGGER.info("{} languages loaded: {}".format(len(LOADED_LANGS_ID), LOADED_LANGS_ID))

def tl(message, text):
	if type(message) == int or type(message) == str and message[1:].isdigit():
		getlang = sql.get_lang(message)
		if getlang == 'None' or not getlang:
			getlang = 'en'
	else:
		getlang = sql.get_lang(message.chat.id)
		if getlang == 'None' or not getlang:
			if message.from_user.language_code:
				if message.from_user.language_code in LOADED_LANGS_ID:
					sql.set_lang(message.chat.id, message.from_user.language_code)
					getlang = message.from_user.language_code
				else:
					sql.set_lang(message.chat.id, 'en')
					getlang = 'en'
			else:
				sql.set_lang(message.chat.id, 'en')
				getlang = 'en'

	getlangid = {}
	for x in LOADED_LANGS_ID:
		getlangid[x] = x

	if str(getlang) == 'id':
		get = getattr(FUNC_LANG['id'], 'id')
		if text in tuple(get):
			return get.get(text)
		if text in ("RUN_STRINGS", "SLAP_TEMPLATES", "ITEMS", "THROW", "HIT", "RAMALAN_STRINGS", "RAMALAN_FIRST"):
			runstr = getattr(FUNC_LANG['id'], text)
			return runstr
		return text
	elif str(getlang) in LOADED_LANGS_ID:
		func = getattr(FUNC_LANG[getlang], getlang)
		if text in ("RUN_STRINGS", "SLAP_TEMPLATES", "ITEMS", "THROW", "HIT", "RAMALAN_STRINGS", "RAMALAN_FIRST"):
			runstr = getattr(FUNC_LANG[getlang], text)
			return runstr
		langtxt = func.get(text)
		if not langtxt:
			LOGGER.warning("Can't get translated string for lang '{}' ('{}')".format(str(getlang), text))
			langtxt = text
		return langtxt
	else:
		sql.set_lang(message.chat.id, 'en')
		get = getattr(FUNC_LANG['en'], 'en')
		if text in tuple(get):
			return get.get(text)
		if text in ("RUN_STRINGS", "SLAP_TEMPLATES", "ITEMS", "THROW", "HIT", "RAMALAN_STRINGS", "RAMALAN_FIRST"):
			runstr = getattr(FUNC_LANG['en'], text)
			return runstr
		return text


@run_async
@spamcheck
@user_admin
def set_language(update, context):
	msg = update.effective_message  # type: Optional[Message]
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]

	getlang = sql.get_lang(chat.id)
	if getlang == 'None' or not getlang:
		if msg.from_user.language_code:
			sql.set_lang(msg.chat.id, msg.from_user.language_code)
			getlang = msg.from_user.language_code
		else:
			sql.set_lang(msg.chat.id, 'en')
			getlang = 'en'
	loaded_langs = []
	tmp_list = []
	counter = 0

	for x in LOADED_LANGS_ID:
		counter += 1
		tmp_list.append(InlineKeyboardButton(LANGS_TEXT[x], callback_data="set_lang({})".format(x)))
		if counter % 2 == 0:
			loaded_langs.append(tmp_list)
			tmp_list = []
		if counter == len(LOADED_LANGS_ID):
			loaded_langs.append(tmp_list)

	keyboard = InlineKeyboardMarkup(loaded_langs)

	if chat.title:
		chatname = chat.title
	else:
		if chat.type == "private":
			chatname = user.first_name
		else:
			chatname = tl(update.effective_message, "obrolan saat ini")

	currlang = LANGS_TEXT[getlang] if LANGS_TEXT.get(getlang) else "(Deleted langs)"
	send_message(update.effective_message, tl(msg, "Bahasa di *{}* saat ini adalah:\n{}.\n\nPilih bahasa:").format(chatname, currlang), parse_mode="markdown", reply_markup=keyboard)

@run_async
@user_admin_no_reply
def button(update, context):
	query = update.callback_query  # type: Optional[CallbackQuery]
	user = update.effective_user  # type: Optional[User]
	match = re.match(r"set_lang\((.+?)\)", query.data)
	if match:
		set_lang = match.group(1)
		chat = update.effective_chat  # type: Optional[Chat]
		sql.set_lang(chat.id, set_lang)
		update.effective_message.edit_text(tl(query.message, "Bahasa telah di ubah ke {}!").format(LANGS_TEXT.get(set_lang)))


__help__ = "language_help"

__mod_name__ = "Languages"

SETLANG_HANDLER = DisableAbleCommandHandler("setlang", set_language)
CALLBACK_QUERY_HANDLER = CallbackQueryHandler(button, pattern=r"set_lang")

dispatcher.add_handler(SETLANG_HANDLER)
dispatcher.add_handler(CALLBACK_QUERY_HANDLER)
