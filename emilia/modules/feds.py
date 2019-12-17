import html
from io import BytesIO
from typing import Optional, List
import random
import uuid
import re
import json
import time
import csv
import os
from time import sleep

from future.utils import string_types
from telegram.error import BadRequest, TelegramError, Unauthorized
from telegram import ParseMode, Update, Bot, Chat, User, MessageEntity, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import run_async, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram.utils.helpers import escape_markdown, mention_html, mention_markdown

from emilia import dispatcher, OWNER_ID, SUDO_USERS, WHITELIST_USERS, TEMPORARY_DATA, LOGGER, spamfilters
from emilia.modules.helper_funcs.handlers import CMD_STARTERS
from emilia.modules.helper_funcs.misc import is_module_loaded, send_to_list
from emilia.modules.helper_funcs.chat_status import is_user_admin
from emilia.modules.helper_funcs.extraction import extract_user, extract_unt_fedban, extract_user_fban
from emilia.modules.helper_funcs.string_handling import markdown_parser
from emilia.modules.disable import DisableAbleCommandHandler

import emilia.modules.sql.feds_sql as sql
from emilia.modules.languages import tl

from emilia.modules.connection import connected
from emilia.modules.helper_funcs.alternate import send_message

# Hello bot owner, I spended for feds many hours of my life, Please don't remove this if you still respect MrYacha and peaktogoo and AyraHikari too
# Federation by MrYacha 2018-2019
# Federation rework by Mizukito Akito 2019
# Federation update v2 by Ayra Hikari 2019
# 
# Time spended on feds = 10h by #MrYacha
# Time spended on reworking on the whole feds = 22+ hours by @peaktogoo
# Time spended on updating version to v2 = 26+ hours by @AyraHikari
# 
# Total spended for making this features is 68+ hours

# LOGGER.info("Original federation module by MrYacha, reworked by Mizukito Akito (@peaktogoo) on Telegram.")

FBAN_ERRORS = {
	"User is an administrator of the chat",
	"Chat not found",
	"Not enough rights to restrict/unrestrict chat member",
	"User_not_participant",
	"Peer_id_invalid",
	"Group chat was deactivated",
	"Need to be inviter of a user to kick it from a basic group",
	"Chat_admin_required",
	"Only the creator of a basic group can kick group administrators",
	"Channel_private",
	"Not in the chat",
	"Have no rights to send a message"
}

UNFBAN_ERRORS = {
	"User is an administrator of the chat",
	"Chat not found",
	"Not enough rights to restrict/unrestrict chat member",
	"User_not_participant",
	"Method is available for supergroup and channel chats only",
	"Not in the chat",
	"Channel_private",
	"Chat_admin_required",
	"Have no rights to send a message"
}

@run_async
def new_fed(bot: Bot, update: Update):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return

	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	message = update.effective_message
	if chat.type != "private":
		send_message(update.effective_message, tl(update.effective_message, "Buat federasi Anda di PM saya, bukan dalam grup."))
		return
	if len(message.text) == 1:
		send_message(update.effective_message, tl(update.effective_message, "Tolong tulis nama federasinya!"))
		return
	fednam = message.text.split(None, 1)[1]
	if not fednam == '':
		fed_id = str(uuid.uuid4())
		fed_name = fednam
		LOGGER.info(fed_id)

		# Currently only for creator
		if fednam == "Team Nusantara Disciplinary Circle":
			fed_id = "TeamNusantaraDevs"
		elif fednam == "Emilia Official Support":
			fed_id = "EmiliaSupport"

		x = sql.new_fed(user.id, fed_name, fed_id)
		if not x:
			send_message(update.effective_message, tl(update.effective_message, "Tidak dapat membuat federasi! Tolong hubungi pembuat saya jika masalah masih berlanjut."))
			return

		send_message(update.effective_message, tl(update.effective_message, "*Anda telah berhasil membuat federasi baru!*"\
											"\nNama: `{}`"\
											"\nID: `{}`"
											"\n\nGunakan perintah di bawah ini untuk bergabung dengan federasi:"
											"\n`/joinfed {}`").format(fed_name, fed_id, fed_id), parse_mode=ParseMode.MARKDOWN)
		try:
			bot.send_message(TEMPORARY_DATA,
				"Federasi <b>{}</b> telah di buat dengan ID: <pre>{}</pre>".format(fed_name, fed_id), parse_mode=ParseMode.HTML)
		except:
			LOGGER.warning("Cannot send a message to TEMPORARY_DATA")
	else:
		send_message(update.effective_message, tl(update.effective_message, "Tolong tulis nama federasinya!"))

@run_async
def del_fed(bot: Bot, update: Update, args: List[str]):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return

	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	if chat.type != "private":
		send_message(update.effective_message, tl(update.effective_message, "Hapus federasi Anda di PM saya, bukan dalam grup."))
		return
	if args:
		is_fed_id = args[0]
		getinfo = sql.get_fed_info(is_fed_id)
		if getinfo == False:
			send_message(update.effective_message, tl(update.effective_message, "Federasi ini tidak di temukan!"))
			return
		if int(getinfo['owner']) == int(user.id) or int(user.id) == OWNER_ID:
			fed_id = is_fed_id
		else:
			send_message(update.effective_message, tl(update.effective_message, "Hanya pemilik federasi yang dapat melakukan ini!"))
			return
	else:
		send_message(update.effective_message, tl(update.effective_message, "Apa yang harus saya hapus?"))
		return

	if is_user_fed_owner(fed_id, user.id) == False:
		send_message(update.effective_message, tl(update.effective_message, "Hanya pemilik federasi yang dapat melakukan ini!"))
		return

	send_message(update.effective_message, tl(update.effective_message, "Anda yakin ingin menghapus federasi Anda? Tindakan ini tidak bisa dibatalkan, Anda akan kehilangan seluruh daftar larangan Anda, dan '{}' akan hilang secara permanen.").format(getinfo['fname']),
			reply_markup=InlineKeyboardMarkup(
						[[InlineKeyboardButton(text=tl(update.effective_message, "⚠️ Hapus Federasi ⚠️"), callback_data="rmfed_{}".format(fed_id))],
						[InlineKeyboardButton(text=tl(update.effective_message, "Batalkan"), callback_data="rmfed_cancel")]]))

@run_async
def fed_chat(bot: Bot, update: Update, args: List[str]):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return

	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	fed_id = sql.get_fed_id(chat.id)

	user_id = update.effective_message.from_user.id
	if not is_user_admin(update.effective_chat, user_id):
		send_message(update.effective_message, tl(update.effective_message, "Anda harus menjadi admin untuk menjalankan perintah ini"))
		return

	if not fed_id:
		send_message(update.effective_message, tl(update.effective_message, "Grup ini tidak dalam federasi apa pun!"))
		return

	user = update.effective_user  # type: Optional[Chat]
	chat = update.effective_chat  # type: Optional[Chat]
	info = sql.get_fed_info(fed_id)

	text = tl(update.effective_message, "Obrolan ini adalah bagian dari federasi berikut:")
	text += "\n{} (ID: <code>{}</code>)".format(info['fname'], fed_id)

	send_message(update.effective_message, text, parse_mode=ParseMode.HTML)

@run_async
def join_fed(bot: Bot, update: Update, args: List[str]):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return

	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]

	if chat.type == 'private':
		send_message(update.effective_message, tl(update.effective_message, "Perintah ini di khususkan untuk grup, bukan pada PM!"))
		return

	message = update.effective_message
	administrators = chat.get_administrators()
	fed_id = sql.get_fed_id(chat.id)

	if user.id in SUDO_USERS:
		pass
	else:
		for admin in administrators:
			status = admin.status
			if status == "creator":
				if str(admin.user.id) == str(user.id):
					pass
				else:
					send_message(update.effective_message, tl(update.effective_message, "Hanya pembuat grup yang dapat melakukannya!"))
					return
	if fed_id:
		send_message(update.effective_message, tl(update.effective_message, "Anda tidak bisa bergabung dua federasi dalam satu obrolan"))
		return

	if len(args) >= 1:
		getfed = sql.search_fed_by_id(args[0])
		if getfed == False:
			send_message(update.effective_message, tl(update.effective_message, "Silakan masukkan id federasi yang valid."))
			return

		x = sql.chat_join_fed(args[0], chat.title, chat.id)
		if not x:
			send_message(update.effective_message, tl(update.effective_message, "Gagal bergabung dengan federasi! Tolong hubungi pembuat saya jika masalah ini masih berlanjut."))
			return

		get_fedlog = sql.get_fed_log(args[0])
		if get_fedlog:
			if eval(get_fedlog):
				bot.send_message(get_fedlog, tl(update.effective_message, "Obrolan *{}* telah bergabung ke federasi *{}*").format(chat.title, getfed['fname']), parse_mode="markdown")

		send_message(update.effective_message, tl(update.effective_message, "Obrolan ini telah bergabung dengan federasi {}!").format(getfed['fname']))

@run_async
def leave_fed(bot: Bot, update: Update, args: List[str]):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return

	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]

	if chat.type == 'private':
		send_message(update.effective_message, tl(update.effective_message, "Perintah ini di khususkan untuk grup, bukan pada PM!"))
		return

	fed_id = sql.get_fed_id(chat.id)
	fed_info = sql.get_fed_info(fed_id)

	# administrators = chat.get_administrators().status
	getuser = bot.get_chat_member(chat.id, user.id).status
	if getuser in 'creator' or user.id in SUDO_USERS:
		if sql.chat_leave_fed(chat.id) == True:
			get_fedlog = sql.get_fed_log(fed_id)
			if get_fedlog:
				if eval(get_fedlog):
					bot.send_message(get_fedlog, tl(update.effective_message, "Obrolan *{}* telah keluar ke federasi *{}*").format(chat.title, fed_info['fname']), parse_mode="markdown")
			send_message(update.effective_message, tl(update.effective_message, "Obrolan ini telah keluar dari federasi {}!").format(fed_info['fname']))
		else:
			send_message(update.effective_message, tl(update.effective_message, "Mengapa Anda meninggalkan federasi ketika Anda belum bergabung?!"))
	else:
		send_message(update.effective_message, tl(update.effective_message, "Hanya pembuat grup yang dapat melakukannya!"))

