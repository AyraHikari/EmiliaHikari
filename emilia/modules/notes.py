import re, ast
from io import BytesIO
from typing import Optional, List

from telegram import MAX_MESSAGE_LENGTH, ParseMode, InlineKeyboardMarkup
from telegram import Message, Update, Bot
from telegram.error import BadRequest
from telegram.ext import CommandHandler, RegexHandler
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import escape_markdown

import emilia.modules.sql.notes_sql as sql
from emilia import dispatcher, MESSAGE_DUMP, LOGGER, spamfilters
from emilia.modules.disable import DisableAbleCommandHandler
from emilia.modules.helper_funcs.chat_status import user_admin
from emilia.modules.helper_funcs.misc import build_keyboard, revert_buttons
from emilia.modules.helper_funcs.msg_types import get_note_type

from emilia.modules.connection import connected

FILE_MATCHER = re.compile(r"^###file_id(!photo)?###:(.*?)(?:\s|$)")
STICKER_MATCHER = re.compile(r"^###sticker(!photo)?###:")
BUTTON_MATCHER = re.compile(r"^###button(!photo)?###:(.*?)(?:\s|$)")
MYFILE_MATCHER = re.compile(r"^###file(!photo)?###:")
MYPHOTO_MATCHER = re.compile(r"^###photo(!photo)?###:")
MYAUDIO_MATCHER = re.compile(r"^###audio(!photo)?###:")
MYVOICE_MATCHER = re.compile(r"^###voice(!photo)?###:")
MYVIDEO_MATCHER = re.compile(r"^###video(!photo)?###:")

ENUM_FUNC_MAP = {
    sql.Types.TEXT.value: dispatcher.bot.send_message,
    sql.Types.BUTTON_TEXT.value: dispatcher.bot.send_message,
    sql.Types.STICKER.value: dispatcher.bot.send_sticker,
    sql.Types.DOCUMENT.value: dispatcher.bot.send_document,
    sql.Types.PHOTO.value: dispatcher.bot.send_photo,
    sql.Types.AUDIO.value: dispatcher.bot.send_audio,
    sql.Types.VOICE.value: dispatcher.bot.send_voice,
    sql.Types.VIDEO.value: dispatcher.bot.send_video
}


# Do not async
def get(bot, update, notename, show_none=True, no_format=False):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    conn = connected(bot, update, chat, user.id, need_admin=False)
    if not conn == False:
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
                        message.reply_text("Pesan ini tampaknya telah hilang - saya akan menghapusnya "
                                           "dari daftar catatan Anda.")
                        sql.rm_note(chat_id, notename)
                    else:
                        raise
            else:
                try:
                    bot.forward_message(chat_id=chat_id, from_chat_id=chat_id, message_id=note.value)
                except BadRequest as excp:
                    if excp.message == "Message to forward not found":
                        message.reply_text("Sepertinya pengirim asli dari catatan ini telah dihapus "
                                           "pesan mereka - maaf! Dapatkan admin bot Anda untuk mulai menggunakan "
                                           "pesan dump untuk menghindari ini. Saya akan menghapus catatan ini dari "
                                           "catatan tersimpan Anda.")
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
                if note.msgtype in (sql.Types.BUTTON_TEXT, sql.Types.TEXT):
                    try:
                        bot.send_message(send_id, text, reply_to_message_id=reply_id,
                                         parse_mode=parseMode, disable_web_page_preview=True,
                                         reply_markup=keyboard)
                    except BadRequest as excp:
                        if excp.message == "Wrong http url":
                            failtext = "Kesalahan: URL pada tombol tidak valid! Harap perbaruhi catatan ini."
                            failtext += "\n\n```\n{}```".format(note.value + revert_buttons(buttons))
                            message.reply_text(failtext, parse_mode="markdown")
                        print("Gagal mengirim catatan: " + excp.message)
                        pass
                else:
                    ENUM_FUNC_MAP[note.msgtype](send_id, note.file, caption=text, reply_to_message_id=reply_id,
                                                parse_mode=parseMode, disable_web_page_preview=True,
                                                reply_markup=keyboard)
                    
            except BadRequest as excp:
                if excp.message == "Entity_mention_user_invalid":
                    message.reply_text("Sepertinya Anda mencoba menyebutkan seseorang yang belum pernah saya lihat sebelumnya. "
                                       "Jika kamu benar-benar ingin menyebutkannya, meneruskan salah satu pesan mereka kepada saya, "
                                       "dan saya akan dapat untuk menandai mereka!")
                elif FILE_MATCHER.match(note.value):
                    message.reply_text("Catatan ini adalah file yang salah diimpor dari bot lain - saya tidak bisa menggunakan "
                                       "ini. Jika Anda benar-benar membutuhkannya, Anda harus menyimpannya lagi. "
                                       "Sementara itu, saya akan menghapusnya dari daftar catatan Anda.")
                    sql.rm_note(chat_id, notename)
                else:
                    message.reply_text("Catatan ini tidak dapat dikirim karena formatnya salah.")
                    LOGGER.exception("Tidak dapat menguraikan pesan #%s di obrolan %s", notename, str(chat_id))
                    LOGGER.warning("Pesan itu: %s", str(note.value))
        return
    elif show_none:
        message.reply_text("Catatan ini tidak ada")


