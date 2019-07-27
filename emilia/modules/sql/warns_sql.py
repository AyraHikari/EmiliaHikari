import threading

from sqlalchemy import Integer, Column, String, UnicodeText, func, distinct, Boolean
from sqlalchemy.dialects import postgresql

from emilia.modules.sql import SESSION, BASE


class Warns(BASE):
    __tablename__ = "warns"

    user_id = Column(Integer, primary_key=True)
    chat_id = Column(String(14), primary_key=True)
    num_warns = Column(Integer, default=0)
    reasons = Column(postgresql.ARRAY(UnicodeText))

    def __init__(self, user_id, chat_id):
        self.user_id = user_id
        self.chat_id = str(chat_id)
        self.num_warns = 0
        self.reasons = []

    def __repr__(self):
        return "<{} warns for {} in {} for reasons {}>".format(
            self.num_warns, self.user_id, self.chat_id, self.reasons
        )


class WarnFilters(BASE):
    __tablename__ = "warn_filters"
    chat_id = Column(String(14), primary_key=True)
    keyword = Column(UnicodeText, primary_key=True, nullable=False)
    reply = Column(UnicodeText, nullable=False)

    def __init__(self, chat_id, keyword, reply):
        self.chat_id = str(chat_id)  # ensure string
        self.keyword = keyword
        self.reply = reply

    def __repr__(self):
        return "<Permissions for %s>" % self.chat_id

    def __eq__(self, other):
        return bool(
            isinstance(other, WarnFilters)
            and self.chat_id == other.chat_id
            and self.keyword == other.keyword
        )


class WarnSettings(BASE):
    __tablename__ = "warn_settings"
    chat_id = Column(String(14), primary_key=True)
    warn_limit = Column(Integer, default=3)
    soft_warn = Column(Boolean, default=False)
    warn_mode = Column(Integer, default=0)

    def __init__(self, chat_id, warn_limit=3, soft_warn=False, warn_mode=0):
        self.chat_id = str(chat_id)
        self.warn_limit = warn_limit
        self.soft_warn = soft_warn
        self.warn_mode = warn_mode

    def __repr__(self):
        return "<{} has {} possible warns.>".format(self.chat_id, self.warn_limit)


Warns.__table__.create(checkfirst=True)
WarnFilters.__table__.create(checkfirst=True)
WarnSettings.__table__.create(checkfirst=True)

WARN_INSERTION_LOCK = threading.RLock()
WARN_FILTER_INSERTION_LOCK = threading.RLock()
WARN_SETTINGS_LOCK = threading.RLock()

WARN_FILTERS = {}


def warn_user(user_id, chat_id, reason=None):
    with WARN_INSERTION_LOCK:
        warned_user = SESSION.query(Warns).get((user_id, str(chat_id)))
        if not warned_user:
            warned_user = Warns(user_id, str(chat_id))

        warned_user.num_warns += 1
        if reason:
            warned_user.reasons = warned_user.reasons + [
                reason
            ]  # TODO:: double check this wizardry

        reasons = warned_user.reasons
        num = warned_user.num_warns

        SESSION.add(warned_user)
        SESSION.commit()

        return num, reasons


def remove_warn(user_id, chat_id):
    with WARN_INSERTION_LOCK:
        removed = False
        warned_user = SESSION.query(Warns).get((user_id, str(chat_id)))

        if warned_user and warned_user.num_warns > 0:
            warned_user.num_warns -= 1

            SESSION.add(warned_user)
            SESSION.commit()
            removed = True

        SESSION.close()
        return removed


def reset_warns(user_id, chat_id):
    with WARN_INSERTION_LOCK:
        warned_user = SESSION.query(Warns).get((user_id, str(chat_id)))
        if warned_user:
            warned_user.num_warns = 0
            warned_user.reasons = []

            SESSION.add(warned_user)
            SESSION.commit()
        SESSION.close()


def get_warns(user_id, chat_id):
    try:
        user = SESSION.query(Warns).get((user_id, str(chat_id)))
        if not user:
            return None
        reasons = user.reasons
        num = user.num_warns
        return num, reasons
    finally:
        SESSION.close()


def add_warn_filter(chat_id, keyword, reply):
    with WARN_FILTER_INSERTION_LOCK:
        warn_filt = WarnFilters(str(chat_id), keyword, reply)

        if keyword not in WARN_FILTERS.get(str(chat_id), []):
            WARN_FILTERS[str(chat_id)] = sorted(
                WARN_FILTERS.get(str(chat_id), []) + [keyword],
                key=lambda x: (-len(x), x),
            )

        SESSION.merge(warn_filt)  # merge to avoid duplicate key issues
        SESSION.commit()


def remove_warn_filter(chat_id, keyword):
    with WARN_FILTER_INSERTION_LOCK:
        warn_filt = SESSION.query(WarnFilters).get((str(chat_id), keyword))
        if warn_filt:
            if keyword in WARN_FILTERS.get(str(chat_id), []):  # sanity check
                WARN_FILTERS.get(str(chat_id), []).remove(keyword)

            SESSION.delete(warn_filt)
            SESSION.commit()
            return True
        SESSION.close()
        return False


def get_chat_warn_triggers(chat_id):
    return WARN_FILTERS.get(str(chat_id), set())


