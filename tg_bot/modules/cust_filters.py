import re
from typing import Optional

import telegram
from telegram import ParseMode, InlineKeyboardMarkup, Message, Chat
from telegram import Update, Bot
from telegram.error import BadRequest
from telegram.ext import CommandHandler, MessageHandler, DispatcherHandlerStop, run_async
from telegram.utils.helpers import escape_markdown

from tg_bot import dispatcher, LOGGER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import user_admin
from tg_bot.modules.helper_funcs.extraction import extract_text
from tg_bot.modules.helper_funcs.filters import CustomFilters
from tg_bot.modules.helper_funcs.misc import build_keyboard
from tg_bot.modules.helper_funcs.string_handling import split_quotes, button_markdown_parser
from tg_bot.modules.sql import cust_filters_sql as sql

HANDLER_GROUP = 10
BASIC_FILTER_STRING = "*이 채팅방의 필터 :*\n"


@run_async
def list_handlers(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    all_handlers = sql.get_chat_triggers(chat.id)

    if not all_handlers:
        update.effective_message.reply_text("필터가 활성화되어 있지 않아요!")
        return

    filter_list = BASIC_FILTER_STRING
    for keyword in all_handlers:
        entry = " - {}\n".format(escape_markdown(keyword))
        if len(entry) + len(filter_list) > telegram.MAX_MESSAGE_LENGTH:
            update.effective_message.reply_text(filter_list, parse_mode=telegram.ParseMode.MARKDOWN)
            filter_list = entry
        else:
            filter_list += entry

    if not filter_list == BASIC_FILTER_STRING:
        update.effective_message.reply_text(filter_list, parse_mode=telegram.ParseMode.MARKDOWN)


# NOT ASYNC BECAUSE DISPATCHER HANDLER RAISED
@user_admin
def filters(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]
    args = msg.text.split(None, 1)  # use python's maxsplit to separate Cmd, keyword, and reply_text

    if len(args) < 2:
        return

    extracted = split_quotes(args[1])
    if len(extracted) < 1:
        return
    # set trigger -> lower, so as to avoid adding duplicate filters with different cases
    keyword = extracted[0].lower()

    is_sticker = False
    is_document = False
    is_image = False
    is_voice = False
    is_audio = False
    is_video = False
    buttons = []

    # determine what the contents of the filter are - text, image, sticker, etc
    if len(extracted) >= 2:
        offset = len(extracted[1]) - len(msg.text)  # set correct offset relative to command + notename
        content, buttons = button_markdown_parser(extracted[1], entities=msg.parse_entities(), offset=offset)
        content = content.strip()
        if not content:
            msg.reply_text("노트에 글자가 없어요 - 버튼만 사용하실 수 없고, 함께 보낼 메시지가 꼭 필요해요!")
            return

    elif msg.reply_to_message and msg.reply_to_message.sticker:
        content = msg.reply_to_message.sticker.file_id
        is_sticker = True

    elif msg.reply_to_message and msg.reply_to_message.document:
        content = msg.reply_to_message.document.file_id
        is_document = True

    elif msg.reply_to_message and msg.reply_to_message.photo:
        content = msg.reply_to_message.photo[-1].file_id  # last elem = best quality
        is_image = True

    elif msg.reply_to_message and msg.reply_to_message.audio:
        content = msg.reply_to_message.audio.file_id
        is_audio = True

    elif msg.reply_to_message and msg.reply_to_message.voice:
        content = msg.reply_to_message.voice.file_id
        is_voice = True

    elif msg.reply_to_message and msg.reply_to_message.video:
        content = msg.reply_to_message.video.file_id
        is_video = True

    else:
        msg.reply_text("무엇으로 답해드려야 할지 구체적으로 알려주세요! '예:/filter 제목 내용'")
        return

    # Add the filter
    # Note: perhaps handlers can be removed somehow using sql.get_chat_filters
    for handler in dispatcher.handlers.get(HANDLER_GROUP, []):
        if handler.filters == (keyword, chat.id):
            dispatcher.remove_handler(handler, HANDLER_GROUP)

    sql.add_filter(chat.id, keyword, content, is_sticker, is_document, is_image, is_audio, is_voice, is_video,
                   buttons)

    msg.reply_text("필터 '{}' 이(가) 추가되었어요!".format(keyword))
    raise DispatcherHandlerStop


# NOT ASYNC BECAUSE DISPATCHER HANDLER RAISED
@user_admin
def stop_filter(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    args = update.effective_message.text.split(None, 1)

    if len(args) < 2:
        return

    chat_filters = sql.get_chat_triggers(chat.id)

    if not chat_filters:
        update.effective_message.reply_text("필터가 활성화되어 있지 않아요!")
        return

    for keyword in chat_filters:
        if keyword == args[1]:
            sql.remove_filter(chat.id, args[1])
            update.effective_message.reply_text("네, 이 필터를 삭제할게요!")
            raise DispatcherHandlerStop

    update.effective_message.reply_text("필터를 찾을 수 없어요 - 활성화되어 있는 모든 필터를 보려면 /filters 를 입력해주세요.")


@run_async
def reply_filter(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]
    to_match = extract_text(message)
    if not to_match:
        return

    chat_filters = sql.get_chat_triggers(chat.id)
    for keyword in chat_filters:
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, to_match, flags=re.IGNORECASE):
            filt = sql.get_filter(chat.id, keyword)
            if filt.is_sticker:
                message.reply_sticker(filt.reply)
            elif filt.is_document:
                message.reply_document(filt.reply)
            elif filt.is_image:
                message.reply_photo(filt.reply)
            elif filt.is_audio:
                message.reply_audio(filt.reply)
            elif filt.is_voice:
                message.reply_voice(filt.reply)
            elif filt.is_video:
                message.reply_video(filt.reply)
            elif filt.has_markdown:
                buttons = sql.get_buttons(chat.id, filt.keyword)
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                try:
                    message.reply_text(filt.reply, parse_mode=ParseMode.MARKDOWN,
                                       disable_web_page_preview=True,
                                       reply_markup=keyboard)
                except BadRequest as excp:
                    if excp.message == "URL 프로토콜이 지원되지 않아요.":
                        message.reply_text("지원되지 않는 URL 프로토콜을 사용하시는 것 같네요. tg:// "
                                           "와 같은 일부 프로토콜은 텔레그램에서 버튼을 지원하지 않아요. 다시 "
                                           "시도해보시거나, @MarieSupport 에 도움을 요청하세요.")
                    elif excp.message == "Reply message not found":
                        bot.send_message(chat.id, filt.reply, parse_mode=ParseMode.MARKDOWN,
                                         disable_web_page_preview=True,
                                         reply_markup=keyboard)
                    else:
                        message.reply_text("이 노트는 형식이 달라서 보낼 수 없어요. 이유를 알 수 없으면 "
                                           "@MarieSupport 에 물어보세요!")
                        LOGGER.warning("Message %s could not be parsed", str(filt.reply))
                        LOGGER.exception("Could not parse filter %s in chat %s", str(filt.keyword), str(chat.id))

            else:
                # LEGACY - all new filters will have has_markdown set to True.
                message.reply_text(filt.reply)
            break


def __stats__():
    return "{}개의 채팅방에서 {}개의 필터가 사용되고 있어요.".format(sql.num_chats(), sql.num_filters())


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    cust_filters = sql.get_chat_triggers(chat_id)
    return "여기에 `{}` 사용자 필터가 있어요.".format(len(cust_filters))


__help__ = """
 - /filters: 활성화되어있는 모든 필터를 알려줘요.

*관리자용 명령어*
 - /filter <제목> <내용>: 해당 채팅방에 필터를 추가해요. '제목'을 작성하시면 제가 그 메시지에 대해서 응답을 해드릴게요. \
스티커를 제목으로 설정하시면 그 스티커로 답장해드려요. 참고: 모든 필터 제목은 소문자로 설정하세요. \
키워드를 문장으로 사용하려면 따옴표를 사용해 주세요. 
예: /filter "hey there" How you \
doin?
 - /stop <필터 제목>: 필터를 삭제해요.
"""

__mod_name__ = "필터"

FILTER_HANDLER = CommandHandler("filter", filters)
STOP_HANDLER = CommandHandler("stop", stop_filter)
LIST_HANDLER = DisableAbleCommandHandler("filters", list_handlers, admin_ok=True)
CUST_FILTER_HANDLER = MessageHandler(CustomFilters.has_text, reply_filter)

dispatcher.add_handler(FILTER_HANDLER)
dispatcher.add_handler(STOP_HANDLER)
dispatcher.add_handler(LIST_HANDLER)
dispatcher.add_handler(CUST_FILTER_HANDLER, HANDLER_GROUP)