@run_async
def cmd_get(bot: Bot, update: Update, args: List[str]):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    if len(args) >= 2 and args[1].lower() == "noformat":
        get(bot, update, args[0], show_none=True, no_format=True)
    elif len(args) >= 1:
        get(bot, update, args[0], show_none=True)
    else:
        update.effective_message.reply_text("Get apa?")


@run_async
def hash_get(bot: Bot, update: Update):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    message = update.effective_message.text
    fst_word = message.split()[0]
    no_hash = fst_word[1:]
    get(bot, update, no_hash, show_none=False)


# TODO: FIX THIS
@run_async
@user_admin
def save(bot: Bot, update: Update):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    conn = connected(bot, update, chat, user.id)
    if not conn == False:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        chat_id = update.effective_chat.id
        if chat.type == "private":
            chat_name = "catatan lokal"
        else:
            chat_name = chat.title

    msg = update.effective_message  # type: Optional[Message]

    note_name, text, data_type, content, buttons = get_note_type(msg)

    if data_type is None:
        msg.reply_text("Tidak ada catatan!")
        return
    
    if len(text.strip()) == 0:
        text = note_name
        
    sql.add_note_to_db(chat_id, note_name, text, data_type, buttons=buttons, file=content)
    msg.reply_text("Ok, `{note_name}` ditambahkan di *{chat_name}*.\ndapatkan dengan `/get {note_name}`, atau `#{note_name}`".format(note_name=note_name, chat_name=chat_name), parse_mode=ParseMode.MARKDOWN)

    #if msg.reply_to_message and msg.reply_to_message.from_user.is_bot:
    #    if text:
    #        msg.reply_text("Sepertinya Anda mencoba menyimpan pesan dari bot. Sayangnya, "
    #                       "bot tidak dapat meneruskan pesan bot, jadi saya tidak dapat menyimpan pesan yang tepat. "
    #                       "\nSaya akan menyimpan semua teks yang saya bisa, tetapi jika Anda menginginkan lebih banyak, "
    #                       "Anda harus melakukannya meneruskan pesan sendiri, lalu simpan.")
    #    else:
    #        msg.reply_text("Bot agak cacat oleh telegram, sehingga sulit untuk berinteraksi dengan "
    #                       "bot lain, jadi saya tidak dapat menyimpan pesan ini. "
    #                       "Apakah Anda keberatan meneruskannya dan "
    #                       "lalu menyimpan pesan baru itu? Terima kasih! ☺️")
    #    return


