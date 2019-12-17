import re, ast
from io import BytesIO
from typing import Optional, List

from telegram import MAX_MESSAGE_LENGTH, ParseMode, InlineKeyboardMarkup
from telegram import Message, Update, Bot
from telegram.error import BadRequest, Unauthorized
from telegram.ext import CommandHandler, RegexHandler
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import escape_markdown

import emilia.modules.sql.notes_sql as sql
from emilia import dispatcher, MESSAGE_DUMP, LOGGER, spamfilters, OWNER_ID
from emilia.modules.disable import DisableAbleCommandHandler
from emilia.modules.helper_funcs.chat_status import user_admin
from emilia.modules.helper_funcs.misc import build_keyboard, revert_buttons
from emilia.modules.helper_funcs.msg_types import get_note_type

from emilia.modules.connection import connected
from emilia.modules.languages import tl
from emilia.modules.helper_funcs.alternate import send_message

FILE_MATCHER = re.compile(r"^###file_id(!photo)?###:(.*?)(?:\s|$)")
STICKER_MATCHER = re.compile(r"^###sticker(!photo)?###:")
BUTTON_MATCHER = re.compile(r"^###button(!photo)?###:(.*?)(?:\s|$)")
MYFILE_MATCHER = re.compile(r"^###file(!photo)?###:")
MYPHOTO_MATCHER = re.compile(r"^###photo(!photo)?###:")
MYAUDIO_MATCHER = re.compile(r"^###audio(!photo)?###:")
MYVOICE_MATCHER = re.compile(r"^###voice(!photo)?###:")
MYVIDEO_MATCHER = re.compile(r"^###video(!photo)?###:")
MYVIDEONOTE_MATCHER = re.compile(r"^###video_note(!photo)?###:")

ENUM_FUNC_MAP = {
	sql.Types.TEXT.value: dispatcher.bot.send_message,
	sql.Types.BUTTON_TEXT.value: dispatcher.bot.send_message,
	sql.Types.STICKER.value: dispatcher.bot.send_sticker,
	sql.Types.DOCUMENT.value: dispatcher.bot.send_document,
	sql.Types.PHOTO.value: dispatcher.bot.send_photo,
	sql.Types.AUDIO.value: dispatcher.bot.send_audio,
	sql.Types.VOICE.value: dispatcher.bot.send_voice,
	sql.Types.VIDEO.value: dispatcher.bot.send_video,
	sql.Types.VIDEO_NOTE.value: dispatcher.bot.send_video_note
}


