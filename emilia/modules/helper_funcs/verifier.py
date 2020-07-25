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
"🙏": "785aba452f52876c71782.jpg", 
"👈": "521ca6dacb63b1e1762a1.jpg",
"👉": "3ff7a4c25abd3227e4a4c.jpg",
"👇": "5ec6e0de9c518eefa0892.jpg",
"👆": "8011dfd625f4fb83c45dd.jpg",
"❤️": "70ab2793d0ebcb6e32242.jpg",
"🅰️": "09db669a8d477f4b999d9.jpg",
"🅱️": "377919cb050cbfc17bcdf.jpg",
"0️⃣": "47fe59efcf35b9cedcdff.jpg",
"1️⃣": "eb56b61a801e4956ebe74.jpg",
"2️⃣": "aed9b6f2074abee5cdf93.jpg",
"3️⃣": "bc5fa0f129a6e21fe55ce.jpg",
"4️⃣": "ec9f513014afa7946f1b0.jpg",
"5️⃣": "8ac42b877524b0d30c5a3.jpg",
"6️⃣": "1d69ec6b5dd8e827979d5.jpg",
"7️⃣": "b0fc2d10db9c7acedfe2a.jpg",
"8️⃣": "557644891a14b7e7ac72f.jpg",
"9️⃣": "148a5c2ff8d1ca354dca7.jpg",
"🔟": "67175a896d5769617a3e3.jpg"}


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
	was_set = False
	for x in range(3):
		x += 1
		for y in range(3):
			y += 1
			if verbox[0] == y and verbox[1] == x:
				was_set = True
				linebox.append(InlineKeyboardButton(text=real_btn, callback_data="verify_me(y|{}|{})".format(user_id, chat_id)))
			else:
				verify_emoji = random.choice(verify_code)
				linebox.append(InlineKeyboardButton(text=verify_emoji, callback_data="verify_me(n|{}|{})".format(user_id, chat_id)))
				verify_code.remove(verify_emoji)
		buttons.append(linebox)
		linebox = []
	if not was_set:
		verbox = (random.randint(1, 3), random.randint(1, 3))
		linebox[verbox[0]-1][verbox[1]-1] = InlineKeyboardButton(text=real_btn, callback_data="verify_me(y|{}|{})".format(user_id, chat_id))
	buttons.append([InlineKeyboardButton(text="Refresh", callback_data="verify_me(re|{}|{})".format(user_id, chat_id))])
	context.bot.send_photo(user_id, photo=open("emilia/modules/helper_funcs/emojis/" + verify_code_images[real_btn], 'rb'), caption=tl(update.effective_message, "Tolong pilih emoji yang sama dibawah ini:") + "\n" + tl(update.effective_message, "Jika tidak ada emoji yang sama, harap klik tombol refresh"), parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))

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
			context.bot.restrict_chat_member(chat_id, user_id, permissions=ChatPermissions(
											can_send_messages=True,
											can_send_media_messages=True,
											can_send_polls=True,
											can_send_other_messages=True,
											can_add_web_page_previews=True,
											can_change_info=True,
											can_invite_users=True,
											can_pin_messages=True)
										)
			sql.add_to_userlist(chat_id, user_id, True)
			sql.rm_from_timeout(chat_id, user_id)
		except BadRequest as err:
			if not update.effective_chat.get_member(context.bot.id).can_restrict_members:
				query.answer(text=tl(update.effective_message, "Saya tidak dapat membatasi orang disini, tanya admin untuk unmute!"))
			else:
				query.answer(text="Error: " + str(err))
			return
		chat_name = context.bot.get_chat(chat_id).title
		# query.message.delete()
		# context.bot.send_photo(chat.id, photo="https://telegra.ph/file/06d2c5ec80af3858c2d4b.jpg", caption=tl(update.effective_message, "*Berhasil!*\n\nKerja bagus manusia, kini Anda dapat chatting di: *{}*").format(chat_name), parse_mode="markdown")
		context.bot.edit_message_media(chat.id, message_id=query.message.message_id, media=InputMediaPhoto(media=open("emilia/modules/helper_funcs/emojis/done.jpg", 'rb'), caption=tl(update.effective_message, "*Berhasil!*\n\nKerja bagus manusia, kini Anda dapat chatting di: *{}*").format(chat_name), parse_mode="markdown"))
		query.answer(text=tl(update.effective_message, "Berhasil! Anda dapat chatting di {} sekarang").format(chat_name), show_alert=True)
	elif is_ok == "re":
		user_id = update.effective_user.id
		is_clicked = sql.get_chat_userlist(chat_id)
		if user_id not in list(is_clicked):
			context.bot.edit_message_text(chat.id, message_id=query.message.message_id, text=tl(update.effective_message, "Anda sedang tidak dalam mode verifikasi, jika anda sedang di bisukan, anda dapat meminta tolong pada admin di grup yang bersangkutan"))
			return query.answer(text=tl(update.effective_message, "Error"), show_alert=False)
		elif user_id in list(is_clicked) and is_clicked[user_id] == True:
			context.bot.edit_message_text(chat.id, message_id=query.message.message_id, text=tl(update.effective_message, "Anda sedang tidak dalam mode verifikasi, jika anda sedang di bisukan, anda dapat meminta tolong pada admin di grup yang bersangkutan"))
			return query.answer(text=tl(update.effective_message, "Error"), show_alert=False)
		verify_code = ["🙏", "👈", "👉", "👇", "👆", "❤️", "🅰️", "🅱️", "0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
		real_btn = random.choice(verify_code)
		print(real_btn)
		verify_code.remove(real_btn)
		verbox = (random.randint(1, 3), random.randint(1, 3))
		buttons = []
		linebox = []
		was_set = False
		for x in range(3):
			x += 1
			for y in range(3):
				y += 1
				if verbox[0] == y and verbox[1] == x:
					was_set = True
					print("button was set to " + real_btn + "at " + str(verbox[0]) + " - " + str(verbox[1]))
					linebox.append(InlineKeyboardButton(text=real_btn, callback_data="verify_me(y|{}|{})".format(user_id, chat_id)))
				else:
					verify_emoji = random.choice(verify_code)
					linebox.append(InlineKeyboardButton(text=verify_emoji, callback_data="verify_me(n|{}|{})".format(user_id, chat_id)))
					verify_code.remove(verify_emoji)
			buttons.append(linebox)
			linebox = []
		if not was_set:
			verbox = (random.randint(1, 3), random.randint(1, 3))
			linebox[verbox[0]-1][verbox[1]-1] = InlineKeyboardButton(text=real_btn, callback_data="verify_me(y|{}|{})".format(user_id, chat_id))
			print("[x] button was set to " + real_btn + "at " + str(verbox[0]) + " - " + str(verbox[1]))
		buttons.append([InlineKeyboardButton(text="Refresh", callback_data="verify_me(re|{}|{})".format(user_id, chat_id))])
		# query.message.delete()
		# context.bot.send_photo(chat.id, photo=open("emilia/modules/helper_funcs/emojis/" + verify_code_images[real_btn], 'rb'), caption=tl(update.effective_message, "Tolong pilih emoji yang sama dibawah ini:") + "\n" + tl(update.effective_message, "Jika tidak ada emoji yang sama, harap klik tombol refresh"), parse_mode="markdown", reply_markup=InlineKeyboardMarkup(buttons))
		context.bot.edit_message_media(chat.id, message_id=query.message.message_id, media=InputMediaPhoto(media=open("emilia/modules/helper_funcs/emojis/" + verify_code_images[real_btn], 'rb'), caption=tl(update.effective_message, "Tolong pilih emoji yang sama dibawah ini:") + "\n" + tl(update.effective_message, "Jika tidak ada emoji yang sama, harap klik tombol refresh"), parse_mode="markdown"), reply_markup=InlineKeyboardMarkup(buttons))
		query.answer(text=tl(update.effective_message, "Done"), show_alert=False)
	else:
		# query.message.delete()
		# context.bot.send_photo(chat.id, photo=open("emilia/modules/helper_funcs/emojis/fail.jpg", 'rb'), caption=tl(update.effective_message, "Maaf robot, kamu telah salah klik tombol verifikasi.\n\nCoba lagi dengan klik tombol verifikasi pada pesan selamat datang."), parse_mode="markdown")
		context.bot.edit_message_media(chat.id, message_id=query.message.message_id, media=InputMediaPhoto(media=open("emilia/modules/helper_funcs/emojis/fail.jpg", 'rb'), caption=tl(update.effective_message, "Maaf robot, kamu telah salah klik tombol verifikasi.\n\nCoba lagi dengan klik tombol verifikasi pada pesan selamat datang."), parse_mode="markdown"))
		query.answer(text=tl(update.effective_message, "Gagal! Kamu telah salah mengklik tombol verifikasi"), show_alert=True)


verify_callback_handler = CallbackQueryHandler(verify_button_pressed, pattern=r"verify_me")

dispatcher.add_handler(verify_callback_handler)
