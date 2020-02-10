import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher, LOGGER
from tg_bot.modules.helper_funcs.chat_status import bot_admin, user_admin, is_user_admin, can_restrict
from tg_bot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from tg_bot.modules.helper_funcs.string_handling import extract_time
from tg_bot.modules.log_channel import loggable


@run_async
@bot_admin
@user_admin
@loggable
def mute(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("음소거를 할 사용자 id를 주거나, 또는 음소거할 사용자를 답장으로 알려주세요.")
        return ""

    if user_id == bot.id:
        message.reply_text("전 제 자신을 음소거할 수 없어요!")
        return ""

    member = chat.get_member(int(user_id))

    if member:
        if is_user_admin(chat, user_id, member=member):
            message.reply_text("두렵게도 전 관리자가 말을 하는 것을 막을 수 없어요!")

        elif member.can_send_messages is None or member.can_send_messages:
            bot.restrict_chat_member(chat.id, user_id, can_send_messages=False)
            message.reply_text("음소거되었습니다!")
            return "<b>{}:</b>" \
                   "\n#음소거" \
                   "\n<b>관리자:</b> {}" \
                   "\n<b>사용자:</b> {}".format(html.escape(chat.title),
                                              mention_html(user.id, user.first_name),
                                              mention_html(member.user.id, member.user.first_name))

        else:
            message.reply_text("해당 유저는 이미 음소거되어 있어요!")
    else:
        message.reply_text("해당 유저는 이 채팅방에 포함되어있지 않아요!")

    return ""


@run_async
@bot_admin
@user_admin
@loggable
def unmute(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("음소거를 해제하려면 사용자 이름을 알려주거나 답장으로 알려주세요.")
        return ""

    member = chat.get_member(int(user_id))

    if member:
        if is_user_admin(chat, user_id, member=member):
            message.reply_text("해당 유저는 관리자인데, 제가 어떻게 해야 할까요?")
            return ""

        elif member.status != 'kicked' and member.status != 'left':
            if member.can_send_messages and member.can_send_media_messages \
                    and member.can_send_other_messages and member.can_add_web_page_previews:
                message.reply_text("이 사용자는 이미 발언권을 가지고 있어요!")
                return ""
            else:
                bot.restrict_chat_member(chat.id, int(user_id),
                                         can_send_messages=True,
                                         can_send_media_messages=True,
                                         can_send_other_messages=True,
                                         can_add_web_page_previews=True)
                message.reply_text("음소거가 해제되었어요!")
                return "<b>{}:</b>" \
                       "\n#음소거 해제" \
                       "\n<b>관리자:</b> {}" \
                       "\n<b>사용자:</b> {}".format(html.escape(chat.title),
                                                  mention_html(user.id, user.first_name),
                                                  mention_html(member.user.id, member.user.first_name))
    else:
        message.reply_text("이 사용자는 채팅에 참여하지 않아요. 이 사용자의 말을 음소거해도 "
                           "기존 대화보다 더 많은 대화를 할 수 없어요!")

    return ""


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def temp_mute(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("음소거할 사용자를 선택하세요.")
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("해당 사용자를 찾을 수 없어요!")
            return ""
        else:
            raise

    if is_user_admin(chat, user_id, member):
        message.reply_text("관리자는 음소거할 수 없어요")
        return ""

    if user_id == bot.id:
        message.reply_text("전 제 자신을 음소거할 수 없어요")
        return ""

    if not reason:
        message.reply_text("해당 사용자의 음소거할 시간을 지정하지 않았어요!")
        return ""

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    if len(split_reason) > 1:
        reason = split_reason[1]
    else:
        reason = ""

    mutetime = extract_time(message, time_val)

    if not mutetime:
        return ""

    log = "<b>{}:</b>" \
          "\n#시간 음소거" \
          "\n<b>관리자:</b> {}" \
          "\n<b>사용자:</b> {}" \
          "\n<b>시간:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name),
                                     mention_html(member.user.id, member.user.first_name), time_val)
    if reason:
        log += "\n<b>이유:</b> {}".format(reason)

    try:
        if member.can_send_messages is None or member.can_send_messages:
            bot.restrict_chat_member(chat.id, user_id, until_date=mutetime, can_send_messages=False)
            message.reply_text("{} 동안 음소거!".format(time_val))
            return log
        else:
            message.reply_text("해당 유저는 이미 음소거되어 있습니다.")

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text("음소거 : {}!".format(time_val), quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR muting user %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("이런!!! 전 그 사용자를 음소거할 수 없어요.")

    return ""


__help__ = """
*관리자 전용 명령어*
 - /mute <사용자명>: 사용자를 음소거시켜요. 사용자명이 아닌 답장으로 음소거시킬 수도 있어요.
 - /tmute <사용자명> x(m/h/d): 해당 유저를 x 시간 동안 음소거해요. (핸들 또는 답장을 통해). m = 분, h = 시간, d = 날짜.
 - /unmute <사용자명>: 해당 유저의 음소거를 해제해요. 사용자명이 아닌 답장으로 음소거시킬 수도 있어요.
"""

__mod_name__ = "음소거"

MUTE_HANDLER = CommandHandler("mute", mute, pass_args=True, filters=Filters.group)
UNMUTE_HANDLER = CommandHandler("unmute", unmute, pass_args=True, filters=Filters.group)
TEMPMUTE_HANDLER = CommandHandler(["tmute", "tempmute"], temp_mute, pass_args=True, filters=Filters.group)

dispatcher.add_handler(MUTE_HANDLER)
dispatcher.add_handler(UNMUTE_HANDLER)
dispatcher.add_handler(TEMPMUTE_HANDLER)