# Do not async
def get(bot, update, notename, show_none=True, no_format=False):
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	conn = connected(bot, update, chat, user.id, need_admin=False)
	if conn:
		chat_id = conn
		send_id = user.id
	else:
		chat_id = update.effective_chat.id
		send_id = chat_id

	note = sql.get_note(chat_id, notename)
	message = update.effective_message  # type: Optional[Message]

	if note:
		# If we're replying to a message, reply to that message (unless it's an error)
		if message.reply_to_message:
			reply_id = message.reply_to_message.message_id
		else:
			reply_id = message.message_id

		if note.is_reply:
			if MESSAGE_DUMP:
				try:
					bot.forward_message(chat_id=chat_id, from_chat_id=MESSAGE_DUMP, message_id=note.value)
				except BadRequest as excp:
					if excp.message == "Message to forward not found":
						send_message(update.effective_message, tl(update.effective_message, "Pesan ini tampaknya telah hilang - saya akan menghapusnya "
										   "dari daftar catatan Anda."))
						sql.rm_note(chat_id, notename)
					else:
						raise
			else:
				try:
					bot.forward_message(chat_id=chat_id, from_chat_id=chat_id, message_id=note.value)
				except BadRequest as excp:
					if excp.message == "Message to forward not found":
						send_message(update.effective_message, tl(update.effective_message, "Sepertinya pengirim asli dari catatan ini telah dihapus "
										   "pesan mereka - maaf! Dapatkan admin bot Anda untuk mulai menggunakan "
										   "pesan dump untuk menghindari ini. Saya akan menghapus catatan ini dari "
										   "catatan tersimpan Anda."))
						sql.rm_note(chat_id, notename)
					else:
						raise
		else:
			text = note.value
			keyb = []
			parseMode = ParseMode.MARKDOWN
			buttons = sql.get_buttons(chat_id, notename)
			if no_format:
				parseMode = None
				text += revert_buttons(buttons)
			else:
				keyb = build_keyboard(buttons)

			keyboard = InlineKeyboardMarkup(keyb)

			try:
				is_private, is_delete = sql.get_private_note(chat.id)
				if note.msgtype in (sql.Types.BUTTON_TEXT, sql.Types.TEXT):
					try:
						if is_delete:
							update.effective_message.delete()
						if is_private:
							bot.send_message(user.id, text,
										 parse_mode=parseMode, disable_web_page_preview=True,
										 reply_markup=keyboard)
						else:
							bot.send_message(send_id, text, reply_to_message_id=reply_id,
										 parse_mode=parseMode, disable_web_page_preview=True,
										 reply_markup=keyboard)
					except BadRequest as excp:
						if excp.message == "Wrong http url":
							failtext = tl(update.effective_message, "Kesalahan: URL pada tombol tidak valid! Harap perbaruhi catatan ini.")
							failtext += "\n\n```\n{}```".format(note.value + revert_buttons(buttons))
							send_message(update.effective_message, failtext, parse_mode="markdown")
						elif excp.message == "Button_url_invalid":
							failtext = tl(update.effective_message, "Kesalahan: URL pada tombol tidak valid! Harap perbaruhi catatan ini.")
							failtext += "\n\n```\n{}```".format(note.value + revert_buttons(buttons))
							send_message(update.effective_message, failtext, parse_mode="markdown")
						elif excp.message == "Message can't be deleted":
							pass
						elif excp.message == "Have no rights to send a message":
							pass
					except Unauthorized as excp:
						send_message(update.effective_message, tl(update.effective_message, "Hubungi saya di PM dulu untuk mendapatkan catatan ini."), parse_mode="markdown")
						pass
				else:
					try:
						if is_delete:
							update.effective_message.delete()
						if is_private:
							ENUM_FUNC_MAP[note.msgtype](user.id, note.file, caption=text, parse_mode=parseMode, disable_web_page_preview=True, reply_markup=keyboard)
						else:
							ENUM_FUNC_MAP[note.msgtype](send_id, note.file, caption=text, reply_to_message_id=reply_id, parse_mode=parseMode, disable_web_page_preview=True, reply_markup=keyboard)
					except BadRequest as excp:
						if excp.message == "Message can't be deleted":
							pass
						elif excp.message == "Have no rights to send a message":
							pass
					except Unauthorized as excp:
						send_message(update.effective_message, tl(update.effective_message, "Hubungi saya di PM dulu untuk mendapatkan catatan ini."), parse_mode="markdown")
						pass
					
			except BadRequest as excp:
				if excp.message == "Entity_mention_user_invalid":
					send_message(update.effective_message, tl(update.effective_message, "Sepertinya Anda mencoba menyebutkan seseorang yang belum pernah saya lihat sebelumnya. "
									   "Jika kamu benar-benar ingin menyebutkannya, meneruskan salah satu pesan mereka kepada saya, "
									   "dan saya akan dapat untuk menandai mereka!"))
				elif FILE_MATCHER.match(note.value):
					send_message(update.effective_message, tl(update.effective_message, "Catatan ini adalah file yang salah diimpor dari bot lain - saya tidak bisa menggunakan "
									   "ini. Jika Anda benar-benar membutuhkannya, Anda harus menyimpannya lagi. "
									   "Sementara itu, saya akan menghapusnya dari daftar catatan Anda."))
					sql.rm_note(chat_id, notename)
				else:
					send_message(update.effective_message, tl(update.effective_message, "Catatan ini tidak dapat dikirim karena formatnya salah."))
					LOGGER.exception("Tidak dapat menguraikan pesan #%s di obrolan %s", notename, str(chat_id))
					LOGGER.warning("Pesan itu: %s", str(note.value))
		return
	elif show_none:
		send_message(update.effective_message, tl(update.effective_message, "Catatan ini tidak ada"))


