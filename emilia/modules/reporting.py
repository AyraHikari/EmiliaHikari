import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User, ParseMode, ChatMember
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest, Unauthorized
from telegram.ext import CommandHandler, RegexHandler, run_async, Filters, CallbackQueryHandler
from telegram.utils.helpers import mention_html, mention_markdown

from emilia import dispatcher, LOGGER, spamfilters, OWNER_ID, SUDO_USERS, SUPPORT_USERS, STRICT_GBAN
from emilia.modules.helper_funcs.chat_status import user_not_admin, user_admin
from emilia.modules.log_channel import loggable
from emilia.modules.sql import reporting_sql as sql

from emilia.modules.languages import tl
from emilia.modules.helper_funcs.alternate import send_message

REPORT_GROUP = 5

CURRENT_REPORT = {}


@run_async
@user_admin
def report_setting(bot: Bot, update: Update, args: List[str]):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return
	chat = update.effective_chat  # type: Optional[Chat]
	msg = update.effective_message  # type: Optional[Message]

	if chat.type == chat.PRIVATE:
		if len(args) >= 1:
			if args[0] in ("yes", "on"):
				sql.set_user_setting(chat.id, True)
				send_message(update.effective_message, tl(update.effective_message, "Menghidupkan pelaporan! Anda akan diberi tahu setiap kali ada yang melaporkan sesuatu."))

			elif args[0] in ("no", "off"):
				sql.set_user_setting(chat.id, False)
				send_message(update.effective_message, tl(update.effective_message, "Mematikan pelaporan! Anda tidak akan mendapatkan laporan apa pun."))
		else:
			send_message(update.effective_message, tl(update.effective_message, "Preferensi laporan Anda saat ini: `{}`").format(sql.user_should_report(chat.id)),
						   parse_mode=ParseMode.MARKDOWN)

	else:
		if len(args) >= 1:
			if args[0] in ("yes", "on"):
				sql.set_chat_setting(chat.id, True)
				send_message(update.effective_message, tl(update.effective_message, "Menghidupkan pelaporan! Admin yang telah mengaktifkan laporan akan diberi tahu ketika seseorang menyebut /report "
							   "atau @admin."))

			elif args[0] in ("no", "off"):
				sql.set_chat_setting(chat.id, False)
				send_message(update.effective_message, tl(update.effective_message, "Mematikan pelaporan! Tidak ada admin yang akan diberitahukan ketika seseorang menyebut /report atau @admin."))
		else:
			send_message(update.effective_message, tl(update.effective_message, "Pengaturan obrolan saat ini adalah: `{}`").format(sql.chat_should_report(chat.id)),
						   parse_mode=ParseMode.MARKDOWN)


@run_async
@user_not_admin
@loggable
def report(bot: Bot, update: Update) -> str:
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return
	message = update.effective_message  # type: Optional[Message]
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	global CURRENT_REPORT

	if chat and message.reply_to_message and sql.chat_should_report(chat.id):
		reported_user = message.reply_to_message.from_user  # type: Optional[User]
		chat_name = chat.title or chat.first or chat.username

		a, b = user_protection_checker(bot, message.reply_to_message.from_user.id)
		if not a:
			return ""

		admin_list = chat.get_administrators()

		if chat.username and chat.type == Chat.SUPERGROUP:
			msg = tl(update.effective_message, "<b>{}:</b>" \
				  "\n<b>Pengguna yang dilaporkan:</b> {} (<code>{}</code>)" \
				  "\n<b>Dilaporkan oleh:</b> {} (<code>{}</code>)").format(html.escape(chat.title),
																	  mention_html(
																		  reported_user.id,
																		  reported_user.first_name),
																	  reported_user.id,
																	  mention_html(user.id,
																				   user.first_name),
																	  user.id)
			#link = "\n<b>Link:</b> " \
			#       "<a href=\"http://telegram.me/{}/{}\">klik disini</a>".format(chat.username, message.message_id)

		else:
			msg = tl(update.effective_message, "{} memanggil admin di \"{}\"!").format(mention_html(user.id, user.first_name),
															   html.escape(chat_name))
			#link = ""

		if chat.username:
			chatlink = "https://t.me/{}/{}".format(chat.username, str(message.reply_to_message.message_id))
		else:
			chatlink = "https://t.me/c/{}/{}".format(str(chat.id)[4:], str(message.reply_to_message.message_id))
		keyboard = [
			  [InlineKeyboardButton(tl(update.effective_message, "⚠️ Pesan yang dilaporkan"), url=chatlink)],
			  [InlineKeyboardButton(tl(update.effective_message, "⚠️ Tendang"), callback_data="rp_{}=1={}".format(chat.id, reported_user.id)),
			  InlineKeyboardButton(tl(update.effective_message, "⛔️ Banned"), callback_data="rp_{}=2={}".format(chat.id, reported_user.id))],
			  [InlineKeyboardButton(tl(update.effective_message, "Hapus pesan"), callback_data="rp_{}=3={}".format(chat.id, message.reply_to_message.message_id))],
			  [InlineKeyboardButton(tl(update.effective_message, "Tutup Tombol"), callback_data="rp_{}=4={}".format(chat.id, reported_user.id))]
			]
		reply_markup = InlineKeyboardMarkup(keyboard)

		should_forward = True
		bot.send_message(chat.id, tl(update.effective_message, "<i>⚠️ Pesan telah di laporkan ke semua admin!</i>"), parse_mode=ParseMode.HTML, reply_to_message_id=message.message_id)

		CURRENT_REPORT[str(chat.id)] = msg
		CURRENT_REPORT[str(chat.id)+"key"] = reply_markup
		CURRENT_REPORT[str(chat.id)+"user"] = {'name': reported_user.first_name, 'id': reported_user.id, 'rname': user.first_name, 'rid': user.id}
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