@run_async
def user_join_fed(bot: Bot, update: Update, args: List[str]):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return

	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	msg = update.effective_message  # type: Optional[Message]

	if chat.type == 'private':
		send_message(update.effective_message, tl(update.effective_message, "Perintah ini di khususkan untuk grup, bukan pada PM!"))
		return

	fed_id = sql.get_fed_id(chat.id)

	if is_user_fed_owner(fed_id, user.id):
		user_id = extract_user(msg, args)
		if user_id:
			user = bot.get_chat(user_id)
		elif not msg.reply_to_message and not args:
			user = msg.from_user
		elif not msg.reply_to_message and (not args or (
			len(args) >= 1 and not args[0].startswith("@") and not args[0].isdigit() and not msg.parse_entities(
			[MessageEntity.TEXT_MENTION]))):
			send_message(update.effective_message, tl(update.effective_message, "Saya tidak dapat mengekstrak pengguna dari ini."))
			return
		else:
			LOGGER.warning('error')
		getuser = sql.search_user_in_fed(fed_id, user_id)
		fed_id = sql.get_fed_id(chat.id)
		info = sql.get_fed_info(fed_id)
		get_owner = eval(info['fusers'])['owner']
		get_owner = bot.get_chat(get_owner).id
		if user_id == get_owner:
			send_message(update.effective_message, tl(update.effective_message, "Mengapa Anda mencoba mempromosikan pemilik federasi!?"))
			return
		if getuser:
			send_message(update.effective_message, tl(update.effective_message, "Saya tidak dapat mempromosikan pengguna yang sudah menjadi admin federasi! Tapi saya bisa menurunkannya."))
			return
		if user_id == bot.id:
			send_message(update.effective_message, tl(update.effective_message, "Saya sudah menjadi admin federasi dan yang mengelolanya!"))
			return
		res = sql.user_join_fed(fed_id, user_id)
		if res:
			send_message(update.effective_message, tl(update.effective_message, "💖 Berhasil dinaikan jabatannya!"))
		else:
			send_message(update.effective_message, tl(update.effective_message, "Gagal dipromosikan!"))
	else:
		send_message(update.effective_message, tl(update.effective_message, "Hanya pemilik federasi yang dapat melakukan ini!"))


@run_async
def user_demote_fed(bot: Bot, update: Update, args: List[str]):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return

	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]

	if chat.type == 'private':
		send_message(update.effective_message, tl(update.effective_message, "Perintah ini di khususkan untuk grup, bukan pada PM!"))
		return

	fed_id = sql.get_fed_id(chat.id)

	if is_user_fed_owner(fed_id, user.id):
		msg = update.effective_message  # type: Optional[Message]
		user_id = extract_user(msg, args)
		if user_id:
			user = bot.get_chat(user_id)

		elif not msg.reply_to_message and not args:
			user = msg.from_user

		elif not msg.reply_to_message and (not args or (
			len(args) >= 1 and not args[0].startswith("@") and not args[0].isdigit() and not msg.parse_entities(
			[MessageEntity.TEXT_MENTION]))):
			send_message(update.effective_message, tl(update.effective_message, "Saya tidak dapat mengekstrak pengguna dari ini."))
			return
		else:
			LOGGER.warning('error')

		if user_id == bot.id:
			send_message(update.effective_message, tl(update.effective_message, "Apa yang sedang Anda coba lakukan? Menurunkan saya dari federasi Anda?"))
			return

		if sql.search_user_in_fed(fed_id, user_id) == False:
			send_message(update.effective_message, tl(update.effective_message, "Saya tidak dapat mendemosikan pengguna yang bukan merupakan admin federasi! Jika Anda ingin membuatnya menangis, promosikan dia terlebih dahulu!"))
			return

		res = sql.user_demote_fed(fed_id, user_id)
		if res == True:
			send_message(update.effective_message, tl(update.effective_message, "💔 Dia telah di keluarkan dari federasi anda!"))
		else:
			send_message(update.effective_message, tl(update.effective_message, "Saya tidak bisa mengusirnya, Saya tidak berdaya!"))
	else:
		send_message(update.effective_message, tl(update.effective_message, "Hanya pemilik federasi yang dapat melakukan ini!"))
		return

@run_async
def fed_info(bot: Bot, update: Update, args: List[str]):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return

	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	if args:
		fed_id = args[0]
		info = sql.get_fed_info(fed_id)
	else:
		fed_id = sql.get_fed_id(chat.id)
		if not fed_id:
			send_message(update.effective_message, tl(update.effective_message, "Grup ini tidak dalam federasi apa pun!"))
			return
		info = sql.get_fed_info(fed_id)

	if is_user_fed_admin(fed_id, user.id) == False:
		send_message(update.effective_message, tl(update.effective_message, "Hanya admin federasi yang dapat melakukan ini!"))
		return

	owner = bot.get_chat(info['owner'])
	try:
		owner_name = owner.first_name + " " + owner.last_name
	except:
		owner_name = owner.first_name
	FEDADMIN = sql.all_fed_users(fed_id)
	FEDADMIN.append(int(owner.id))
	TotalAdminFed = len(FEDADMIN)

	user = update.effective_user  # type: Optional[Chat]
	chat = update.effective_chat  # type: Optional[Chat]
	info = sql.get_fed_info(fed_id)

	text = tl(update.effective_message, "<b>ℹ️ Info federasi:</b>")
	text += "\nFedID: <code>{}</code>".format(fed_id)
	text += tl(update.effective_message, "\nNama: {}").format(info['fname'])
	text += tl(update.effective_message, "\nPembuat: {}").format(mention_html(owner.id, owner_name))
	text += tl(update.effective_message, "\nSeluruh admin: <code>{}</code>").format(TotalAdminFed)
	getfban = sql.get_all_fban_users(fed_id)
	text += tl(update.effective_message, "\nTotal yang di banned: <code>{}</code>").format(len(getfban))
	getfchat = sql.all_fed_chats(fed_id)
	text += tl(update.effective_message, "\nTotal grup yang terkoneksi: <code>{}</code>").format(len(getfchat))

	send_message(update.effective_message, text, parse_mode=ParseMode.HTML)

@run_async
def fed_admin(bot: Bot, update: Update, args: List[str]):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return

	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]

	if chat.type == 'private':
		send_message(update.effective_message, tl(update.effective_message, "Perintah ini di khususkan untuk grup, bukan pada PM!"))
		return

	fed_id = sql.get_fed_id(chat.id)

	if not fed_id:
		send_message(update.effective_message, tl(update.effective_message, "Grup ini tidak dalam federasi apa pun!"))
		return

	if is_user_fed_admin(fed_id, user.id) == False:
		send_message(update.effective_message, tl(update.effective_message, "Hanya admin federasi yang dapat melakukan ini!"))
		return

	user = update.effective_user  # type: Optional[Chat]
	chat = update.effective_chat  # type: Optional[Chat]
	info = sql.get_fed_info(fed_id)

	text = tl(update.effective_message, "<b>Admin Federasi {}:</b>\n\n").format(info['fname'])
	text += "👑 Owner:\n"
	owner = bot.get_chat(info['owner'])
	try:
		owner_name = owner.first_name + " " + owner.last_name
	except:
		owner_name = owner.first_name
	text += " • {}\n".format(mention_html(owner.id, owner_name))

	members = sql.all_fed_members(fed_id)
	if len(members) == 0:
		text += tl(update.effective_message, "\n🔱 Tidak ada admin di federasi ini")
	else:
		text += "\n🔱 Admins:\n"
		for x in members:
			user = bot.get_chat(x) 
			text += " • {}\n".format(mention_html(user.id, user.first_name))

	send_message(update.effective_message, text, parse_mode=ParseMode.HTML)


