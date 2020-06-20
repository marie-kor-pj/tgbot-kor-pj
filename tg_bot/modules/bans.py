import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import run_async, CommandHandler, Filters
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher, BAN_STICKER, LOGGER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import bot_admin, user_admin, is_user_ban_protected, can_restrict, \
    is_user_admin, is_user_in_chat
from tg_bot.modules.helper_funcs.extraction import extract_user_and_text
from tg_bot.modules.helper_funcs.string_handling import extract_time
from tg_bot.modules.log_channel import loggable


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def ban(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Ban 할 사용자를 지칭하는 것 같지 않아요.")
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("해당 유저를 찾을 수 없어요!")
            return ""
        else:
            raise

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("관리자는 Ban 할 수 없어요!")
        return ""

    if user_id == bot.id:
        message.reply_text("저는 절 Ban 할 수 없어요!")
        return ""

    log = "<b>{}:</b>" \
          "\n#BANNED" \
          "\n<b>관리자:</b> {}" \
          "\n<b>사용자:</b> {} (<code>{}</code>)".format(html.escape(chat.title),
                                                       mention_html(user.id, user.first_name),
                                                       mention_html(member.user.id, member.user.first_name),
                                                       member.user.id)
    if reason:
        log += "\n<b>이유 :</b> {}".format(reason)

    try:
        chat.kick_member(user_id)
        bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        message.reply_text("넌 Ban 이야!")
        return log

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text('넌 Ban 이야!', quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR banning user %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("이런...! 전 그 사용자를 Ban 할 수 없어요!")

    return ""


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def temp_ban(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Ban 할 사용자를 지칭하는 것 같지 않아요.")
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("해당 유저를 찾을 수 없어요!")
            return ""
        else:
            raise

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("관리자는 Ban 할 수 없어요!")
        return ""

    if user_id == bot.id:
        message.reply_text("저는 절 Ban 할 수 없어요!")
        return ""

    if not reason:
        message.reply_text("이 사용자를 Ban 할 시간을 지정하지 않았어요!")
        return ""

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    if len(split_reason) > 1:
        reason = split_reason[1]
    else:
        reason = ""

    bantime = extract_time(message, time_val)

    if not bantime:
        return ""

    log = "<b>{}:</b>" \
          "\n#TEMP_BANNED" \
          "\n<b>관리자:</b> {}" \
          "\n<b>사용자:</b> {} (<code>{}</code>)" \
          "\n<b>시간:</b> {}".format(html.escape(chat.title),
                                     mention_html(user.id, user.first_name),
                                     mention_html(member.user.id, member.user.first_name),
                                     member.user.id,
                                     time_val)
    if reason:
        log += "\n<b>이유 :</b> {}".format(reason)

    try:
        chat.kick_member(user_id, until_date=bantime)
        bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        message.reply_text("넌 {} 까지 Ban이야!".format(time_val))
        return log

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text("넌 {} 까지 Ban이야!".format(time_val), quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR banning user %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("이런...! 전 그 사용자를 Ban할 수 없어요!")

    return ""


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def kick(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("해당 유저를 찾을 수 없어요.")
            return ""
        else:
            raise

    if is_user_ban_protected(chat, user_id):
        message.reply_text("관리자는 추방할 수 없어요!")
        return ""

    if user_id == bot.id:
        message.reply_text("그래요, 전 그렇게 하지 않을 거예요!")
        return ""

    res = chat.unban_member(user_id)  # unban on current user = kick
    if res:
        bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        message.reply_text("넌 추방이야!")
        log = "<b>{}:</b>" \
              "\n#추방" \
              "\n<b>관리자:</b> {}" \
              "\n<b>사용자:</b> {} (<code>{}</code>)".format(html.escape(chat.title),
                                                           mention_html(user.id, user.first_name),
                                                           mention_html(member.user.id, member.user.first_name),
                                                           member.user.id)
        if reason:
            log += "\n<b>이유 :</b> {}".format(reason)

        return log

    else:
        message.reply_text("이런...! 전 사용자를 추방할 수 없어요!")

    return ""


@run_async
@bot_admin
@can_restrict
def kickme(bot: Bot, update: Update):
    user_id = update.effective_message.from_user.id
    if is_user_admin(update.effective_chat, user_id):
        update.effective_message.reply_text("제가 그럴 수 있으면 좋겠네요... 그러나 당신은 관리자예요!")
        return

    res = update.effective_chat.unban_member(user_id)  # unban on current user = kick
    if res:
        update.effective_message.reply_text("문제없어요!")
    else:
        update.effective_message.reply_text("으음? 전 못해요! :/")


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def unban(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message  # type: Optional[Message]
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("해당 유저를 찾을 수 없어요!")
            return ""
        else:
            raise

    if user_id == bot.id:
        message.reply_text("저는 절 Unban 할 수 없어요.")
        return ""

    if is_user_in_chat(chat, user_id):
        message.reply_text("왜 Ban 되지 않은 사람을 Unban 하려는 거에요?")
        return ""

    chat.unban_member(user_id)
    message.reply_text("이제, 해당 유저는 이제 이 방에 들어올 수 있습니다!")

    log = "<b>{}:</b>" \
          "\n#Ban_해제" \
          "\n<b>관리자:</b> {}" \
          "\n<b>사용자:</b> {} (<code>{}</code>)".format(html.escape(chat.title),
                                                       mention_html(user.id, user.first_name),
                                                       mention_html(member.user.id, member.user.first_name),
                                                       member.user.id)
    if reason:
        log += "\n<b>이유:</b> {}".format(reason)

    return log


__help__ = """
 - /kickme: 명령을 실행한 대상을 추방해요.

*관리자용 명령어*
 - /ban <사용자명>: 유저를 Ban 해요. (@사용자명, 또는 답장을 통해서)
 - /tban <사용자명> x(m/h/d): x시간 동안 사용자를 Ban해요. (@사용자명, 또는 답장을 통해서). m = 분, h = 시간, d = 날짜.
 - /unban <사용자명>: 유저의 Ban 을 취소해요. (@사용자명, 또는 답장을 통해서)
 - /kick <사용자명>: 유저를 추방해요. (@사용자명, 또는 답장을 통해서)
"""

__mod_name__ = "Bans"

BAN_HANDLER = CommandHandler("ban", ban, pass_args=True, filters=Filters.group)
TEMPBAN_HANDLER = CommandHandler(["tban", "tempban"], temp_ban, pass_args=True, filters=Filters.group)
KICK_HANDLER = CommandHandler("kick", kick, pass_args=True, filters=Filters.group)
UNBAN_HANDLER = CommandHandler("unban", unban, pass_args=True, filters=Filters.group)
KICKME_HANDLER = DisableAbleCommandHandler("kickme", kickme, filters=Filters.group)

dispatcher.add_handler(BAN_HANDLER)
dispatcher.add_handler(TEMPBAN_HANDLER)
dispatcher.add_handler(KICK_HANDLER)
dispatcher.add_handler(UNBAN_HANDLER)
dispatcher.add_handler(KICKME_HANDLER)
