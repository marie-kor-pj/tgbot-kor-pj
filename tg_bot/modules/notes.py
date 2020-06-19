import re
from io import BytesIO
from typing import Optional, List

from telegram import MAX_MESSAGE_LENGTH, ParseMode, InlineKeyboardMarkup
from telegram import Message, Update, Bot
from telegram.error import BadRequest
from telegram.ext import CommandHandler, RegexHandler
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import escape_markdown

import tg_bot.modules.sql.notes_sql as sql
from tg_bot import dispatcher, MESSAGE_DUMP, LOGGER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import user_admin
from tg_bot.modules.helper_funcs.misc import build_keyboard, revert_buttons
from tg_bot.modules.helper_funcs.msg_types import get_note_type

FILE_MATCHER = re.compile(r"^###file_id(!photo)?###:(.*?)(?:\s|$)")

ENUM_FUNC_MAP = {
    sql.Types.TEXT.value: dispatcher.bot.send_message,
    sql.Types.BUTTON_TEXT.value: dispatcher.bot.send_message,
    sql.Types.STICKER.value: dispatcher.bot.send_sticker,
    sql.Types.DOCUMENT.value: dispatcher.bot.send_document,
    sql.Types.PHOTO.value: dispatcher.bot.send_photo,
    sql.Types.AUDIO.value: dispatcher.bot.send_audio,
    sql.Types.VOICE.value: dispatcher.bot.send_voice,
    sql.Types.VIDEO.value: dispatcher.bot.send_video
}


# Do not async
def get(bot, update, notename, show_none=True, no_format=False):
    chat_id = update.effective_chat.id
    note = sql.get_note(chat_id, notename)
    message = update.effective_message  # type: Optional[Message]

    if note:
        # If we're replying to a message, reply to that message (unless it's an error)
        if message.reply_to_message:
            reply_id = message.reply_to_message.message_id
        else:
            reply_id = message.message_id

        if note.is_reply:
            if MESSAGE_DUMP:
                try:
                    bot.forward_message(chat_id=chat_id, from_chat_id=MESSAGE_DUMP, message_id=note.value)
                except BadRequest as excp:
                    if excp.message == "Message to forward not found":
                        message.reply_text("이 메시지가 손실된 것 같아요. - 기록 목록에서 "
                                           "제거할게요.")
                        sql.rm_note(chat_id, notename)
                    else:
                        raise
            else:
                try:
                    bot.forward_message(chat_id=chat_id, from_chat_id=chat_id, message_id=note.value)
                except BadRequest as excp:
                    if excp.message == "Message to forward not found":
                        message.reply_text("이 노트의 원래 발신인이 메시지를 삭제한 것 같아요. "
                                           "미안해요! 이를 방지하기 위해 봇 관리자에게 메시지 덤프 사용을 "
                                           "시작하도록 하세요. "
                                           "저장된 노트에서 이 노트를 제거할게요.")
                        sql.rm_note(chat_id, notename)
                    else:
                        raise
        else:
            text = note.value
            keyb = []
            parseMode = ParseMode.MARKDOWN
            buttons = sql.get_buttons(chat_id, notename)
            if no_format:
                parseMode = None
                text += revert_buttons(buttons)
            else:
                keyb = build_keyboard(buttons)

            keyboard = InlineKeyboardMarkup(keyb)

            try:
                if note.msgtype in (sql.Types.BUTTON_TEXT, sql.Types.TEXT):
                    bot.send_message(chat_id, text, reply_to_message_id=reply_id,
                                     parse_mode=parseMode, disable_web_page_preview=True,
                                     reply_markup=keyboard)
                else:
                    ENUM_FUNC_MAP[note.msgtype](chat_id, note.file, caption=text, reply_to_message_id=reply_id,
                                                parse_mode=parseMode, disable_web_page_preview=True,
                                                reply_markup=keyboard)

            except BadRequest as excp:
                if excp.message == "Entity_mention_user_invalid":
                    message.reply_text("전에 본 적이 없는 사람을 언급하려 했던 것 같군요. "
                                       "정말로 그들에 대해 언급하고 싶다면, 그들의 메시지들 중 하나를 나에게 전달해주세요, "
                                       "그러면 저는 그들에게 태그를 붙일 수 있을 거예요!")
                elif FILE_MATCHER.match(note.value):
                    message.reply_text("이 노트는 다른 봇에서 잘못 가져온 파일이에요 - 전 그것을 "
                                       "사용할 수 없어요. 만약 정말 필요하다면, 다시 저장할 수 있어요. "
                                       "그동안에 그것을 메모 목록에서 삭제해 드릴게요.")
                    sql.rm_note(chat_id, notename)
                else:
                    message.reply_text("이 노트의 형식이 잘못되었기 때문에 보낼 수 없어요. "
                                       "이유를 알 수 없다면 @MarieSupport 에 문의하세요!")
                    LOGGER.exception("메시지를 구문 분석할 수 없어요 #%s  - %s ", notename, str(chat_id))
                    LOGGER.warning("메시지가 있었어요: %s", str(note.value))
        return
    elif show_none:
        message.reply_text("이 기록은 존재하지 않아요.")


@run_async
def cmd_get(bot: Bot, update: Update, args: List[str]):
    if len(args) >= 2 and args[1].lower() == "noformat":
        get(bot, update, args[0], show_none=True, no_format=True)
    elif len(args) >= 1:
        get(bot, update, args[0], show_none=True)
    else:
        update.effective_message.reply_text("rekt 가져오기")


