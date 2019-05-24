import html
from typing import Optional, List

import telegram.ext as tg
from telegram import Message, Chat, Update, Bot, ParseMode, User, MessageEntity
from telegram import TelegramError
from telegram.error import BadRequest
from telegram.ext import CommandHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import mention_html

import emilia.modules.sql.sticker_sql as sql
from emilia import dispatcher, SUDO_USERS, LOGGER, spamfilters
from emilia.modules.disable import DisableAbleCommandHandler
from emilia.modules.helper_funcs.chat_status import can_delete, is_user_admin, user_not_admin, user_admin, \
		bot_can_delete, is_bot_admin
from emilia.modules.helper_funcs.filters import CustomFilters
from emilia.modules.helper_funcs.misc import split_message
from emilia.modules.log_channel import loggable
from emilia.modules.sql import users_sql
from emilia.modules.connection import connected


@run_async
def blackliststicker(bot: Bot, update: Update, args: List[str]):
	msg = update.effective_message  # type: Optional[Message]
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]

	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
	if spam == True:
		return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
		
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
		
	sticker_list = "<b>Daftar hitam stiker saat saat ini di {}:</b>\n".format(chat_name)

	all_stickerlist = sql.get_chat_stickers(chat_id)

	if len(args) > 0 and args[0].lower() == 'copy':
		for trigger in all_stickerlist:
			sticker_list += "<code>{}</code>\n".format(html.escape(trigger))
	elif len(args) == 0:
		for trigger in all_stickerlist:
			sticker_list += " - <code>{}</code>\n".format(html.escape(trigger))

	split_text = split_message(sticker_list)
	for text in split_text:
		if sticker_list == "<b>Daftar hitam stiker saat saat ini di {}:</b>\n".format(chat_name):
			msg.reply_text("Tidak ada stiker daftar hitam stiker di <b>{}</b>!".format(chat_name), parse_mode=ParseMode.HTML)
			return
	msg.reply_text(text, parse_mode=ParseMode.HTML)


@run_async
@user_admin
def add_blackliststicker(bot: Bot, update: Update):
	msg = update.effective_message  # type: Optional[Message]
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	words = msg.text.split(None, 1)

	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
	if spam == True:
		return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")

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
		text = words[1].replace('https://t.me/addstickers/', '')
		to_blacklist = list(set(trigger.strip() for trigger in text.split("\n") if trigger.strip()))
		added = 0
		for trigger in to_blacklist:
			try:
				get = bot.getStickerSet(trigger)
				sql.add_to_stickers(chat_id, trigger.lower())
				added += 1
			except BadRequest:
				msg.reply_text("Stiker `{}` tidak dapat di temukan!".format(trigger), parse_mode="markdown")

		if added == 0:
			return

		if len(to_blacklist) == 1:
			msg.reply_text("Stiker <code>{}</code> ditambahkan ke daftar hitam stiker di <b>{}</b>!".format(html.escape(to_blacklist[0]), chat_name),
				parse_mode=ParseMode.HTML)
		else:
			msg.reply_text(
					"<code>{}</code> stiker ditambahkan ke daftar hitam stiker di <b>{}</b>!".format(added, chat_name), parse_mode=ParseMode.HTML)
	elif msg.reply_to_message:
		added = 0
		trigger = msg.reply_to_message.sticker.set_name
		if trigger == None:
			msg.reply_text("Stiker tidak valid!")
			return
		try:
			get = bot.getStickerSet(trigger)
			sql.add_to_stickers(chat_id, trigger.lower())
			added += 1
		except BadRequest:
			msg.reply_text("Stiker `{}` tidak dapat di temukan!".format(trigger), parse_mode="markdown")

		if added == 0:
			return

		msg.reply_text("Stiker <code>{}</code> ditambahkan ke daftar hitam stiker di <b>{}</b>!".format(trigger, chat_name), parse_mode=ParseMode.HTML)
	else:
		msg.reply_text("Beri tahu saya stiker apa yang ingin Anda tambahkan ke daftar hitam stiker.")

