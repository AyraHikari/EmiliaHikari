import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User, ParseMode, ChatMember
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest, Unauthorized
from telegram.ext import CommandHandler, RegexHandler, run_async, Filters, CallbackQueryHandler
from telegram.utils.helpers import mention_html

from emilia import dispatcher, LOGGER, spamfilters
from emilia.modules.helper_funcs.chat_status import user_not_admin, user_admin
from emilia.modules.log_channel import loggable
from emilia.modules.sql import reporting_sql as sql

REPORT_GROUP = 5


@run_async
@user_admin
def report_setting(bot: Bot, update: Update, args: List[str]):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
	if spam == True:
		return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
	chat = update.effective_chat  # type: Optional[Chat]
	msg = update.effective_message  # type: Optional[Message]

	if chat.type == chat.PRIVATE:
		if len(args) >= 1:
			if args[0] in ("yes", "on"):
				sql.set_user_setting(chat.id, True)
				msg.reply_text("Menghidupkan pelaporan! Anda akan diberi tahu setiap kali ada yang melaporkan sesuatu.")

			elif args[0] in ("no", "off"):
				sql.set_user_setting(chat.id, False)
				msg.reply_text("Mematikan pelaporan! Anda tidak akan mendapatkan laporan apa pun.")
		else:
			msg.reply_text("Preferensi laporan Anda saat ini: `{}`".format(sql.user_should_report(chat.id)),
						   parse_mode=ParseMode.MARKDOWN)

	else:
		if len(args) >= 1:
			if args[0] in ("yes", "on"):
				sql.set_chat_setting(chat.id, True)
				msg.reply_text("Menghidupkan pelaporan! Admin yang telah mengaktifkan laporan akan diberi tahu ketika seseorang menyebut /report "
							   "atau @admin.")

			elif args[0] in ("no", "off"):
				sql.set_chat_setting(chat.id, False)
				msg.reply_text("Mematikan pelaporan! Tidak ada admin yang akan diberitahukan ketika seseorang menyebut /report atau @admin.")
		else:
			msg.reply_text("Pengaturan obrolan saat ini adalah: `{}`".format(sql.chat_should_report(chat.id)),
						   parse_mode=ParseMode.MARKDOWN)


