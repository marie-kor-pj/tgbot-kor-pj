import html
import re
from typing import Optional, List

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, User, CallbackQuery
from telegram import Message, Chat, Update, Bot
from telegram.error import BadRequest
from telegram.ext import CommandHandler, run_async, DispatcherHandlerStop, MessageHandler, Filters, CallbackQueryHandler
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher, BAN_STICKER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import is_user_admin, bot_admin, user_admin_no_reply, user_admin, \
    can_restrict
from tg_bot.modules.helper_funcs.extraction import extract_text, extract_user_and_text, extract_user
from tg_bot.modules.helper_funcs.filters import CustomFilters
from tg_bot.modules.helper_funcs.misc import split_message
from tg_bot.modules.helper_funcs.string_handling import split_quotes
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.sql import warns_sql as sql

WARN_HANDLER_GROUP = 9
CURRENT_WARNING_FILTER_STRING = "<b>현재 이 채팅방에서 경고 필터로 설정된 단어:</b>\n"


# Not async
def warn(user: User, chat: Chat, reason: str, message: Message, warner: User = None) -> str:
    if is_user_admin(chat, user.id):
        message.reply_text("빌어먹을 관리자들, 경고도 못 해!")
        return ""

    if warner:
        warner_tag = mention_html(warner.id, warner.first_name)
    else:
        warner_tag = "자동 경고 필터."

    limit, soft_warn = sql.get_warn_setting(chat.id)
    num_warns, reasons = sql.warn_user(user.id, chat.id, reason)
    if num_warns >= limit:
        sql.reset_warns(user.id, chat.id)
        if soft_warn:  # kick
            chat.unban_member(user.id)
            reply = "{} 번 경고, {} 님이 강퇴되었어요!".format(limit, mention_html(user.id, user.first_name))

        else:  # ban
            chat.kick_member(user.id)
            reply = "{} 번 경고, {} 님이 Ban 당했어요!".format(limit, mention_html(user.id, user.first_name))

        for warn_reason in reasons:
            reply += "\n - {}".format(html.escape(warn_reason))

        message.bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        keyboard = []
        log_reason = "<b>{}:</b>" \
                     "\n#경고_BAN" \
                     "\n<b>관리자:</b> {}" \
                     "\n<b>유저:</b> {} (<code>{}</code>)" \
                     "\n<b>이유:</b> {}"\
                     "\n<b>횟수:</b> <code>{}/{}</code>".format(html.escape(chat.title),
                                                                  warner_tag,
                                                                  mention_html(user.id, user.first_name),
                                                                  user.id, reason, num_warns, limit)

    else:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("경고 제거", callback_data="rm_warn({})".format(user.id))]])

        reply = "{} (이)가 {}/{} 경고입니다... 조심하세요!".format(mention_html(user.id, user.first_name), num_warns,
                                                             limit)
        if reason:
            reply += "\n마지막 경고 이유:\n{}".format(html.escape(reason))

        log_reason = "<b>{}:</b>" \
                     "\n#경고" \
                     "\n<b>관리자:</b> {}" \
                     "\n<b>유저:</b> {} (<code>{}</code>)" \
                     "\n<b>이유:</b> {}"\
                     "\n<b>횟수:</b> <code>{}/{}</code>".format(html.escape(chat.title),
                                                                  warner_tag,
                                                                  mention_html(user.id, user.first_name),
                                                                  user.id, reason, num_warns, limit)

    try:
        message.reply_text(reply, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text(reply, reply_markup=keyboard, parse_mode=ParseMode.HTML, quote=False)
        else:
            raise
    return log_reason


@run_async
@user_admin_no_reply
@bot_admin
@loggable
def button(bot: Bot, update: Update) -> str:
    query = update.callback_query  # type: Optional[CallbackQuery]
    user = update.effective_user  # type: Optional[User]
    match = re.match(r"rm_warn\((.+?)\)", query.data)
    if match:
        user_id = match.group(1)
        chat = update.effective_chat  # type: Optional[Chat]
        res = sql.remove_warn(user_id, chat.id)
        if res:
            update.effective_message.edit_text(
                "{} 님에 의해 경고가 제거되었어요.".format(mention_html(user.id, user.first_name)),
                parse_mode=ParseMode.HTML)
            user_member = chat.get_member(user_id)
            return "<b>{}:</b>" \
                   "\n#경고_해제" \
                   "\n<b>관리자:</b> {}" \
                   "\n<b>사용자:</b> {} (<code>{}</code>)".format(html.escape(chat.title),
                                                                mention_html(user.id, user.first_name),
                                                                mention_html(user_member.user.id, user_member.user.first_name),
                                                                user_member.user.id)
        else:
            update.effective_message.edit_text(
                "해당 사용자는 이미 경고가 없어요.".format(mention_html(user.id, user.first_name)),
                parse_mode=ParseMode.HTML)

    return ""


@run_async
@user_admin
@can_restrict
@loggable
def warn_user(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    warner = update.effective_user  # type: Optional[User]

    user_id, reason = extract_user_and_text(message, args)

    if user_id:
        if message.reply_to_message and message.reply_to_message.from_user.id == user_id:
            return warn(message.reply_to_message.from_user, chat, reason, message.reply_to_message, warner)
        else:
            return warn(chat.get_member(user_id).user, chat, reason, message, warner)
    else:
        message.reply_text("지정된 사용자가 없어요!")
    return ""


@run_async
@user_admin
@bot_admin
@loggable
def reset_warns(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    user_id = extract_user(message, args)

    if user_id:
        sql.reset_warns(user_id, chat.id)
        message.reply_text("경고가 초기화되었어요")
        warned = chat.get_member(user_id).user
        return "<b>{}:</b>" \
               "\n#경고_초기화" \
               "\n<b>관리자:</b> {}" \
               "\n<b>사용자:</b> {} (<code>{}</code>)".format(html.escape(chat.title),
                                                            mention_html(user.id, user.first_name),
                                                            mention_html(warned.id, warned.first_name),
                                                            warned.id)
    else:
        message.reply_text("지정된 사용자가 없어요!")
    return ""


@run_async
def warns(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user_id = extract_user(message, args) or update.effective_user.id
    result = sql.get_warns(user_id, chat.id)

    if result and result[0] != 0:
        num_warns, reasons = result
        limit, soft_warn = sql.get_warn_setting(chat.id)

        if reasons:
            text = "이 사용자의 경고 횟수는 {}/{} 예요. 이유:".format(num_warns, limit)
            for reason in reasons:
                text += "\n - {}".format(reason)

            msgs = split_message(text)
            for msg in msgs:
                update.effective_message.reply_text(msg)
        else:
            update.effective_message.reply_text(
                "이 사용자의 경고 횟수는 {}/{} 예요. 하지만 아무 이유가 없네요.".format(num_warns, limit))
    else:
        update.effective_message.reply_text("이 사용자에게 경고가 없어요!")


# Dispatcher handler stop - do not async
@user_admin
def add_warn_filter(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]

    args = msg.text.split(None, 1)  # use python's maxsplit to separate Cmd, keyword, and reply_text

    if len(args) < 2:
        return

    extracted = split_quotes(args[1])

    if len(extracted) >= 2:
        # set trigger -> lower, so as to avoid adding duplicate filters with different cases
        keyword = extracted[0].lower()
        content = extracted[1]

    else:
        return

    # Note: perhaps handlers can be removed somehow using sql.get_chat_filters
    for handler in dispatcher.handlers.get(WARN_HANDLER_GROUP, []):
        if handler.filters == (keyword, chat.id):
            dispatcher.remove_handler(handler, WARN_HANDLER_GROUP)

    sql.add_warn_filter(chat.id, keyword, content)

    update.effective_message.reply_text("경고 조정기가 추가되었어요. '{}'!".format(keyword))
    raise DispatcherHandlerStop


@user_admin
def remove_warn_filter(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]

    args = msg.text.split(None, 1)  # use python's maxsplit to separate Cmd, keyword, and reply_text

    if len(args) < 2:
        return

    extracted = split_quotes(args[1])

    if len(extracted) < 1:
        return

    to_remove = extracted[0]

    chat_filters = sql.get_chat_warn_triggers(chat.id)

    if not chat_filters:
        msg.reply_text("여기에는 활성 상태의 경고 필터가 없어요!")
        return

    for filt in chat_filters:
        if filt == to_remove:
            sql.remove_warn_filter(chat.id, to_remove)
            msg.reply_text("네, 그런 경고는 그만할게요.")
            raise DispatcherHandlerStop

    msg.reply_text("현재 경고 필터가 아니에요. 모든 활성 경고 필터를 위해 /warnlist 을(를) 입력해보세요.")


@run_async
def list_warn_filters(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    all_handlers = sql.get_chat_warn_triggers(chat.id)

    if not all_handlers:
        update.effective_message.reply_text("여기에는 활성 상태의 경고 필터가 없어요!")
        return

    filter_list = CURRENT_WARNING_FILTER_STRING
    for keyword in all_handlers:
        entry = " - {}\n".format(html.escape(keyword))
        if len(entry) + len(filter_list) > telegram.MAX_MESSAGE_LENGTH:
            update.effective_message.reply_text(filter_list, parse_mode=ParseMode.HTML)
            filter_list = entry
        else:
            filter_list += entry

    if not filter_list == CURRENT_WARNING_FILTER_STRING:
        update.effective_message.reply_text(filter_list, parse_mode=ParseMode.HTML)


@run_async
@loggable
def reply_filter(bot: Bot, update: Update) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]

    chat_warn_filters = sql.get_chat_warn_triggers(chat.id)
    to_match = extract_text(message)
    if not to_match:
        return ""

    for keyword in chat_warn_filters:
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, to_match, flags=re.IGNORECASE):
            user = update.effective_user  # type: Optional[User]
            warn_filter = sql.get_warn_filter(chat.id, keyword)
            return warn(user, chat, warn_filter.reply, message)
    return ""


@run_async
@user_admin
@loggable
def set_warn_limit(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]

    if args:
        if args[0].isdigit():
            if int(args[0]) < 3:
                msg.reply_text("최소 경고 한도는 3 이에요!")
            else:
                sql.set_warn_limit(chat.id, int(args[0]))
                msg.reply_text("Updated the warn limit to {}".format(args[0]))
                return "<b>{}:</b>" \
                       "\n#경고_한계_설정" \
                       "\n<b>관리자:</b> {}" \
                       "\n경고 한계가 다음과 같이 설정되었습니다 : <code>{}</code>".format(html.escape(chat.title),
                                                                        mention_html(user.id, user.first_name), args[0])
        else:
            msg.reply_text("경고 한계 숫자를 입력해 주세요!")
    else:
        limit, soft_warn = sql.get_warn_setting(chat.id)

        msg.reply_text("현재 경고 한계는 {}회 입니다.".format(limit))
    return ""


@run_async
@user_admin
def set_warn_strength(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]

    if args:
        if args[0].lower() in ("on", "yes"):
            sql.set_warn_strength(chat.id, False)
            msg.reply_text("경고가 너무 많으면 Ban 됩니다!")
            return "<b>{}:</b>\n" \
                   "<b>관리자:</b> {}\n" \
                   "강력한 경고를 활성화했어요. 사용자가 Ban 돼요.".format(html.escape(chat.title),
                                                                            mention_html(user.id, user.first_name))

        elif args[0].lower() in ("off", "no"):
            sql.set_warn_strength(chat.id, True)
            msg.reply_text("경고가 너무 많아지면 강퇴당할 거예요! 사용자들은 나중에 다시 들어올 수 있어요.")
            return "<b>{}:</b>\n" \
                   "<b>관리자:</b> {}\n" \
                   "강력한 경고가 비활성화되었어요. 사용자는 강퇴만 당할 수 있어요.".format(html.escape(chat.title),
                                                                                  mention_html(user.id,
                                                                                               user.first_name))

        else:
            msg.reply_text("저는 on/yes/no/off 만 알아들을 수 있어요!")
    else:
        limit, soft_warn = sql.get_warn_setting(chat.id)
        if soft_warn:
            msg.reply_text("경고는 현재 사용자가 제한을 초과할 경우 *강퇴* 되도록 설정되어 있어요.",
                           parse_mode=ParseMode.MARKDOWN)
        else:
            msg.reply_text("경고는 현재 사용자가 제한을 초과할 경우 *BAN* 되도록 설정되어 있어요.",
                           parse_mode=ParseMode.MARKDOWN)
    return ""


def __stats__():
    return "{}개의 채팅방에서 {}번의 경고를 했어요.\n" \
           "{}개의 채팅방에서 {}개의 경고 필터가 있어요.".format(sql.num_warn_chats(), sql.num_warns(),
                                                      sql.num_warn_filter_chats(), sql.num_warn_filters())


def __import_data__(chat_id, data):
    for user_id, count in data.get('warns', {}).items():
        for x in range(int(count)):
            sql.warn_user(user_id, chat_id)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    num_warn_filters = sql.num_warn_chat_filters(chat_id)
    limit, soft_warn = sql.get_warn_setting(chat_id)
    return "이 채팅에는 `{}` 경고 필터가 있어요. 그것은 `{}` 사용자가 가져오기 전에 " \
           "경고해요 *{}*.".format(num_warn_filters, limit, "kicked" if soft_warn else "banned")


__help__ = """
 - /warns <사용자명>: 경고 횟수 및 이유를 가져와요.
 - /warnlist: 모든 현재 경고 필터 목록을 알려줘요.

*관리자용 명령어*
 - /warn <사용자명>: 사용자를 경고해요. 경고를 3번 받으면, 그룹에서 사용자를 BAN 해요. 사용자명 대신 답장해도 돼요.
 - /resetwarn <사용자명>: 사용자의 경고를 초기화해요. 사용자명 대신 답장해도 돼요.
 - /addwarn <키워드> <답장할 메시지 (경고 이유)>: 특정 키워드에 경고 필터를 설정해요. 키워드를 문장으로 지정하려면 \
다음과 같이 작성해주세요: `/addwarn "very angry" 이 사용자는 화난 사용자예요`.
 - /nowarn <키워드>: 경고 필터를 멈춰요.
 - /warnlimit <숫자>: 경고의 횟수를 지정해요. 기본값인 3에서 다른 값으로 바꿀 수 있어요.
 - /strongwarn <on/yes/off/no>: on으로 설정하고 경고 한계를 초과하면 BAN 돼요. 또한, 강퇴당할 거예요.
"""

__mod_name__ = "경고"

WARN_HANDLER = CommandHandler("warn", warn_user, pass_args=True, filters=Filters.group)
RESET_WARN_HANDLER = CommandHandler(["resetwarn", "resetwarns"], reset_warns, pass_args=True, filters=Filters.group)
CALLBACK_QUERY_HANDLER = CallbackQueryHandler(button, pattern=r"rm_warn")
MYWARNS_HANDLER = DisableAbleCommandHandler("warns", warns, pass_args=True, filters=Filters.group)
ADD_WARN_HANDLER = CommandHandler("addwarn", add_warn_filter, filters=Filters.group)
RM_WARN_HANDLER = CommandHandler(["nowarn", "stopwarn"], remove_warn_filter, filters=Filters.group)
LIST_WARN_HANDLER = DisableAbleCommandHandler(["warnlist", "warnfilters"], list_warn_filters, filters=Filters.group, admin_ok=True)
WARN_FILTER_HANDLER = MessageHandler(CustomFilters.has_text & Filters.group, reply_filter)
WARN_LIMIT_HANDLER = CommandHandler("warnlimit", set_warn_limit, pass_args=True, filters=Filters.group)
WARN_STRENGTH_HANDLER = CommandHandler("strongwarn", set_warn_strength, pass_args=True, filters=Filters.group)

dispatcher.add_handler(WARN_HANDLER)
dispatcher.add_handler(CALLBACK_QUERY_HANDLER)
dispatcher.add_handler(RESET_WARN_HANDLER)
dispatcher.add_handler(MYWARNS_HANDLER)
dispatcher.add_handler(ADD_WARN_HANDLER)
dispatcher.add_handler(RM_WARN_HANDLER)
dispatcher.add_handler(LIST_WARN_HANDLER)
dispatcher.add_handler(WARN_LIMIT_HANDLER)
dispatcher.add_handler(WARN_STRENGTH_HANDLER)
dispatcher.add_handler(WARN_FILTER_HANDLER, WARN_HANDLER_GROUP)