@run_async
def cmd_get(bot: Bot, update: Update, args: List[str]):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return
	if len(args) >= 2 and args[1].lower() == "noformat":
		get(bot, update, args[0], show_none=True, no_format=True)
	elif len(args) >= 1:
		get(bot, update, args[0], show_none=True)
	else:
		send_message(update.effective_message, tl(update.effective_message, "Get apa?"))


@run_async
def hash_get(bot: Bot, update: Update):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return
	message = update.effective_message.text
	fst_word = message.split()[0]
	no_hash = fst_word[1:]
	get(bot, update, no_hash, show_none=False)


# TODO: FIX THIS
@run_async
@user_admin
def save(bot: Bot, update: Update):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	conn = connected(bot, update, chat, user.id)
	if conn:
		chat_id = conn
		chat_name = dispatcher.bot.getChat(conn).title
	else:
		chat_id = update.effective_chat.id
		if chat.type == "private":
			chat_name = "catatan lokal"
		else:
			chat_name = chat.title

	msg = update.effective_message  # type: Optional[Message]

	checktext = msg.text.split()
	if msg.reply_to_message:
		if len(checktext) <= 1:
			send_message(update.effective_message, tl(update.effective_message, "Anda harus memberi nama untuk catatan ini!"))
			return
	else:
		if len(checktext) <= 2:
			send_message(update.effective_message, tl(update.effective_message, "Anda harus memberi nama untuk catatan ini!"))
			return

	note_name, text, data_type, content, buttons = get_note_type(msg)

	if data_type is None:
		send_message(update.effective_message, tl(update.effective_message, "Tidak ada catatan!"))
		return

	if len(text.strip()) == 0:
		text = "`" + note_name + "`"
		
	sql.add_note_to_db(chat_id, note_name, text, data_type, buttons=buttons, file=content)
	if conn:
		savedtext = tl(update.effective_message, "Ok, catatan `{note_name}` disimpan di *{chat_name}*.").format(note_name=note_name, chat_name=chat_name)
	else:
		savedtext = tl(update.effective_message, "Ok, catatan `{note_name}` disimpan.").format(note_name=note_name)
	try:
		send_message(update.effective_message, savedtext, parse_mode=ParseMode.MARKDOWN)
	except BadRequest:
		if conn:
			savedtext = tl(update.effective_message, "Ok, catatan <code>{note_name}</code> disimpan di <b>{chat_name}</b>.").format(note_name=note_name, chat_name=chat_name)
		else:
			savedtext = tl(update.effective_message, "Ok, catatan <code>{note_name}</code> disimpan.").format(note_name=note_name)
		send_message(update.effective_message, savedtext, parse_mode=ParseMode.HTML)

	#if msg.reply_to_message and msg.reply_to_message.from_user.is_bot:
	#    if text:
	#        send_message(update.effective_message, "Sepertinya Anda mencoba menyimpan pesan dari bot. Sayangnya, "
	#                       "bot tidak dapat meneruskan pesan bot, jadi saya tidak dapat menyimpan pesan yang tepat. "
	#                       "\nSaya akan menyimpan semua teks yang saya bisa, tetapi jika Anda menginginkan lebih banyak, "
	#                       "Anda harus melakukannya meneruskan pesan sendiri, lalu simpan.")
	#    else:
	#        send_message(update.effective_message, "Bot agak cacat oleh telegram, sehingga sulit untuk berinteraksi dengan "
	#                       "bot lain, jadi saya tidak dapat menyimpan pesan ini. "
	#                       "Apakah Anda keberatan meneruskannya dan "
	#                       "lalu menyimpan pesan baru itu? Terima kasih! ☺️")
	#    return


