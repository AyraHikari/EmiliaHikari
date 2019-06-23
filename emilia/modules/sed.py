import re
import sre_constants
import time

import telegram
from telegram import Update, Bot
from telegram.ext import run_async

from emilia import dispatcher, LOGGER, spamfilters
from emilia.modules.disable import DisableAbleRegexHandler

DELIMITERS = ("/", ":", "|", "_")


def separate_sed(sed_string):
    if len(sed_string) >= 3 and sed_string[1] in DELIMITERS and sed_string.count(sed_string[1]) >= 2:
        delim = sed_string[1]
        start = counter = 2
        while counter < len(sed_string):
            if sed_string[counter] == "\\":
                counter += 1

            elif sed_string[counter] == delim:
                replace = sed_string[start:counter]
                counter += 1
                start = counter
                break

            counter += 1

        else:
            return None

        while counter < len(sed_string):
            if sed_string[counter] == "\\" and counter + 1 < len(sed_string) and sed_string[counter + 1] == delim:
                sed_string = sed_string[:counter] + sed_string[counter + 1:]

            elif sed_string[counter] == delim:
                replace_with = sed_string[start:counter]
                counter += 1
                break

            counter += 1
        else:
            return replace, sed_string[start:], ""

        flags = ""
        if counter < len(sed_string):
            flags = sed_string[counter:]
        return replace, replace_with, flags.lower()

def elapsed_time():
    global start_time
    return time.time() - start_time

number = 0
score = 0
start_time = time.time()
max_time = 5

@run_async
def sed(bot: Bot, update: Update):
    start = time.time()
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return
    if update.effective_message.from_user.id != 388576209:
        return
    while elapsed_time() < max_time:
        sed_result = separate_sed(update.effective_message.text)
        if sed_result and update.effective_message.reply_to_message:
            if update.effective_message.reply_to_message.text:
                to_fix = update.effective_message.reply_to_message.text
            elif update.effective_message.reply_to_message.caption:
                to_fix = update.effective_message.reply_to_message.caption
            else:
                return

            repl, repl_with, flags = sed_result

            if not repl:
                update.effective_message.reply_to_message.reply_text("Anda mencoba untuk mengganti... "
                                                                     "tidak ada apa-apa dengan sesuatu?")
                return

            try:
                check = re.match(repl, to_fix, flags=re.IGNORECASE)

                if check and check.group(0).lower() == to_fix.lower():
                    update.effective_message.reply_to_message.reply_text("Hai semuanya, {} sedang mencoba untuk membuat "
                                                                         "saya mengatakan hal-hal yang saya tidak mau "
                                                                         "katakan!".format(update.effective_user.first_name))
                    return

                if 'i' in flags and 'g' in flags:
                    text = re.sub(repl, repl_with, to_fix, flags=re.I).strip()
                elif 'i' in flags:
                    text = re.sub(repl, repl_with, to_fix, count=1, flags=re.I).strip()
                elif 'g' in flags:
                    text = re.sub(repl, repl_with, to_fix).strip()
                else:
                    text = re.sub(repl, repl_with, to_fix, count=1).strip()
            except sre_constants.error:
                LOGGER.warning(update.effective_message.text)
                LOGGER.exception("SRE constant error")
                update.effective_message.reply_text("Apakah itu sed? Sepertinya tidak.")
                return

            # empty string errors -_-
            if len(text) >= telegram.MAX_MESSAGE_LENGTH:
                return update.effective_message.reply_text("Hasil dari perintah sed terlalu lama untuk \
                                                     telegram!")
            elif text:
                return update.effective_message.reply_to_message.reply_text(text)
    return update.effective_message.reply_to_message.reply_text("Hasil terlalu lama untuk di proses!")


__help__ = """
 - s/<text1>/<text2>(/<flags>): Balas pesan dengan ini untuk melakukan operasi sed pada pesan itu, mengganti semua \
kemunculan dari 'text1' dengan 'text2'. Flags adalah opsional, dan saat ini termasuk 'i' untuk kasus abaikan, 'g' untuk global, \
atau tidak sama sekali. Pembatas termasuk `/`, `_`, `|`, dan `:`. Pengelompokan teks didukung. Pesan yang dihasilkan tidak bisa \
lebih besar dari {}.

*Peringatan:* Sed menggunakan beberapa karakter khusus untuk membuat pencocokan lebih mudah, seperti ini `+*.?\\`
Jika Anda ingin menggunakan karakter ini, pastikan Anda menghindarinya!
seperti: \\?.
""".format(telegram.MAX_MESSAGE_LENGTH)

__mod_name__ = "Sed/Regex"


SED_HANDLER = DisableAbleRegexHandler(r's([{}]).*?\1.*'.format("".join(DELIMITERS)), sed, friendly="sed")

dispatcher.add_handler(SED_HANDLER)
