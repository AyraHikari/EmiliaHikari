import threading
from typing import Union

from sqlalchemy import Column, Integer, String, UnicodeText

from emilia.modules.sql import SESSION, BASE


class UserLanguage(BASE):
    __tablename__ = "user_lang"
    chat_id = Column(String(14), primary_key=True)
    lang = Column(UnicodeText, default='None')

    def __init__(self, chat_id, lang):
        self.chat_id = chat_id
        self.lang = lang

    def __repr__(self):
        return "<User {} using language {}>".format(self.chat_id, self.lang)


UserLanguage.__table__.create(checkfirst=True)

INSERTION_LOCK = threading.RLock()

GLOBAL_USERLANG = {}

def set_lang(chat_id, user_lang):
    global GLOBAL_USERLANG
    with INSERTION_LOCK:
        set_lang = SESSION.query(UserLanguage).get(str(chat_id))
        if not set_lang:
            set_lang = UserLanguage(str(chat_id), 'None')
        set_lang.lang = user_lang

        SESSION.add(set_lang)
        SESSION.commit()
        GLOBAL_USERLANG[str(chat_id)] = str(user_lang)

def get_lang(chat_id):
    return GLOBAL_USERLANG.get(str(chat_id))


def __load_userlang():
    global GLOBAL_USERLANG
    try:
        qall = SESSION.query(UserLanguage).all()
        for x in qall:
            GLOBAL_USERLANG[str(x.chat_id)] = x.lang
    finally:
        SESSION.close()

__load_userlang()
