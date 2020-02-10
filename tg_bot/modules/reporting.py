import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User, ParseMode
from telegram.error import BadRequest, Unauthorized
from telegram.ext import CommandHandler, RegexHandler, run_async, Filters
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher, LOGGER
from tg_bot.modules.helper_funcs.chat_status import user_not_admin, user_admin
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.sql import reporting_sql as sql

REPORT_GROUP = 5


@run_async
@user_admin
def report_setting(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]

    if chat.type == chat.PRIVATE:
        if len(args) >= 1:
            if args[0] in ("yes", "on"):
                sql.set_user_setting(chat.id, True)
                msg.reply_text("채팅방 관리자에게 신고 기능을 켰어요! 관리자들은 누군가 /report 명령어를 쓰는 즉시 알림이 뜰 거예요!")

            elif args[0] in ("no", "off"):
                sql.set_user_setting(chat.id, False)
                msg.reply_text("채팅방 관리자에게 신고 기능을 껐어요! 당신은 아무것도 보고할 수 없어요.")
        else:
            msg.reply_text("현재 당신의 채팅방 관리자에게 신고 기능 설정 : `{}`".format(sql.user_should_report(chat.id)),
                           parse_mode=ParseMode.MARKDOWN)

    else:
        if len(args) >= 1:
            if args[0] in ("yes", "on"):
                sql.set_chat_setting(chat.id, True)
                msg.reply_text("채팅방 관리자에게 신고 기능을 켰어요! 관리자들은 누군가 /report 명령어를 쓰는 즉시 알림이 뜰 거예요!")

            elif args[0] in ("no", "off"):
                sql.set_chat_setting(chat.id, False)
                msg.reply_text("채팅방 관리자에게 신고 기능을 껐어요! 당신은 아무것도 신고할 수 없어요.")
        else:
            msg.reply_text("현재 당신의 채팅방 관리자에게 신고 기능 설정 : `{}`".format(sql.chat_should_report(chat.id)),
                           parse_mode=ParseMode.MARKDOWN)


@run_async
@user_not_admin
@loggable
def report(bot: Bot, update: Update) -> str:
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    if chat and message.reply_to_message and sql.chat_should_report(chat.id):
        reported_user = message.reply_to_message.from_user  # type: Optional[User]
        chat_name = chat.title or chat.first or chat.username
        admin_list = chat.get_administrators()

        if chat.username and chat.type == Chat.SUPERGROUP:
            msg = "<b>{}:</b>" \
                  "\n<b>신고하는 유저:</b> {} (<code>{}</code>)" \
                  "\n<b>신고 대상:</b> {} (<code>{}</code>)".format(html.escape(chat.title),
                                                                      mention_html(
                                                                          reported_user.id,
                                                                          reported_user.first_name),
                                                                      reported_user.id,
                                                                      mention_html(user.id,
                                                                                   user.first_name),
                                                                      user.id)
            link = "\n<b>링크:</b> " \
                   "<a href=\"http://telegram.me/{}/{}\">여기를 누르세요</a>".format(chat.username, message.message_id)

            should_forward = False

        else:
            msg = "{} 이(가) \"{}\" 방의 관리자에게 말해요!".format(mention_html(user.id, user.first_name),
                                                               html.escape(chat_name))
            link = ""
            should_forward = True

        for admin in admin_list:
            if admin.user.is_bot:  # can't message bots
                continue

            if sql.user_should_report(admin.user.id):
                try:
                    bot.send_message(admin.user.id, msg + link, parse_mode=ParseMode.HTML)

                    if should_forward:
                        message.reply_to_message.forward(admin.user.id)

                        if len(message.text.split()) > 1:  # If user is giving a reason, send his message too
                            message.forward(admin.user.id)

                except Unauthorized:
                    pass
                except BadRequest as excp:  # TODO: cleanup exceptions
                    LOGGER.exception("사용자를 채팅방 관리자에게 신고하는 동안 예외 발생.")
        return msg

    return ""


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return "이 채팅은 /report 와 @admin 으로 사용자 보고서를 관리자에게 전송하도록 설정돼있어요 `{}`".format(
        sql.chat_should_report(chat_id))


def __user_settings__(user_id):
    return "당신이 관리자인 채팅으로부터 신고를 받아요: `{}`.\n개인 채팅에서 /reports 로 전환하실 수 있어요.".format(
        sql.user_should_report(user_id))


__mod_name__ = "채팅방 관리자에게 신고"

__help__ = """
 - /report <이유>: 메시지를 답장하면 채팅방 관리자에게 신고할 수 있어요.
 - @admin: /report 와 같이 메시지를 답장하면 채팅방 관리자에게 신고할 수 있어요.
참고: 관리자들은 위 명령어를 사용하실 수 없으시고, 일반 유저만 위 명령어를 사용하실 수 있어요.

*관리자용 명령어*
 - /reports <on/off>: 채팅방 관리자에게 신고 기능의 설정을 변경하거나 현재 상태를 봐요.
   - 개인 메시지가 완료되면, 상태를 전환해요.
   - 채팅 중이면 해당 채팅의 상태를 전환해요.
"""

REPORT_HANDLER = CommandHandler("report", report, filters=Filters.group)
SETTING_HANDLER = CommandHandler("reports", report_setting, pass_args=True)
ADMIN_REPORT_HANDLER = RegexHandler("(?i)@admin(s)?", report)

dispatcher.add_handler(REPORT_HANDLER, REPORT_GROUP)
dispatcher.add_handler(ADMIN_REPORT_HANDLER, REPORT_GROUP)
dispatcher.add_handler(SETTING_HANDLER)
