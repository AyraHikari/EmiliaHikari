import threading

from sqlalchemy import Column, String, UnicodeText, Boolean, func, distinct

from emilia.modules.sql import SESSION, BASE


class Disable(BASE):
    __tablename__ = "disabled_commands"
    chat_id = Column(String(14), primary_key=True)
    command = Column(UnicodeText, primary_key=True)

    def __init__(self, chat_id, command):
        self.chat_id = chat_id
        self.command = command

    def __repr__(self):
        return "Disabled cmd {} in {}".format(self.command, self.chat_id)

class DisableDelete(BASE):
    __tablename__ = "disabled_del"

    chat_id = Column(UnicodeText, primary_key=True)
    is_enable = Column(Boolean, default=False)

    def __init__(self, chat_id, is_enable=False):
        self.chat_id = chat_id
        self.is_enable = is_enable

    def __repr__(self):
        return "disable del status for {}".format(self.chat_id)


Disable.__table__.create(checkfirst=True)
DisableDelete.__table__.create(checkfirst=True)
DISABLE_INSERTION_LOCK = threading.RLock()
DISABLEDEL_INSERTION_LOCK = threading.RLock()

DISABLED = {}
DISABLEABLE = []
DISABLEDEL = []


def disable_command(chat_id, disable):
    with DISABLE_INSERTION_LOCK:
        disabled = SESSION.query(Disable).get((str(chat_id), disable))

        if not disabled:
            DISABLED.setdefault(str(chat_id), set()).add(disable)
            
            disabled = Disable(str(chat_id), disable)
            SESSION.add(disabled)
            SESSION.commit()
            return True

        SESSION.close()
        return False


def enable_command(chat_id, enable):
    with DISABLE_INSERTION_LOCK:
        disabled = SESSION.query(Disable).get((str(chat_id), enable))

        if disabled:
            if enable in DISABLED.get(str(chat_id)):  # sanity check
                DISABLED.setdefault(str(chat_id), set()).remove(enable)
                
            SESSION.delete(disabled)
            SESSION.commit()
            return True

        SESSION.close()
        return False

def disabledel_set(chat_id, is_enable):
    with DISABLEDEL_INSERTION_LOCK:
        curr = SESSION.query(DisableDelete).get(str(chat_id))
        if curr:
            SESSION.delete(curr)

        curr = DisableDelete(str(chat_id), is_enable)

        if is_enable:
            if str(chat_id) not in DISABLEDEL:
                DISABLEDEL.append(str(chat_id))
        else:
            if str(chat_id) in DISABLEDEL:
                DISABLEDEL.remove(str(chat_id))

        SESSION.add(curr)
        SESSION.commit()

def is_disable_del(chat_id):
    return str(chat_id) in DISABLEDEL

def is_command_disabled(chat_id, cmd):
    return cmd in DISABLED.get(str(chat_id), set())


def get_all_disabled(chat_id):
    return DISABLED.get(str(chat_id), set())


def num_chats():
    try:
        return SESSION.query(func.count(distinct(Disable.chat_id))).scalar()
    finally:
        SESSION.close()


def num_disabled():
    try:
        return SESSION.query(Disable).count()
    finally:
        SESSION.close()


def migrate_chat(old_chat_id, new_chat_id):
    with DISABLE_INSERTION_LOCK:
        chats = SESSION.query(Disable).filter(Disable.chat_id == str(old_chat_id)).all()
        for chat in chats:
            chat.chat_id = str(new_chat_id)
            SESSION.add(chat)
            
        if str(old_chat_id) in DISABLED:
            DISABLED[str(new_chat_id)] = DISABLED.get(str(old_chat_id), set())

        SESSION.commit()

def disableable_cache(cmd):
    global DISABLEABLE
    if type(cmd) == list:
        for x in cmd:
            DISABLEABLE.append(x)
    else:
        DISABLEABLE.append(cmd)

def get_disableable():
    return DISABLEABLE

def __load_disabled_commands():
    global DISABLED
    try:
        all_chats = SESSION.query(Disable).all()
        for chat in all_chats:
            DISABLED.setdefault(chat.chat_id, set()).add(chat.command)

    finally:
        SESSION.close()

def __load_disabledel():
    global DISABLEDEL
    try:
        all_disabledel = SESSION.query(DisableDelete).all()
        for x in all_disabledel:
            if x.is_enable:
                DISABLEDEL.append(str(x.chat_id))

    finally:
        SESSION.close()


__load_disabled_commands()
__load_disabledel()
