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

BASE_BLACKLIST_STRING = "현재 <b>Blacklisted</b> 에 추가된 단어들 :\n"


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
            msg.reply_text("Blacklist 에 오른 메시지가 없어요!")
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
            msg.reply_text("<code>{}</code> 가 Blacklist 에 추가되었어요!".format(html.escape(to_blacklist[0])),
                           parse_mode=ParseMode.HTML)

        else:
            msg.reply_text(
                "<code>{}</code> 가 Blacklist 에 추가되었어요!".format(len(to_blacklist)), parse_mode=ParseMode.HTML)

    else:
        msg.reply_text("Blacklist 에 추가할 단어를 알려주세요.")


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
                msg.reply_text("<code>{}</code> 가 Blacklist 에서 제거되었어요!".format(html.escape(to_unblacklist[0])),
                               parse_mode=ParseMode.HTML)
            else:
                msg.reply_text("이 단어는 Blacklist 에 오른 메시지가 아니예요...!")

        elif successful == len(to_unblacklist):
            msg.reply_text(
                "<code>{}</code> 가 Blacklist 에서 제거되었어요.".format(
                    successful), parse_mode=ParseMode.HTML)

        elif not successful:
            msg.reply_text(
                "이 메시지들은 모두 Blacklist 에 존재하지 않기 때문에 제거되지 않았어요.".format(
                    successful, len(to_unblacklist) - successful), parse_mode=ParseMode.HTML)

        else:
            msg.reply_text(
                "<code>{}</code> 가 Blacklist 에서 제거되었어요. {} 라는 단어는 Blacklist 에 존재하지 않네요!"
                "그래서 삭제할 수 없어요.".format(successful, len(to_unblacklist) - successful),
                parse_mode=ParseMode.HTML)
    else:
        msg.reply_text("Blacklist 에서 어떤 단어를 삭제하고 싶으신지 말씀해주세요.")


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
                if excp.message == "Message to delete not found":
                    pass
                else:
                    LOGGER.exception("Blacklist 메시지 삭제 중 오류 발생!")
            break


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    blacklisted = sql.num_blacklist_chat_filters(chat_id)
    return "{} 이란 단어는 Blacklist 에 오른 단어에요!".format(blacklisted)


def __stats__():
    return "{}개의 채팅방에서 {}개의 단어가 Blacklist 단어예요.".format(sql.num_blacklist_filters(), 
                                                            sql.num_blacklist_filter_chats())


__mod_name__ = "블랙리스트"

__help__ = """
블랙리스트는 특정 단어가 그룹에서 언급되는 것을 방지하는 데 사용돼요.
특정 단어를 언급할 때마다 메시지가 즉시 삭제돼요. 경고 필터와 함께 사용하는 것은 좋은 조합이에요!
*NOTE:* Blacklist 는 그룹 관리자에게 영향을 미치지 않아요.
 - /blacklist: 현재 Blacklist 에 나열된 단어를 보여줘요.
*관리자용 명령어*
 - /addblacklist <단어들>: Blacklist 에 단어를 추가해요. 여러 단어들을 추가하려면 엔터를(개행) 사용하세요.
 - /unblacklist <단어들>: Blacklist 에서 단어를 제거해요. addblacklist 와 마찬가지로 여러 단어들을 한번에 제거하려면 엔터를(개행) 이용하세요.
 - /rmblacklist <triggers>: 위 명령어와 같아요.
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