@run_async
@user_admin
def clear(bot: Bot, update: Update, args: List[str]):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	conn = connected(bot, update, chat, user.id)
	if conn:
		chat_id = conn
		chat_name = dispatcher.bot.getChat(conn).title
	else:
		chat_id = update.effective_chat.id
		if chat.type == "private":
			chat_name = "local notes"
		else:
			chat_name = chat.title

	if len(args) >= 1:
		catatan = []
		catatangagal = []
		for x in range(len(args)):
			notename = args[x]
			if sql.rm_note(chat_id, notename):
				catatan.append(notename)
			else:
				catatangagal.append(notename)
		if len(catatan) >= 1 and len(catatangagal) == 0:
			if conn:
				rtext = tl(update.effective_message, "Catatan di *{chat_name}* untuk `{note_name}` dihapus 😁").format(chat_name=chat_name, note_name=", ".join(catatan))
			else:
				rtext = tl(update.effective_message, "Catatan `{note_name}` dihapus 😁").format(note_name=", ".join(catatan))
			try:
				send_message(update.effective_message, rtext, parse_mode=ParseMode.MARKDOWN)
			except BadRequest:
				if conn:
					rtext = tl(update.effective_message, "Catatan di <b>{chat_name}</b> untuk <code>{note_name}</code> dihapus 😁").format(chat_name=chat_name, note_name=", ".join(catatan))
				else:
					rtext = tl(update.effective_message, "Catatan <code>{note_name}</code> dihapus 😁").format(note_name=", ".join(catatan))
				send_message(update.effective_message, rtext, parse_mode=ParseMode.HTML)
		elif len(catatangagal) >= 0 and len(catatan) == 0:
			if conn:
				rtext = tl(update.effective_message, "Catatan di *{chat_name}* untuk `{fnote_name}` gagal dihapus!").format(chat_name=chat_name, fnote_name=", ".join(catatangagal))
			else:
				rtext = tl(update.effective_message, "Catatan `{fnote_name}` gagal dihapus!").format(fnote_name=", ".join(catatangagal))
			try:
				send_message(update.effective_message, rtext, parse_mode=ParseMode.MARKDOWN)
			except BadRequest:
				if conn:
					rtext = tl(update.effective_message, "Catatan di <b>{chat_name}</b> untuk <code>{fnote_name}</code> gagal dihapus!").format(chat_name=chat_name, fnote_name=", ".join(catatangagal))
				else:
					rtext = tl(update.effective_message, "Catatan <code>{fnote_name}</code> gagal dihapus!").format(fnote_name=", ".join(catatangagal))
				send_message(update.effective_message, tl(update.effective_message, rtext), parse_mode=ParseMode.HTML)
		else:
			if conn:
				rtext = tl(update.effective_message, "Catatan di *{chat_name}* untuk `{note_name}` dihapus 😁\nCatatan `{fnote_name}` gagal dihapus!").format(chat_name=chat_name, note_name=", ".join(catatan), fnote_name=", ".join(catatangagal))
			else:
				rtext = tl(update.effective_message, "Catatan `{note_name}` dihapus 😁\nCatatan `{fnote_name}` gagal dihapus!").format(note_name=", ".join(catatan), fnote_name=", ".join(catatangagal))
			try:
				send_message(update.effective_message, rtext, parse_mode=ParseMode.MARKDOWN)
			except BadRequest:
				if conn:
					rtext = tl(update.effective_message, "Catatan di <b>{chat_name}</b> untuk <code>{note_name}</code> dihapus 😁\nCatatan <code>{fnote_name}</code> gagal dihapus!").format(chat_name=chat_name, note_name=", ".join(catatan), fnote_name=", ".join(catatangagal))
				else:
					rtext = tl(update.effective_message, "Catatan <code>{note_name}</code> dihapus 😁\nCatatan <code>{fnote_name}</code> gagal dihapus!").format(note_name=", ".join(catatan), fnote_name=", ".join(catatangagal))
				send_message(update.effective_message, tl(update.effective_message, rtext), parse_mode=ParseMode.HTML)

	else:
		send_message(update.effective_message, tl(update.effective_message, "Apa yang ingin dihapus?"))

