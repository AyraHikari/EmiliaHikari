import os

from telegram import ParseMode
from telegram import Update, Bot
from telegram.ext import CommandHandler, run_async, Filters

from emilia import dispatcher, OWNER_ID


@run_async
def reboot(bot: Bot, update: Update):
    msg = update.effective_message
    chat_id = update.effective_chat.id
    update.effective_message.reply_text("Rebooting...", parse_mode=ParseMode.MARKDOWN)
    try:
        os.system("cd /home/ayra/emilia/ && python3.6 -m emilia &")
        os.system("kill %d" % os.getpid())
        update.effective_message.reply_text(
            "Reboot Berhasil!", parse_mode=ParseMode.MARKDOWN
        )
    except:
        update.effective_message.reply_text(
            "Reboot Gagal!", parse_mode=ParseMode.MARKDOWN
        )


@run_async
def executor(bot: Bot, update: Update):
    msg = update.effective_message
    if msg.text:
        args = msg.text.split(None, 1)
        code = args[1]
        chat = msg.chat.id
        try:
            exec(code)
        except Exception as error:
            bot.send_message(
                chat,
                "*Gagal:* {}".format(error),
                parse_mode="markdown",
                reply_to_message_id=msg.message_id,
            )


REBOOT_HANDLER = CommandHandler("emreboot", reboot, filters=Filters.user(OWNER_ID))
EXEC_HANDLER = CommandHandler("emil", executor, filters=Filters.user(OWNER_ID))

# dispatcher.add_handler(REBOOT_HANDLER)
dispatcher.add_handler(EXEC_HANDLER)
