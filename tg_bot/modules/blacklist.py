import html
import re
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, MessageHandler, Filters, run_async

import tg_bot.modules.sql.blacklist_sql as sql
from tg_bot import dispatcher, LOGGER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import user_admin, user_not_admin
from tg_bot.modules.helper_funcs.extraction import extract_text
from tg_bot.modules.helper_funcs.misc import split_message

BLACKLIST_GROUP = 11

BASE_BLACKLIST_STRING = "현재 <b>blacklisted</b> 에 추가된 단어들 :\n"


@run_async
def blacklist(bot: Bot, update: Update, args: List[str]):
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]

    all_blacklisted = sql.get_chat_blacklist(chat.id)

    filter_list = BASE_BLACKLIST_STRING

    if len(args) > 0 and args[0].lower() == 'copy':
        for trigger in all_blacklisted:
            filter_list += "<code>{}</code>\n".format(html.escape(trigger))
    else:
        for trigger in all_blacklisted:
            filter_list += " - <code>{}</code>\n".format(html.escape(trigger))

    split_text = split_message(filter_list)
    for text in split_text:
        if text == BASE_BLACKLIST_STRING:
            msg.reply_text("블랙리스트에 오른 메세지가 없습니다!")
            return
        msg.reply_text(text, parse_mode=ParseMode.HTML)


@run_async
@user_admin
def add_blacklist(bot: Bot, update: Update):
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    words = msg.text.split(None, 1)
    if len(words) > 1:
        text = words[1]
        to_blacklist = list(set(trigger.strip() for trigger in text.split("\n") if trigger.strip()))
        for trigger in to_blacklist:
            sql.add_to_blacklist(chat.id, trigger.lower())

        if len(to_blacklist) == 1:
            msg.reply_text("<code>{}</code> 가 Blacklist에 추가되었습니다!".format(html.escape(to_blacklist[0])),
                           parse_mode=ParseMode.HTML)

        else:
            msg.reply_text(
                "<code>{}</code> 가 Blacklist에 추가되었어요!".format(len(to_blacklist)), parse_mode=ParseMode.HTML)

    else:
        msg.reply_text("블랙리스트에 추가할 단어를 알려주세요.")


@run_async
@user_admin
def unblacklist(bot: Bot, update: Update):
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    words = msg.text.split(None, 1)
    if len(words) > 1:
        text = words[1]
        to_unblacklist = list(set(trigger.strip() for trigger in text.split("\n") if trigger.strip()))
        successful = 0
        for trigger in to_unblacklist:
            success = sql.rm_from_blacklist(chat.id, trigger.lower())
            if success:
                successful += 1

        if len(to_unblacklist) == 1:
            if successful:
                msg.reply_text("<code>{}</code> 가 Blacklist에서 제거되었습니다!".format(html.escape(to_unblacklist[0])),
                               parse_mode=ParseMode.HTML)
            else:
                msg.reply_text("이 단어는 Blacklist에 오른 메시지가 아니예요...!")

        elif successful == len(to_unblacklist):
            msg.reply_text(
                "<code>{}</code> 가 Blacklist에서 제거되었어요.".format(
                    successful), parse_mode=ParseMode.HTML)

        elif not successful:
            msg.reply_text(
                "이 메시지들은 모두 존재하지 않기 때문에 제거되지 않았어요.".format(
                    successful, len(to_unblacklist) - successful), parse_mode=ParseMode.HTML)

        else:
            msg.reply_text(
                "<code>{}</code> 가 Blacklist에서 제거되었어요. {} 라는 단어는 존재하지 않네요!"
                "그래서 삭제할 수 없어요.".format(successful, len(to_unblacklist) - successful),
                parse_mode=ParseMode.HTML)
    else:
        msg.reply_text("Blacklist에서 어떤 단어를 삭제하고 싶은지 말해주세요.")


@run_async
@user_not_admin
def del_blacklist(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]
    to_match = extract_text(message)
    if not to_match:
        return

    chat_filters = sql.get_chat_blacklist(chat.id)
    for trigger in chat_filters:
        pattern = r"( |^|[^\w])" + re.escape(trigger) + r"( |$|[^\w])"
        if re.search(pattern, to_match, flags=re.IGNORECASE):
            try:
                message.delete()
            except BadRequest as excp:
                if excp.message == "삭제할 메시지를 찾을 수 없어요.:
                    pass
                else:
                    LOGGER.exception("Blacklist 메시지 삭제 중 오류 발생!")
            break


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    blacklisted = sql.num_blacklist_chat_filters(chat_id)
    return "{} 이란 단어는 Blacklist에 오른 단어에요!".format(blacklisted)


def __stats__():
    return "{} 이란 단어는 Blacklist 단어이다, {} 채팅방에서.".format(sql.num_blacklist_filters(),
                                                            sql.num_blacklist_filter_chats())


__mod_name__ = "Word Blacklists"

__help__ = """
블랙리스트는 특정 단어가 그룹에서 언급되는 것을 방지하는 데 사용됩니다.
특정 단어를 언급할 때마다 메시지가 즉시 삭제됩니다. 좋은 콤비는 때때로 경고 필터와 짝을 짓습니다!
*NOTE:* Blacklist는 그룹 관리자에게 영향을 미치지 않습니다.
 - /blacklist: 현재 Blacklist에 나열된 단어 보기.
*Admin only:*
 - /addblacklist <단어들>: Blacklist에 단어를 추가합니다. 각 라인은 하나의 단어로 간주되므로 다른 단어를 추가할 경우 \ 를 사용합니다.
라인을 사용하면 여러 단어들을 추가할 수 있습니다.
 - /unblacklist <단어들>: Blacklist에서 단어를 제거합니다. 여기에 동일한 새 라인 논리가 적용되므로 \을(를) 제거할 수 있습니다.
여러 단어들을 한 번에 제거합니다.
 - /rmblacklist <triggers>: 위와 같습니다.
"""

BLACKLIST_HANDLER = DisableAbleCommandHandler("blacklist", blacklist, filters=Filters.group, pass_args=True,
                                              admin_ok=True)
ADD_BLACKLIST_HANDLER = CommandHandler("addblacklist", add_blacklist, filters=Filters.group)
UNBLACKLIST_HANDLER = CommandHandler(["unblacklist", "rmblacklist"], unblacklist, filters=Filters.group)
BLACKLIST_DEL_HANDLER = MessageHandler(
    (Filters.text | Filters.command | Filters.sticker | Filters.photo) & Filters.group, del_blacklist, edited_updates=True)

dispatcher.add_handler(BLACKLIST_HANDLER)
dispatcher.add_handler(ADD_BLACKLIST_HANDLER)
dispatcher.add_handler(UNBLACKLIST_HANDLER)
dispatcher.add_handler(BLACKLIST_DEL_HANDLER, group=BLACKLIST_GROUP)