@run_async
@user_admin
def private_note(bot: Bot, update: Update, args: List[str]):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	conn = connected(bot, update, chat, user.id)
	if conn:
		chat_id = conn
		chat_name = dispatcher.bot.getChat(conn).title
	else:
		chat_id = update.effective_chat.id
		if chat.type == "private":
			chat_name = chat.title
		else:
			chat_name = chat.title

	if len(args) >= 1:
		if args[0] in ("yes", "on", "ya"):
			if len(args) >= 2:
				if args[1] == "del":
					sql.private_note(str(chat_id), True, True)
					send_message(update.effective_message, tl(update.effective_message, "Private Note di *aktifkan*, ketika pengguna mengambil catatan, pesan catatan akan dikirim ke PM dan pesan pengguna akan segera di hapus."), parse_mode="markdown")
				else:
					sql.private_note(str(chat_id), True, False)
					send_message(update.effective_message, tl(update.effective_message, "Private Note di *aktifkan*, ketika pengguna mengambil catatan, pesan catatan akan dikirim ke PM."), parse_mode="markdown")
			else:
				sql.private_note(str(chat_id), True, False)
				send_message(update.effective_message, tl(update.effective_message, "Private Note di *aktifkan*, ketika pengguna mengambil catatan, pesan catatan akan dikirim ke PM."), parse_mode="markdown")
		elif args[0] in ("no", "off"):
			sql.private_note(str(chat_id), False, False)
			send_message(update.effective_message, tl(update.effective_message, "Private Note di *non-aktifkan*, pesan catatan akan di kirim di grup."), parse_mode="markdown")
		else:
			send_message(update.effective_message, tl(update.effective_message, "Argumen tidak dikenal - harap gunakan 'yes', atau 'no'."))
	else:
		is_private, is_delete = sql.get_private_note(chat_id)
		print(is_private, is_delete)
		send_message(update.effective_message, tl(update.effective_message, "Pengaturan Private Note di {}: *{}*{}").format(chat_name, "Enabled" if is_private else "Disabled", " - *Hash will be deleted*" if is_delete else ""), parse_mode="markdown")


@run_async
def list_notes(bot: Bot, update: Update):
	spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
	if spam == True:
		return
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	conn = connected(bot, update, chat, user.id, need_admin=False)
	if conn:
		chat_id = conn
		chat_name = dispatcher.bot.getChat(conn).title
		msg = tl(update.effective_message, "*Catatan di {}:*\n").format(chat_name)
	else:
		chat_id = update.effective_chat.id
		if chat.type == "private":
			chat_name = ""
			msg = tl(update.effective_message, "*Catatan lokal:*\n")
		else:
			chat_name = chat.title
			msg = tl(update.effective_message, "*Catatan di {}:*\n").format(chat_name)

	note_list = sql.get_all_chat_notes(chat_id)

	for note in note_list:
		note_name = " - `{}`\n".format(note.name)
		if len(msg) + len(note_name) > MAX_MESSAGE_LENGTH:
			send_message(update.effective_message, msg, parse_mode=ParseMode.MARKDOWN)
			msg = ""
		msg += note_name

	if msg == tl(update.effective_message, "*Catatan di {}:*\n").format(chat_name) or msg == tl(update.effective_message, "*Catatan lokal:*\n"):
		if conn:
			send_message(update.effective_message, tl(update.effective_message, "Tidak ada catatan di obrolan *{}*!").format(chat_name), parse_mode="markdown")
		else:
			send_message(update.effective_message, tl(update.effective_message, "Tidak ada catatan di obrolan ini!"))

	elif len(msg) != 0:
		msg += tl(update.effective_message, "\nAnda dapat mengambil catatan ini dengan menggunakan `/get notename`, atau `#notename`")
		try:
			send_message(update.effective_message, msg, parse_mode=ParseMode.MARKDOWN)
		except BadRequest:
			if chat.type == "private":
				chat_name = ""
				msg = tl(update.effective_message, "<b>Catatan lokal:</b>\n")
			else:
				chat_name = chat.title
				msg = tl(update.effective_message, "<b>Catatan di {}:</b>\n").format(chat_name)
			for note in note_list:
				note_name = " - <code>{}</code>\n".format(note.name)
				if len(msg) + len(note_name) > MAX_MESSAGE_LENGTH:
					send_message(update.effective_message, msg, parse_mode=ParseMode.MARKDOWN)
					msg = ""
				msg += note_name
			msg += tl(update.effective_message, "\nAnda dapat mengambil catatan ini dengan menggunakan <code>/get notename</code>, atau <code>#notename</code>")
			send_message(update.effective_message, msg, parse_mode=ParseMode.HTML)