@run_async
def hash_get(bot: Bot, update: Update):
    message = update.effective_message.text
    fst_word = message.split()[0]
    no_hash = fst_word[1:]
    get(bot, update, no_hash, show_none=False)


@run_async
@user_admin
def save(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    msg = update.effective_message  # type: Optional[Message]

    note_name, text, data_type, content, buttons = get_note_type(msg)

    if data_type is None:
        msg.reply_text("메모가 존재하지 않아요!")
        return
    
    if len(text.strip()) == 0:
        text = note_name
        
    sql.add_note_to_db(chat_id, note_name, text, data_type, buttons=buttons, file=content)

    msg.reply_text(
        "{note_name} 을(를) 추가했어요.\n/get {note_name} 또는 #{note_name} 을(를) 이용하여 노트를 가져옵니다.".format(note_name=note_name))

    if msg.reply_to_message and msg.reply_to_message.from_user.is_bot:
        if text:
            msg.reply_text("저에게 메시지를 저장하려고 하는 것 같아요. 불행하게도, "
                           "봇은 봇의 메시지를 전달할 수 없어요, 그래서 전 정확한 메시지를 저장할 수 없어요. "
                           "\n가능한 한 모든 메시지들을 저장하겠지만, "
                           "더 많은 내용을 원한다면 직접 메시지를 전달하고 저장해야 해요.")
        else:
            msg.reply_text("봇들은 Telegram 으로 인한 장애가 있어서, 봇이 다른 봇과 상호작용하기 "
                           "힘들기 때문에 이 메시지를 평소와 같이 "
                           "저장하실 수 없어요 - 그 메시지를 전달하고 나서 그 새로운 메시지를 저장해도 "
                           "괜찮을까요? 고마워요!")
        return


@run_async
@user_admin
def clear(bot: Bot, update: Update, args: List[str]):
    chat_id = update.effective_chat.id
    if len(args) >= 1:
        notename = args[0]

        if sql.rm_note(chat_id, notename):
            update.effective_message.reply_text("노트를 성공적으로 제거했어요.")
        else:
            update.effective_message.reply_text("그 노트는 제 데이터베이스에 있는 메모가 아니에요!")


@run_async
def list_notes(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    note_list = sql.get_all_chat_notes(chat_id)

    msg = "*Notes in chat:*\n"
    for note in note_list:
        note_name = escape_markdown(" - {}\n".format(note.name))
        if len(msg) + len(note_name) > MAX_MESSAGE_LENGTH:
            update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
            msg = ""
        msg += note_name

    if msg == "*Notes in chat:*\n":
        update.effective_message.reply_text("이 채팅방에는 노트가 없어요!")

    elif len(msg) != 0:
        update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


def __import_data__(chat_id, data):
    failures = []
    for notename, notedata in data.get('extra', {}).items():
        match = FILE_MATCHER.match(notedata)

        if match:
            failures.append(notename)
            notedata = notedata[match.end():].strip()
            if notedata:
                sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.TEXT)
        else:
            sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.TEXT)

    if failures:
        with BytesIO(str.encode("\n".join(failures))) as output:
            output.name = "failed_imports.txt"
            dispatcher.bot.send_document(chat_id, document=output, filename="failed_imports.txt",
                                         caption="이러한 파일/사진은 다른 봇이 보냈기 때문에 가져오지 못했어요. "
                                                 "이것은 Telegram API 제한사항이므로 피할 수 없어요. "
                                                 "불편을 끼쳐드려 죄송합니다!")


def __stats__():
    return "{}개의 채팅방에 {}개의 노트가 있어요.".format(sql.num_chats(), sql.num_notes())


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    notes = sql.get_all_chat_notes(chat_id)
    return "이 채팅방에는 '{}' 개의 노트가 있어요.".format(len(notes))


__help__ = """
 - /get <notename>: notename 이라는 이름을 사용하여 노트를 가져와요.
 - #<notename>: /get 명령어와 같아요.
 - /notes or /saved: 이 채팅방에서 저장된 모든 노트를 나열해요.

포맷 없이 노트의 내용을 검색하려면 '/get <notename> noformat'을 사용하세요.
이 기능은 현재 노트를 업데이트할 때 유용해요.

*Admin only:*
 - /save <notename> <notedata>: 이름이 notename 인 노트를 nothedata 에 저장해요.
표준 마크다운 링크 구문을 사용하여 노트에 버튼을 추가할 수 있어요 - 링크 앞에는 \
`buttonurl:` 섹션이 있어야 해요, 예를 들어 `[somelink](buttonurl:example.com)` 처럼요. 더 많은 정보를 얻고 싶다면 /markdownhelp 명령어를 통해 알아보세요.
 - /save <notename>: 답장한 메시지를 name 이 아닌 notename (으)로 저장해요.
 - /clear <notename>: notename 이라는 이름의 노트를 제거해요.
"""

__mod_name__ = "메모"

GET_HANDLER = CommandHandler("get", cmd_get, pass_args=True)
HASH_GET_HANDLER = RegexHandler(r"^#[^\s]+", hash_get)

SAVE_HANDLER = CommandHandler("save", save)
DELETE_HANDLER = CommandHandler("clear", clear, pass_args=True)

LIST_HANDLER = DisableAbleCommandHandler(["notes", "saved"], list_notes, admin_ok=True)

dispatcher.add_handler(GET_HANDLER)
dispatcher.add_handler(SAVE_HANDLER)
dispatcher.add_handler(LIST_HANDLER)
dispatcher.add_handler(DELETE_HANDLER)
dispatcher.add_handler(HASH_GET_HANDLER)