@run_async
@user_admin
def clear(bot: Bot, update: Update, args: List[str]):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    conn = connected(bot, update, chat, user.id)
    if not conn == False:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        chat_id = update.effective_chat.id
        if chat.type == "private":
            chat_name = "local notes"
        else:
            chat_name = chat.title

    if len(args) >= 1:
        catatan = ""
        catatangagal = ""
        for x in range(len(args)):
            notename = args[x]
            if sql.rm_note(chat_id, notename):
                catatan += "{}, ".format(notename)
            else:
                catatangagal += "{}, ".format(notename)
        if catatan != "" and catatangagal == "":
            update.effective_message.reply_text("Catatan di *{}* untuk {}berhasil dihapus 😁".format(chat_name, catatan), parse_mode=ParseMode.MARKDOWN)
        elif catatangagal != "" and catatan == "":
            update.effective_message.reply_text("Catatan di *{}* untuk {}gagal dihapus!".format(chat_name, catatangagal), parse_mode=ParseMode.MARKDOWN)
        else:
            update.effective_message.reply_text("Catatan di *{}* untuk {}berhasil dihapus 😁\nCatatan {}gagal dihapus!".format(chat_name, catatan, catatangagal), parse_mode=ParseMode.MARKDOWN)

@run_async
def list_notes(bot: Bot, update: Update):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    conn = connected(bot, update, chat, user.id, need_admin=False)
    if not conn == False:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
        msg = "*Catatan di {}:*\n".format(chat_name)
    else:
        chat_id = update.effective_chat.id
        if chat.type == "private":
            chat_name = ""
            msg = "*Catatan lokal:*\n"
        else:
            chat_name = chat.title
            msg = "*Catatan di {}:*\n".format(chat_name)

    note_list = sql.get_all_chat_notes(chat_id)

    for note in note_list:
        note_name = " - `{}`\n".format(note.name)
        if len(msg) + len(note_name) > MAX_MESSAGE_LENGTH:
            update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
            msg = ""
        msg += note_name

    if msg == "*Catatan di {}:*\n".format(chat_name) or msg == "*Catatan Lokal:*\n":
        update.effective_message.reply_text("Tidak ada catatan di obrolan ini!")

    elif len(msg) != 0:
        msg += "\nAnda dapat mengambil catatan ini dengan menggunakan `/get notename`, atau `#notename`"
        update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


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
        else:
            sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.TEXT)

    if failures:
        with BytesIO(str.encode("\n".join(failures))) as output:
            output.name = "failed_imports.txt"
            dispatcher.bot.send_document(chat_id, document=output, filename="failed_imports.txt",
                                         caption="File/foto ini gagal diimpor karena berasal "
                                                 "dari bot lain. Ini adalah pembatasan API telegram, dan tidak bisa "
                                                 "dihindari. Maaf untuk ketidaknyamanannya!")


def __stats__():
    return "{} catatan, pada {} obrolan.".format(sql.num_notes(), sql.num_chats())


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    notes = sql.get_all_chat_notes(chat_id)
    return "Ada catatan `{}` dalam obrolan ini.".format(len(notes))


__help__ = """
 - /get <notename>: dapatkan catatan dengan notename ini, gunakan ``noformat`` di akhir untuk mendapatkan note tanpa format
 - #<notename>: sama seperti /get
 - /notes atau /saved: daftar semua catatan yang disimpan dalam obrolan ini

*Hanya admin:*
 - /save <notename> <notedata>: menyimpan recordsata sebagai catatan dengan nama notename
Sebuah tombol dapat ditambahkan ke catatan dengan menggunakan sintaks markdown standar tautan - tautan harus ditambahkan dengan \
bagian `buttonurl:`, Seperti: `[tulisannya](buttonurl:contoh.com)`. Cek /markdownhelp untuk info lebih lanjut.
 - /save <notename>: simpan pesan yang dijawab sebagai catatan dengan nama nama file
 - /clear <notename>: hapus catatan dengan nama ini
"""

__mod_name__ = "Notes"

GET_HANDLER = CommandHandler("get", cmd_get, pass_args=True)
HASH_GET_HANDLER = RegexHandler(r"^#[^\s]+", hash_get)

SAVE_HANDLER = CommandHandler("save", save)
DELETE_HANDLER = CommandHandler("clear", clear, pass_args=True)

LIST_HANDLER = DisableAbleCommandHandler(["notes", "saved"], list_notes, admin_ok=True)

dispatcher.add_handler(GET_HANDLER)
dispatcher.add_handler(SAVE_HANDLER)
dispatcher.add_handler(LIST_HANDLER)
dispatcher.add_handler(DELETE_HANDLER)
dispatcher.add_handler(HASH_GET_HANDLER)
