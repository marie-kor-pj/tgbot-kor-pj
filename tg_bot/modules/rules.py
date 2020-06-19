from typing import Optional

from telegram import Message, Update, Bot, User
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest
from telegram.ext import CommandHandler, run_async, Filters
from telegram.utils.helpers import escape_markdown

import tg_bot.modules.sql.rules_sql as sql
from tg_bot import dispatcher
from tg_bot.modules.helper_funcs.chat_status import user_admin
from tg_bot.modules.helper_funcs.string_handling import markdown_parser


@run_async
def get_rules(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    send_rules(update, chat_id)


# Do not async - not from a handler
def send_rules(update, chat_id, from_pm=False):
    bot = dispatcher.bot
    user = update.effective_user  # type: Optional[User]
    try:
        chat = bot.get_chat(chat_id)
    except BadRequest as excp:
        if excp.message == "Chat not found" and from_pm:
            bot.send_message(user.id, "이 채팅의 규칙 바로 가기가 제대로 설정되지 않았어요! 관리자에게 이 문제를 해결하도록 "
                                      "말해주세요.")
            return
        else:
            raise

    rules = sql.get_rules(chat_id)
    text = "*{}* 을(를) 위한 규칙은:\n\n{} 에요.".format(escape_markdown(chat.title), rules)

    if from_pm and rules:
        bot.send_message(user.id, text, parse_mode=ParseMode.MARKDOWN)
    elif from_pm:
        bot.send_message(user.id, "그룹의 관리자가 이 채팅에 어떠한 규칙도 적용하지 않았어요. "
                                  "이것은 이 그룹에 규칙이 없다는 것을 의미하지는 않을 거예요!")
    elif rules:
        update.effective_message.reply_text("이 그룹의 규칙을 확인하시려면 저에게 개인 메시지로 연락하세요.",
                                            reply_markup=InlineKeyboardMarkup(
                                                [[InlineKeyboardButton(text="규칙",
                                                                       url="t.me/{}?start={}".format(bot.username,
                                                                                                     chat_id))]]))
    else:
        update.effective_message.reply_text("그룹의 관리자가 이 채팅에 어떠한 규칙도 적용하지 않았어요. "
                                            "이것은 이 그룹에 규칙이 없다는 것을 의미하지는 않을 거예요!")


@run_async
@user_admin
def set_rules(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    msg = update.effective_message  # type: Optional[Message]
    raw_text = msg.text
    args = raw_text.split(None, 1)  # use python's maxsplit to separate cmd and args
    if len(args) == 2:
        txt = args[1]
        offset = len(txt) - len(raw_text)  # set correct offset relative to command
        markdown_rules = markdown_parser(txt, entities=msg.parse_entities(), offset=offset)

        sql.set_rules(chat_id, markdown_rules)
        update.effective_message.reply_text("이 그룹에 성공적으로 규칙을 적용했어요!")


@run_async
@user_admin
def clear_rules(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    sql.set_rules(chat_id, "")
    update.effective_message.reply_text("규칙을 성공적으로 제거했어요!")

    
def __stats__():
    return "{}개의 채팅방에 규칙이 설정되어 있어요.".format(sql.num_chats())


def __import_data__(chat_id, data):
    # set chat rules
    rules = data.get('info', {}).get('rules', "")
    sql.set_rules(chat_id, rules)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return "이 채팅의 규칙입니다: `{}`".format(bool(sql.get_rules(chat_id)))


__help__ = """
 - /rules: 이 채팅방의 규칙을 보여줘요.

*관리자용 명령어*
 - /setrules <규칙>: 이 채팅방의 규칙을 설정해요.
 - /clearrules: 이 채팅방의 규칙을 지워요.
"""

__mod_name__ = "규칙"

GET_RULES_HANDLER = CommandHandler("rules", get_rules, filters=Filters.group)
SET_RULES_HANDLER = CommandHandler("setrules", set_rules, filters=Filters.group)
RESET_RULES_HANDLER = CommandHandler("clearrules", clear_rules, filters=Filters.group)

dispatcher.add_handler(GET_RULES_HANDLER)
dispatcher.add_handler(SET_RULES_HANDLER)
dispatcher.add_handler(RESET_RULES_HANDLER)