@run_async
@user_admin
def unblackliststicker(bot: Bot, update: Update):
	msg = update.effective_message  # type: Optional[Message]
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	words = msg.text.split(None, 1)

	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
	if spam == True:
		return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")

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
		text = words[1].replace('https://t.me/addstickers/', '')
		to_unblacklist = list(set(trigger.strip() for trigger in text.split("\n") if trigger.strip()))
		successful = 0
		for trigger in to_unblacklist:
			success = sql.rm_from_stickers(chat_id, trigger.lower())
			if success:
				successful += 1

		if len(to_unblacklist) == 1:
			if successful:
				msg.reply_text("Stiker <code>{}</code> dihapus dari daftar hitam di <b>{}</b>!".format(html.escape(to_unblacklist[0]), chat_name),
							   parse_mode=ParseMode.HTML)
			else:
				msg.reply_text("Ini tidak ada di daftar hitam stiker...!")

		elif successful == len(to_unblacklist):
			msg.reply_text(
				"Stiker <code>{}</code> dihapus dari daftar hitam di <b>{}</b>!".format(
					successful, chat_name), parse_mode=ParseMode.HTML)

		elif not successful:
			msg.reply_text(
				"Tidak satu pun stiker ini ada, sehingga tidak dapat dihapus.".format(
					successful, len(to_unblacklist) - successful), parse_mode=ParseMode.HTML)

		else:
			msg.reply_text(
				"Stiker <code>{}</code> dihapus dari daftar hitam. {} Tidak ada, "
				"jadi tidak dihapus.".format(successful, len(to_unblacklist) - successful),
				parse_mode=ParseMode.HTML)
	elif msg.reply_to_message:
		trigger = msg.reply_to_message.sticker.set_name
		if trigger == None:
			msg.reply_text("Stiker tidak valid!")
			return
		success = sql.rm_from_stickers(chat_id, trigger.lower())

		if success:
			msg.reply_text("Stiker <code>{}</code> dihapus dari daftar hitam di <b>{}</b>!".format(trigger, chat_name),
							   parse_mode=ParseMode.HTML)
		else:
			msg.reply_text("{} tidak ada di daftar hitam stiker...!".format(trigger))
	else:
		msg.reply_text("Beri tahu saya stiker apa yang ingin Anda tambahkan ke daftar hitam stiker.")

@run_async
@user_not_admin
def del_blackliststicker(bot: Bot, update: Update):
	chat = update.effective_chat  # type: Optional[Chat]
	message = update.effective_message  # type: Optional[Message]
	to_match = message.sticker
	if not to_match:
		return

	chat_filters = sql.get_chat_stickers(chat.id)
	for trigger in chat_filters:
		if to_match.set_name.lower() == trigger.lower():
			try:
				message.delete()
			except BadRequest as excp:
				if excp.message == "Message to delete not found":
					pass
				else:
					LOGGER.exception("Error while deleting blacklist message.")
				break


def __import_data__(chat_id, data):
    # set chat blacklist
    blacklist = data.get('sticker_blacklist', {})
    for trigger in blacklist:
        sql.add_to_blacklist(chat_id, trigger)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    blacklisted = sql.num_sticker_chat_filters(chat_id)
    return "Ada {} daftar hitam stiker.".format(blacklisted)

def __stats__():
    return "{} pemicu daftar hitam stiker, di seluruh {} obrolan.".format(sql.num_stickers_filters(),
                                                            sql.num_stickers_filter_chats())

__help__ = """
Daftar hitam stiker digunakan untuk menghentikan stiker tertentu. Kapan pun stiker dikirim, pesan akan segera dihapus.

*CATATAN:* daftar hitam stiker tidak mempengaruhi admin grup.

 - /blsticker: Lihat kata-kata daftar hitam saat ini.

*Hanya admin:*
 - /addblsticker <pemicu>: Tambahkan pemicu stiker ke daftar hitam. Setiap baris dianggap sebagai pemicu, jadi gunakan garis yang berbeda akan memungkinkan Anda menambahkan beberapa pemicu.
 - /unblsticker <pemicu>: Hapus pemicu dari daftar hitam. Logika newline yang sama berlaku di sini, sehingga Anda dapat menghapus beberapa pemicu sekaligus.
 - /rmblsticker <pemicu>: Sama seperti di atas.

Catatan:
 - `<pemicu>` bisa menjadi `https://t.me/addstickers/<pemicu>` atau hanya `<pemicu>`
 - Command diatas bisa di gunakan dengan membalas stiker pemicu
"""

__mod_name__ = "Daftar Hitam Stiker"

BLACKLIST_STICKER_HANDLER = DisableAbleCommandHandler("blsticker", blackliststicker, pass_args=True, admin_ok=True)
ADDBLACKLIST_STICKER_HANDLER = DisableAbleCommandHandler("addblsticker", add_blackliststicker)
UNBLACKLIST_STICKER_HANDLER = CommandHandler(["unblsticker", "rmblsticker"], unblackliststicker)
BLACKLIST_STICKER_DEL_HANDLER = MessageHandler(Filters.sticker & Filters.group, del_blackliststicker)

dispatcher.add_handler(BLACKLIST_STICKER_HANDLER)
dispatcher.add_handler(ADDBLACKLIST_STICKER_HANDLER)
dispatcher.add_handler(UNBLACKLIST_STICKER_HANDLER)
dispatcher.add_handler(BLACKLIST_STICKER_DEL_HANDLER)
