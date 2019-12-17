import html
import re
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, MessageHandler, Filters, run_async
from telegram.utils.helpers import mention_html, escape_markdown

import emilia.modules.sql.blacklist_sql as sql
from emilia import dispatcher, LOGGER, spamfilters, OWNER_ID
from emilia.modules.disable import DisableAbleCommandHandler
from telegram.utils.helpers import mention_markdown
from emilia.modules.helper_funcs.chat_status import user_admin, user_not_admin
from emilia.modules.helper_funcs.extraction import extract_text
from emilia.modules.helper_funcs.misc import split_message
from emilia.modules.log_channel import loggable
from emilia.modules.warns import warn
from emilia.modules.helper_funcs.string_handling import extract_time
from emilia.modules.connection import connected

from emilia.modules.languages import tl
from emilia.modules.helper_funcs.alternate import send_message

BLACKLIST_GROUP = 11


@run_async
def blacklist(bot: Bot, update: Update, args: List[str]):
	msg = update.effective_message  # type: Optional[Message]
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]

	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return
	
	conn = connected(bot, update, chat, user.id, need_admin=False)
	if conn:
		chat_id = conn
		chat_name = dispatcher.bot.getChat(conn).title
	else:
		if chat.type == "private":
			return
		else:
			chat_id = update.effective_chat.id
			chat_name = chat.title
	
	filter_list = tl(update.effective_message, "<b>Kata daftar hitam saat ini di {}:</b>\n").format(chat_name)

	all_blacklisted = sql.get_chat_blacklist(chat_id)

	if len(args) > 0 and args[0].lower() == 'copy':
		for trigger in all_blacklisted:
			filter_list += "<code>{}</code>\n".format(html.escape(trigger))
	else:
		for trigger in all_blacklisted:
			filter_list += " - <code>{}</code>\n".format(html.escape(trigger))

	# for trigger in all_blacklisted:
	#     filter_list += " - <code>{}</code>\n".format(html.escape(trigger))

	split_text = split_message(filter_list)
	for text in split_text:
		if filter_list == tl(update.effective_message, "<b>Kata daftar hitam saat ini di {}:</b>\n").format(chat_name):
			send_message(update.effective_message, tl(update.effective_message, "Tidak ada pesan daftar hitam di <b>{}</b>!").format(chat_name), parse_mode=ParseMode.HTML)
			return
		send_message(update.effective_message, text, parse_mode=ParseMode.HTML)


@run_async
@user_admin
def add_blacklist(bot: Bot, update: Update):
	msg = update.effective_message  # type: Optional[Message]
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	words = msg.text.split(None, 1)

	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return

	conn = connected(bot, update, chat, user.id)
	if conn:
		chat_id = conn
		chat_name = dispatcher.bot.getChat(conn).title
	else:
		chat_id = update.effective_chat.id
		if chat.type == "private":
			return
		else:
			chat_name = chat.title

	if len(words) > 1:
		text = words[1]
		to_blacklist = list(set(trigger.strip() for trigger in text.split("\n") if trigger.strip()))
		for trigger in to_blacklist:
			sql.add_to_blacklist(chat_id, trigger.lower())

		if len(to_blacklist) == 1:
			send_message(update.effective_message, tl(update.effective_message, "<code>{}</code> ditambahkan ke daftar hitam di <b>{}</b>!").format(html.escape(to_blacklist[0]), chat_name),
				parse_mode=ParseMode.HTML)

		else:
			send_message(update.effective_message, tl(update.effective_message, "<code>{}</code> Pemicu ditambahkan ke daftar hitam di <b>{}</b>!").format(len(to_blacklist), chat_name), parse_mode=ParseMode.HTML)

	else:
		send_message(update.effective_message, tl(update.effective_message, "Beri tahu saya kata-kata apa yang ingin Anda hapus dari daftar hitam."))


