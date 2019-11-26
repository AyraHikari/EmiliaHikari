import threading
from typing import Union

from sqlalchemy import Column, Integer, String, Boolean

from emilia.modules.sql import SESSION, BASE


class PermanentPin(BASE):
    __tablename__ = "permanent_pin"
    chat_id = Column(String(14), primary_key=True)
    message_id = Column(Integer)

    def __init__(self, chat_id):
        self.chat_id = str(chat_id)

    def __repr__(self):
        return "<Permanent pin for ({})>".format(self.chat_id)

PermanentPin.__table__.create(checkfirst=True)

PERMPIN_LOCK = threading.RLock()


def set_permapin(chat_id, message_id):
    with PERMPIN_LOCK:
        permpin = SESSION.query(PermanentPin).get(str(chat_id))
        if not permpin:
            permpin = PermanentPin(chat_id)

        permpin.message_id = int(message_id)
        SESSION.add(permpin)
        SESSION.commit()

def get_permapin(chat_id):
    try:
        permapin = SESSION.query(PermanentPin).get(str(chat_id))
        if permapin:
            return permapin.message_id
        return 0
    finally:
        SESSION.close()