@run_async
@user_not_admin
@loggable
def report_alt(bot: Bot, update: Update) -> str:
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return
	message = update.effective_message  # type: Optional[Message]
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]

	if chat and message.reply_to_message and sql.chat_should_report(chat.id):
		reported_user = message.reply_to_message.from_user  # type: Optional[User]
		chat_name = chat.title or chat.first or chat.username
		admin_list = chat.get_administrators()

		msg = tl(update.effective_message, "<b>{}:</b>" \
			  "\n<b>Pengguna yang dilaporkan:</b> {} (<code>{}</code>)" \
			  "\n<b>Dilaporkan oleh:</b> {} (<code>{}</code>)").format(html.escape(chat.title),
																	  mention_html(
																		  reported_user.id,
																		  reported_user.first_name),
																	  reported_user.id,
																	  mention_html(user.id,
																				   user.first_name),
																	  user.id)
		all_admins = []
		for admin in admin_list:
			if admin.user.is_bot:  # don't tag bot
				continue

			if sql.user_should_report(admin.user.id):
				all_admins.append("<a href='tg://user?id={}'>⁣</a>".format(admin.user.id))

		bot.send_message(chat.id, tl(update.effective_message, "⚠️ {} <b>telah di laporkan ke admin!</b>{}").format(
					mention_html(reported_user.id, reported_user.first_name),
					"".join(all_admins)), parse_mode=ParseMode.HTML, reply_to_message_id=message.reply_to_message.message_id)
		return msg

	return ""