@run_async
@user_not_admin
@loggable
def report(bot: Bot, update: Update) -> str:
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
	if spam == True:
		return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
	message = update.effective_message  # type: Optional[Message]
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	global msg
	global keyboard

	if chat and message.reply_to_message and sql.chat_should_report(chat.id):
		reported_user = message.reply_to_message.from_user  # type: Optional[User]
		chat_name = chat.title or chat.first or chat.username
		admin_list = chat.get_administrators()

		if chat.username and chat.type == Chat.SUPERGROUP:
			msg = "<b>{}:</b>" \
				  "\n<b>Pengguna yang dilaporkan:</b> {} (<code>{}</code>)" \
				  "\n<b>Dilaporkan oleh:</b> {} (<code>{}</code>)".format(html.escape(chat.title),
																	  mention_html(
																		  reported_user.id,
																		  reported_user.first_name),
																	  reported_user.id,
																	  mention_html(user.id,
																				   user.first_name),
																	  user.id)
			#link = "\n<b>Link:</b> " \
			#       "<a href=\"http://telegram.me/{}/{}\">klik disini</a>".format(chat.username, message.message_id)

			keyboard = [
			  [InlineKeyboardButton(u"⚠️ Pesan yang dilaporkan", url="https://t.me/{}/{}".format(chat.username, str(message.reply_to_message.message_id)))],
			  [InlineKeyboardButton(u"⚠️ Tendang", callback_data="report_{}=kick={}={}".format(chat.id, reported_user.id, reported_user.first_name)),
			  InlineKeyboardButton(u"⛔️ Banned", callback_data="report_{}=banned={}={}".format(chat.id, reported_user.id, reported_user.first_name))],
			  [InlineKeyboardButton(u"Hapus pesan", callback_data="report_{}=delete={}={}".format(chat.id, reported_user.id, message.reply_to_message.message_id))],
			  [InlineKeyboardButton(u"Tutup Tombol", callback_data="report_{}=close={}={}".format(chat.id, reported_user.id, reported_user.first_name))]
			]
			reply_markup = InlineKeyboardMarkup(keyboard)

			should_forward = True
			bot.send_message(chat.id, "<i>⚠️ Pesan telah di laporkan ke semua admin!</i>", parse_mode=ParseMode.HTML, reply_to_message_id=message.message_id)

		else:
			msg = "{} memanggil admin di \"{}\"!".format(mention_html(user.id, user.first_name),
															   html.escape(chat_name))
			#link = ""
			reply_markup = ""

			should_forward = True
			bot.send_message(chat.id, "<i>⚠️ Pesan telah di laporkan ke semua admin!</i>", parse_mode=ParseMode.HTML, reply_to_message_id=message.message_id)

		for admin in admin_list:
			if admin.user.is_bot:  # can't message bots
				continue

			if sql.user_should_report(admin.user.id):
				try:
					#bot.send_message(admin.user.id, msg + link, parse_mode=ParseMode.HTML)
					#bot.send_message(admin.user.id, msg, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

					try:
						if should_forward:
							message.reply_to_message.forward(admin.user.id)

							if len(message.text.split()) > 1:  # If user is giving a reason, send his message too
								message.forward(admin.user.id)
					except:
						pass
					bot.send_message(admin.user.id, msg, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

				except Unauthorized:
					pass
				except BadRequest as excp:  # TODO: cleanup exceptions
					LOGGER.exception("Exception while reporting user")
		return msg

	return ""


def button(bot, update):
	query = update.callback_query
	splitter = query.data.replace("report_", "").split("=")
	chat = update.effective_chat
	global report_chat, report_method, report_target, report_name
	report_chat = splitter[0]
	report_method = splitter[1]
	report_target = splitter[2]
	report_name = splitter[3]
	admin_list = bot.getChatAdministrators(report_chat)
	try:
		cek = msg
	except:
		return bot.edit_message_text(text="Sesi telah berakhir!\nSilahkan di eksekusi manual ya kak!",
									 chat_id=query.message.chat_id,
									 message_id=query.message.message_id, parse_mode=ParseMode.HTML)
	idadmin = []
	for x in admin_list:
		idadmin.append(x.user.id)
	if chat.id not in idadmin:
		return bot.edit_message_text(text="Anda bukan admin!",
									 chat_id=query.message.chat_id,
									 message_id=query.message.message_id, parse_mode=ParseMode.HTML)
	if splitter[1] == "kick":
		keyboard = [
			[InlineKeyboardButton(u"Ya", callback_data="ask_kick+y"),
			InlineKeyboardButton(u"Tidak", callback_data="ask_kick+n")]
		]
		reply_markup = InlineKeyboardMarkup(keyboard)
		bot.edit_message_text(text=msg + "\n\nApakah anda yakin ingin menendang {}?".format(splitter[3]),
						  chat_id=query.message.chat_id,
						  message_id=query.message.message_id, parse_mode=ParseMode.HTML,
						  reply_markup=reply_markup)
	elif splitter[1] == "banned":
		keyboard = [
			[InlineKeyboardButton(u"Ya", callback_data="ask_banned+y"),
			InlineKeyboardButton(u"Tidak", callback_data="ask_banned+n")]
		]
		reply_markup = InlineKeyboardMarkup(keyboard)
		bot.edit_message_text(text=msg + "\n\nApakah anda yakin ingin banned {}?".format(splitter[3]),
						  chat_id=query.message.chat_id,
						  message_id=query.message.message_id, parse_mode=ParseMode.HTML,
						  reply_markup=reply_markup)
	elif splitter[1] == "delete":
		keyboard = [
			[InlineKeyboardButton(u"Ya", callback_data="ask_delete+y"),
			InlineKeyboardButton(u"Tidak", callback_data="ask_delete+n")]
		]
		reply_markup = InlineKeyboardMarkup(keyboard)
		bot.edit_message_text(text=msg + "\n\nHapus pesan?",
						  chat_id=query.message.chat_id,
						  message_id=query.message.message_id, parse_mode=ParseMode.HTML,
						  reply_markup=reply_markup)
	elif splitter[1] == "close":
		try:
			bot.edit_message_text(text=msg + "\n\nTombol ditutup!",
						  chat_id=query.message.chat_id,
						  message_id=query.message.message_id, parse_mode=ParseMode.HTML)
		except Exception as err:
			bot.edit_message_text(text=msg + "\n\nError: {}".format(err),
						  chat_id=query.message.chat_id,
						  message_id=query.message.message_id, parse_mode=ParseMode.HTML)
		"""
		bot.edit_message_text(text="Chat: {}\nAction: {}\nUser: {}".format(splitter[0], splitter[1], splitter[2]),
						  chat_id=query.message.chat_id,
						  message_id=query.message.message_id)
		"""


def buttonask(bot, update):
	query = update.callback_query
	splitter = query.data.replace("ask_", "").split("+")
	chat = update.effective_chat
	try:
		cek = msg
		cek = keyboard
	except:
		return bot.edit_message_text(text="Sesi telah berakhir!\nSilahkan di eksekusi manual ya kak!",
									 chat_id=query.message.chat_id,
									 message_id=query.message.message_id, parse_mode=ParseMode.HTML)
	reply_markup = InlineKeyboardMarkup(keyboard)
	if splitter[1] == "y":
		if splitter[0] == "kick":
			try:
				bot.kickChatMember(report_chat, report_target)
				bot.unbanChatMember(report_chat, report_target)
				bot.sendMessage(report_chat, text="[{}](tg://user?id={}) telah di tendang!\nOleh: [{}](tg://user?id={})".format(\
					report_name, report_target, chat.first_name, chat.id), \
					parse_mode=ParseMode.MARKDOWN)
				bot.edit_message_text(text=msg + "\n\n{} telah di tendang!".format(report_name),
							  chat_id=query.message.chat_id,
							  message_id=query.message.message_id, parse_mode=ParseMode.HTML)
			except Exception as err:
				bot.edit_message_text(text=msg + "\n\nError: {}".format(err),
							  chat_id=query.message.chat_id,
							  message_id=query.message.message_id, parse_mode=ParseMode.HTML)
		elif splitter[0] == "banned":
			try:
				bot.kickChatMember(report_chat, report_target)
				bot.sendMessage(report_chat, text="[{}](tg://user?id={}) telah di banned!\nOleh: [{}](tg://user?id={})".format(\
					report_name, report_target, chat.first_name, chat.id), \
					parse_mode=ParseMode.MARKDOWN)
				bot.edit_message_text(text=msg + "\n\n{} telah di banned!".format(report_name),
							  chat_id=query.message.chat_id,
							  message_id=query.message.message_id, parse_mode=ParseMode.HTML)
			except Exception as err:
				bot.edit_message_text(text=msg + "\n\nError: {}".format(err),
							  chat_id=query.message.chat_id,
							  message_id=query.message.message_id, parse_mode=ParseMode.HTML)
		elif splitter[0] == "delete":
			try:
				bot.deleteMessage(report_chat, report_name)
				bot.edit_message_text(text=msg + "\n\nPesan dihapus!",
							  chat_id=query.message.chat_id,
							  message_id=query.message.message_id, parse_mode=ParseMode.HTML)
			except Exception as err:
				bot.edit_message_text(text=msg + "\n\nError: {}".format(err),
							  chat_id=query.message.chat_id,
							  message_id=query.message.message_id, parse_mode=ParseMode.HTML)
	elif splitter[1] == "n":
		bot.edit_message_text(text=msg,
							  chat_id=query.message.chat_id,
							  message_id=query.message.message_id, parse_mode=ParseMode.HTML,
							  reply_markup=reply_markup)


def __migrate__(old_chat_id, new_chat_id):
	sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
	return "Obrolan ini disetel untuk mengirim laporan pengguna ke admin, melalui /report dan @admin: `{}`".format(
		sql.chat_should_report(chat_id))


def __user_settings__(user_id):
	return "Anda menerima laporan dari obrolan yang Anda ikuti: `{}`.\nAktifkan ini dengan /reports di PM.".format(
		sql.user_should_report(user_id))


__mod_name__ = "Pelaporan"

__help__ = """
 - /report <alasan>: membalas pesan untuk melaporkannya ke admin.
 - @admin: membalas pesan untuk melaporkannya ke admin.
CATATAN: tidak satu pun dari ini akan dipicu jika digunakan oleh admin

*Hanya admin:*
 - /reports <on/off>: ubah pengaturan laporan, atau lihat status saat ini.
   - Jika selesai di PM, matikan status Anda.
   - Jika dalam obrolan, matikan status obrolan itu.
"""

REPORT_HANDLER = CommandHandler("report", report, filters=Filters.group)
SETTING_HANDLER = CommandHandler("reports", report_setting, pass_args=True)
ADMIN_REPORT_HANDLER = RegexHandler("(?i)@admin(s)?", report)
Callback_Report = CallbackQueryHandler(button, pattern=r"report_")
Callback_ReportAsk = CallbackQueryHandler(buttonask, pattern=r"ask_")

dispatcher.add_handler(REPORT_HANDLER, REPORT_GROUP)
dispatcher.add_handler(ADMIN_REPORT_HANDLER, REPORT_GROUP)
dispatcher.add_handler(SETTING_HANDLER)
dispatcher.add_handler(Callback_Report)
dispatcher.add_handler(Callback_ReportAsk)