@run_async
def fed_ban(bot: Bot, update: Update, args: List[str]):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return

	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]

	if chat.type == 'private':
		send_message(update.effective_message, tl(update.effective_message, "Perintah ini di khususkan untuk grup, bukan pada PM!"))
		return

	fed_id = sql.get_fed_id(chat.id)

	if not fed_id:
		send_message(update.effective_message, tl(update.effective_message, "Grup ini tidak dalam federasi apa pun!"))
		return

	info = sql.get_fed_info(fed_id)
	getfednotif = sql.user_feds_report(info['owner'])

	if is_user_fed_admin(fed_id, user.id) == False:
		send_message(update.effective_message, tl(update.effective_message, "Hanya admin federasi yang dapat melakukan ini!"))
		return

	message = update.effective_message  # type: Optional[Message]

	user_id, reason = extract_unt_fedban(message, args)

	fban, fbanreason, fbantime = sql.get_fban_user(fed_id, user_id)

	if not user_id:
		send_message(update.effective_message, tl(update.effective_message, "Anda sepertinya tidak merujuk ke pengguna."))
		return

	if user_id == bot.id:
		send_message(update.effective_message, tl(update.effective_message, "Apa yang lebih lucu dari menendang creator grup? Fban diri saya sendiri."))
		return

	if is_user_fed_owner(fed_id, user_id) == True:
		send_message(update.effective_message, tl(update.effective_message, "Mengapa Anda mencoba fban pemilik federasi?"))
		return

	if is_user_fed_admin(fed_id, user_id) == True:
		send_message(update.effective_message, tl(update.effective_message, "Dia adalah admin dari federasi, saya tidak bisa fban dia."))
		return

	if user_id == OWNER_ID:
		send_message(update.effective_message, tl(update.effective_message, "Aku tidak ingin memblokir tuanku, itu ide yang sangat bodoh!"))
		return

	if int(user_id) in SUDO_USERS:
		send_message(update.effective_message, tl(update.effective_message, "Saya tidak akan fban pengguna sudo!"))
		return

	if int(user_id) in WHITELIST_USERS:
		send_message(update.effective_message, tl(update.effective_message, "Orang ini masuk daftar putih, jadi tidak bisa di fban!"))
		return

	try:
		user_chat = bot.get_chat(user_id)
		isvalid = True
		fban_user_id = user_chat.id
		fban_user_name = user_chat.first_name
		fban_user_lname = user_chat.last_name
		fban_user_uname = user_chat.username
	except BadRequest as excp:
		if not str(user_id).isdigit():
			send_message(update.effective_message, excp.message)
			return
		elif not len(str(user_id)) == 9:
			send_message(update.effective_message, tl(update.effective_message, "Itu bukan pengguna!"))
			return
		isvalid = False
		fban_user_id = int(user_id)
		fban_user_name = "user({})".format(user_id)
		fban_user_lname = None
		fban_user_uname = None


	if isvalid and user_chat.type != 'private':
		send_message(update.effective_message, tl(update.effective_message, "Itu bukan pengguna!"))
		return

	if isvalid:
		user_target = mention_html(fban_user_id, fban_user_name)
	else:
		user_target = fban_user_name

	if fban:
		fed_name = info['fname']
		starting = tl(update.effective_message, "Alasan fban di ganti untuk {} pada Federasi <b>{}</b>.").format(user_target, fed_name)
		send_message(update.effective_message, starting, parse_mode=ParseMode.HTML)

		if reason == "":
			reason = tl(update.effective_message, "Tidak ada alasan.")

		temp = sql.un_fban_user(fed_id, fban_user_id)
		if not temp:
			send_message(update.effective_message, tl(update.effective_message, "Gagal mengupdate alasan fedban!"))
			return
		x = sql.fban_user(fed_id, fban_user_id, fban_user_name, fban_user_lname, fban_user_uname, reason, int(time.time()))
		if not x:
			send_message(update.effective_message, tl(update.effective_message, "Gagal melarangan federasi! Jika masalah ini terus terjadi, hubungi pembuat saya."))
			return

		fed_chats = sql.all_fed_chats(fed_id)
		# Will send to current chat
		bot.send_message(chat.id, tl(update.effective_message, "<b>Alasan FedBan Diperbarui</b>" \
								  "\n<b>Federasi:</b> {}" \
								  "\n<b>Federasi Admin:</b> {}" \
								  "\n<b>Pengguna:</b> {}" \
								  "\n<b>Pengguna ID:</b> <code>{}</code>" \
								  "\n<b>Alasan:</b> {}").format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
		# Send message to owner if fednotif is enabled
		if getfednotif:
			bot.send_message(info['owner'], tl(update.effective_message, "<b>Alasan FedBan Diperbarui</b>" \
											"\n<b>Federasi:</b> {}" \
											"\n<b>Federasi Admin:</b> {}" \
											"\n<b>Pengguna:</b> {}" \
											"\n<b>Pengguna ID:</b> <code>{}</code>" \
											"\n<b>Alasan:</b> {}").format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
		# If fedlog is set, then send message, except fedlog is current chat
		get_fedlog = sql.get_fed_log(fed_id)
		if get_fedlog:
			if int(get_fedlog) != int(chat.id):
				bot.send_message(get_fedlog, tl(update.effective_message, "<b>Alasan FedBan Diperbarui</b>" \
											"\n<b>Federasi:</b> {}" \
											"\n<b>Federasi Admin:</b> {}" \
											"\n<b>Pengguna:</b> {}" \
											"\n<b>Pengguna ID:</b> <code>{}</code>" \
											"\n<b>Alasan:</b> {}").format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
		for fedschat in fed_chats:
			try:
				# Do not spamming all fed chats
				"""
				bot.send_message(fedschat, "<b>Alasan FedBan Diperbarui</b>" \
							 "\n<b>Federasi:</b> {}" \
							 "\n<b>Federasi Admin:</b> {}" \
							 "\n<b>Pengguna:</b> {}" \
							 "\n<b>Pengguna ID:</b> <code>{}</code>" \
							 "\n<b>Alasan:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
				"""
				bot.kick_chat_member(fedschat, fban_user_id)
			except BadRequest as excp:
				if excp.message in FBAN_ERRORS:
					try:
						dispatcher.bot.getChat(fedschat)
					except Unauthorized:
						sql.chat_leave_fed(fedschat)
						LOGGER.info("Chat {} has leave fed {} because bot is kicked".format(fedschat, info['fname']))
						continue
				elif excp.message == "User_id_invalid":
					break
				else:
					LOGGER.warning("Tidak dapat fban di {} karena: {}".format(fedschat, excp.message))
			except TelegramError:
				pass

		# Also do not spamming all fed admins
		"""
		send_to_list(bot, FEDADMIN,
				 "<b>Alasan FedBan Diperbarui</b>" \
				 "\n<b>Federasi:</b> {}" \
				 "\n<b>Federasi Admin:</b> {}" \
				 "\n<b>Pengguna:</b> {}" \
				 "\n<b>Pengguna ID:</b> <code>{}</code>" \
				 "\n<b>Alasan:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), 
				html=True)
		"""

		# Fban for fed subscriber
		subscriber = list(sql.get_subscriber(fed_id))
		if len(subscriber) != 0:
			for fedsid in subscriber:
				all_fedschat = sql.all_fed_chats(fedsid)
				for fedschat in all_fedschat:
					try:
						bot.kick_chat_member(fedschat, fban_user_id)
					except BadRequest as excp:
						if excp.message in FBAN_ERRORS:
							try:
								dispatcher.bot.getChat(fedschat)
							except Unauthorized:
								targetfed_id = sql.get_fed_id(fedschat)
								sql.unsubs_fed(fed_id, targetfed_id)
								LOGGER.info("Chat {} has unsub fed {} because bot is kicked".format(fedschat, info['fname']))
								continue
						elif excp.message == "User_id_invalid":
							break
						else:
							LOGGER.warning("Tidak dapat fban di {} karena: {}".format(fedschat, excp.message))
					except TelegramError:
						pass
		send_message(update.effective_message, tl(update.effective_message, "Alasan fedban telah di perbarui."))
		return

	fed_name = info['fname']

	starting = tl(update.effective_message, "Memulai larangan federasi untuk {} pada Federasi <b>{}</b>.").format(user_target, fed_name)
	send_message(update.effective_message, starting, parse_mode=ParseMode.HTML)

	if reason == "":
		reason = tl(update.effective_message, "Tidak ada alasan.")

	x = sql.fban_user(fed_id, fban_user_id, fban_user_name, fban_user_lname, fban_user_uname, reason, int(time.time()))
	if not x:
		send_message(update.effective_message, tl(update.effective_message, "Gagal melarangan federasi! Jika masalah ini terus terjadi, hubungi pembuat saya."))
		return

	fed_chats = sql.all_fed_chats(fed_id)
	# Will send to current chat
	bot.send_message(chat.id, tl(update.effective_message, "<b>FedBan baru</b>" \
							  "\n<b>Federasi:</b> {}" \
							  "\n<b>Federasi Admin:</b> {}" \
							  "\n<b>Pengguna:</b> {}" \
							  "\n<b>Pengguna ID:</b> <code>{}</code>" \
							  "\n<b>Alasan:</b> {}").format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
	# Send message to owner if fednotif is enabled
	if getfednotif:
		bot.send_message(info['owner'], tl(update.effective_message, "<b>FedBan baru</b>" \
										"\n<b>Federasi:</b> {}" \
										"\n<b>Federasi Admin:</b> {}" \
										"\n<b>Pengguna:</b> {}" \
										"\n<b>Pengguna ID:</b> <code>{}</code>" \
										"\n<b>Alasan:</b> {}").format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
	# If fedlog is set, then send message, except fedlog is current chat
	get_fedlog = sql.get_fed_log(fed_id)
	if get_fedlog:
		if int(get_fedlog) != int(chat.id):
			bot.send_message(get_fedlog, tl(update.effective_message, "<b>FedBan baru</b>" \
										"\n<b>Federasi:</b> {}" \
										"\n<b>Federasi Admin:</b> {}" \
										"\n<b>Pengguna:</b> {}" \
										"\n<b>Pengguna ID:</b> <code>{}</code>" \
										"\n<b>Alasan:</b> {}").format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
	for fedschat in fed_chats:
		try:
			# Do not spamming all fed chats
			"""
			bot.send_message(fedschat, "<b>FedBan baru</b>" \
						 "\n<b>Federasi:</b> {}" \
						 "\n<b>Federasi Admin:</b> {}" \
						 "\n<b>Pengguna:</b> {}" \
						 "\n<b>Pengguna ID:</b> <code>{}</code>" \
						 "\n<b>Alasan:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
			"""
			bot.kick_chat_member(fedschat, fban_user_id)
		except BadRequest as excp:
			if excp.message in FBAN_ERRORS:
				pass
			elif excp.message == "User_id_invalid":
				break
			else:
				LOGGER.warning("Tidak dapat fban di {} karena: {}".format(fedschat, excp.message))
		except TelegramError:
			pass

	# Also do not spamming all fed admins
	"""
	send_to_list(bot, FEDADMIN,
			 "<b>FedBan baru</b>" \
			 "\n<b>Federasi:</b> {}" \
			 "\n<b>Federasi Admin:</b> {}" \
			 "\n<b>Pengguna:</b> {}" \
			 "\n<b>Pengguna ID:</b> <code>{}</code>" \
			 "\n<b>Alasan:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), 
			html=True)
	"""

	# Fban for fed subscriber
	subscriber = list(sql.get_subscriber(fed_id))
	if len(subscriber) != 0:
		for fedsid in subscriber:
			all_fedschat = sql.all_fed_chats(fedsid)
			for fedschat in all_fedschat:
				try:
					bot.kick_chat_member(fedschat, fban_user_id)
				except BadRequest as excp:
					if excp.message in FBAN_ERRORS:
						try:
							dispatcher.bot.getChat(fedschat)
						except Unauthorized:
							targetfed_id = sql.get_fed_id(fedschat)
							sql.unsubs_fed(fed_id, targetfed_id)
							LOGGER.info("Chat {} has unsub fed {} because bot is kicked".format(fedschat, info['fname']))
							continue
					elif excp.message == "User_id_invalid":
						break
					else:
						LOGGER.warning("Tidak dapat fban di {} karena: {}".format(fedschat, excp.message))
				except TelegramError:
					pass
	send_message(update.effective_message, tl(update.effective_message, "Orang ini telah di fbanned."))


@run_async
def unfban(bot: Bot, update: Update, args: List[str]):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return

	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	message = update.effective_message  # type: Optional[Message]

	if chat.type == 'private':
		send_message(update.effective_message, tl(update.effective_message, "Perintah ini di khususkan untuk grup, bukan pada PM!"))
		return

	fed_id = sql.get_fed_id(chat.id)

	if not fed_id:
		send_message(update.effective_message, tl(update.effective_message, "Grup ini tidak dalam federasi apa pun!"))
		return

	info = sql.get_fed_info(fed_id)
	getfednotif = sql.user_feds_report(info['owner'])

	if is_user_fed_admin(fed_id, user.id) == False:
		send_message(update.effective_message, tl(update.effective_message, "Hanya admin federasi yang dapat melakukan ini!"))
		return

	user_id = extract_user_fban(message, args)
	if not user_id:
		send_message(update.effective_message, tl(update.effective_message, "Anda sepertinya tidak merujuk ke pengguna."))
		return

	try:
		user_chat = bot.get_chat(user_id)
		isvalid = True
		fban_user_id = user_chat.id
		fban_user_name = user_chat.first_name
		fban_user_lname = user_chat.last_name
		fban_user_uname = user_chat.username
	except BadRequest as excp:
		if not str(user_id).isdigit():
			send_message(update.effective_message, excp.message)
			return
		elif not len(str(user_id)) == 9:
			send_message(update.effective_message, tl(update.effective_message, "Itu bukan pengguna!"))
			return
		isvalid = False
		fban_user_id = int(user_id)
		fban_user_name = "user({})".format(user_id)
		fban_user_lname = None
		fban_user_uname = None

	if isvalid and user_chat.type != 'private':
		send_message(update.effective_message, tl(update.effective_message, "Itu bukan pengguna!"))
		return

	if isvalid:
		user_target = mention_html(fban_user_id, fban_user_name)
	else:
		user_target = fban_user_name

	fban, fbanreason, fbantime = sql.get_fban_user(fed_id, fban_user_id)
	if fban == False:
		send_message(update.effective_message, tl(update.effective_message, "Pengguna ini tidak di fbanned!"))
		return

	banner = update.effective_user  # type: Optional[User]

	send_message(update.effective_message, tl(update.effective_message, "Saya akan memberi {} kesempatan kedua dalam federasi ini.").format(user_target), parse_mode="HTML")

	chat_list = sql.all_fed_chats(fed_id)
	# Will send to current chat
	bot.send_message(chat.id, tl(update.effective_message, "<b>Un-FedBan</b>" \
						 "\n<b>Federasi:</b> {}" \
						 "\n<b>Federasi Admin:</b> {}" \
						 "\n<b>Pengguna:</b> {}" \
						 "\n<b>Pengguna ID:</b> <code>{}</code>").format(info['fname'], mention_html(user.id, user.first_name), user_target, fban_user_id), parse_mode="HTML")
	# Send message to owner if fednotif is enabled
	if getfednotif:
		bot.send_message(info['owner'], tl(update.effective_message, "<b>Un-FedBan</b>" \
						 "\n<b>Federasi:</b> {}" \
						 "\n<b>Federasi Admin:</b> {}" \
						 "\n<b>Pengguna:</b> {}" \
						 "\n<b>Pengguna ID:</b> <code>{}</code>").format(info['fname'], mention_html(user.id, user.first_name), user_target, fban_user_id), parse_mode="HTML")
	# If fedlog is set, then send message, except fedlog is current chat
	get_fedlog = sql.get_fed_log(fed_id)
	if get_fedlog:
		if int(get_fedlog) != int(chat.id):
			bot.send_message(get_fedlog, tl(update.effective_message, "<b>Un-FedBan</b>" \
						 "\n<b>Federasi:</b> {}" \
						 "\n<b>Federasi Admin:</b> {}" \
						 "\n<b>Pengguna:</b> {}" \
						 "\n<b>Pengguna ID:</b> <code>{}</code>").format(info['fname'], mention_html(user.id, user.first_name), user_target, fban_user_id), parse_mode="HTML")
	for fedchats in chat_list:
		try:
			member = bot.get_chat_member(fedchats, user_id)
			if member.status == 'kicked':
				bot.unban_chat_member(fedchats, user_id)
				# Do not spamming all fed chats
				"""
				bot.send_message(fedchats, "<b>Un-FedBan</b>" \
						 "\n<b>Federasi:</b> {}" \
						 "\n<b>Federasi Admin:</b> {}" \
						 "\n<b>Pengguna:</b> {}" \
						 "\n<b>Pengguna ID:</b> <code>{}</code>".format(info['fname'], mention_html(user.id, user.first_name), user_target, fban_user_id), parse_mode="HTML")
				"""
		except BadRequest as excp:
			if excp.message in UNFBAN_ERRORS:
				pass
			elif excp.message == "User_id_invalid":
				break
			else:
				LOGGER.warning("Tidak dapat fban di {} karena: {}".format(fedchats, excp.message))
		except TelegramError:
			pass

	try:
		x = sql.un_fban_user(fed_id, user_id)
		if not x:
			send_message(update.effective_message, tl(update.effective_message, "Gagal fban, Pengguna ini mungkin sudah di un-fedbanned!"))
			return
	except:
		pass

	# UnFban for fed subscriber
	subscriber = list(sql.get_subscriber(fed_id))
	if len(subscriber) != 0:
		for fedsid in subscriber:
			all_fedschat = sql.all_fed_chats(fedsid)
			for fedschat in all_fedschat:
				try:
					bot.unban_chat_member(fedchats, user_id)
				except BadRequest as excp:
					if excp.message in FBAN_ERRORS:
						try:
							dispatcher.bot.getChat(fedschat)
						except Unauthorized:
							targetfed_id = sql.get_fed_id(fedschat)
							sql.unsubs_fed(fed_id, targetfed_id)
							LOGGER.info("Chat {} has unsub fed {} because bot is kicked".format(fedschat, info['fname']))
							continue
					elif excp.message == "User_id_invalid":
						break
					else:
						LOGGER.warning("Tidak dapat fban di {} karena: {}".format(fedschat, excp.message))
				except TelegramError:
					pass

	send_message(update.effective_message, tl(update.effective_message, "Orang ini telah di un-fbanned."))
	# Also do not spamming all fed admins
	"""
	FEDADMIN = sql.all_fed_users(fed_id)
	for x in FEDADMIN:
		getreport = sql.user_feds_report(x)
		if getreport == False:
			FEDADMIN.remove(x)
	send_to_list(bot, FEDADMIN,
			 "<b>Un-FedBan</b>" \
			 "\n<b>Federasi:</b> {}" \
			 "\n<b>Federasi Admin:</b> {}" \
			 "\n<b>Pengguna:</b> {}" \
			 "\n<b>Pengguna ID:</b> <code>{}</code>".format(info['fname'], mention_html(user.id, user.first_name), user_target, fban_user_id),
			html=True)
	"""


@run_async
def set_frules(bot: Bot, update: Update, args: List[str]):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return

	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]

	if chat.type == 'private':
		send_message(update.effective_message, tl(update.effective_message, "Perintah ini di khususkan untuk grup, bukan pada PM!"))
		return

	fed_id = sql.get_fed_id(chat.id)

	if not fed_id:
		send_message(update.effective_message, tl(update.effective_message, "Obrolan ini tidak ada di federasi apa pun!"))
		return

	if is_user_fed_admin(fed_id, user.id) == False:
		send_message(update.effective_message, tl(update.effective_message, "Hanya admin federasi yang dapat melakukan ini!"))
		return

	if len(args) >= 1:
		msg = update.effective_message  # type: Optional[Message]
		raw_text = msg.text
		args = raw_text.split(None, 1)  # use python's maxsplit to separate cmd and args
		if len(args) == 2:
			txt = args[1]
			offset = len(txt) - len(raw_text)  # set correct offset relative to command
			markdown_rules = markdown_parser(txt, entities=msg.parse_entities(), offset=offset)
		x = sql.set_frules(fed_id, markdown_rules)
		if not x:
			send_message(update.effective_message, "There is an error while setting federation rules! If you wondered why please ask it in support group!")
			return

		rules = sql.get_fed_info(fed_id)['frules']
		getfed = sql.get_fed_info(fed_id)
		get_fedlog = sql.get_fed_log(fed_id)
		if get_fedlog:
			if eval(get_fedlog):
				bot.send_message(get_fedlog, tl(update.effective_message, "*{}* telah mengganti aturan federasi *{}*").format(user.first_name, getfed['fname']), parse_mode="markdown")
		send_message(update.effective_message, tl(update.effective_message, "Aturan telah di ganti menjadi:\n{}!").format(rules))
	else:
		send_message(update.effective_message, tl(update.effective_message, "Silakan tulis aturan untuk mengaturnya!"))


@run_async
def get_frules(bot: Bot, update: Update, args: List[str]):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return

	chat = update.effective_chat  # type: Optional[Chat]

	if chat.type == 'private':
		send_message(update.effective_message, tl(update.effective_message, "Perintah ini di khususkan untuk grup, bukan pada PM!"))
		return

	fed_id = sql.get_fed_id(chat.id)
	if not fed_id:
		send_message(update.effective_message, tl(update.effective_message, "Grup ini tidak dalam federasi apa pun!"))
		return

	rules = sql.get_frules(fed_id)
	text = tl(update.effective_message, "*Peraturan di fed ini:*\n")
	text += rules
	send_message(update.effective_message, text, parse_mode=ParseMode.MARKDOWN)


@run_async
def fed_broadcast(bot: Bot, update: Update, args: List[str]):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return

	msg = update.effective_message  # type: Optional[Message]
	user = update.effective_user  # type: Optional[User]
	chat = update.effective_chat  # type: Optional[Chat]

	if chat.type == 'private':
		send_message(update.effective_message, tl(update.effective_message, "Perintah ini di khususkan untuk grup, bukan pada PM!"))
		return

	if args:
		chat = update.effective_chat  # type: Optional[Chat]
		fed_id = sql.get_fed_id(chat.id)
		fedinfo = sql.get_fed_info(fed_id)
		# Parsing md
		raw_text = msg.text
		args = raw_text.split(None, 1)  # use python's maxsplit to separate cmd and args
		txt = args[1]
		offset = len(txt) - len(raw_text)  # set correct offset relative to command
		text_parser = markdown_parser(txt, entities=msg.parse_entities(), offset=offset)
		text = text_parser
		try:
			broadcaster = user.first_name
		except:
			broadcaster = user.first_name + " " + user.last_name
		text += "\n\n- {}".format(mention_markdown(user.id, broadcaster))
		chat_list = sql.all_fed_chats(fed_id)
		failed = 0
		for chat in chat_list:
			title = tl(chat, "*Siaran baru dari Federasi {}*\n").format(fedinfo['fname'])
			try:
				bot.sendMessage(chat, title + text, parse_mode="markdown")
			except TelegramError:
				try:
					dispatcher.bot.getChat(chat)
				except Unauthorized:
					failed += 1
					sql.chat_leave_fed(chat)
					LOGGER.info("Chat {} has leave fed {} because bot is kicked".format(chat, fedinfo['fname']))
					continue
				failed += 1
				LOGGER.warning("Couldn't send broadcast to {}".format(str(chat)))

		send_text = tl(update.effective_message, "Siaran Federasi selesai.")
		if failed >= 1:
			send_text += tl(update.effective_message, "{} grup gagal menerima pesan, mungkin karena meninggalkan federasi.").format(failed)
		send_message(update.effective_message, send_text)

@run_async
def fed_ban_list(bot: Bot, update: Update, args: List[str], chat_data):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return

	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]

	if chat.type == 'private':
		send_message(update.effective_message, tl(update.effective_message, "Perintah ini di khususkan untuk grup, bukan pada PM!"))
		return

	fed_id = sql.get_fed_id(chat.id)
	info = sql.get_fed_info(fed_id)

	if not fed_id:
		send_message(update.effective_message, tl(update.effective_message, "Grup ini tidak dalam federasi apa pun!"))
		return

	if is_user_fed_owner(fed_id, user.id) == False:
		send_message(update.effective_message, tl(update.effective_message, "Hanya pemilik federasi yang dapat melakukan ini!"))
		return

	user = update.effective_user  # type: Optional[Chat]
	chat = update.effective_chat  # type: Optional[Chat]
	getfban = sql.get_all_fban_users(fed_id)
	if len(getfban) == 0:
		send_message(update.effective_message, tl(update.effective_message, "Tidak ada pengguna yang di fban di federasi {}").format(info['fname']), parse_mode=ParseMode.HTML)
		return

	if args:
		if args[0] == 'json':
			jam = time.time()
			new_jam = jam + 1800
			cek = get_chat(chat.id, chat_data)
			if cek.get('status'):
				if jam <= int(cek.get('value')):
					waktu = time.strftime("%H:%M:%S %d/%m/%Y", time.localtime(cek.get('value')))
					send_message(update.effective_message, tl(update.effective_message, "Anda dapat mendapatkan data 30 menit sekali!\nAnda dapat mendapatkan data ini lagi pada `{}`").format(waktu), parse_mode=ParseMode.MARKDOWN)
					return
				else:
					if user.id not in SUDO_USERS:
						put_chat(chat.id, new_jam, chat_data)
			else:
				if user.id not in SUDO_USERS:
					put_chat(chat.id, new_jam, chat_data)
			backups = ""
			for users in getfban:
				getuserinfo = sql.get_all_fban_users_target(fed_id, users)
				json_parser = {"user_id": users, "first_name": getuserinfo['first_name'], "last_name": getuserinfo['last_name'], "user_name": getuserinfo['user_name'], "reason": getuserinfo['reason']}
				backups += json.dumps(json_parser)
				backups += "\n"
			with BytesIO(str.encode(backups)) as output:
				output.name = "emilia_fbanned_users.json"
				update.effective_message.reply_document(document=output, filename="emilia_fbanned_users.json",
													caption=tl(update.effective_message, "Total {} pengguna terkena blokir federasi {}.").format(len(getfban), info['fname']))
			return
		elif args[0] == 'csv':
			jam = time.time()
			new_jam = jam + 1800
			cek = get_chat(chat.id, chat_data)
			if cek.get('status'):
				if jam <= int(cek.get('value')):
					waktu = time.strftime("%H:%M:%S %d/%m/%Y", time.localtime(cek.get('value')))
					send_message(update.effective_message, tl(update.effective_message, "Anda dapat mendapatkan data 30 menit sekali!\nAnda dapat mendapatkan data ini lagi pada `{}`").format(waktu), parse_mode=ParseMode.MARKDOWN)
					return
				else:
					if user.id not in SUDO_USERS:
						put_chat(chat.id, new_jam, chat_data)
			else:
				if user.id not in SUDO_USERS:
					put_chat(chat.id, new_jam, chat_data)
			backups = "id,firstname,lastname,username,reason\n"
			for users in getfban:
				getuserinfo = sql.get_all_fban_users_target(fed_id, users)
				backups += "{user_id},{first_name},{last_name},{user_name},{reason}".format(user_id=users, first_name=getuserinfo['first_name'], last_name=getuserinfo['last_name'], user_name=getuserinfo['user_name'], reason=getuserinfo['reason'])
				backups += "\n"
			with BytesIO(str.encode(backups)) as output:
				output.name = "emilia_fbanned_users.csv"
				update.effective_message.reply_document(document=output, filename="emilia_fbanned_users.csv",
													caption=tl(update.effective_message, "Total {} pengguna terkena blokir federasi {}.").format(len(getfban), info['fname']))
			return

	text = tl(update.effective_message, "<b>Ada {} pengguna yang di fban pada federasi {}:</b>\n").format(len(getfban), info['fname'])
	for users in getfban:
		getuserinfo = sql.get_all_fban_users_target(fed_id, users)
		if getuserinfo == False:
			text = tl(update.effective_message, "Tidak ada pengguna yang di fban di federasi {}").format(info['fname'])
			break
		user_name = getuserinfo['first_name']
		if getuserinfo['last_name']:
			user_name += " " + getuserinfo['last_name']
		text += " • {} (<code>{}</code>)\n".format(mention_html(users, user_name), users)

	try:
		send_message(update.effective_message, text, parse_mode=ParseMode.HTML)
	except:
		jam = time.time()
		new_jam = jam + 1800
		cek = get_chat(chat.id, chat_data)
		if cek.get('status'):
			if jam <= int(cek.get('value')):
				waktu = time.strftime("%H:%M:%S %d/%m/%Y", time.localtime(cek.get('value')))
				send_message(update.effective_message, tl(update.effective_message, "Anda dapat mendapatkan data 30 menit sekali!\nAnda dapat mendapatkan data ini lagi pada `{}`").format(waktu), parse_mode=ParseMode.MARKDOWN)
				return
			else:
				if user.id not in SUDO_USERS:
					put_chat(chat.id, new_jam, chat_data)
		else:
			if user.id not in SUDO_USERS:
				put_chat(chat.id, new_jam, chat_data)
		cleanr = re.compile('<.*?>')
		cleantext = re.sub(cleanr, '', text)
		with BytesIO(str.encode(cleantext)) as output:
			output.name = "fbanlist.txt"
			update.effective_message.reply_document(document=output, filename="fbanlist.txt",
													caption=tl(update.effective_message, "Berikut adalah daftar pengguna yang saat ini difban pada federasi {}.").format(info['fname']))

@run_async
def fed_notif(bot: Bot, update: Update, args: List[str]):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return

	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	msg = update.effective_message  # type: Optional[Message]
	fed_id = sql.get_fed_id(chat.id)

	if not fed_id:
		send_message(update.effective_message, tl(update.effective_message, "Grup ini tidak dalam federasi apa pun!"))
		return

	if args:
		if args[0] in ("yes", "on", "ya"):
			sql.set_feds_setting(user.id, True)
			send_message(update.effective_message, tl(update.effective_message, "Pelaporan federasi hidup! Setiap ada pengguna yang di fban/unfban anda akan di beritahu via PM."))
		elif args[0] in ("no", "off", "ga"):
			sql.set_feds_setting(user.id, False)
			send_message(update.effective_message, tl(update.effective_message, "Pelaporan federasi mati! Setiap ada pengguna yang di fban/unfban anda tidak akan di beritahu via PM."))
		else:
			send_message(update.effective_message, tl(update.effective_message, "Tolong masukan `ya`/`on`/`ga`/`off`"), parse_mode="markdown")
	else:
		getreport = sql.user_feds_report(user.id)
		send_message(update.effective_message, tl(update.effective_message, "Preferensi laporan federasi anda saat ini: `{}`").format(getreport), parse_mode="markdown")

@run_async
def fed_chats(bot: Bot, update: Update, args: List[str]):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return

	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]

	if chat.type == 'private':
		send_message(update.effective_message, tl(update.effective_message, "Perintah ini di khususkan untuk grup, bukan pada PM!"))
		return

	fed_id = sql.get_fed_id(chat.id)
	info = sql.get_fed_info(fed_id)

	if not fed_id:
		send_message(update.effective_message, tl(update.effective_message, "Grup ini tidak dalam federasi apa pun!"))
		return

	if is_user_fed_admin(fed_id, user.id) == False:
		send_message(update.effective_message, tl(update.effective_message, "Hanya admin federasi yang dapat melakukan ini!"))
		return

	getlist = sql.all_fed_chats(fed_id)
	if len(getlist) == 0:
		send_message(update.effective_message, tl(update.effective_message, "Tidak ada obrolan yang bergabung pada federasi {}").format(info['fname']), parse_mode=ParseMode.HTML)
		return

	text = tl(update.effective_message, "<b>Obrolan yang bergabung pada federasi {}:</b>\n").format(info['fname'])
	for chats in getlist:
		chat_name = sql.get_fed_name(chats)
		text += " • {} (<code>{}</code>)\n".format(chat_name, chats)

	try:
		send_message(update.effective_message, text, parse_mode=ParseMode.HTML)
	except:
		cleanr = re.compile('<.*?>')
		cleantext = re.sub(cleanr, '', text)
		with BytesIO(str.encode(cleantext)) as output:
			output.name = "fedchats.txt"
			update.effective_message.reply_document(document=output, filename="fedchats.txt",
													caption=tl(update.effective_message, "Berikut adalah daftar obrolan yang bergabung federasi {}.").format(info['fname']))

@run_async
def fed_import_bans(bot: Bot, update: Update, chat_data):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return

	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	msg = update.effective_message  # type: Optional[Message]

	if chat.type == 'private':
		send_message(update.effective_message, tl(update.effective_message, "Perintah ini di khususkan untuk grup, bukan pada PM!"))
		return

	fed_id = sql.get_fed_id(chat.id)
	info = sql.get_fed_info(fed_id)
	getfed = sql.get_fed_info(fed_id)

	if not fed_id:
		send_message(update.effective_message, tl(update.effective_message, "Grup ini tidak dalam federasi apa pun!"))
		return

	if is_user_fed_owner(fed_id, user.id) == False:
		send_message(update.effective_message, tl(update.effective_message, "Hanya pemilik federasi yang dapat melakukan ini!"))
		return

	if msg.reply_to_message and msg.reply_to_message.document:
		jam = time.time()
		new_jam = jam + 1800
		cek = get_chat(chat.id, chat_data)
		if cek.get('status'):
			if jam <= int(cek.get('value')):
				waktu = time.strftime("%H:%M:%S %d/%m/%Y", time.localtime(cek.get('value')))
				send_message(update.effective_message, tl(update.effective_message, "Anda dapat mendapatkan data 30 menit sekali!\nAnda dapat mendapatkan data ini lagi pada `{}`").format(waktu), parse_mode=ParseMode.MARKDOWN)
				return
			else:
				if user.id not in SUDO_USERS:
					put_chat(chat.id, new_jam, chat_data)
		else:
			if user.id not in SUDO_USERS:
				put_chat(chat.id, new_jam, chat_data)
		# if int(int(msg.reply_to_message.document.file_size)/1024) >= 200:
		# 	send_message(update.effective_message, "File ini terlalu besar!")
		# 	return
		success = 0
		failed = 0
		try:
			file_info = bot.get_file(msg.reply_to_message.document.file_id)
		except BadRequest:
			send_message(update.effective_message, tl(update.effective_message, "Coba unduh dan unggah ulang filenya, yang ini sepertinya rusak!"))
			return
		fileformat = msg.reply_to_message.document.file_name.split('.')[-1]
		if fileformat == 'json':
			multi_fed_id = []
			multi_import_userid = []
			multi_import_firstname = []
			multi_import_lastname = []
			multi_import_username = []
			multi_import_reason = []
			with BytesIO() as file:
				file_info.download(out=file)
				file.seek(0)
				reading = file.read().decode('UTF-8')
				splitting = reading.split('\n')
				for x in splitting:
					if x == '':
						continue
					try:
						data = json.loads(x)
					except json.decoder.JSONDecodeError as err:
						failed += 1
						continue
					try:
						import_userid = int(data['user_id']) # Make sure it int
						import_firstname = str(data['first_name'])
						import_lastname = str(data['last_name'])
						import_username = str(data['user_name'])
						import_reason = str(data['reason'])
					except ValueError:
						failed += 1
						continue
					# Checking user
					if int(import_userid) == bot.id:
						failed += 1
						continue
					if is_user_fed_owner(fed_id, import_userid) == True:
						failed += 1
						continue
					if is_user_fed_admin(fed_id, import_userid) == True:
						failed += 1
						continue
					if str(import_userid) == str(OWNER_ID):
						failed += 1
						continue
					if int(import_userid) in SUDO_USERS:
						failed += 1
						continue
					if int(import_userid) in WHITELIST_USERS:
						failed += 1
						continue
					multi_fed_id.append(fed_id)
					multi_import_userid.append(str(import_userid))
					multi_import_firstname.append(import_firstname)
					multi_import_lastname.append(import_lastname)
					multi_import_username.append(import_username)
					multi_import_reason.append(import_reason)
					success += 1
				sql.multi_fban_user(multi_fed_id, multi_import_userid, multi_import_firstname, multi_import_lastname, multi_import_username, multi_import_reason)
			text = tl(update.effective_message, "Berkas blokir berhasil diimpor. {} orang diblokir.").format(success)
			if failed >= 1:
				text += tl(update.effective_message, " {} gagal di impor.").format(failed)
			get_fedlog = sql.get_fed_log(fed_id)
			if get_fedlog:
				if eval(get_fedlog):
					teks = tl(update.effective_message, "Federasi *{}* telah berhasil mengimpor data. {} di blokir").format(getfed['fname'], success)
					if failed >= 1:
						teks += tl(update.effective_message, " {} gagal di impor.").format(failed)
					bot.send_message(get_fedlog, teks, parse_mode="markdown")
		elif fileformat == 'csv':
			multi_fed_id = []
			multi_import_userid = []
			multi_import_firstname = []
			multi_import_lastname = []
			multi_import_username = []
			multi_import_reason = []
			file_info.download("fban_{}.csv".format(msg.reply_to_message.document.file_id))
			with open("fban_{}.csv".format(msg.reply_to_message.document.file_id), 'r', encoding="utf8") as csvFile:
				reader = csv.reader(csvFile)
				for data in reader:
					try:
						import_userid = int(data[0]) # Make sure it int
						import_firstname = str(data[1])
						import_lastname = str(data[2])
						import_username = str(data[3])
						import_reason = str(data[4])
					except ValueError:
						failed += 1
						continue
					# Checking user
					if int(import_userid) == bot.id:
						failed += 1
						continue
					if is_user_fed_owner(fed_id, import_userid) == True:
						failed += 1
						continue
					if is_user_fed_admin(fed_id, import_userid) == True:
						failed += 1
						continue
					if str(import_userid) == str(OWNER_ID):
						failed += 1
						continue
					if int(import_userid) in SUDO_USERS:
						failed += 1
						continue
					if int(import_userid) in WHITELIST_USERS:
						failed += 1
						continue
					multi_fed_id.append(fed_id)
					multi_import_userid.append(str(import_userid))
					multi_import_firstname.append(import_firstname)
					multi_import_lastname.append(import_lastname)
					multi_import_username.append(import_username)
					multi_import_reason.append(import_reason)
					success += 1
					# t = ThreadWithReturnValue(target=sql.fban_user, args=(fed_id, str(import_userid), import_firstname, import_lastname, import_username, import_reason,))
					# t.start()
				sql.multi_fban_user(multi_fed_id, multi_import_userid, multi_import_firstname, multi_import_lastname, multi_import_username, multi_import_reason)
			csvFile.close()
			os.remove("fban_{}.csv".format(msg.reply_to_message.document.file_id))
			text = tl(update.effective_message, "Berkas blokir berhasil diimpor. {} orang diblokir.").format(success)
			if failed >= 1:
				text += tl(update.effective_message, " {} gagal di impor.").format(failed)
			get_fedlog = sql.get_fed_log(fed_id)
			if get_fedlog:
				if eval(get_fedlog):
					teks = tl(update.effective_message, "Federasi *{}* telah berhasil mengimpor data. {} di blokir").format(getfed['fname'], success)
					if failed >= 1:
						teks += tl(update.effective_message, " {} gagal di impor.").format(failed)
					bot.send_message(get_fedlog, teks, parse_mode="markdown")
		else:
			send_message(update.effective_message, tl(update.effective_message, "File tidak di dukung."))
			return
		send_message(update.effective_message, text)

@run_async
def del_fed_button(bot, update):
	query = update.callback_query
	userid = query.message.chat.id
	fed_id = query.data.split("_")[1]

	if fed_id == 'cancel':
		query.message.edit_text(tl(update.effective_message, "Penghapusan federasi dibatalkan"))
		return

	getfed = sql.get_fed_info(fed_id)
	if getfed:
		delete = sql.del_fed(fed_id)
		if delete:
			query.message.edit_text(tl(update.effective_message, "Anda telah menghapus federasi Anda! Sekarang semua Grup yang terhubung dengan `{}` sekarang tidak memiliki federasi.").format(getfed['fname']), parse_mode='markdown')

@run_async
def fed_stat_user(bot, update, args):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return

	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	msg = update.effective_message  # type: Optional[Message]

	if args:
		if args[0].isdigit():
			user_id = args[0]
		else:
			user_id = extract_user(msg, args)
	else:
		user_id = extract_user(msg, args)

	if user_id:
		if len(args) == 2 and args[0].isdigit():
			fed_id = args[1]
			user_name, reason, fbantime = sql.get_user_fban(fed_id, str(user_id))
			if fbantime:
				fbantime = time.strftime("%d/%m/%Y", time.localtime(fbantime))
			else:
				fbantime = "Unavaiable"
			if user_name == False:
				send_message(update.effective_message, tl(update.effective_message, "Federasi {} tidak di temukan!").format(fed_id), parse_mode="markdown")
				return
			if user_name == "" or user_name == None:
				user_name = tl(update.effective_message, "Dia")
			if not reason:
				send_message(update.effective_message, tl(update.effective_message, "{} belum di larang di federasi ini!").format(user_name))
			else:
				teks = tl(update.effective_message, "{} di larang di federasi ini karena:\n`{}`\n*Di banned pada:* `{}`").format(user_name, reason, fbantime)
				send_message(update.effective_message, teks, parse_mode="markdown")
			return
		user_name, fbanlist = sql.get_user_fbanlist(str(user_id))
		if user_name == "":
			try:
				user_name = bot.get_chat(user_id).first_name
			except BadRequest:
				user_name = tl(update.effective_message, "Dia")
			if user_name == "" or user_name == None:
				user_name = tl(update.effective_message, "Dia")
		if len(fbanlist) == 0:
			send_message(update.effective_message, tl(update.effective_message, "{} belum di larang di federasi mana pun!").format(user_name))
			return
		else:
			teks = tl(update.effective_message, "{} sudah di larang di federasi ini:\n").format(user_name)
			for x in fbanlist:
				teks += "- `{}`: {}\n".format(x[0], x[1][:20])
			teks += tl(update.effective_message, "\nJika anda ingin mengetahui lebih lanjut tentang alasan fedban dengan spesifik, gunakan /fbanstat <FedID>")
			send_message(update.effective_message, teks, parse_mode="markdown")

	elif not msg.reply_to_message and not args:
		user_id = msg.from_user.id
		user_name, fbanlist = sql.get_user_fbanlist(user_id)
		if user_name == "":
			user_name = msg.from_user.first_name
		if len(fbanlist) == 0:
			send_message(update.effective_message, tl(update.effective_message, "{} belum di larang di federasi mana pun!").format(user_name))
		else:
			teks = tl(update.effective_message, "{} sudah di larang di federasi ini:\n").format(user_name)
			for x in fbanlist:
				teks += "- `{}`: {}\n".format(x[0], x[1][:20])
			teks += tl(update.effective_message, "\nJika anda ingin mengetahui lebih lanjut tentang alasan fedban dengan spesifik, gunakan /fbanstat <FedID>")
			send_message(update.effective_message, teks, parse_mode="markdown")

	else:
		fed_id = args[0]
		fedinfo = sql.get_fed_info(fed_id)
		if not fedinfo:
			send_message(update.effective_message, tl(update.effective_message, "Federasi {} tidak di temukan!").format(fed_id))
			return
		name, reason, fbantime = sql.get_user_fban(fed_id, msg.from_user.id)
		if fbantime:
			fbantime = time.strftime("%d/%m/%Y", time.localtime(fbantime))
		else:
			fbantime = "Unavaiable"
		if not name:
			name = msg.from_user.first_name
		if not reason:
			send_message(update.effective_message, tl(update.effective_message, "{} tidak di larang di federasi ini").format(name))
			return
		send_message(update.effective_message, tl(update.effective_message, "{} di larang di federasi ini karena:\n`{}`\n*Di banned pada:* `{}`").format(name, reason, fbantime), parse_mode="markdown")


@run_async
def set_fed_log(bot, update, args):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return

	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	msg = update.effective_message  # type: Optional[Message]

	if chat.type == 'private':
		send_message(update.effective_message, tl(update.effective_message, "Perintah ini di khususkan untuk grup, bukan pada PM!"))
		return

	if args:
		fedinfo = sql.get_fed_info(args[0])
		if not fedinfo:
			send_message(update.effective_message, tl(update.effective_message, "Federasi ini tidak ada!"))
			return
		isowner = is_user_fed_owner(args[0], user.id)
		if not isowner:
			send_message(update.effective_message, tl(update.effective_message, "Hanya pencipta federasi yang bisa menetapkan log federasi."))
			return
		setlog = sql.set_fed_log(args[0], chat.id)
		if setlog:
			send_message(update.effective_message, tl(update.effective_message, "Log federasi `{}` telah di setel pada {}").format(fedinfo['fname'], chat.title), parse_mode="markdown")
	else:
		send_message(update.effective_message, tl(update.effective_message, "Anda belum memberikan ID federasinya!"))

@run_async
def unset_fed_log(bot, update, args):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return

	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	msg = update.effective_message  # type: Optional[Message]

	if chat.type == 'private':
		send_message(update.effective_message, tl(update.effective_message, "Perintah ini di khususkan untuk grup, bukan pada PM!"))
		return

	if args:
		fedinfo = sql.get_fed_info(args[0])
		if not fedinfo:
			send_message(update.effective_message, tl(update.effective_message, "Federasi ini tidak ada!"))
			return
		isowner = is_user_fed_owner(args[0], user.id)
		if not isowner:
			send_message(update.effective_message, tl(update.effective_message, "Hanya pencipta federasi yang bisa menetapkan log federasi."))
			return
		setlog = sql.set_fed_log(args[0], None)
		if setlog:
			send_message(update.effective_message, tl(update.effective_message, "Log federasi `{}` telah di cabut pada {}").format(fedinfo['fname'], chat.title), parse_mode="markdown")
	else:
		send_message(update.effective_message, tl(update.effective_message, "Anda belum memberikan ID federasinya!"))


@run_async
def subs_feds(bot, update, args):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return

	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	msg = update.effective_message  # type: Optional[Message]

	if chat.type == 'private':
		send_message(update.effective_message, tl(update.effective_message, "Perintah ini di khususkan untuk grup, bukan pada PM!"))
		return

	fed_id = sql.get_fed_id(chat.id)
	fedinfo = sql.get_fed_info(fed_id)

	if not fed_id:
		send_message(update.effective_message, tl(update.effective_message, "Grup ini tidak dalam federasi apa pun!"))
		return

	if is_user_fed_owner(fed_id, user.id) == False:
		send_message(update.effective_message, tl(update.effective_message, "Hanya pemilik federasi yang dapat melakukan ini!"))
		return

	if args:
		getfed = sql.search_fed_by_id(args[0])
		if getfed == False:
			send_message(update.effective_message, tl(update.effective_message, "Silakan masukkan id federasi yang valid."))
			return
		subfed = sql.subs_fed(args[0], fed_id)
		if subfed:
			send_message(update.effective_message, tl(update.effective_message, "Federasi `{}` telah mengikuti federasi `{}`. Setiap ada fedban dari federasi tersebut, federasi ini juga akan banned pengguna tsb.").format(fedinfo['fname'], getfed['fname']), parse_mode="markdown")
			get_fedlog = sql.get_fed_log(args[0])
			if get_fedlog:
				if int(get_fedlog) != int(chat.id):
					bot.send_message(get_fedlog, tl(update.effective_message, "Federasi `{}` telah mengikuti federasi `{}`").format(fedinfo['fname'], getfed['fname']), parse_mode="markdown")
		else:
			send_message(update.effective_message, tl(update.effective_message, "Federasi `{}` sudah mengikuti federasi `{}`.").format(fedinfo['fname'], getfed['fname']), parse_mode="markdown")
	else:
		send_message(update.effective_message, tl(update.effective_message, "Anda belum memberikan ID federasinya!"))

@run_async
def unsubs_feds(bot, update, args):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return

	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	msg = update.effective_message  # type: Optional[Message]

	if chat.type == 'private':
		send_message(update.effective_message, tl(update.effective_message, "Perintah ini di khususkan untuk grup, bukan pada PM!"))
		return

	fed_id = sql.get_fed_id(chat.id)
	fedinfo = sql.get_fed_info(fed_id)

	if not fed_id:
		send_message(update.effective_message, tl(update.effective_message, "Grup ini tidak dalam federasi apa pun!"))
		return

	if is_user_fed_owner(fed_id, user.id) == False:
		send_message(update.effective_message, tl(update.effective_message, "Hanya pemilik federasi yang dapat melakukan ini!"))
		return

	if args:
		getfed = sql.search_fed_by_id(args[0])
		if getfed == False:
			send_message(update.effective_message, tl(update.effective_message, "Silakan masukkan id federasi yang valid."))
			return
		subfed = sql.unsubs_fed(args[0], fed_id)
		if subfed:
			send_message(update.effective_message, tl(update.effective_message, "Federasi `{}` sudah tidak mengikuti `{}` lagi.").format(fedinfo['fname'], getfed['fname']), parse_mode="markdown")
			get_fedlog = sql.get_fed_log(args[0])
			if get_fedlog:
				if int(get_fedlog) != int(chat.id):
					bot.send_message(get_fedlog, tl(update.effective_message, "Federasi `{}` sudah tidak mengikuti `{}`").format(fedinfo['fname'], getfed['fname']), parse_mode="markdown")
		else:
			send_message(update.effective_message, tl(update.effective_message, "Federasi `{}` tidak mengikuti federasi `{}`.").format(fedinfo['fname'], getfed['fname']), parse_mode="markdown")
	else:
		send_message(update.effective_message, tl(update.effective_message, "Anda belum memberikan ID federasinya!"))

@run_async
def get_myfedsubs(bot, update, args):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return

	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	msg = update.effective_message  # type: Optional[Message]

	if chat.type == 'private':
		send_message(update.effective_message, tl(update.effective_message, "Perintah ini di khususkan untuk grup, bukan pada PM!"))
		return

	fed_id = sql.get_fed_id(chat.id)
	fedinfo = sql.get_fed_info(fed_id)

	if not fed_id:
		send_message(update.effective_message, tl(update.effective_message, "Grup ini tidak dalam federasi apa pun!"))
		return

	if is_user_fed_owner(fed_id, user.id) == False:
		send_message(update.effective_message, tl(update.effective_message, "Hanya pemilik federasi yang dapat melakukan ini!"))
		return

	getmy = sql.get_mysubs(fed_id)

	if len(getmy) == 0:
		send_message(update.effective_message, tl(update.effective_message, "Federasi `{}` tidak mengikuti federasi apapun.").format(fedinfo['fname']), parse_mode="markdown")
		return
	else:
		listfed = tl(update.effective_message, "Federasi `{}` mengikuti federasi berikut ini:\n").format(fedinfo['fname'])
		for x in getmy:
			listfed += "- `{}`\n".format(x)
		listfed += tl(update.effective_message, "\nUntuk info federasi, ketik `/fedinfo <fedid>`. Untuk berhenti berlangganan ketik `/unsubfed <fedid>`.")
		send_message(update.effective_message, listfed, parse_mode="markdown")

@run_async
def get_myfeds_list(bot, update):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return

	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	msg = update.effective_message  # type: Optional[Message]

	fedowner = sql.get_user_owner_fed_full(user.id)
	if fedowner:
		text = tl(update.effective_message, "*Ini adalah federasi milik anda:\n*")
		for f in fedowner:
			text += "- `{}`: *{}*\n".format(f['fed_id'], f['fed']['fname'])
	else:
		text = tl(update.effective_message, "*Anda tidak mempunyai federasi!*")
	send_message(update.effective_message, text, parse_mode="markdown")


def is_user_fed_admin(fed_id, user_id):
	fed_admins = sql.all_fed_users(fed_id)
	if fed_admins == False:
		return False
	if int(user_id) in fed_admins or int(user_id) == OWNER_ID:
		return True
	else:
		return False


def is_user_fed_owner(fed_id, user_id):
	getsql = sql.get_fed_info(fed_id)
	if getsql == False:
		return False
	getfedowner = eval(getsql['fusers'])
	if getfedowner == None or getfedowner == False:
		return False
	getfedowner = getfedowner['owner']
	if str(user_id) == getfedowner or int(user_id) == OWNER_ID:
		return True
	else:
		return False


@run_async
def welcome_fed(bot, update):
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]

	fed_id = sql.get_fed_id(chat.id)
	fban, fbanreason, fbantime = sql.get_fban_user(fed_id, user.id)
	if fban:
		send_message(update.effective_message, "This user is banned in current federation! I will remove him.")
		bot.kick_chat_member(chat.id, user.id)
		return True
	else:
		return False


def __stats__():
	all_fbanned = sql.get_all_fban_users_global()
	all_feds = sql.get_all_feds_users_global()
	return tl(OWNER_ID, "{} pengguna di fbanned, pada {} federasi").format(len(all_fbanned), len(all_feds))


def __user_info__(user_id, chat_id):
	fed_id = sql.get_fed_id(chat_id)
	if fed_id:
		fban, fbanreason, fbantime = sql.get_fban_user(fed_id, user_id)
		info = sql.get_fed_info(fed_id)
		infoname = info['fname']

		if int(info['owner']) == user_id:
			text = tl(chat_id, "Pengguna ini adalah owner di federasi saat ini: <b>{}</b>.").format(infoname)
		elif is_user_fed_admin(fed_id, user_id):
			text = tl(chat_id, "Pengguna ini adalah admin di federasi saat ini: <b>{}</b>.").format(infoname)

		elif fban:
			text = tl(chat_id, "Dilarang di federasi saat ini: <b>Ya</b>")
			text += tl(chat_id, "\n<b>Alasan:</b> {}").format(fbanreason)
		else:
			text = tl(chat_id, "Dilarang di federasi saat ini: <b>Tidak</b>")
	else:
		text = ""
	return text


# Temporary data
def put_chat(chat_id, value, chat_data):
	# print(chat_data)
	if value == False:
		status = False
	else:
		status = True
	chat_data[chat_id] = {'federation': {"status": status, "value": value}}

def get_chat(chat_id, chat_data):
	# print(chat_data)
	try:
		value = chat_data[chat_id]['federation']
		return value
	except KeyError:
		return {"status": False, "value": False}


__mod_name__ = "Federations"

__help__ = "feds_help"

NEW_FED_HANDLER = CommandHandler("newfed", new_fed)
DEL_FED_HANDLER = CommandHandler("delfed", del_fed, pass_args=True)
JOIN_FED_HANDLER = CommandHandler("joinfed", join_fed, pass_args=True)
LEAVE_FED_HANDLER = CommandHandler("leavefed", leave_fed, pass_args=True)
PROMOTE_FED_HANDLER = CommandHandler("fpromote", user_join_fed, pass_args=True)
DEMOTE_FED_HANDLER = CommandHandler("fdemote", user_demote_fed, pass_args=True)
INFO_FED_HANDLER = CommandHandler("fedinfo", fed_info, pass_args=True)
BAN_FED_HANDLER = DisableAbleCommandHandler(["fban", "fedban"], fed_ban, pass_args=True)
UN_BAN_FED_HANDLER = CommandHandler("unfban", unfban, pass_args=True)
FED_BROADCAST_HANDLER = CommandHandler("fbroadcast", fed_broadcast, pass_args=True)
FED_SET_RULES_HANDLER = CommandHandler("setfrules", set_frules, pass_args=True)
FED_GET_RULES_HANDLER = CommandHandler("frules", get_frules, pass_args=True)
FED_CHAT_HANDLER = CommandHandler("chatfed", fed_chat, pass_args=True)
FED_ADMIN_HANDLER = CommandHandler("fedadmins", fed_admin, pass_args=True)
FED_USERBAN_HANDLER = CommandHandler("fbanlist", fed_ban_list, pass_args=True, pass_chat_data=True)
FED_NOTIF_HANDLER = CommandHandler("fednotif", fed_notif, pass_args=True)
FED_CHATLIST_HANDLER = CommandHandler("fedchats", fed_chats, pass_args=True)
FED_IMPORTBAN_HANDLER = CommandHandler("importfbans", fed_import_bans, pass_chat_data=True, filters=Filters.user(OWNER_ID))
FEDSTAT_USER = DisableAbleCommandHandler(["fedstat", "fbanstat"], fed_stat_user, pass_args=True)
SET_FED_LOG = CommandHandler("setfedlog", set_fed_log, pass_args=True)
UNSET_FED_LOG = CommandHandler("unsetfedlog", unset_fed_log, pass_args=True)
SUBS_FED = CommandHandler("subfed", subs_feds, pass_args=True)
UNSUBS_FED = CommandHandler("unsubfed", unsubs_feds, pass_args=True)
MY_SUB_FED = CommandHandler("fedsubs", get_myfedsubs, pass_args=True)
MY_FEDS_LIST = CommandHandler("myfeds", get_myfeds_list)

DELETEBTN_FED_HANDLER = CallbackQueryHandler(del_fed_button, pattern=r"rmfed_")

dispatcher.add_handler(NEW_FED_HANDLER)
dispatcher.add_handler(DEL_FED_HANDLER)
dispatcher.add_handler(JOIN_FED_HANDLER)
dispatcher.add_handler(LEAVE_FED_HANDLER)
dispatcher.add_handler(PROMOTE_FED_HANDLER)
dispatcher.add_handler(DEMOTE_FED_HANDLER)
dispatcher.add_handler(INFO_FED_HANDLER)
dispatcher.add_handler(BAN_FED_HANDLER)
dispatcher.add_handler(UN_BAN_FED_HANDLER)
dispatcher.add_handler(FED_BROADCAST_HANDLER)
dispatcher.add_handler(FED_SET_RULES_HANDLER)
dispatcher.add_handler(FED_GET_RULES_HANDLER)
dispatcher.add_handler(FED_CHAT_HANDLER)
dispatcher.add_handler(FED_ADMIN_HANDLER)
dispatcher.add_handler(FED_USERBAN_HANDLER)
dispatcher.add_handler(FED_NOTIF_HANDLER)
dispatcher.add_handler(FED_CHATLIST_HANDLER)
dispatcher.add_handler(FED_IMPORTBAN_HANDLER)
dispatcher.add_handler(FEDSTAT_USER)
dispatcher.add_handler(SET_FED_LOG)
dispatcher.add_handler(UNSET_FED_LOG)
dispatcher.add_handler(SUBS_FED)
dispatcher.add_handler(UNSUBS_FED)
dispatcher.add_handler(MY_SUB_FED)
dispatcher.add_handler(MY_FEDS_LIST)

dispatcher.add_handler(DELETEBTN_FED_HANDLER)