def __import_data__(chat_id, data):
	failures = []
	for notename, notedata in data.get('extra', {}).items():
		match = FILE_MATCHER.match(notedata)
		matchsticker = STICKER_MATCHER.match(notedata)
		matchbtn = BUTTON_MATCHER.match(notedata)
		matchfile = MYFILE_MATCHER.match(notedata)
		matchphoto = MYPHOTO_MATCHER.match(notedata)
		matchaudio = MYAUDIO_MATCHER.match(notedata)
		matchvoice = MYVOICE_MATCHER.match(notedata)
		matchvideo = MYVIDEO_MATCHER.match(notedata)
		matchvn = MYVIDEONOTE_MATCHER.match(notedata)

		if match:
			failures.append(notename)
			notedata = notedata[match.end():].strip()
			if notedata:
				sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.TEXT)
		elif matchsticker:
			content = notedata[matchsticker.end():].strip()
			if content:
				sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.STICKER, file=content)
		elif matchbtn:
			parse = notedata[matchbtn.end():].strip()
			notedata = parse.split("<###button###>")[0]
			buttons = parse.split("<###button###>")[1]
			buttons = ast.literal_eval(buttons)
			if buttons:
				sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.BUTTON_TEXT, buttons=buttons)
		elif matchfile:
			file = notedata[matchfile.end():].strip()
			file = file.split("<###TYPESPLIT###>")
			notedata = file[1]
			content = file[0]
			if content:
				sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.DOCUMENT, file=content)
		elif matchphoto:
			photo = notedata[matchphoto.end():].strip()
			photo = photo.split("<###TYPESPLIT###>")
			notedata = photo[1]
			content = photo[0]
			if content:
				sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.PHOTO, file=content)
		elif matchaudio:
			audio = notedata[matchaudio.end():].strip()
			audio = audio.split("<###TYPESPLIT###>")
			notedata = audio[1]
			content = audio[0]
			if content:
				sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.AUDIO, file=content)
		elif matchvoice:
			voice = notedata[matchvoice.end():].strip()
			voice = voice.split("<###TYPESPLIT###>")
			notedata = voice[1]
			content = voice[0]
			if content:
				sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.VOICE, file=content)
		elif matchvideo:
			video = notedata[matchvideo.end():].strip()
			video = video.split("<###TYPESPLIT###>")
			notedata = video[1]
			content = video[0]
			if content:
				sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.VIDEO, file=content)
		elif matchvn:
			video_note = notedata[matchvn.end():].strip()
			video_note = video_note.split("<###TYPESPLIT###>")
			notedata = video_note[1]
			content = video_note[0]
			if content:
				sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.VIDEO_NOTE, file=content)
		else:
			sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.TEXT)

	if failures:
		with BytesIO(str.encode("\n".join(failures))) as output:
			output.name = "failed_imports.txt"
			dispatcher.bot.send_document(chat_id, document=output, filename="failed_imports.txt",
										 caption=tl(update.effective_message, "File/foto ini gagal diimpor karena berasal "
												 "dari bot lain. Ini adalah pembatasan API telegram, dan tidak bisa "
												 "dihindari. Maaf untuk ketidaknyamanannya!"))


def __stats__():
	return tl(OWNER_ID, "{} catatan, pada {} obrolan.").format(sql.num_notes(), sql.num_chats())


def __migrate__(old_chat_id, new_chat_id):
	sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
	notes = sql.get_all_chat_notes(chat_id)
	return tl(user_id, "Ada catatan `{}` dalam obrolan ini.").format(len(notes))


__help__ = "notes_help"

__mod_name__ = "Notes"

GET_HANDLER = CommandHandler("get", cmd_get, pass_args=True)
HASH_GET_HANDLER = RegexHandler(r"^#[^\s]+", hash_get)

SAVE_HANDLER = CommandHandler("save", save)
DELETE_HANDLER = CommandHandler("clear", clear, pass_args=True)

PMNOTE_HANDLER = CommandHandler("privatenote", private_note, pass_args=True)

LIST_HANDLER = DisableAbleCommandHandler(["notes", "saved"], list_notes, admin_ok=True)

dispatcher.add_handler(GET_HANDLER)
dispatcher.add_handler(SAVE_HANDLER)
dispatcher.add_handler(LIST_HANDLER)
dispatcher.add_handler(DELETE_HANDLER)
dispatcher.add_handler(PMNOTE_HANDLER)
dispatcher.add_handler(HASH_GET_HANDLER)
