import json, time, os
from io import BytesIO
from typing import Optional

from telegram import MAX_MESSAGE_LENGTH, ParseMode, InlineKeyboardMarkup
from telegram import Message, Chat, Update, Bot
from telegram.error import BadRequest
from telegram.ext import CommandHandler, run_async, Filters

import emilia.modules.sql.notes_sql as sql
from emilia import dispatcher, LOGGER, OWNER_ID, SUDO_USERS, spamfilters, TEMPORARY_DATA
from emilia.__main__ import DATA_IMPORT
from emilia.modules.helper_funcs.chat_status import user_admin
from emilia.modules.helper_funcs.misc import build_keyboard, revert_buttons
from emilia.modules.helper_funcs.msg_types import get_note_type
from emilia.modules.rules import get_rules
from emilia.modules.helper_funcs.string_handling import button_markdown_parser, make_time

# SQL
import emilia.modules.sql.antiflood_sql as antifloodsql
import emilia.modules.sql.blacklist_sql as blacklistsql
import emilia.modules.sql.blsticker_sql as blackliststksql
from emilia.modules.sql import disable_sql as disabledsql
from emilia.modules.sql import cust_filters_sql as filtersql
from emilia.modules.sql import languages_sql as langsql
import emilia.modules.sql.locks_sql as locksql
from emilia.modules.locks import LOCK_TYPES, RESTRICTION_TYPES
from emilia.modules.sql import notes_sql as notesql
from emilia.modules.sql import reporting_sql as reportsql
import emilia.modules.sql.rules_sql as rulessql
from emilia.modules.sql import warns_sql as warnssql
import emilia.modules.sql.welcome_sql as welcsql

from emilia.modules.connection import connected

from emilia.modules.helper_funcs.msg_types import Types
from emilia.modules.languages import tl
from emilia.modules.helper_funcs.alternate import send_message