@run_async
@user_admin
def unblacklist(bot: Bot, update: Update):
	msg = update.effective_message  # type: Optional[Message]
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	words = msg.text.split(None, 1)

	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return

	conn = connected(bot, update, chat, user.id)
	if conn:
		chat_id = conn
		chat_name = dispatcher.bot.getChat(conn).title
	else:
		chat_id = update.effective_chat.id
		if chat.type == "private":
			return
		else:
			chat_name = chat.title


	if len(words) > 1:
		text = words[1]
		to_unblacklist = list(set(trigger.strip() for trigger in text.split("\n") if trigger.strip()))
		successful = 0
		for trigger in to_unblacklist:
			success = sql.rm_from_blacklist(chat_id, trigger.lower())
			if success:
				successful += 1

		if len(to_unblacklist) == 1:
			if successful:
				send_message(update.effective_message, tl(update.effective_message, "<code>{}</code> dihapus dari daftar hitam di <b>{}</b>!").format(html.escape(to_unblacklist[0]), chat_name),
							   parse_mode=ParseMode.HTML)
			else:
				send_message(update.effective_message, "Ini bukan pemicu daftar hitam...!")

		elif successful == len(to_unblacklist):
			send_message(update.effective_message, tl(update.effective_message, "<code>{}</code> Pemicu dihapus dari daftar hitam di <b>{}</b>!").format(
					successful, chat_name), parse_mode=ParseMode.HTML)

		elif not successful:
			send_message(update.effective_message, tl(update.effective_message, "Tidak satu pun pemicu ini ada, sehingga tidak dapat dihapus.").format(
					successful, len(to_unblacklist) - successful), parse_mode=ParseMode.HTML)

		else:
			send_message(update.effective_message, tl(update.effective_message, "Pemicu <code>{}</code> dihapus dari daftar hitam. {} Tidak ada, "
				"jadi tidak dihapus.").format(successful, len(to_unblacklist) - successful),
				parse_mode=ParseMode.HTML)
	else:
		send_message(update.effective_message, tl(update.effective_message, "Beri tahu saya kata-kata apa yang ingin Anda hapus dari daftar hitam."))


