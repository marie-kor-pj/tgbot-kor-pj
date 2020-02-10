import html
from typing import Optional, List

from telegram import Message, Update, Bot, User
from telegram import ParseMode, MAX_MESSAGE_LENGTH
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import escape_markdown

import tg_bot.modules.sql.userinfo_sql as sql
from tg_bot import dispatcher, SUDO_USERS
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.extraction import extract_user


@run_async
def about_me(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]
    user_id = extract_user(message, args)

    if user_id:
        user = bot.get_chat(user_id)
    else:
        user = message.from_user

    info = sql.get_user_me_info(user.id)

    if info:
        update.effective_message.reply_text("*{}*:\n{}".format(user.first_name, escape_markdown(info)),
                                            parse_mode=ParseMode.MARKDOWN)
    elif message.reply_to_message:
        username = message.reply_to_message.from_user.first_name
        update.effective_message.reply_text(username + " 님은 아직 me 메시지를 설정하지 않았어요!")
    else:
        update.effective_message.reply_text("아직 자신에 대한 info 메시지를 설정하지 않았어요!")


@run_async
def set_about_me(bot: Bot, update: Update):
    message = update.effective_message  # type: Optional[Message]
    user_id = message.from_user.id
    text = message.text
    info = text.split(None, 1)  # use python's maxsplit to only remove the cmd, hence keeping newlines.
    if len(info) == 2:
        if len(info[1]) < MAX_MESSAGE_LENGTH // 4:
            sql.set_user_me_info(user_id, info[1])
            message.reply_text("info 을(를) 업데이트했어요!")
        else:
            message.reply_text(
                "me 의 글자 수는 {} 자 아래여야 해요! 그러나 당신은 {} 자를 입력했어요.".format(MAX_MESSAGE_LENGTH // 4, len(info[1])))


@run_async
def about_bio(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if user_id:
        user = bot.get_chat(user_id)
    else:
        user = message.from_user

    info = sql.get_user_bio(user.id)

    if info:
        update.effective_message.reply_text("*{}*:\n{}".format(user.first_name, escape_markdown(info)),
                                            parse_mode=ParseMode.MARKDOWN)
    elif message.reply_to_message:
        username = user.first_name
        update.effective_message.reply_text("아직 {} 님에 대한 메시지를 설정하지 못했어요!".format(username))
    else:
        update.effective_message.reply_text("아직 자신의 Bio 메시지를 가지고 있지 않아요!")


@run_async
def set_about_bio(bot: Bot, update: Update):
    message = update.effective_message  # type: Optional[Message]
    sender = update.effective_user  # type: Optional[User]
    if message.reply_to_message:
        repl_message = message.reply_to_message
        user_id = repl_message.from_user.id
        if user_id == message.from_user.id:
            message.reply_text("자기 자신의 Bio 메시지를 설정할 수 없어요! 당신의 Bio 은(는) 다른 사람들의 마음대로입니다...")
            return
        elif user_id == bot.id and sender.id not in SUDO_USERS:
            message.reply_text("음... 저의 Bio 은(는) 오직 절 개발한 개발자만 설정할 수 있어요.")
            return

        text = message.text
        bio = text.split(None, 1)  # use python's maxsplit to only remove the cmd, hence keeping newlines.
        if len(bio) == 2:
            if len(bio[1]) < MAX_MESSAGE_LENGTH // 4:
                sql.set_user_bio(user_id, bio[1])
                message.reply_text("{} 님의 Bio 을(를) 업데이트했어요!".format(repl_message.from_user.first_name))
            else:
                message.reply_text(
                    "Bio 은(는) {} 자 아래여야 해요! 그러나 당신은 {} 자를 입력했어요.".format(
                        MAX_MESSAGE_LENGTH // 4, len(bio[1])))
    else:
        message.reply_text("답장으로 Bio 을(를) 설정하려는 사용자를 알려주세요!")


def __user_info__(user_id):
    bio = html.escape(sql.get_user_bio(user_id) or "")
    me = html.escape(sql.get_user_me_info(user_id) or "")
    if bio and me:
        return "<b>유저에 관한 메시지(me):</b>\n{me}\n<b>다른사람이 유저에게 한 메시지(Bio):</b>\n{bio}".format(me=me, bio=bio)
    elif bio:
        return "<b>다른사람이 유저에게 한 메시지(Bio):</b>\n{bio}\n".format(me=me, bio=bio)
    elif me:
        return "<b>유저에 관한 메시지(me):</b>\n{me}".format(me=me, bio=bio)
    else:
        return ""


def __gdpr__(user_id):
    sql.clear_user_info(user_id)
    sql.clear_user_bio(user_id)


__help__ = """
 - /setbio <text>: 답장을 통해 다른 사용자의 Bio 을(를) 저장할 수 있어요.
 - /bio: 자신 혹은 다른 사용자의 Bio 을(를) 볼 수 있습니다. Bio 은(는) 혼자 설정할 수 없어요.
 - /setme <text>: 자신의 me 을(를) 설정할 수 있어요.
 - /me: 자신 혹은 다른 사용자의 me 을(를) 볼 수 있어요.
"""

__mod_name__ = "Bios and Abouts"

SET_BIO_HANDLER = DisableAbleCommandHandler("setbio", set_about_bio)
GET_BIO_HANDLER = DisableAbleCommandHandler("bio", about_bio, pass_args=True)

SET_ABOUT_HANDLER = DisableAbleCommandHandler("setme", set_about_me)
GET_ABOUT_HANDLER = DisableAbleCommandHandler("me", about_me, pass_args=True)

dispatcher.add_handler(SET_BIO_HANDLER)
dispatcher.add_handler(GET_BIO_HANDLER)
dispatcher.add_handler(SET_ABOUT_HANDLER)
dispatcher.add_handler(GET_ABOUT_HANDLER)
