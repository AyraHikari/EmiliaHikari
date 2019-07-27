import threading
from typing import Union

from sqlalchemy import Column, Integer, String, Boolean

from emilia.modules.sql import SESSION, BASE


class ReportingUserSettings(BASE):
    __tablename__ = "user_report_settings"
    user_id = Column(Integer, primary_key=True)
    should_report = Column(Boolean, default=True)

    def __init__(self, user_id):
        self.user_id = user_id

    def __repr__(self):
        return "<User report settings ({})>".format(self.user_id)


class ReportingChatSettings(BASE):
    __tablename__ = "chat_report_settings"
    chat_id = Column(String(14), primary_key=True)
    should_report = Column(Boolean, default=True)

    def __init__(self, chat_id):
        self.chat_id = str(chat_id)

    def __repr__(self):
        return "<Chat report settings ({})>".format(self.chat_id)


ReportingUserSettings.__table__.create(checkfirst=True)
ReportingChatSettings.__table__.create(checkfirst=True)

CHAT_LOCK = threading.RLock()
USER_LOCK = threading.RLock()


def chat_should_report(chat_id: Union[str, int]) -> bool:
    try:
        chat_setting = SESSION.query(ReportingChatSettings).get(str(chat_id))
        if chat_setting:
            return chat_setting.should_report
        return False
    finally:
        SESSION.close()


def user_should_report(user_id: int) -> bool:
    try:
        user_setting = SESSION.query(ReportingUserSettings).get(user_id)
        if user_setting:
            return user_setting.should_report
        return True
    finally:
        SESSION.close()


def set_chat_setting(chat_id: Union[int, str], setting: bool):
    with CHAT_LOCK:
        chat_setting = SESSION.query(ReportingChatSettings).get(str(chat_id))
        if not chat_setting:
            chat_setting = ReportingChatSettings(chat_id)

        chat_setting.should_report = setting
        SESSION.add(chat_setting)
        SESSION.commit()


def set_user_setting(user_id: int, setting: bool):
    with USER_LOCK:
        user_setting = SESSION.query(ReportingUserSettings).get(user_id)
        if not user_setting:
            user_setting = ReportingUserSettings(user_id)

        user_setting.should_report = setting
        SESSION.add(user_setting)
        SESSION.commit()


def migrate_chat(old_chat_id, new_chat_id):
    with CHAT_LOCK:
        chat_notes = (
            SESSION.query(ReportingChatSettings)
            .filter(ReportingChatSettings.chat_id == str(old_chat_id))
            .all()
        )
        for note in chat_notes:
            note.chat_id = str(new_chat_id)
        SESSION.commit()