@run_async
@loggable
@user_admin
def blacklist_mode(bot: Bot, update: Update, args: List[str]):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	msg = update.effective_message  # type: Optional[Message]

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

	if args:
		if args[0].lower() == 'off' or args[0].lower() == 'nothing' or args[0].lower() == 'no':
			settypeblacklist = tl(update.effective_message, 'di biarkan')
			sql.set_blacklist_strength(chat_id, 0, "0")
		elif args[0].lower() == 'del' or args[0].lower() == 'delete':
			settypeblacklist = tl(update.effective_message, 'di biarkan, pesannya akan dihapus')
			sql.set_blacklist_strength(chat_id, 1, "0")
		elif args[0].lower() == 'warn':
			settypeblacklist = tl(update.effective_message, 'di peringati')
			sql.set_blacklist_strength(chat_id, 2, "0")
		elif args[0].lower() == 'mute':
			settypeblacklist = tl(update.effective_message, 'di bisukan')
			sql.set_blacklist_strength(chat_id, 3, "0")
		elif args[0].lower() == 'kick':
			settypeblacklist = tl(update.effective_message, 'di tendang')
			sql.set_blacklist_strength(chat_id, 4, "0")
		elif args[0].lower() == 'ban':
			settypeblacklist = tl(update.effective_message, 'di blokir')
			sql.set_blacklist_strength(chat_id, 5, "0")
		elif args[0].lower() == 'tban':
			if len(args) == 1:
				teks = tl(update.effective_message, """Sepertinya Anda mencoba menetapkan nilai sementara untuk blacklist, tetapi belum menentukan waktu; gunakan `/blacklistmode tban <timevalue>`.

Contoh nilai waktu: 4m = 4 menit, 3h = 3 jam, 6d = 6 hari, 5w = 5 minggu.""")
				send_message(update.effective_message, teks, parse_mode="markdown")
				return ""
			restime = extract_time(msg, args[1])
			if not restime:
				teks = tl(update.effective_message, """Nilai waktu tidak valid!
Contoh nilai waktu: 4m = 4 menit, 3h = 3 jam, 6d = 6 hari, 5w = 5 minggu.""")
				send_message(update.effective_message, teks, parse_mode="markdown")
				return ""
			settypeblacklist = tl(update.effective_message, 'di blokir sementara selama {}').format(args[1])
			sql.set_blacklist_strength(chat_id, 6, str(args[1]))
		elif args[0].lower() == 'tmute':
			if len(args) == 1:
				teks = tl(update.effective_message, """Sepertinya Anda mencoba menetapkan nilai sementara untuk blacklist, tetapi belum menentukan waktu; gunakan `/blacklistmode tmute <timevalue>`.

Contoh nilai waktu: 4m = 4 menit, 3h = 3 jam, 6d = 6 hari, 5w = 5 minggu.""")
				send_message(update.effective_message, teks, parse_mode="markdown")
				return ""
			restime = extract_time(msg, args[1])
			if not restime:
				teks = tl(update.effective_message, """Nilai waktu tidak valid!
Contoh nilai waktu: 4m = 4 menit, 3h = 3 jam, 6d = 6 hari, 5w = 5 minggu.""")
				send_message(update.effective_message, teks, parse_mode="markdown")
				return ""
			settypeblacklist = tl(update.effective_message, 'di bisukan sementara selama {}').format(args[1])
			sql.set_blacklist_strength(chat_id, 7, str(args[1]))
		else:
			send_message(update.effective_message, tl(update.effective_message, "Saya hanya mengerti off/del/warn/ban/kick/mute/tban/tmute!"))
			return ""
		if conn:
			text = tl(update.effective_message, "Mode blacklist diubah, Pengguna akan `{}` pada *{}*!").format(settypeblacklist, chat_name)
		else:
			text = tl(update.effective_message, "Mode blacklist diubah, Pengguna akan `{}`!").format(settypeblacklist)
		send_message(update.effective_message, text, parse_mode="markdown")
		return "<b>{}:</b>\n" \
				"<b>Admin:</b> {}\n" \
				"Changed the blacklist mode. will {}.".format(html.escape(chat.title),
																			mention_html(user.id, user.first_name), settypeblacklist)
	else:
		getmode, getvalue = sql.get_blacklist_setting(chat.id)
		if getmode == 0:
			settypeblacklist = tl(update.effective_message, "tidak aktif")
		elif getmode == 1:
			settypeblacklist = tl(update.effective_message, "hapus")
		elif getmode == 2:
			settypeblacklist = tl(update.effective_message, "warn")
		elif getmode == 3:
			settypeblacklist = tl(update.effective_message, "mute")
		elif getmode == 4:
			settypeblacklist = tl(update.effective_message, "kick")
		elif getmode == 5:
			settypeblacklist = tl(update.effective_message, "ban")
		elif getmode == 6:
			settypeblacklist = tl(update.effective_message, "banned sementara selama {}").format(getvalue)
		elif getmode == 7:
			settypeblacklist = tl(update.effective_message, "mute sementara selama {}").format(getvalue)
		if conn:
			text = tl(update.effective_message, "Mode blacklist saat ini disetel ke *{}* pada *{}*.").format(settypeblacklist, chat_name)
		else:
			text = tl(update.effective_message, "Mode blacklist saat ini disetel ke *{}*.").format(settypeblacklist)
		send_message(update.effective_message, text, parse_mode=ParseMode.MARKDOWN)
	return ""


def findall(p, s):
	i = s.find(p)
	while i != -1:
		yield i
		i = s.find(p, i+1)

