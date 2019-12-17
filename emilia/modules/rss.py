import html
import re

from feedparser import parse
from telegram import ParseMode, constants, error
from telegram.ext import CommandHandler

from emilia import dispatcher, updater, spamfilters
from emilia.modules.helper_funcs.chat_status import user_admin
from emilia.modules.sql import rss_sql as sql

from emilia.modules.languages import tl
from emilia.modules.helper_funcs.alternate import send_message

def show_url(bot, update, args):
    tg_chat_id = str(update.effective_chat.id)
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return

    if len(args) >= 1:
        tg_feed_link = args[0]
        link_processed = parse(tg_feed_link)

        if link_processed.bozo == 0:
            feed_title = link_processed.feed.get("title", default="Unknown")
            feed_description = "<i>{}</i>".format(
                re.sub('<[^<]+?>', '', link_processed.feed.get("description", default="Unknown")))
            feed_link = link_processed.feed.get("link", default="Unknown")

            feed_message = tl(update.effective_message, "<b>Judul Feed:</b> \n{}" \
                           "\n\n<b>Deskripsi Feed:</b> \n{}" \
                           "\n\n<b>Link Feed:</b> \n{}").format(html.escape(feed_title),
                                                               feed_description,
                                                               html.escape(feed_link))

            if len(link_processed.entries) >= 1:
                entry_title = link_processed.entries[0].get("title", default="Unknown")
                entry_description = "<i>{}</i>".format(
                    re.sub('<[^<]+?>', '', link_processed.entries[0].get("description", default="Unknown")))
                entry_link = link_processed.entries[0].get("link", default="Unknown")

                entry_message = tl(update.effective_message, "\n\n<b>Judul Entri:</b> \n{}" \
                                "\n\n<b>Deskripsi Entri:</b> \n{}" \
                                "\n\n<b>Entri Masuk:</b> \n{}").format(html.escape(entry_title),
                                                                     entry_description,
                                                                     html.escape(entry_link))
                final_message = feed_message + entry_message

                bot.send_message(chat_id=tg_chat_id, text=final_message, parse_mode=ParseMode.HTML)
            else:
                bot.send_message(chat_id=tg_chat_id, text=feed_message, parse_mode=ParseMode.HTML)
        else:
            send_message(update.effective_message, tl(update.effective_message, "Tautan ini bukan tautan Umpan RSS"))
    else:
        send_message(update.effective_message, tl(update.effective_message, "URL hilang"))


def list_urls(bot, update):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return
    tg_chat_id = str(update.effective_chat.id)

    user_data = sql.get_urls(tg_chat_id)

    # this loops gets every link from the DB based on the filter above and appends it to the list
    links_list = [row.feed_link for row in user_data]

    final_content = "\n\n".join(links_list)

    # check if the length of the message is too long to be posted in 1 chat bubble
    if len(final_content) == 0:
        bot.send_message(chat_id=tg_chat_id, text=tl(update.effective_message, "Obrolan ini tidak berlangganan ke tautan apa pun"))
    elif len(final_content) <= constants.MAX_MESSAGE_LENGTH:
        bot.send_message(chat_id=tg_chat_id, text=tl(update.effective_message, "Obrolan ini dilanggan ke tautan berikut:\n") + final_content)
    else:
        bot.send_message(chat_id=tg_chat_id, parse_mode=ParseMode.HTML,
                         text=tl(update.effective_message, "<b>Peringatan:</b> Pesan terlalu panjang untuk dikirim"))


@user_admin
def add_url(bot, update, args):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return
    if len(args) >= 1:
        chat = update.effective_chat

        tg_chat_id = str(update.effective_chat.id)

        tg_feed_link = args[0]

        link_processed = parse(tg_feed_link)

        # check if link is a valid RSS Feed link
        if link_processed.bozo == 0:
            if len(link_processed.entries[0]) >= 1:
                tg_old_entry_link = link_processed.entries[0].link
            else:
                tg_old_entry_link = ""

            # gather the row which contains exactly that telegram group ID and link for later comparison
            row = sql.check_url_availability(tg_chat_id, tg_feed_link)

            # check if there's an entry already added to DB by the same user in the same group with the same link
            if row:
                send_message(update.effective_message, tl(update.effective_message, "URL ini sudah ditambahkan"))
            else:
                sql.add_url(tg_chat_id, tg_feed_link, tg_old_entry_link)

                send_message(update.effective_message, tl(update.effective_message, "URL ditambahkan ke langganan"))
        else:
            send_message(update.effective_message, tl(update.effective_message, "Tautan ini bukan tautan Umpan RSS"))
    else:
        send_message(update.effective_message, tl(update.effective_message, "URL hilang"))


@user_admin
def remove_url(bot, update, args):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return
    if len(args) >= 1:
        tg_chat_id = str(update.effective_chat.id)

        tg_feed_link = args[0]

        link_processed = parse(tg_feed_link)

        if link_processed.bozo == 0:
            user_data = sql.check_url_availability(tg_chat_id, tg_feed_link)

            if user_data:
                sql.remove_url(tg_chat_id, tg_feed_link)

                send_message(update.effective_message, tl(update.effective_message, "URL dihapus dari langganan"))
            else:
                send_message(update.effective_message, tl(update.effective_message, "Anda belum berlangganan ke URL ini"))
        else:
            send_message(update.effective_message, tl(update.effective_message, "Tautan ini bukan tautan Umpan RSS"))
    else:
        send_message(update.effective_message, tl(update.effective_message, "URL hilang"))


