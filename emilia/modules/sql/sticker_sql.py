import threading

from sqlalchemy import func, distinct, Column, String, UnicodeText

from emilia.modules.sql import SESSION, BASE


class StickersFilters(BASE):
    __tablename__ = "blacklist_stickers"
    chat_id = Column(String(14), primary_key=True)
    trigger = Column(UnicodeText, primary_key=True, nullable=False)

    def __init__(self, chat_id, trigger):
        self.chat_id = str(chat_id)  # ensure string
        self.trigger = trigger

    def __repr__(self):
        return "<Stickers filter '%s' for %s>" % (self.trigger, self.chat_id)

    def __eq__(self, other):
        return bool(isinstance(other, StickersFilters)
                    and self.chat_id == other.chat_id
                    and self.trigger == other.trigger)


StickersFilters.__table__.create(checkfirst=True)

STICKERS_FILTER_INSERTION_LOCK = threading.RLock()

CHAT_STICKERS = {}


def add_to_stickers(chat_id, trigger):
    with STICKERS_FILTER_INSERTION_LOCK:
        stickers_filt = StickersFilters(str(chat_id), trigger)

        SESSION.merge(stickers_filt)  # merge to avoid duplicate key issues
        SESSION.commit()
        global CHAT_STICKERS
        if CHAT_STICKERS.get(str(chat_id), set()) == set():
            CHAT_STICKERS[str(chat_id)] = {trigger}
        else:
            CHAT_STICKERS.get(str(chat_id), set()).add(trigger)


def rm_from_stickers(chat_id, trigger):
    with STICKERS_FILTER_INSERTION_LOCK:
        stickers_filt = SESSION.query(StickersFilters).get((str(chat_id), trigger))
        if stickers_filt:
            if trigger in CHAT_STICKERS.get(str(chat_id), set()):  # sanity check
                CHAT_STICKERS.get(str(chat_id), set()).remove(trigger)

            SESSION.delete(stickers_filt)
            SESSION.commit()
            return True

        SESSION.close()
        return False


def get_chat_stickers(chat_id):
    return CHAT_STICKERS.get(str(chat_id), set())


def num_stickers_filters():
    try:
        return SESSION.query(StickersFilters).count()
    finally:
        SESSION.close()


def num_stickers_chat_filters(chat_id):
    try:
        return SESSION.query(StickersFilters.chat_id).filter(StickersFilters.chat_id == str(chat_id)).count()
    finally:
        SESSION.close()


def num_stickers_filter_chats():
    try:
        return SESSION.query(func.count(distinct(StickersFilters.chat_id))).scalar()
    finally:
        SESSION.close()


def __load_CHAT_STICKERS():
    global CHAT_STICKERS
    try:
        chats = SESSION.query(StickersFilters.chat_id).distinct().all()
        for (chat_id,) in chats:  # remove tuple by ( ,)
            CHAT_STICKERS[chat_id] = []

        all_filters = SESSION.query(StickersFilters).all()
        for x in all_filters:
            CHAT_STICKERS[x.chat_id] += [x.trigger]

        CHAT_STICKERS = {x: set(y) for x, y in CHAT_STICKERS.items()}

    finally:
        SESSION.close()


def migrate_chat(old_chat_id, new_chat_id):
    with STICKERS_FILTER_INSERTION_LOCK:
        chat_filters = SESSION.query(StickersFilters).filter(StickersFilters.chat_id == str(old_chat_id)).all()
        for filt in chat_filters:
            filt.chat_id = str(new_chat_id)
        SESSION.commit()


__load_CHAT_STICKERS()
