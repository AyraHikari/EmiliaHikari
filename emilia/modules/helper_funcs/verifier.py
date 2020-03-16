import random
import re

from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, ChatPermissions
from telegram.ext import CallbackQueryHandler
from telegram.error import BadRequest

from emilia import dispatcher
import emilia.modules.sql.welcome_sql as sql
from emilia.modules.languages import tl

from emilia.modules.helper_funcs.alternate import send_message


verify_code = ["🙏", "👈", "👉", "👇", "👆", "❤️", "🅰️", "🅱️", "0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
verify_code_images = {
"🙏": "https://telegra.ph/file/785aba452f52876c71782.jpg", 
"👈": "https://telegra.ph/file/521ca6dacb63b1e1762a1.jpg",
"👉": "https://telegra.ph/file/3ff7a4c25abd3227e4a4c.jpg",
"👇": "https://telegra.ph/file/5ec6e0de9c518eefa0892.jpg",
"👆": "https://telegra.ph/file/8011dfd625f4fb83c45dd.jpg",
"❤️": "https://telegra.ph/file/70ab2793d0ebcb6e32242.jpg",
"🅰️": "https://telegra.ph/file/09db669a8d477f4b999d9.jpg",
"🅱️": "https://telegra.ph/file/377919cb050cbfc17bcdf.jpg",
"0️⃣": "https://telegra.ph/file/47fe59efcf35b9cedcdff.jpg",
"1️⃣": "https://telegra.ph/file/eb56b61a801e4956ebe74.jpg",
"2️⃣": "https://telegra.ph/file/aed9b6f2074abee5cdf93.jpg",
"3️⃣": "https://telegra.ph/file/bc5fa0f129a6e21fe55ce.jpg",
"4️⃣": "https://telegra.ph/file/ec9f513014afa7946f1b0.jpg",
"5️⃣": "https://telegra.ph/file/8ac42b877524b0d30c5a3.jpg",
"6️⃣": "https://telegra.ph/file/1d69ec6b5dd8e827979d5.jpg",
"7️⃣": "https://telegra.ph/file/b0fc2d10db9c7acedfe2a.jpg",
"8️⃣": "https://telegra.ph/file/557644891a14b7e7ac72f.jpg",
"9️⃣": "https://telegra.ph/file/148a5c2ff8d1ca354dca7.jpg",
"🔟": "https://telegra.ph/file/67175a896d5769617a3e3.jpg"}


def verify_welcome(update, context, chat_id):
	user_id = update.effective_user.id
	is_clicked = sql.get_chat_userlist(chat_id)
	if user_id not in list(is_clicked):
		send_message(update.effective_message, tl(update.effective_message, "Anda sedang tidak dalam mode verifikasi, jika anda sedang di bisukan, anda dapat meminta tolong pada admin di grup yang bersangkutan"))
		return
	elif user_id in list(is_clicked) and is_clicked[user_id] == True:
		send_message(update.effective_message, tl(update.effective_message, "Anda sedang tidak dalam mode verifikasi, jika anda sedang di bisukan, anda dapat meminta tolong pada admin di grup yang bersangkutan"))
		return
	verify_code = ["🙏", "👈", "👉", "👇", "👆", "❤️", "🅰️", "🅱️", "0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
	print(len(verify_code))
	real_btn = random.choice(verify_code)
	verify_code.remove(real_btn)
	verbox = (random.randint(1, 3), random.randint(1, 3))
	buttons = []
	linebox = []
	for x in range(3):
		x += 1
		if verbox[1] == x:
			ver1 = True
		else:
			ver1 = False
		for y in range(3):
			y += 1
			if verbox[0] == y and ver1:
				verify_emoji = real_btn
				linebox.append(InlineKeyboardButton(text=verify_emoji, callback_data="verify_me(y|{}|{})".format(user_id, chat_id)))
			else:
				verify_emoji = random.choice(verify_code)
				linebox.append(InlineKeyboardButton(text=verify_emoji, callback_data="verify_me(n|{}|{})".format(user_id, chat_id)))
				verify_code.remove(verify_emoji)
		buttons.append(linebox)
		linebox = []
	context.bot.send_photo(user_id, photo=verify_code_images[real_btn], caption=tl(update.effective_message, "Tolong pilih emoji yang sama dibawah ini:"), parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))

def verify_button_pressed(update, context):
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	query = update.callback_query  # type: Optional[CallbackQuery]
	match = re.match(r"verify_me\((.+?)\)", query.data)
	match = match.group(1).split("|")
	is_ok = match[0]
	user_id = match[1]
	chat_id = match[2]
	message = update.effective_message  # type: Optional[Message]
	print("-> {} was clicked welcome verify button".format(user.id))
	if is_ok == "y":
		if context.bot.getChatMember(chat_id, user_id).status in ('left'):
			query.answer(text=tl(update.effective_message, "Failed: user left chat"))
			return
		try:
			context.bot.restrict_chat_member(chat_id, user_id, permissions=ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
			sql.add_to_userlist(chat_id, user_id, True)
			sql.rm_from_timeout(chat_id, user_id)
		except BadRequest as err:
			if not update.effective_chat.get_member(context.bot.id).can_restrict_members:
				query.answer(text=tl(update.effective_message, "Saya tidak dapat membatasi orang disini, tanya admin untuk unmute!"))
			else:
				query.answer(text="Error: " + str(err))
			return
		chat_name = context.bot.get_chat(chat_id).title
		context.bot.edit_message_media(chat.id, message_id=query.message.message_id, media=InputMediaPhoto(media="https://telegra.ph/file/06d2c5ec80af3858c2d4b.jpg", caption=tl(update.effective_message, "*Berhasil!*\n\nKerja bagus manusia, kini Anda dapat chatting di: *{}*").format(chat_name), parse_mode="markdown"))
		query.answer(text=tl(update.effective_message, "Berhasil! Anda dapat chatting di {} sekarang").format(chat_name), show_alert=True)
	else:
		context.bot.edit_message_media(chat.id, message_id=query.message.message_id, media=InputMediaPhoto(media="https://telegra.ph/file/d81cdcbafb240071add84.jpg", caption=tl(update.effective_message, "Maaf robot, kamu telah salah klik tombol verifikasi.\n\nCoba lagi dengan klik tombol verifikasi pada pesan selamat datang."), parse_mode="markdown"))
		query.answer(text=tl(update.effective_message, "Gagal! Kamu telah salah mengklik tombol verifikasi"), show_alert=True)


verify_callback_handler = CallbackQueryHandler(verify_button_pressed, pattern=r"verify_me")

dispatcher.add_handler(verify_callback_handler)
