import threading

from sqlalchemy import Column, String, UnicodeText, Boolean, func, distinct

from emilia.modules.sql import SESSION, BASE


class Rules(BASE):
    __tablename__ = "rules"
    chat_id = Column(String(14), primary_key=True)
    rules = Column(UnicodeText, default="")

    def __init__(self, chat_id):
        self.chat_id = chat_id

    def __repr__(self):
        return "<Chat {} rules: {}>".format(self.chat_id, self.rules)

class PrivateRules(BASE):
    __tablename__ = "rules_private"

    chat_id = Column(UnicodeText, primary_key=True)
    is_private = Column(Boolean, default=True)

    def __init__(self, chat_id, is_private=True):
        self.chat_id = chat_id
        self.is_private = is_private

    def __repr__(self):
        return "rules_private for {}".format(self.chat_id)


Rules.__table__.create(checkfirst=True)
PrivateRules.__table__.create(checkfirst=True)

INSERTION_LOCK = threading.RLock()
PR_INSERTION_LOCK = threading.RLock()


def set_rules(chat_id, rules_text):
    with INSERTION_LOCK:
        rules = SESSION.query(Rules).get(str(chat_id))
        if not rules:
            rules = Rules(str(chat_id))
        rules.rules = rules_text

        SESSION.add(rules)
        SESSION.commit()


def get_rules(chat_id):
    rules = SESSION.query(Rules).get(str(chat_id))
    ret = ""
    if rules:
        ret = rules.rules

    SESSION.close()
    return ret


def private_rules(chat_id, is_private):
    with PR_INSERTION_LOCK:
        curr = SESSION.query(PrivateRules).get(str(chat_id))
        if curr:
            SESSION.delete(curr)
        
        curr = PrivateRules(str(chat_id), is_private)

        SESSION.add(curr)
        SESSION.commit()

def get_private_rules(chat_id):
    curr = SESSION.query(PrivateRules).get(str(chat_id))
    if curr:
        return curr.is_private
    else:
        return True


def num_chats():
    try:
        return SESSION.query(func.count(distinct(Rules.chat_id))).scalar()
    finally:
        SESSION.close()


def migrate_chat(old_chat_id, new_chat_id):
    with INSERTION_LOCK:
        chat = SESSION.query(Rules).get(str(old_chat_id))
        if chat:
            chat.chat_id = str(new_chat_id)
        SESSION.commit()
