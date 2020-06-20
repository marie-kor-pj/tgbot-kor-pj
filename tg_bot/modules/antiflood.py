import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import Filters, MessageHandler, CommandHandler, run_async
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher
from tg_bot.modules.helper_funcs.chat_status import is_user_admin, user_admin, can_restrict
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.sql import antiflood_sql as sql

FLOOD_GROUP = 3


@run_async
@loggable
def check_flood(bot: Bot, update: Update) -> str:
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]

    if not user:  # ignore channels
        return ""

    # ignore admins
    if is_user_admin(chat, user.id):
        sql.update_flood(chat.id, None)
        return ""

    should_ban = sql.update_flood(chat.id, user.id)
    if not should_ban:
        return ""

    try:
        chat.kick_member(user.id)
        msg.reply_text("메시지를 한 번에 너무 많이 보낸 이유로 강퇴 당하셨습니다!")

        return "<b>{}:</b>" \
               "\n#밴" \
               "\n<b>사용자:</b> {}" \
               "\nFlooded the group.".format(html.escape(chat.title),
                                             mention_html(user.id, user.first_name))

    except BadRequest:
        msg.reply_text("강퇴시킬 수 없어요! 저에게 권한을 주실 때까지 도배 방지 기능은 사용할 수 없어요.")
        sql.set_flood(chat.id, 0)
        return "<b>{}:</b>" \
               "\n#정보" \
               "\n저에게 사용자 차단 권한이 없기 때문에 도배 방지 기능이 자동으로 비활성화됩니다!".format(chat.title)


@run_async
@user_admin
@can_restrict
@loggable
def set_flood(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    if len(args) >= 1:
        val = args[0].lower()
        if val == "off" or val == "no" or val == "0":
            sql.set_flood(chat.id, 0)
            message.reply_text("도배 방지가 비활성화되었어요.")

        elif val.isdigit():
            amount = int(val)
            if amount <= 0:
                sql.set_flood(chat.id, 0)
                message.reply_text("도배 방지가 비활성화되었어요.")
                return "<b>{}:</b>" \
                       "\n#도배_방지_설정" \
                       "\n<b>관리자:</b> {}" \
                       "\n도배 방지가 비활성화되었어요.".format(html.escape(chat.title), mention_html(user.id, user.first_name))

            elif amount < 3:
                message.reply_text("도배 방지 기능은 0(비활성화) 또는 3보다 큰 숫자여야 해요!")
                return ""

            else:
                sql.set_flood(chat.id, amount)
                message.reply_text("도배 방지가 {}개로 설정되었어요.".format(amount))
                return "<b>{}:</b>" \
                       "\n#도배_방지_설정" \
                       "\n<b>관리자:</b> {}" \
                       "\n도배 방지가 업데이트되었어요! : <code>{}</code>.".format(html.escape(chat.title),
                                                                    mention_html(user.id, user.first_name), amount)

        else:
            message.reply_text("올바르지 않은 명령어예요! - 숫자를 사용하여 도배 방지 기능을 키거나, 'off' 나 'no' 를 이용하여 도배 방지 기능을 비활성화하실 수 있어요.")

    return ""


@run_async
def flood(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]

    limit = sql.get_flood_limit(chat.id)
    if limit == 0:
        update.effective_message.reply_text("현재 도배 방지 기능을 사용하지 않고 있어요. 먼저 /setflood 명령어를 이용하여 도배방지 기능을 활성화해 주세요.")
    else:
        update.effective_message.reply_text(
            "도배 방지가 {} 개로 설정되어 있어요!".format(limit))


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    limit = sql.get_flood_limit(chat_id)
    if limit == 0:
        return "현재 도배 방지 기능 실행 중이 아니에요!"
    else:
        return "도배 방지가 {} 개로 설정되어 있어요!".format(limit)


__help__ = """
 - /flood: 현재 설정된 도배 방지 관련 내용을 확인하실 수 있어요.

*관리자용 명령어*
 - /setflood <숫자/'no'/'off'>: 도배 방지를 활성화하거나 비활성화하실 수 있어요.
"""

__mod_name__ = "도배 방지"

FLOOD_BAN_HANDLER = MessageHandler(Filters.all & ~Filters.status_update & Filters.group, check_flood)
SET_FLOOD_HANDLER = CommandHandler("setflood", set_flood, pass_args=True, filters=Filters.group)
FLOOD_HANDLER = CommandHandler("flood", flood, filters=Filters.group)

dispatcher.add_handler(FLOOD_BAN_HANDLER, FLOOD_GROUP)
dispatcher.add_handler(SET_FLOOD_HANDLER)
dispatcher.add_handler(FLOOD_HANDLER)
