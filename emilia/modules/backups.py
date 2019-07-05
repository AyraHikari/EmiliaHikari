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
from emilia.modules.helper_funcs.string_handling import button_markdown_parser

# SQL
import emilia.modules.sql.antiflood_sql as antifloodsql
import emilia.modules.sql.blacklist_sql as blacklistsql
from emilia.modules.sql import disable_sql as disabledsql
from emilia.modules.sql import cust_filters_sql as filtersql
from emilia.modules.sql import languages_sql as langsql
import emilia.modules.sql.locks_sql as locksql
from emilia.modules.sql import notes_sql as notesql
from emilia.modules.sql import reporting_sql as reportsql
import emilia.modules.sql.rules_sql as rulessql
from emilia.modules.sql import warns_sql as warnssql
import emilia.modules.sql.welcome_sql as welcsql

from emilia.modules.connection import connected

from emilia.modules.helper_funcs.msg_types import Types
from emilia.modules.languages import tl

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
			update.effective_message.reply_text(tl(update.effective_message, "Anda bisa lakukan command ini pada grup, bukan pada PM"))
			return ""
		chat = update.effective_chat
		chat_id = update.effective_chat.id
		chat_name = update.effective_message.chat.title

	if msg.reply_to_message and msg.reply_to_message.document:
		filetype = msg.reply_to_message.document.file_name
		if filetype.split('.')[-1] not in ("backup", "json", "txt"):
			msg.reply_text(tl(update.effective_message, "File cadangan tidak valid!"))
			return
		try:
			file_info = bot.get_file(msg.reply_to_message.document.file_id)
		except BadRequest:
			msg.reply_text(tl(update.effective_message, "Coba unduh dan unggah ulang file seperti Anda sendiri sebelum mengimpor - yang ini sepertinya rusak!"))
			return

		with BytesIO() as file:
			file_info.download(out=file)
			file.seek(0)
			data = json.load(file)

		# If backup is from miss rose
		# doing manual lol
		if data.get('bot_id') == 609517172:
			imp_antiflood = False
			imp_blacklist = False
			imp_blacklist_count = 0
			imp_disabled_count = 0
			imp_filters_count = 0
			imp_greet = False
			imp_notes = 0
			imp_report = False
			imp_rules = False
			imp_lang = False
			imp_warn = False
			if data.get('data'):
				# Import antiflood
				if data['data'].get('antiflood'):
					floodlimit = data['data']['antiflood'].get('flood_limit')
					action = data['data']['antiflood'].get('action')
					# TODO
					# actionduration = data['data']['antiflood'].get('action_duration')
					antifloodsql.set_flood(chat_id, int(floodlimit))
					if action == "ban":
						antifloodsql.set_flood_strength(chat_id, 1, "0")
						imp_antiflood = True
					elif action == "kick":
						antifloodsql.set_flood_strength(chat_id, 2, "0")
						imp_antiflood = True
					elif action == "mute":
						antifloodsql.set_flood_strength(chat_id, 3, "0")
						imp_antiflood = True
				# Import blacklist
				if data['data'].get('blacklists'):
					action = data['data']['blacklists'].get('action')
					strengthdone = False
					if action == "del":
						strengthdone = True
						blacklistsql.set_blacklist_strength(chat_id, 1, "0")
						imp_blacklist = True
					elif action == "warn":
						strengthdone = True
						blacklistsql.set_blacklist_strength(chat_id, 2, "0")
						imp_blacklist = True
					elif action == "mute":
						strengthdone = True
						blacklistsql.set_blacklist_strength(chat_id, 3, "0")
						imp_blacklist = True
					elif action == "kick":
						strengthdone = True
						blacklistsql.set_blacklist_strength(chat_id, 4, "0")
						imp_blacklist = True
					elif action == "ban":
						strengthdone = True
						blacklistsql.set_blacklist_strength(chat_id, 5, "0")
						imp_blacklist = True
					else:
						if not strengthdone:
							action = data['data']['blacklists'].get('should_delete')
							if action:
								blacklistsql.set_blacklist_strength(chat_id, 1, "0")
								imp_blacklist = True
					blacklisted = data['data']['blacklists'].get('filters')
					for x in blacklisted:
						blacklistsql.add_to_blacklist(chat_id, x['name'].lower())
						imp_blacklist_count += 1
				# Import disabled
				if data['data'].get('disabled'):
					candisable = disabledsql.get_disableable()
					for listdisabled in data['data']['disabled'].get('disabled'):
						if listdisabled in candisable:
							disabledsql.disable_command(chat_id, listdisabled)
							imp_disabled_count += 1
				# Import filters
				if data['data'].get('filters'):
					for x in data['data']['filters'].get('filters'):
						if x['type'] == 0:
							note_data, buttons = button_markdown_parser(x['text'].replace("\\", ""), entities=0)
							filtersql.add_filter(chat_id, x['name'], note_data, False, False, False, False, False, False, buttons)
							imp_filters_count += 1
				# Import greetings
				if data['data'].get('greetings'):
					if data['data']['greetings'].get('welcome'):
						welctext = data['data']['greetings']['welcome'].get('text')
						if welctext:
							note_data, buttons = button_markdown_parser(welctext.replace("\\", ""), entities=0)
							welcsql.set_custom_welcome(chat_id, None, note_data, Types.TEXT, buttons)
							imp_greet = True
					# TODO for gbye
				# TODO Locks
				# Import notes
				if data['data'].get('notes'):
					allnotes = data['data']['notes']['notes']
					for x in allnotes:
						# If this text
						if x['type'] == 0:
							note_data, buttons = button_markdown_parser(x['text'].replace("\\", ""), entities=0)
							note_name = x['name']
							notesql.add_note_to_db(chat_id, note_name, note_data, Types.TEXT, buttons, None)
							imp_notes += 1
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
					if action == "kick":
						warnssql.set_warn_mode(chat.id, 1)
						imp_warn = True
					elif action == "ban":
						warnssql.set_warn_mode(chat.id, 2)
						imp_warn = True
					elif action == "mute":
						warnssql.set_warn_mode(chat.id, 3)
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
				if imp_greet:
					text += tl(update.effective_message, "- Pesan salam\n")
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
				msg.reply_text(text, parse_mode="markdown")
				return

		# only import one group
		if len(data) > 1 and str(chat.id) not in data:
			msg.reply_text(tl(update.effective_message, "Ada lebih dari satu grup di file ini, dan tidak ada yang memiliki id obrolan yang sama dengan"
						   "grup ini - bagaimana cara memilih apa yang akan diimpor?"))
			return

		# Check if backup is this chat
		try:
			if data.get(str(chat.id)) == None:
				if conn:
					text = tl(update.effective_message, "Backup berasal chat lain, Saya tidak bisa mengembalikan chat lain kedalam chat *{}*").format(chat_name)
				else:
					text = tl(update.effective_message, "Backup berasal chat lain, Saya tidak bisa mengembalikan chat lain kedalam chat ini")
				return msg.reply_text(text, parse_mode="markdown")
		except:
			return msg.reply_text(tl(update.effective_message, "Telah terjadi error dalam pengecekan data, silahkan laporkan kepada pembuat saya "
								  "untuk masalah ini untuk membuat saya lebih baik! Terima kasih! 🙂"))
		# Check if backup is from self
		try:
			if str(bot.id) != str(data[str(chat.id)]['bot']):
				return msg.reply_text(tl(update.effective_message, "Backup berasal dari bot lain, dokumen, foto, video, audio, suara tidak akan "
							   "bekerja, jika file anda tidak ingin hilang, import dari bot yang dicadangkan."
							   "jika masih tidak bekerja, laporkan pada pembuat bot tersebut untuk "
							   "membuat saya lebih baik! Terima kasih! 🙂"))
		except:
			pass
		# Select data source
		if str(chat.id) in data:
			data = data[str(chat.id)]['hashes']
		else:
			data = data[list(data.keys())[0]]['hashes']

		try:
			for mod in DATA_IMPORT:
				mod.__import_data__(str(chat.id), data)
		except Exception:
			msg.reply_text(tl(update.effective_message, "Kesalahan terjadi saat memulihkan data Anda. Prosesnya mungkin tidak lengkap. Jika "
						   "Anda mengalami masalah dengan ini, pesan @AyraHikari dengan file cadangan Anda, jadi "
						   "masalah bisa di-debug. Pemilik saya akan dengan senang hati membantu, dan setiap bug "
						   "dilaporkan membuat saya lebih baik! Terima kasih! 🙂"))
			LOGGER.exception("Impor untuk id chat %s dengan nama %s gagal.", str(chat.id), str(chat.title))
			return

		# TODO: some of that link logic
		# NOTE: consider default permissions stuff?
		if conn:
			text = tl(update.effective_message, "Cadangan sepenuhnya dikembalikan pada *{}*. Selamat datang kembali! 😀").format(chat_name)
		else:
			text = tl(update.effective_message, "Cadangan sepenuhnya dikembalikan. Selamat datang kembali! 😀").format(chat_name)
		msg.reply_text(text, parse_mode="markdown")


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
			update.effective_message.reply_text(tl(update.effective_message, "Anda bisa lakukan command ini pada grup, bukan pada PM"))
			return ""
		chat = update.effective_chat
		chat_id = update.effective_chat.id
		chat_name = update.effective_message.chat.title

	jam = time.time()
	new_jam = jam + 10800
	cek = get_chat(chat_id, chat_data)
	if cek.get('status'):
		if jam <= int(cek.get('value')):
			waktu = time.strftime("%H:%M:%S %d/%m/%Y", time.localtime(cek.get('value')))
			update.effective_message.reply_text(tl(update.effective_message, "Anda dapat mencadangan data sekali dalam 3 jam!\nAnda dapat mencadangan data lagi pada `{}`").format(waktu), parse_mode=ParseMode.MARKDOWN)
			return
		else:
			if user.id != 388576209:
				put_chat(chat_id, new_jam, chat_data)
	else:
		if user.id != 388576209:
			put_chat(chat_id, new_jam, chat_data)

	note_list = sql.get_all_chat_notes(chat_id)
	backup = {}
	notes = {}
	button = ""
	buttonlist = []
	namacat = ""
	isicat = ""
	rules = ""
	count = 0
	countbtn = 0
	# Notes
	for note in note_list:
		count += 1
		getnote = sql.get_note(chat_id, note.name)
		namacat += '{}<###splitter###>'.format(note.name)
		if note.msgtype == 1:
			tombol = sql.get_buttons(chat_id, note.name)
			keyb = []
			for btn in tombol:
				countbtn += 1
				if btn.same_line:
					buttonlist.append(('{}'.format(btn.name), '{}'.format(btn.url), True))
				else:
					buttonlist.append(('{}'.format(btn.name), '{}'.format(btn.url), False))
			isicat += '###button###: {}<###button###>{}<###splitter###>'.format(note.value,str(buttonlist))
			buttonlist.clear()
		elif note.msgtype == 2:
			isicat += '###sticker###:{}<###splitter###>'.format(note.file)
		elif note.msgtype == 3:
			isicat += '###file###:{}<###TYPESPLIT###>{}<###splitter###>'.format(note.file, note.value)
		elif note.msgtype == 4:
			isicat += '###photo###:{}<###TYPESPLIT###>{}<###splitter###>'.format(note.file, note.value)
		elif note.msgtype == 5:
			isicat += '###audio###:{}<###TYPESPLIT###>{}<###splitter###>'.format(note.file, note.value)
		elif note.msgtype == 6:
			isicat += '###voice###:{}<###TYPESPLIT###>{}<###splitter###>'.format(note.file, note.value)
		elif note.msgtype == 7:
			isicat += '###video###:{}<###TYPESPLIT###>{}<###splitter###>'.format(note.file, note.value)
		elif note.msgtype == 8:
			isicat += '###video_note###:{}<###TYPESPLIT###>{}<###splitter###>'.format(note.file, note.value)
		else:
			isicat += '{}<###splitter###>'.format(note.value)
	for x in range(count):
		notes['#{}'.format(namacat.split("<###splitter###>")[x])] = '{}'.format(isicat.split("<###splitter###>")[x])
	# Rules
	rules = rulessql.get_rules(chat_id)
	# Blacklist
	bl = list(blacklistsql.get_chat_blacklist(chat_id))
	# Disabled command
	disabledcmd = list(disabledsql.get_all_disabled(chat_id))
	# Filters (TODO)
	"""
	all_filters = list(filtersql.get_chat_triggers(chat_id))
	export_filters = {}
	for filters in all_filters:
		filt = filtersql.get_filter(chat_id, filters)
		# print(vars(filt))
		if filt.is_sticker:
			tipefilt = "sticker"
		elif filt.is_document:
			tipefilt = "doc"
		elif filt.is_image:
			tipefilt = "img"
		elif filt.is_audio:
			tipefilt = "audio"
		elif filt.is_voice:
			tipefilt = "voice"
		elif filt.is_video:
			tipefilt = "video"
		elif filt.has_buttons:
			tipefilt = "button"
			buttons = filtersql.get_buttons(chat.id, filt.keyword)
			print(vars(buttons))
		elif filt.has_markdown:
			tipefilt = "text"
		if tipefilt == "button":
			content = "{}#=#{}|btn|{}".format(tipefilt, filt.reply, buttons)
		else:
			content = "{}#=#{}".format(tipefilt, filt.reply)
		print(content)
		export_filters[filters] = content
	print(export_filters)
	"""
	# Welcome (TODO)
	# welc = welcsql.get_welc_pref(chat_id)
	# Locked
	locks = locksql.get_locks(chat_id)
	locked = []
	if locks:
		if locks.sticker:
			locked.append('sticker')
		if locks.document:
			locked.append('document')
		if locks.contact:
			locked.append('contact')
		if locks.audio:
			locked.append('audio')
		if locks.game:
			locked.append('game')
		if locks.bots:
			locked.append('bots')
		if locks.gif:
			locked.append('gif')
		if locks.photo:
			locked.append('photo')
		if locks.video:
			locked.append('video')
		if locks.voice:
			locked.append('voice')
		if locks.location:
			locked.append('location')
		if locks.forward:
			locked.append('forward')
		if locks.url:
			locked.append('url')
		restr = locksql.get_restr(chat_id)
		if restr.other:
			locked.append('other')
		if restr.messages:
			locked.append('messages')
		if restr.preview:
			locked.append('preview')
		if restr.media:
			locked.append('media')
	# Warns (TODO)
	# warns = warnssql.get_warns(chat_id)
	# Backing up
	backup[chat_id] = {'bot': bot.id, 'hashes': {'info': {'rules': rules}, 'extra': notes, 'blacklist': bl, 'disabled': disabledcmd, 'locks': locked}}
	catatan = json.dumps(backup, indent=4)
	f=open("cadangan{}.backup".format(chat_id), "w")
	f.write(str(catatan))
	f.close()
	bot.sendChatAction(current_chat_id, "upload_document")
	tgl = time.strftime("%H:%M:%S - %d/%m/%Y", time.localtime(time.time()))
	try:
		bot.sendMessage(TEMPORARY_DATA, "*Berhasil mencadangan untuk:*\nNama chat: `{}`\nID chat: `{}`\nPada: `{}`".format(chat.title, chat_id, tgl), parse_mode=ParseMode.MARKDOWN)
	except BadRequest:
		pass
	bot.sendDocument(current_chat_id, document=open('cadangan{}.backup'.format(chat_id), 'rb'), caption=tl(update.effective_message, "*Berhasil mencadangan untuk:*\nNama chat: `{}`\nID chat: `{}`\nPada: `{}`\n\nNote: cadangan ini khusus untuk bot ini, jika di import ke bot lain maka catatan dokumen, video, audio, voice, dan lain-lain akan hilang").format(chat.title, chat_id, tgl), timeout=360, reply_to_message_id=msg.message_id, parse_mode=ParseMode.MARKDOWN)
	os.remove("cadangan{}.backup".format(chat_id)) # Cleaning file


# Temporary data
def put_chat(chat_id, value, chat_data):
	# print(chat_data)
	if value == False:
		status = False
	else:
		status = True
	chat_data[chat_id] = {'backups': {"status": status, "value": value}}

def get_chat(chat_id, chat_data):
	# print(chat_data)
	try:
		value = chat_data[chat_id]['backups']
		return value
	except KeyError:
		return {"status": False, "value": False}


__mod_name__ = "Import/Export"

__help__ = "backups_help"

IMPORT_HANDLER = CommandHandler("import", import_data)
EXPORT_HANDLER = CommandHandler("export", export_data, pass_chat_data=True)
# EXPORT_HANDLER = CommandHandler("export", export_data, filters=Filters.user(OWNER_ID))

dispatcher.add_handler(IMPORT_HANDLER)
dispatcher.add_handler(EXPORT_HANDLER)