def button(bot, update):
	query = update.callback_query
	splitter = query.data.replace("rp_", "").split("=")
	chat = update.effective_chat
	report_chat = splitter[0]
	report_method = splitter[1]
	report_target = splitter[2]
	msg = CURRENT_REPORT.get(str(report_chat))
	userinfo = CURRENT_REPORT.get(str(report_chat)+"user")
	key = CURRENT_REPORT.get(str(report_chat)+"key")
	if msg == None or userinfo == None or key == None:
		query.message.edit_text(tl(update.effective_message, "Sesi telah berakhir!"))
		return

	if splitter[1] == "1":
		keyboard = [
			[InlineKeyboardButton(tl(update.effective_message, "Ya"), callback_data="ak_1+y|{}={}".format(report_chat, report_target)),
			InlineKeyboardButton(tl(update.effective_message, "Tidak"), callback_data="ak_1+n|{}={}".format(report_chat, report_target))]
		]
		reply_markup = InlineKeyboardMarkup(keyboard)
		bot.edit_message_text(text=msg + tl(update.effective_message, "\n\nApakah anda yakin ingin menendang {}?").format(userinfo.get('name')),
						  chat_id=query.message.chat_id,
						  message_id=query.message.message_id, parse_mode=ParseMode.HTML,
						  reply_markup=reply_markup)
	elif splitter[1] == "2":
		keyboard = [
			[InlineKeyboardButton(tl(update.effective_message, "Ya"), callback_data="ak_2+y|{}={}".format(report_chat, report_target)),
			InlineKeyboardButton(tl(update.effective_message, "Tidak"), callback_data="ak_2+n|{}={}".format(report_chat, report_target))]
		]
		reply_markup = InlineKeyboardMarkup(keyboard)
		bot.edit_message_text(text=msg + tl(update.effective_message, "\n\nApakah anda yakin ingin banned {}?").format(userinfo.get('name')),
						  chat_id=query.message.chat_id,
						  message_id=query.message.message_id, parse_mode=ParseMode.HTML,
						  reply_markup=reply_markup)
	elif splitter[1] == "3":
		keyboard = [
			[InlineKeyboardButton(tl(update.effective_message, "Ya"), callback_data="ak_3+y|{}={}".format(report_chat, report_target)),
			InlineKeyboardButton(tl(update.effective_message, "Tidak"), callback_data="ak_3+n|{}={}".format(report_chat, report_target))]
		]
		reply_markup = InlineKeyboardMarkup(keyboard)
		bot.edit_message_text(text=msg + tl(update.effective_message, "\n\nHapus pesan?"),
						  chat_id=query.message.chat_id,
						  message_id=query.message.message_id, parse_mode=ParseMode.HTML,
						  reply_markup=reply_markup)
	elif splitter[1] == "4":
		try:
			bot.edit_message_text(text=msg + tl(update.effective_message, "\n\nTombol ditutup!"),
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
	splitter = query.data.replace("ak_", "").split("+")
	isyes = splitter[1].split('|')[0]
	report_chat = splitter[1].split('|')[1].split('=')[0]
	report_target = splitter[1].split('|')[1].split('=')[1]
	chat = update.effective_chat
	msg = CURRENT_REPORT.get(str(report_chat))
	userinfo = CURRENT_REPORT.get(str(report_chat)+"user")
	key = CURRENT_REPORT.get(str(report_chat)+"key")

	if isyes == "y":
		a, b = user_protection_checker(bot, report_target)
		if not a:
			bot.edit_message_text(text=msg + b,
							  chat_id=query.message.chat_id,
							  message_id=query.message.message_id, parse_mode=ParseMode.HTML)
			return
		if splitter[0] == "1":
			try:
				bot.unbanChatMember(report_chat, report_target)
				bot.sendMessage(report_chat, text=tl(update.effective_message, "{} telah di tendang!\nOleh: {}").format(\
					mention_markdown(userinfo['id'], userinfo['name']), mention_markdown(chat.id, chat.first_name)), \
					parse_mode=ParseMode.MARKDOWN)
				bot.edit_message_text(text=msg + tl(update.effective_message, "\n\n{} telah di tendang!").format(mention_html(userinfo['id'], userinfo['name'])),
							  chat_id=query.message.chat_id,
							  message_id=query.message.message_id, parse_mode=ParseMode.HTML)
			except Exception as err:
				bot.edit_message_text(text=msg + "\n\nError: {}".format(err),
							  chat_id=query.message.chat_id,
							  message_id=query.message.message_id, parse_mode=ParseMode.HTML)
		elif splitter[0] == "2":
			try:
				bot.kickChatMember(report_chat, report_target)
				bot.sendMessage(report_chat, text=tl(update.effective_message, "{} telah di banned!\nOleh: {}").format(\
					mention_markdown(userinfo['id'], userinfo['name']), mention_markdown(chat.id, chat.first_name)), \
					parse_mode=ParseMode.MARKDOWN)
				bot.edit_message_text(text=msg + tl(update.effective_message, "\n\n{} telah di banned!").format(mention_html(userinfo['id'], userinfo['name'])),
							  chat_id=query.message.chat_id,
							  message_id=query.message.message_id, parse_mode=ParseMode.HTML)
			except Exception as err:
				bot.edit_message_text(text=msg + "\n\nError: {}".format(err),
							  chat_id=query.message.chat_id,
							  message_id=query.message.message_id, parse_mode=ParseMode.HTML)
		elif splitter[0] == "3":
			try:
				bot.deleteMessage(report_chat, report_target)
				bot.edit_message_text(text=msg + tl(update.effective_message, "\n\nPesan dihapus!"),
							  chat_id=query.message.chat_id,
							  message_id=query.message.message_id, parse_mode=ParseMode.HTML)
			except Exception as err:
				bot.edit_message_text(text=msg + "\n\nError: {}".format(err),
							  chat_id=query.message.chat_id,
							  message_id=query.message.message_id, parse_mode=ParseMode.HTML)
	elif isyes == "n":
		bot.edit_message_text(text=msg,
							  chat_id=query.message.chat_id,
							  message_id=query.message.message_id, parse_mode=ParseMode.HTML,
							  reply_markup=key)


def user_protection_checker(bot, user_id):
	if not user_id:
		return False, tl(update.effective_message, "Anda sepertinya tidak mengacu pada pengguna.")

	if int(user_id) == OWNER_ID:
		return False, "\n\nError: This one is my owner!"

	if int(user_id) in SUDO_USERS:
		return False, "\n\nError: User is under protection"

	# if int(user_id) in SUPPORT_USERS:
	# 	return False, "Error: User is under protection"

	if int(user_id) == bot.id:
		return False, "\n\nError: This is myself!"

	return True, ""


def __migrate__(old_chat_id, new_chat_id):
	sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
	return tl(user_id, "Obrolan ini disetel untuk mengirim laporan pengguna ke admin, melalui /report dan @admin: `{}`").format(
		sql.chat_should_report(chat_id))


def __user_settings__(user_id):
	return tl(user_id, "Anda menerima laporan dari obrolan yang Anda ikuti: `{}`.\nAktifkan ini dengan /reports di PM.").format(
		sql.user_should_report(user_id))


__mod_name__ = "Reporting"

__help__ = "reporting_help"


REPORT_HANDLER = CommandHandler("report", report, filters=Filters.group)
SETTING_HANDLER = CommandHandler("reports", report_setting, pass_args=True)
ADMIN_REPORT_HANDLER = RegexHandler("(?i)@admin(s)?", report)
Callback_Report = CallbackQueryHandler(button, pattern=r"rp_")
Callback_ReportAsk = CallbackQueryHandler(buttonask, pattern=r"ak_")

dispatcher.add_handler(REPORT_HANDLER, REPORT_GROUP)
dispatcher.add_handler(ADMIN_REPORT_HANDLER, REPORT_GROUP)
dispatcher.add_handler(SETTING_HANDLER)
dispatcher.add_handler(Callback_Report)
dispatcher.add_handler(Callback_ReportAsk)