@run_async
@user_admin
def import_data(bot: Bot, update):
	msg = update.effective_message  # type: Optional[Message]
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	# TODO: allow uploading doc with command, not just as reply
	# only work with a doc
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return

	conn = connected(bot, update, chat, user.id, need_admin=True)
	if conn:
		chat = dispatcher.bot.getChat(conn)
		chat_id = conn
		chat_name = dispatcher.bot.getChat(conn).title
	else:
		if update.effective_message.chat.type == "private":
			send_message(update.effective_message, tl(update.effective_message, "Anda bisa lakukan command ini pada grup, bukan pada PM"))
			return ""
		chat = update.effective_chat
		chat_id = update.effective_chat.id
		chat_name = update.effective_message.chat.title

	if msg.reply_to_message and msg.reply_to_message.document:
		filetype = msg.reply_to_message.document.file_name
		if filetype.split('.')[-1] not in ("backup", "json", "txt"):
			send_message(update.effective_message, tl(update.effective_message, "File cadangan tidak valid!"))
			return
		try:
			file_info = bot.get_file(msg.reply_to_message.document.file_id)
		except BadRequest:
			send_message(update.effective_message, tl(update.effective_message, "Coba unduh dan unggah ulang file seperti Anda sendiri sebelum mengimpor - yang ini sepertinya rusak!"))
			return

		with BytesIO() as file:
			file_info.download(out=file)
			file.seek(0)
			data = json.load(file)

		try:
			# If backup is from Emilia
			if data.get('bot_base') == "Emilia":
				imp_antiflood = False
				imp_blacklist = False
				imp_blacklist_count = 0
				imp_blsticker = False
				imp_blsticker_count = 0
				imp_disabled_count = 0
				imp_filters_count = 0
				imp_greet = False
				imp_gdbye = False
				imp_greet_pref = False
				imp_locks = False
				imp_notes = 0
				imp_report = False
				imp_rules = False
				imp_lang = False
				imp_warn = False
				imp_warn_chat = 0
				imp_warn_filter = 0
				NOT_IMPORTED = "This cannot be imported because from other bot."
				NOT_IMPORTED_INT = 0
				# If backup is from this bot, import all files
				if data.get('bot_id') == bot.id:
					is_self = True
				else:
					is_self = False
				# Import antiflood
				if data.get('antiflood'):
					imp_antiflood = True
					flood_limit = data['antiflood'].get('flood_limit')
					flood_mode = data['antiflood'].get('flood_mode')
					flood_duration = data['antiflood'].get('flood_duration')

					# Add to db
					antifloodsql.set_flood(chat_id, int(flood_limit))
					antifloodsql.set_flood_strength(chat_id, flood_mode, flood_duration)

				# Import blacklist
				if data.get('blacklists'):
					imp_blacklist = True
					blacklist_mode = data['blacklists'].get('blacklist_mode')
					blacklist_duration = data['blacklists'].get('blacklist_duration')
					blacklisted = data['blacklists'].get('blacklists')

					# Add to db
					blacklistsql.set_blacklist_strength(chat_id, blacklist_mode, blacklist_duration)
					if blacklisted:
						for x in blacklisted:
							blacklistsql.add_to_blacklist(chat_id, x.lower())
							imp_blacklist_count += 1

				# Import blacklist sticker
				if data.get('blstickers'):
					imp_blsticker = True
					blsticker_mode = data['blstickers'].get('blsticker_mode')
					blsticker_duration = data['blstickers'].get('blsticker_duration')
					blstickers = data['blstickers'].get('blstickers')

					# Add to db
					blackliststksql.set_blacklist_strength(chat_id, blsticker_mode, blsticker_duration)
					if blstickers:
						for x in blstickers:
							blackliststksql.add_to_stickers(chat_id, x.lower())
							imp_blsticker_count += 1

				# Import disabled
				if data.get('disabled'):
					candisable = disabledsql.get_disableable()
					if data['disabled'].get('disabled'):
						for listdisabled in data['disabled'].get('disabled'):
							if listdisabled in candisable:
								disabledsql.disable_command(chat_id, listdisabled)
								imp_disabled_count += 1

				# Import filters
				if data.get('filters'):
					NOT_IMPORTED += "\n\nFilters:\n"
					for x in data['filters'].get('filters'):
						# If from self, import all
						if is_self:
							is_sticker = False
							is_document = False
							is_image = False
							is_audio = False
							is_voice = False
							is_video = False
							has_markdown = False
							universal = False
							if x['type'] == 1:
								is_sticker = True
							elif x['type'] == 2:
								is_document = True
							elif x['type'] == 3:
								is_image = True
							elif x['type'] == 4:
								is_audio = True
							elif x['type'] == 5:
								is_voice = True
							elif x['type'] == 6:
								is_video = True
							elif x['type'] == 0:
								has_markdown = True
							note_data, buttons = button_markdown_parser(x['reply'], entities=0)
							filtersql.add_filter(chat_id, x['name'], note_data, is_sticker, is_document, is_image, is_audio, is_voice, is_video, buttons)
							imp_filters_count += 1	
						else:
							if x['has_markdown']:
								note_data, buttons = button_markdown_parser(x['reply'], entities=0)
								filtersql.add_filter(chat_id, x['name'], note_data, False, False, False, False, False, False, buttons)
								imp_filters_count += 1
							else:
								NOT_IMPORTED += "- {}\n".format(x['name'])
								NOT_IMPORTED_INT += 1

				# Import greetings
				if data.get('greetings'):
					if data['greetings'].get('welcome'):
						welcenable = data['greetings']['welcome'].get('enable')
						welcsql.set_welc_preference(str(chat_id), bool(welcenable))

						welctext = data['greetings']['welcome'].get('text')
						welctype = data['greetings']['welcome'].get('type')
						if welctype == 0:
							welctype = Types.TEXT
						elif welctype == 1:
							welctype = Types.BUTTON_TEXT
						elif welctype == 2:
							welctype = Types.STICKER
						elif welctype == 3:
							welctype = Types.DOCUMENT
						elif welctype == 4:
							welctype = Types.PHOTO
						elif welctype == 5:
							welctype = Types.AUDIO
						elif welctype == 6:
							welctype = Types.VOICE
						elif welctype == 7:
							welctype = Types.VIDEO
						elif welctype == 8:
							welctype = Types.VIDEO_NOTE
						else:
							welctype = None
						welccontent = data['greetings']['welcome'].get('content')
						if welctext and welctype:
							note_data, buttons = button_markdown_parser(welctext, entities=0)
							welcsql.set_custom_welcome(chat_id, welccontent, note_data, welctype, buttons)
							imp_greet = True
					if data['greetings'].get('goodbye'):
						gdbyenable = data['greetings']['goodbye'].get('enable')
						welcsql.set_gdbye_preference(str(chat_id), bool(gdbyenable))

						gdbytext = data['greetings']['goodbye'].get('text')
						gdbytype = data['greetings']['goodbye'].get('type')
						if gdbytype == 0:
							gdbytype = Types.TEXT
						elif gdbytype == 1:
							gdbytype = Types.BUTTON_TEXT
						elif gdbytype == 2:
							gdbytype = Types.STICKER
						elif gdbytype == 3:
							gdbytype = Types.DOCUMENT
						elif gdbytype == 4:
							gdbytype = Types.PHOTO
						elif gdbytype == 5:
							gdbytype = Types.AUDIO
						elif gdbytype == 6:
							gdbytype = Types.VOICE
						elif gdbytype == 7:
							gdbytype = Types.VIDEO
						elif gdbytype == 8:
							gdbytype = Types.VIDEO_NOTE
						else:
							gdbytype = None
						gdbycontent = data['greetings']['goodbye'].get('content')
						if welctext and gdbytype:
							note_data, buttons = button_markdown_parser(gdbytext, entities=0)
							welcsql.set_custom_gdbye(chat_id, gdbycontent, note_data, gdbytype, buttons)
							imp_gdbye = True

				# clean service
				cleanserv = data['greetings'].get('clean_service')
				welcsql.set_clean_service(chat_id, bool(cleanserv))

				# security welcome
				if data['greetings'].get('security'):
					secenable = data['greetings']['security'].get('enable')
					secbtn = data['greetings']['security'].get('text')
					sectime = data['greetings']['security'].get('time')
					welcsql.set_welcome_security(chat_id, bool(secenable), str(sectime), str(secbtn))
					imp_greet_pref = True

				# Import language
				if data['greetings'].get('language'):
					lang = data['language'].get('language')
					if lang:
						if lang in ('en', 'id'):
							langsql.set_lang(chat_id, lang)
							imp_lang = True

				# Import Locks
				if data.get('locks'):
					if data['locks'].get('lock_warn'):
						locksql.set_lockconf(chat_id, True)
					else:
						locksql.set_lockconf(chat_id, False)
					if data['locks'].get('locks'):
						for x in list(data['locks'].get('locks')):
							if x in LOCK_TYPES:
								is_locked = data['locks']['locks'].get('x')
								locksql.update_lock(chat_id, x, locked=is_locked)
								imp_locks = True
							if x in RESTRICTION_TYPES:
								is_locked = data['locks']['locks'].get('x')
								locksql.update_restriction(chat_id, x, locked=is_locked)
								imp_locks = True

				# Import notes
				if data.get('notes'):
					allnotes = data['notes']
					NOT_IMPORTED += "\n\nNotes:\n"
					for x in allnotes:
						# If from self, import all
						if is_self:
							note_data, buttons = button_markdown_parser(x['note_data'], entities=0)
							note_name = x['note_tag']
							note_file = None
							note_type = x['note_type']
							if x['note_file']:
								note_file = x['note_file']
							if note_type == 0:
								note_type = Types.TEXT
							elif note_type == 1:
								note_type = Types.BUTTON_TEXT
							elif note_type == 2:
								note_type = Types.STICKER
							elif note_type == 3:
								note_type = Types.DOCUMENT
							elif note_type == 4:
								note_type = Types.PHOTO
							elif note_type == 5:
								note_type = Types.AUDIO
							elif note_type == 6:
								note_type = Types.VOICE
							elif note_type == 7:
								note_type = Types.VIDEO
							elif note_type == 8:
								note_type = Types.VIDEO_NOTE
							else:
								note_type = None
							if note_type <= 8:
								notesql.add_note_to_db(chat_id, note_name, note_data, note_type, buttons, note_file)
								imp_notes += 1
						else:
							# If this text
							if x['note_type'] == 0:
								note_data, buttons = button_markdown_parser(x['text'].replace("\\", ""), entities=0)
								note_name = x['name']
								notesql.add_note_to_db(chat_id, note_name, note_data, Types.TEXT, buttons, None)
								imp_notes += 1
							else:
								NOT_IMPORTED += "- {}\n".format(x['name'])
								NOT_IMPORTED_INT += 1

				# Import reports
				if data.get('report'):
					reporting = data['report'].get('report')
					reportsql.set_chat_setting(chat_id, bool(reporting))
					imp_report = True

				# Import rules
				if data.get('rules'):
					contrules = data['rules'].get('rules')
					if contrules:
						rulessql.set_rules(chat_id, contrules)
						imp_rules = True

				# Import warn config
				if data.get('warns'):
					warn_limit = data['warns'].get('warn_limit')
					if warn_limit >= 3:
						warnssql.set_warn_limit(chat_id, int(warn_limit))

					warn_mode = data['warns'].get('warn_mode')
					if warn_mode:
						if warn_mode <= 3:
							warnssql.set_warn_mode(chat_id, int(warn_mode))
							imp_warn = True

					# Import all warn filters
					if data['warns'].get('warn_filters'):
						for x in data['warns'].get('warn_filters'):
							warnssql.add_warn_filter(chat_id, x['name'], x['reason'])
							imp_warn_filter += 1

					# Import all warn from backup chat, reset first for prevent overwarn
					if data['warns'].get('chat_warns'):
						for x in data['warns'].get('chat_warns'):
							# If this invaild
							if x['warns'] > warn_limit:
								break
							warnssql.reset_warns(x['user_id'], chat_id)
							warnssql.import_warns(x['user_id'], chat_id, int(x['warns']), x['reasons'])
							imp_warn_chat += 1

				if conn:
					text = tl(update.effective_message, "Cadangan sepenuhnya dikembalikan pada *{}*. Selamat datang kembali! 😀").format(chat_name)
				else:
					text = tl(update.effective_message, "Cadangan sepenuhnya dikembalikan. Selamat datang kembali! 😀").format(chat_name)
				text += tl(update.effective_message, "\n\nYang saya kembalikan:\n")
				if imp_antiflood:
					text += tl(update.effective_message, "- Pengaturan Antiflood\n")
				if imp_blacklist:
					text += tl(update.effective_message, "- Pengaturan Blacklist\n")
				if imp_blacklist_count:
					text += tl(update.effective_message, "- {} blacklists\n").format(imp_blacklist_count)
				if imp_blsticker:
					text += tl(update.effective_message, "- {} blacklist stickers\n").format(imp_blsticker_count)
				if imp_disabled_count:
					text += tl(update.effective_message, "- {} cmd disabled\n").format(imp_disabled_count)
				if imp_filters_count:
					text += tl(update.effective_message, "- {} filters\n").format(imp_filters_count)
				if imp_greet_pref:
					text += tl(update.effective_message, "- Pengaturan salam\n")
				if imp_greet:
					text += tl(update.effective_message, "- Pesan salam\n")
				if imp_gdbye:
					text += tl(update.effective_message, "- Pesan selamat tinggal\n")
				if imp_locks:
					text += tl(update.effective_message, "- Penguncian\n")
				if imp_notes:
					text += tl(update.effective_message, "- {} catatan\n").format(imp_notes)
				if imp_report:
					text += tl(update.effective_message, "- Pengaturan pelaporan\n")
				if imp_rules:
					text += tl(update.effective_message, "- Pesan peraturan grup\n")
				if imp_lang:
					text += tl(update.effective_message, "- Pengaturan bahasa\n")
				if imp_warn:
					text += tl(update.effective_message, "- Pengaturan peringatan\n")
				if imp_warn_chat:
					text += tl(update.effective_message, "- {} pengguna peringatan\n").format(imp_warn_chat)
				if imp_warn_filter:
					text += tl(update.effective_message, "- {} filter peringatan\n").format(imp_warn_filter)
				try:
					send_message(update.effective_message, text, parse_mode="markdown")
				except BadRequest:
					send_message(update.effective_message, text, parse_mode="markdown", quote=False)
				if NOT_IMPORTED_INT:
					f = open("{}-notimported.txt".format(chat_id), "w")
					f.write(str(NOT_IMPORTED))
					f.close()
					bot.sendDocument(chat_id, document=open('{}-notimported.txt'.format(chat_id), 'rb'), caption=tl(update.effective_message, "*Data yang tidak dapat di import*"), timeout=360, parse_mode=ParseMode.MARKDOWN)
					os.remove("{}-notimported.txt".format(chat_id))
				return
		except Exception as err:
			send_message(update.effective_message, tl(update.effective_message, "Telah terjadi kesalahan dalam import backup Emilia!\nGabung ke [Grup support](https://t.me/joinchat/Fykz0VTMpqZvlkb8S0JevQ) kami untuk melaporkan dan mengatasi masalah ini!\n\nTerima kasih"), parse_mode="markdown")
			LOGGER.exception("An error when importing from Emilia base!")
			return

		try:
			# If backup is from rose
			# doing manual lol
			if data.get('bot_id') == 609517172:
				imp_antiflood = False
				imp_blacklist = False
				imp_blacklist_count = 0
				imp_disabled_count = 0
				imp_filters_count = 0
				imp_greet = False
				imp_gdbye = False
				imp_greet_pref = False
				imp_notes = 0
				imp_report = False
				imp_rules = False
				imp_lang = False
				imp_warn = False
				NOT_IMPORTED = "This cannot be imported because from other bot."
				NOT_IMPORTED_INT = 0
				if data.get('data'):
					# Import antiflood
					if data['data'].get('antiflood'):
						floodlimit = data['data']['antiflood'].get('flood_limit')
						action = data['data']['antiflood'].get('action')
						actionduration = data['data']['antiflood'].get('action_duration')
						act_dur = make_time(int(actionduration))
						antifloodsql.set_flood(chat_id, int(floodlimit))
						if action == "ban":
							antifloodsql.set_flood_strength(chat_id, 1, str(act_dur))
							imp_antiflood = True
						elif action == "kick":
							antifloodsql.set_flood_strength(chat_id, 2, str(act_dur))
							imp_antiflood = True
						elif action == "mute":
							antifloodsql.set_flood_strength(chat_id, 3, str(act_dur))
							imp_antiflood = True
					# Import blacklist
					if data['data'].get('blacklists'):
						action = data['data']['blacklists'].get('action')
						actionduration = data['data']['blacklists'].get('action_duration')
						act_dur = make_time(int(actionduration))
						strengthdone = False
						if action == "del":
							strengthdone = True
							blacklistsql.set_blacklist_strength(chat_id, 1, str(act_dur))
							imp_blacklist = True
						elif action == "warn":
							strengthdone = True
							blacklistsql.set_blacklist_strength(chat_id, 2, str(act_dur))
							imp_blacklist = True
						elif action == "mute":
							strengthdone = True
							blacklistsql.set_blacklist_strength(chat_id, 3, str(act_dur))
							imp_blacklist = True
						elif action == "kick":
							strengthdone = True
							blacklistsql.set_blacklist_strength(chat_id, 4, str(act_dur))
							imp_blacklist = True
						elif action == "ban":
							strengthdone = True
							blacklistsql.set_blacklist_strength(chat_id, 5, str(act_dur))
							imp_blacklist = True
						else:
							if not strengthdone:
								action = data['data']['blacklists'].get('should_delete')
								if action:
									blacklistsql.set_blacklist_strength(chat_id, 1, "0")
									imp_blacklist = True
						blacklisted = data['data']['blacklists'].get('filters')
						if blacklisted:
							for x in blacklisted:
								blacklistsql.add_to_blacklist(chat_id, x['name'].lower())
								imp_blacklist_count += 1
					# Import disabled
					if data['data'].get('disabled'):
						if data['data']['disabled'].get('disabled'):
							candisable = disabledsql.get_disableable()
							for listdisabled in data['data']['disabled'].get('disabled'):
								if listdisabled in candisable:
									disabledsql.disable_command(chat_id, listdisabled)
									imp_disabled_count += 1
					# Import filters
					if data['data'].get('filters'):
						NOT_IMPORTED += "\n\nFilters:\n"
						if data['data']['filters'].get('filters'):
							for x in data['data']['filters'].get('filters'):
								if x['type'] == 0:
									note_data, buttons = button_markdown_parser(x['text'].replace("\\", ""), entities=0)
									filtersql.add_filter(chat_id, x['name'], note_data, False, False, False, False, False, False, buttons)
									imp_filters_count += 1
								else:
									NOT_IMPORTED += "- {}\n".format(x['name'])
									NOT_IMPORTED_INT += 1
					# Import greetings
					if data['data'].get('greetings'):
						if data['data']['greetings'].get('welcome'):
							welctext = data['data']['greetings']['welcome'].get('text')
							if welctext:
								note_data, buttons = button_markdown_parser(welctext.replace("\\", ""), entities=0)
								welcsql.set_custom_welcome(chat_id, None, note_data, Types.TEXT, buttons)
								imp_greet = True
						if data['data']['greetings'].get('goodbye'):
							gdbytext = data['data']['greetings']['goodbye'].get('text')
							if welctext:
								note_data, buttons = button_markdown_parser(gdbytext.replace("\\", ""), entities=0)
								welcsql.set_custom_gdbye(chat_id, None, note_data, Types.TEXT, buttons)
								imp_gdbye = True
						# Welcome config
						if data['data']['greetings'].get('should_welcome'):
							welcsql.set_welc_preference(str(chat_id), True)
						else:
							welcsql.set_welc_preference(str(chat_id), False)
						# Goodbye config
						if data['data']['greetings'].get('should_goodbye'):
							welcsql.set_gdbye_preference(str(chat_id), True)
						else:
							welcsql.set_gdbye_preference(str(chat_id), False)
						# clean service
						if data['data']['greetings'].get('should_delete_service'):
							welcsql.set_clean_service(chat_id, True)
						else:
							welcsql.set_clean_service(chat_id, False)
						# custom mute btn
						if data['data']['greetings'].get('mute_text'):
							getcur, cur_value, cust_text = welcsql.welcome_security(chat_id)
							welcsql.set_welcome_security(chat_id, getcur, cur_value, data['data']['greetings'].get('mute_text'))
						imp_greet_pref = True
						# TODO parsing unix time and import that
					# TODO Locks
					# Import notes
					if data['data'].get('notes'):
						NOT_IMPORTED += "\n\nNotes:\n"
						allnotes = data['data']['notes']['notes']
						for x in allnotes:
							# If this text
							if x['type'] == 0:
								note_data, buttons = button_markdown_parser(x['text'].replace("\\", ""), entities=0)
								note_name = x['name']
								notesql.add_note_to_db(chat_id, note_name, note_data, Types.TEXT, buttons, None)
								imp_notes += 1
							else:
								NOT_IMPORTED += "- {}\n".format(x['name'])
								NOT_IMPORTED_INT += 1
					# Import reports
					if data['data'].get('reports'):
						if data['data']['reports'].get('disable_reports'):
							reporting = False
						else:
							reporting = True
						reportsql.set_chat_setting(chat_id, reporting)
						imp_report = True
					# Import rules
					if data['data'].get('rules'):
						contrules = data['data']['rules'].get('content')
						if contrules:
							rulessql.set_rules(chat_id, contrules.replace("\\", ""))
							imp_rules = True
					# Import current lang
					if data['data'].get('translations'):
						lang = data['data']['translations'].get('lang')
						if lang:
							if lang in ('en', 'id'):
								langsql.set_lang(chat_id, lang)
								imp_lang = True
					# Import warn
					if data['data'].get('warns'):
						action = data['data']['warns'].get('action')
						# actionduration = data['data']['warns'].get('action_duration')
						# act_dur = make_time(int(actionduration))
						if action == "kick":
							warnssql.set_warn_mode(chat_id, 1)
							imp_warn = True
						elif action == "ban":
							warnssql.set_warn_mode(chat_id, 2)
							imp_warn = True
						elif action == "mute":
							warnssql.set_warn_mode(chat_id, 3)
							imp_warn = True
					if conn:
						text = tl(update.effective_message, "Cadangan sepenuhnya dikembalikan pada *{}*. Selamat datang kembali! 😀").format(chat_name)
					else:
						text = tl(update.effective_message, "Cadangan sepenuhnya dikembalikan. Selamat datang kembali! 😀").format(chat_name)
					text += tl(update.effective_message, "\n\nYang saya kembalikan:\n")
					if imp_antiflood:
						text += tl(update.effective_message, "- Pengaturan Antiflood\n")
					if imp_blacklist:
						text += tl(update.effective_message, "- Pengaturan Blacklist\n")
					if imp_blacklist_count:
						text += tl(update.effective_message, "- {} blacklists\n").format(imp_blacklist_count)
					if imp_disabled_count:
						text += tl(update.effective_message, "- {} cmd disabled\n").format(imp_disabled_count)
					if imp_filters_count:
						text += tl(update.effective_message, "- {} filters\n").format(imp_filters_count)
					if imp_greet_pref:
						text += tl(update.effective_message, "- Pengaturan salam\n")
					if imp_greet:
						text += tl(update.effective_message, "- Pesan salam\n")
					if imp_gdbye:
						text += tl(update.effective_message, "- Pesan selamat tinggal\n")
					if imp_notes:
						text += tl(update.effective_message, "- {} catatan\n").format(imp_notes)
					if imp_report:
						text += tl(update.effective_message, "- Pengaturan pelaporan\n")
					if imp_rules:
						text += tl(update.effective_message, "- Pesan peraturan grup\n")
					if imp_lang:
						text += tl(update.effective_message, "- Pengaturan bahasa\n")
					if imp_warn:
						text += tl(update.effective_message, "- Pengaturan peringatan\n")
					try:
						send_message(update.effective_message, text, parse_mode="markdown")
					except BadRequest:
						send_message(update.effective_message, text, parse_mode="markdown", quote=False)
					if NOT_IMPORTED_INT:
						f = open("{}-notimported.txt".format(chat_id), "w")
						f.write(str(NOT_IMPORTED))
						f.close()
						bot.sendDocument(chat_id, document=open('{}-notimported.txt'.format(chat_id), 'rb'), caption=tl(update.effective_message, "*Data yang tidak dapat di import*"), timeout=360, parse_mode=ParseMode.MARKDOWN)
						os.remove("{}-notimported.txt".format(chat_id))
					return
		except Exception as err:
			send_message(update.effective_message, tl(update.effective_message, "Telah terjadi kesalahan dalam import backup Rose!\nGabung ke [Grup support](https://t.me/joinchat/Fykz0VTMpqZvlkb8S0JevQ) kami untuk melaporkan dan mengatasi masalah ini!\n\nTerima kasih"), parse_mode="markdown")
			LOGGER.exception("An error when importing from Rose base!")
			return

		# only import one group
		if len(data) > 1 and str(chat_id) not in data:
			send_message(update.effective_message, tl(update.effective_message, "Ada lebih dari satu grup di file ini, dan tidak ada yang memiliki id obrolan yang sama dengan"
						   "grup ini - bagaimana cara memilih apa yang akan diimpor?"))
			return

		# Check if backup is this chat
		try:
			if data.get(str(chat_id)) == None:
				if conn:
					text = tl(update.effective_message, "Backup berasal chat lain, Saya tidak bisa mengembalikan chat lain kedalam chat *{}*").format(chat_name)
				else:
					text = tl(update.effective_message, "Backup berasal chat lain, Saya tidak bisa mengembalikan chat lain kedalam chat ini")
				return send_message(update.effective_message, text, parse_mode="markdown")
		except:
			return send_message(update.effective_message, tl(update.effective_message, "Telah terjadi error dalam pengecekan data, silahkan laporkan kepada pembuat saya "
								  "untuk masalah ini untuk membuat saya lebih baik! Terima kasih! 🙂"))
		# Check if backup is from self
		try:
			if str(bot.id) != str(data[str(chat_id)]['bot']):
				return send_message(update.effective_message, tl(update.effective_message, "Backup berasal dari bot lain, dokumen, foto, video, audio, suara tidak akan "
							   "bekerja, jika file anda tidak ingin hilang, import dari bot yang dicadangkan."
							   "jika masih tidak bekerja, laporkan pada pembuat bot tersebut untuk "
							   "membuat saya lebih baik! Terima kasih! 🙂"))
		except:
			pass
		# Select data source
		if str(chat_id) in data:
			data = data[str(chat_id)]['hashes']
		else:
			data = data[list(data.keys())[0]]['hashes']

		try:
			for mod in DATA_IMPORT:
				mod.__import_data__(str(chat_id), data)
		except Exception:
			send_message(update.effective_message, tl(update.effective_message, "Kesalahan terjadi saat memulihkan data Anda. Prosesnya mungkin tidak lengkap. Jika "
						   "Anda mengalami masalah dengan ini, pesan @AyraHikari dengan file cadangan Anda, jadi "
						   "masalah bisa di-debug. Pemilik saya akan dengan senang hati membantu, dan setiap bug "
						   "dilaporkan membuat saya lebih baik! Terima kasih! 🙂"))
			LOGGER.exception("Impor untuk id chat %s dengan nama %s gagal.", str(chat_id), str(chat.title))
			return

		# TODO: some of that link logic
		# NOTE: consider default permissions stuff?
		if conn:
			text = tl(update.effective_message, "Cadangan sepenuhnya dikembalikan pada *{}*. Selamat datang kembali! 😀").format(chat_name)
		else:
			text = tl(update.effective_message, "Cadangan sepenuhnya dikembalikan. Selamat datang kembali! 😀").format(chat_name)
		send_message(update.effective_message, text, parse_mode="markdown")