def rss_update(bot, job):
    user_data = sql.get_all()

    # this loop checks for every row in the DB
    for row in user_data:
        row_id = row.id
        tg_chat_id = row.chat_id
        tg_feed_link = row.feed_link

        feed_processed = parse(tg_feed_link)

        tg_old_entry_link = row.old_entry_link

        new_entry_links = []
        new_entry_titles = []

        # this loop checks for every entry from the RSS Feed link from the DB row
        for entry in feed_processed.entries:
            # check if there are any new updates to the RSS Feed from the old entry
            if entry.link != tg_old_entry_link:
                new_entry_links.append(entry.link)
                new_entry_titles.append(entry.title)
            else:
                break

        # check if there's any new entries queued from the last check
        if new_entry_links:
            sql.update_url(row_id, new_entry_links)
        else:
            pass

        if len(new_entry_links) < 5:
            # this loop sends every new update to each user from each group based on the DB entries
            for link, title in zip(reversed(new_entry_links), reversed(new_entry_titles)):
                final_message = "<b>{}</b>\n\n{}".format(html.escape(title), html.escape(link))

                if len(final_message) <= constants.MAX_MESSAGE_LENGTH:
                    try:
                        bot.send_message(chat_id=tg_chat_id, text=final_message, parse_mode=ParseMode.HTML)
                    except error.Unauthorized:
                        print("Cannot send msg bcz bot is kicked")
                        sql.remove_url(tg_chat_id, tg_feed_link)
                else:
                    try:
                        bot.send_message(chat_id=tg_chat_id, text=tl(tg_chat_id, "<b>Peringatan:</b> Pesan terlalu panjang untuk dikirim"),
                                     parse_mode=ParseMode.HTML)
                    except error.Unauthorized:
                        print("Cannot send msg bcz bot is kicked")
                        sql.remove_url(tg_chat_id, tg_feed_link)
        else:
            for link, title in zip(reversed(new_entry_links[-5:]), reversed(new_entry_titles[-5:])):
                final_message = "<b>{}</b>\n\n{}".format(html.escape(title), html.escape(link))

                if len(final_message) <= constants.MAX_MESSAGE_LENGTH:
                    try:
                        bot.send_message(chat_id=tg_chat_id, text=final_message, parse_mode=ParseMode.HTML)
                    except error.Unauthorized:
                        sql.remove_url(tg_chat_id, tg_feed_link)
                else:
                    try:
                        bot.send_message(chat_id=tg_chat_id, text=tl(tg_chat_id, "<b>Peringatan:</b> Pesan terlalu panjang untuk dikirim"),
                                     parse_mode=ParseMode.HTML)
                    except error.Unauthorized:
                        sql.remove_url(tg_chat_id, tg_feed_link)

            try:
                bot.send_message(chat_id=tg_chat_id, parse_mode=ParseMode.HTML,
                             text=tl(tg_chat_id, "<b>Peringatan: </b>{} kejadian telah ditinggalkan untuk mencegah spam")
                             .format(len(new_entry_links) - 5))
            except error.Unauthorized:
                sql.remove_url(tg_chat_id, tg_feed_link)


def rss_set(bot, job):
    user_data = sql.get_all()

    # this loop checks for every row in the DB
    for row in user_data:
        row_id = row.id
        tg_feed_link = row.feed_link
        tg_old_entry_link = row.old_entry_link

        feed_processed = parse(tg_feed_link)

        new_entry_links = []
        new_entry_titles = []

        # this loop checks for every entry from the RSS Feed link from the DB row
        for entry in feed_processed.entries:
            # check if there are any new updates to the RSS Feed from the old entry
            if entry.link != tg_old_entry_link:
                new_entry_links.append(entry.link)
                new_entry_titles.append(entry.title)
            else:
                break

        # check if there's any new entries queued from the last check
        if new_entry_links:
            sql.update_url(row_id, new_entry_links)
        else:
            pass


__help__ = "rss_help"

__mod_name__ = "RSS Feed"

job = updater.job_queue

job_rss_set = job.run_once(rss_set, 5)
job_rss_update = job.run_repeating(rss_update, interval=60, first=60)
job_rss_set.enabled = True
job_rss_update.enabled = True

SHOW_URL_HANDLER = CommandHandler("rss", show_url, pass_args=True)
ADD_URL_HANDLER = CommandHandler("addrss", add_url, pass_args=True)
REMOVE_URL_HANDLER = CommandHandler("removerss", remove_url, pass_args=True)
LIST_URLS_HANDLER = CommandHandler("listrss", list_urls)

dispatcher.add_handler(SHOW_URL_HANDLER)
dispatcher.add_handler(ADD_URL_HANDLER)
dispatcher.add_handler(REMOVE_URL_HANDLER)
dispatcher.add_handler(LIST_URLS_HANDLER)