@run_async
@user_not_admin
def del_blacklist(bot: Bot, update: Update):
	chat = update.effective_chat  # type: Optional[Chat]
	message = update.effective_message  # type: Optional[Message]
	user = update.effective_user
	to_match = extract_text(message)
	if not to_match:
		return

	getmode, value = sql.get_blacklist_setting(chat.id)

	chat_filters = sql.get_chat_blacklist(chat.id)
	for trigger in chat_filters:
		pattern = r"( |^|[^\w])" + re.escape(trigger) + r"( |$|[^\w])"
		if re.search(pattern, to_match, flags=re.IGNORECASE):
			try:
				if getmode == 0:
					return
				elif getmode == 1:
					message.delete()
				elif getmode == 2:
					message.delete()
					warn(update.effective_user, chat, tl(update.effective_message, "Mengatakan kata '{}' yang ada di daftar hitam").format(trigger), message, update.effective_user, conn=False)
					return
				elif getmode == 3:
					message.delete()
					bot.restrict_chat_member(chat.id, update.effective_user.id, can_send_messages=False)
					bot.sendMessage(chat.id, tl(update.effective_message, "{} di bisukan karena mengatakan kata '{}' yang ada di daftar hitam").format(mention_markdown(user.id, user.first_name), trigger), parse_mode="markdown")
					return
				elif getmode == 4:
					message.delete()
					res = chat.unban_member(update.effective_user.id)
					if res:
						bot.sendMessage(chat.id, tl(update.effective_message, "{} di tendang karena mengatakan kata '{}' yang ada di daftar hitam").format(mention_markdown(user.id, user.first_name), trigger), parse_mode="markdown")
					return
				elif getmode == 5:
					message.delete()
					chat.kick_member(user.id)
					bot.sendMessage(chat.id, tl(update.effective_message, "{} di blokir karena mengatakan kata '{}' yang ada di daftar hitam").format(mention_markdown(user.id, user.first_name), trigger), parse_mode="markdown")
					return
				elif getmode == 6:
					message.delete()
					bantime = extract_time(message, value)
					chat.kick_member(user.id, until_date=bantime)
					bot.sendMessage(chat.id, tl(update.effective_message, "{} di blokir selama {} karena mengatakan kata '{}' yang ada di daftar hitam").format(mention_markdown(user.id, user.first_name), value, trigger), parse_mode="markdown")
					return
				elif getmode == 7:
					message.delete()
					mutetime = extract_time(message, value)
					bot.restrict_chat_member(chat.id, user.id, until_date=mutetime, can_send_messages=False)
					bot.sendMessage(chat.id, tl(update.effective_message, "{} di bisukan selama {} karena mengatakan kata '{}' yang ada di daftar hitam").format(mention_markdown(user.id, user.first_name), value, trigger), parse_mode="markdown")
					return
			except BadRequest as excp:
				if excp.message == "Message to delete not found":
					pass
				else:
					LOGGER.exception("Error while deleting blacklist message.")
			break


def __import_data__(chat_id, data):
	# set chat blacklist
	blacklist = data.get('blacklist', {})
	for trigger in blacklist:
		sql.add_to_blacklist(chat_id, trigger)


def __migrate__(old_chat_id, new_chat_id):
	sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
	blacklisted = sql.num_blacklist_chat_filters(chat_id)
	return tl(user_id, "Ada `{}` kata daftar hitam.").format(blacklisted)


def __stats__():
	return tl(OWNER_ID, "{} pemicu daftar hitam, di seluruh {} obrolan.").format(sql.num_blacklist_filters(),
															sql.num_blacklist_filter_chats())


__mod_name__ = "Word Blacklists"

__help__ = "blacklist_help"

BLACKLIST_HANDLER = DisableAbleCommandHandler("blacklist", blacklist, pass_args=True,
											  admin_ok=True)
ADD_BLACKLIST_HANDLER = CommandHandler("addblacklist", add_blacklist)
UNBLACKLIST_HANDLER = CommandHandler(["unblacklist", "rmblacklist"], unblacklist)
BLACKLISTMODE_HANDLER = CommandHandler("blacklistmode", blacklist_mode, pass_args=True)
BLACKLIST_DEL_HANDLER = MessageHandler(
	(Filters.text | Filters.command | Filters.sticker | Filters.photo) & Filters.group, del_blacklist, edited_updates=True)

dispatcher.add_handler(BLACKLIST_HANDLER)
dispatcher.add_handler(ADD_BLACKLIST_HANDLER)
dispatcher.add_handler(UNBLACKLIST_HANDLER)
dispatcher.add_handler(BLACKLISTMODE_HANDLER)
dispatcher.add_handler(BLACKLIST_DEL_HANDLER, group=BLACKLIST_GROUP)