@run_async
@user_admin
def export_data(bot: Bot, update: Update, chat_data):
	msg = update.effective_message  # type: Optional[Message]
	user = update.effective_user  # type: Optional[User]
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return

	chat_id = update.effective_chat.id
	chat = update.effective_chat
	current_chat_id = update.effective_chat.id

	conn = connected(bot, update, chat, user.id, need_admin=True)
	if conn:
		chat = dispatcher.bot.getChat(conn)
		chat_id = conn
		chat_name = dispatcher.bot.getChat(conn).title
	else:
		if update.effective_message.chat.type == "private":
			send_message(update.effective_message, tl(update.effective_message, "Anda bisa lakukan command ini pada grup, bukan pada PM"))
			return ""
		chat = update.effective_chat
		chat_id = update.effective_chat.id
		chat_name = update.effective_message.chat.title

	jam = time.time()
	new_jam = jam + 43200
	cek = get_chat(chat_id, chat_data)
	if cek.get('status'):
		if jam <= int(cek.get('value')):
			waktu = time.strftime("%H:%M:%S %d/%m/%Y", time.localtime(cek.get('value')))
			send_message(update.effective_message, tl(update.effective_message, "Anda dapat mencadangan data sekali dalam 12 jam!\n[Orang ini](tg://user?id={}) sudah mencadangan data\nAnda dapat mencadangan data lagi pada `{}`").format(cek.get('user'), waktu), parse_mode=ParseMode.MARKDOWN)
			return
		else:
			if user.id != OWNER_ID:
				put_chat(chat_id, user.id, new_jam, chat_data)
	else:
		if user.id != OWNER_ID:
			put_chat(chat_id, user.id, new_jam, chat_data)


	# Backup version
	# Revision: 07/07/2019
	backup_ver = 1
	bot_base = "Emilia"

	# Make sure this backup is for this bot
	bot_id = bot.id

	# Backuping antiflood
	flood_mode, flood_duration = antifloodsql.get_flood_setting(chat_id)
	flood_limit = antifloodsql.get_flood_limit(chat_id)
	antiflood = {'flood_mode': flood_mode, 'flood_duration': flood_duration, 'flood_limit': flood_limit}

	# Backuping blacklists
	all_blacklisted = blacklistsql.get_chat_blacklist(chat_id)
	blacklist_mode, blacklist_duration = blacklistsql.get_blacklist_setting(chat.id)
	blacklists = {'blacklist_mode': blacklist_mode, 'blacklist_duration': blacklist_duration, 'blacklists': all_blacklisted}

	# Backuping blacklists sticker
	all_blsticker = blackliststksql.get_chat_stickers(chat_id)
	blsticker_mode, blsticker_duration = blacklistsql.get_blacklist_setting(chat.id)
	blstickers = {'blsticker_mode': blsticker_mode, 'blsticker_duration': blsticker_duration, 'blstickers': all_blsticker}

	# Backuping disabled
	cmd_disabled = disabledsql.get_all_disabled(chat_id)
	disabled = {'disabled': cmd_disabled}

	# Backuping filters
	all_filters = filtersql.get_chat_triggers(chat_id)
	filters_gen = []
	for x in all_filters:
		filt = filtersql.get_filter(chat.id, x)
		if filt.is_sticker:
			filt_type = 1
		elif filt.is_document:
			filt_type = 2
		elif filt.is_image:
			filt_type = 3
		elif filt.is_audio:
			filt_type = 4
		elif filt.is_voice:
			filt_type = 5
		elif filt.is_video:
			filt_type = 6
		elif filt.has_markdown:
			filt_type = 0
		else:
			filt_type = 7
		filters_gen.append({"name": x, "reply": filt.reply, "type": filt_type})
	filters = {'filters': filters_gen}

	# Backuping greetings msg and config
	greetings = {}
	pref, welcome_m, cust_content, welcome_type = welcsql.get_welc_pref(chat_id)
	if not welcome_m:
		welcome_m = ""
	if not cust_content:
		cust_content = ""
	buttons = welcsql.get_welc_buttons(chat_id)
	welcome_m += revert_buttons(buttons)
	greetings["welcome"] = {"enable": pref, "text": welcome_m, "content": cust_content, "type": welcome_type}

	pref, goodbye_m, cust_content, goodbye_type = welcsql.get_gdbye_pref(chat_id)
	if not goodbye_m:
		goodbye_m = ""
	if not cust_content:
		cust_content = ""
	buttons = welcsql.get_gdbye_buttons(chat_id)
	goodbye_m += revert_buttons(buttons)
	greetings["goodbye"] = {"enable": pref, "text": goodbye_m, "content": cust_content, "type": goodbye_type}

	curr = welcsql.clean_service(chat_id)
	greetings["clean_service"] = curr

	getcur, cur_value, cust_text = welcsql.welcome_security(chat_id)
	greetings["security"] = {"enable": getcur, "text": cust_text, "time": cur_value}

	# Backuping chat language
	getlang = langsql.get_lang(chat_id)
	language = {"language": getlang}

	# Backuping locks
	curr_locks = locksql.get_locks(chat_id)
	curr_restr = locksql.get_restr(chat_id)

	if curr_locks:
		locked_lock = {
			"sticker": curr_locks.sticker,
			"audio": curr_locks.audio,
			"voice": curr_locks.voice,
			"document": curr_locks.document,
			"video": curr_locks.video,
			"contact": curr_locks.contact,
			"photo": curr_locks.photo,
			"gif": curr_locks.gif,
			"url": curr_locks.url,
			"bots": curr_locks.bots,
			"forward": curr_locks.forward,
			"game": curr_locks.game,
			"location": curr_locks.location,
			"rtl": curr_locks.rtl
		}
	else:
		locked_lock = {}

	if curr_restr:
		locked_restr = {
			"messages": curr_restr.messages,
			"media": curr_restr.media,
			"other": curr_restr.other,
			"previews": curr_restr.preview,
			"all": all([curr_restr.messages, curr_restr.media, curr_restr.other, curr_restr.preview])
		}
	else:
		locked_restr = {}

	lock_warn = locksql.get_lockconf(chat_id)

	locks = {'lock_warn': lock_warn, 'locks': locked_lock, 'restrict': locked_restr}

	# Backuping notes
	note_list = notesql.get_all_chat_notes(chat_id)
	notes = []
	for note in note_list:
		buttonlist = ""
		note_tag = note.name
		note_type = note.msgtype
		getnote = notesql.get_note(chat_id, note.name)
		if not note.value:
			note_data = ""
		else:
			tombol = notesql.get_buttons(chat_id, note_tag)
			keyb = []
			buttonlist = ""
			for btn in tombol:
				if btn.same_line:
					buttonlist += "[{}](buttonurl:{}:same)\n".format(btn.name, btn.url)
				else:
					buttonlist += "[{}](buttonurl:{})\n".format(btn.name, btn.url)
			note_data = "{}\n\n{}".format(note.value, buttonlist)
		note_file = note.file
		if not note_file:
			note_file = ""
		notes.append({"note_tag": note_tag, "note_data": note_data, "note_file": note_file, "note_type": note_type})

	# Backuping reports
	get_report = reportsql.user_should_report(chat_id)
	report = {'report': get_report}

	# Backuping rules
	getrules = rulessql.get_rules(chat_id)
	rules = {"rules": getrules}

	# Backuping warns config and warn filters
	warn_limit, _, warn_mode = warnssql.get_warn_setting(chat_id)
	all_handlers = warnssql.get_chat_warn_triggers(chat_id)
	all_warn_filter = []
	for x in all_handlers:
		warnreply = warnssql.get_warn_filter(chat_id, x)
		all_warn_filter.append({'name': x, 'reason': warnreply.reply})
	if not warn_mode:
		warn_mode = ""
	# Get all warnings in current chat
	allwarns = warnssql.get_allwarns(chat_id)
	warns = {"warn_limit": warn_limit, "warn_mode": warn_mode, "warn_filters": all_warn_filter, "chat_warns": allwarns}


	# Parsing backups
	backup = {"bot_id": bot_id, "bot_base": bot_base, "antiflood": antiflood, "blacklists": blacklists, "blstickers": blstickers, "disabled": disabled, "filters": filters, "greetings": greetings, "language": language, "locks": locks, "notes": notes, "report": report, "rules": rules, "warns": warns, "version": backup_ver}


	all_backups = json.dumps(backup, indent=4, cls=SetEncoder)
	f = open("{}-Emilia.backup".format(chat_id), "w")
	f.write(str(all_backups))
	f.close()
	bot.sendChatAction(current_chat_id, "upload_document")
	tgl = time.strftime("%H:%M:%S - %d/%m/%Y", time.localtime(time.time()))
	try:
		bot.sendMessage(TEMPORARY_DATA, "*Berhasil mencadangan untuk:*\nNama chat: `{}`\nID chat: `{}`\nPada: `{}`".format(chat.title, chat_id, tgl), parse_mode=ParseMode.MARKDOWN)
	except BadRequest:
		pass
	send = bot.sendDocument(current_chat_id, document=open('{}-Emilia.backup'.format(chat_id), 'rb'), caption=tl(update.effective_message, "*Berhasil mencadangan untuk:*\nNama chat: `{}`\nID chat: `{}`\nPada: `{}`\n\nNote: cadangan ini khusus untuk bot ini, jika di import ke bot lain maka catatan dokumen, video, audio, voice, dan lain-lain akan hilang").format(chat.title, chat_id, tgl), timeout=360, reply_to_message_id=msg.message_id, parse_mode=ParseMode.MARKDOWN)
	try:
		# Send to temp data for prevent unexpected issue
		bot.sendDocument(TEMPORARY_DATA, document=send.document.file_id, caption=tl(update.effective_message, "*Berhasil mencadangan untuk:*\nNama chat: `{}`\nID chat: `{}`\nPada: `{}`\n\nNote: cadangan ini khusus untuk bot ini, jika di import ke bot lain maka catatan dokumen, video, audio, voice, dan lain-lain akan hilang").format(chat.title, chat_id, tgl), timeout=360, parse_mode=ParseMode.MARKDOWN)
	except BadRequest:
		pass
	os.remove("{}-Emilia.backup".format(chat_id)) # Cleaning file


class SetEncoder(json.JSONEncoder):
	def default(self, obj):
		if isinstance(obj, set):
			return list(obj)
		return json.JSONEncoder.default(self, obj)


# Temporary data
def put_chat(chat_id, user_id, value, chat_data):
	# print(chat_data)
	if value == False:
		status = False
	else:
		status = True
	chat_data[chat_id] = {'backups': {"status": status, "user": user_id, "value": value}}

def get_chat(chat_id, chat_data):
	# print(chat_data)
	try:
		value = chat_data[chat_id]['backups']
		return value
	except KeyError:
		return {"status": False, "user": None, "value": False}


__mod_name__ = "Import/Export"

__help__ = "backups_help"

IMPORT_HANDLER = CommandHandler("import", import_data, filters=Filters.group)
EXPORT_HANDLER = CommandHandler("export", export_data, pass_chat_data=True)
# EXPORT_HANDLER = CommandHandler("export", export_data, filters=Filters.user(OWNER_ID))

dispatcher.add_handler(IMPORT_HANDLER)
dispatcher.add_handler(EXPORT_HANDLER)