def get_chat_warn_filters(chat_id):
    try:
        return (
            SESSION.query(WarnFilters).filter(WarnFilters.chat_id == str(chat_id)).all()
        )
    finally:
        SESSION.close()


def get_warn_filter(chat_id, keyword):
    try:
        return SESSION.query(WarnFilters).get((str(chat_id), keyword))
    finally:
        SESSION.close()


def set_warn_limit(chat_id, warn_limit):
    with WARN_SETTINGS_LOCK:
        curr_setting = SESSION.query(WarnSettings).get(str(chat_id))
        if not curr_setting:
            curr_setting = WarnSettings(chat_id, warn_limit=warn_limit)

        curr_setting.warn_limit = warn_limit

        SESSION.add(curr_setting)
        SESSION.commit()


def set_warn_strength(chat_id, soft_warn):
    with WARN_SETTINGS_LOCK:
        curr_setting = SESSION.query(WarnSettings).get(str(chat_id))
        if not curr_setting:
            curr_setting = WarnSettings(chat_id, soft_warn=soft_warn)

        curr_setting.soft_warn = soft_warn

        SESSION.add(curr_setting)
        SESSION.commit()


def get_warn_setting(chat_id):
    try:
        setting = SESSION.query(WarnSettings).get(str(chat_id))
        if setting:
            return setting.warn_limit, setting.soft_warn, setting.warn_mode
        else:
            return 3, False, 1

    finally:
        SESSION.close()


def set_warn_mode(chat_id, warn_mode):
    with WARN_SETTINGS_LOCK:
        curr_setting = SESSION.query(WarnSettings).get(str(chat_id))
        if not curr_setting:
            curr_setting = WarnSettings(chat_id, warn_mode=warn_mode)

        curr_setting.warn_mode = warn_mode

        SESSION.add(curr_setting)
        SESSION.commit()


def get_warn_mode(chat_id):
    try:
        setting = SESSION.query(WarnSettings).get(str(chat_id))
        if setting:
            return setting.warn_mode, setting.warn_mode
        else:
            return 3, False

    finally:
        SESSION.close()


def num_warns():
    try:
        return SESSION.query(func.sum(Warns.num_warns)).scalar() or 0
    finally:
        SESSION.close()


def num_warn_chats():
    try:
        return SESSION.query(func.count(distinct(Warns.chat_id))).scalar()
    finally:
        SESSION.close()


def num_warn_filters():
    try:
        return SESSION.query(WarnFilters).count()
    finally:
        SESSION.close()


def num_warn_chat_filters(chat_id):
    try:
        return (
            SESSION.query(WarnFilters.chat_id)
            .filter(WarnFilters.chat_id == str(chat_id))
            .count()
        )
    finally:
        SESSION.close()


def num_warn_filter_chats():
    try:
        return SESSION.query(func.count(distinct(WarnFilters.chat_id))).scalar()
    finally:
        SESSION.close()


def __load_chat_warn_filters():
    global WARN_FILTERS
    try:
        chats = SESSION.query(WarnFilters.chat_id).distinct().all()
        for (chat_id,) in chats:  # remove tuple by ( ,)
            WARN_FILTERS[chat_id] = []

        all_filters = SESSION.query(WarnFilters).all()
        for x in all_filters:
            WARN_FILTERS[x.chat_id] += [x.keyword]

        WARN_FILTERS = {
            x: sorted(set(y), key=lambda i: (-len(i), i))
            for x, y in WARN_FILTERS.items()
        }

    finally:
        SESSION.close()


def migrate_chat(old_chat_id, new_chat_id):
    with WARN_INSERTION_LOCK:
        chat_notes = (
            SESSION.query(Warns).filter(Warns.chat_id == str(old_chat_id)).all()
        )
        for note in chat_notes:
            note.chat_id = str(new_chat_id)
        SESSION.commit()

    with WARN_FILTER_INSERTION_LOCK:
        chat_filters = (
            SESSION.query(WarnFilters)
            .filter(WarnFilters.chat_id == str(old_chat_id))
            .all()
        )
        for filt in chat_filters:
            filt.chat_id = str(new_chat_id)
        SESSION.commit()
        WARN_FILTERS[str(new_chat_id)] = WARN_FILTERS[str(old_chat_id)]
        del WARN_FILTERS[str(old_chat_id)]

    with WARN_SETTINGS_LOCK:
        chat_settings = (
            SESSION.query(WarnSettings)
            .filter(WarnSettings.chat_id == str(old_chat_id))
            .all()
        )
        for setting in chat_settings:
            setting.chat_id = str(new_chat_id)
        SESSION.commit()


def get_allwarns(chat_id):
    get = SESSION.query(Warns).all()
    allwarns = []
    for x in get:
        if x.chat_id == str(chat_id) and x.num_warns > 0:
            allwarns.append(
                {"user_id": x.user_id, "warns": x.num_warns, "reasons": x.reasons}
            )
    return allwarns


def import_warns(user_id, chat_id, warns, reasons):
    with WARN_INSERTION_LOCK:
        warned_user = SESSION.query(Warns).get((user_id, str(chat_id)))
        if not warned_user:
            warned_user = Warns(user_id, str(chat_id))

        warned_user.num_warns = warns
        warned_user.reasons = reasons

        SESSION.add(warned_user)
        SESSION.commit()

        return


__load_chat_warn_filters()
