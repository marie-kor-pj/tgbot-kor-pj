import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher, LOGGER
from tg_bot.modules.helper_funcs.chat_status import user_admin, can_delete
from tg_bot.modules.log_channel import loggable


@run_async
@user_admin
@loggable
def purge(bot: Bot, update: Update, args: List[str]) -> str:
    msg = update.effective_message  # type: Optional[Message]
    if msg.reply_to_message:
        user = update.effective_user  # type: Optional[User]
        chat = update.effective_chat  # type: Optional[Chat]
        if can_delete(chat, bot.id):
            message_id = msg.reply_to_message.message_id
            delete_to = msg.message_id - 1
            if args and args[0].isdigit():
                new_del = message_id + int(args[0])
                # No point deleting messages which haven't been written yet.
                if new_del < delete_to:
                    delete_to = new_del
            for m_id in range(delete_to, message_id - 1, -1):  # Reverse iteration over message ids
                try:
                    bot.deleteMessage(chat.id, m_id)
                except BadRequest as err:
                    if err.message == "Message can't be deleted":
                        bot.send_message(chat.id, "모든 메시지들을 제거할 수 없어요. 그 메시지들은 너무 오래되었어요. "
                                                  "저에게 삭제 권한이 없거나 슈퍼 그룹이 아닐 수 있어요.")

                    elif err.message != "Message to delete not found":
                        LOGGER.exception("채팅 메시지를 삭제하는 동안 오류가 발생했어요.")

            try:
                msg.delete()
            except BadRequest as err:
                if err.message == "Message can't be deleted":
                    bot.send_message(chat.id, "모든 메시지들을 제거할 수 없어요. 그 메시지들은 너무 오래되었어요. "
                                              "제게 삭제 권한이 없거나 슈퍼 그룹이 아닐 수 있어요.")

                elif err.message != "Message to delete not found":
                    LOGGER.exception("채팅 메시지를 삭제하는 동안 오류가 발생했어요.")

            bot.send_message(chat.id, "완벽하게 제거했어요!")
            return "<b>{}:</b>" \
                   "\n#메시지_대량_제거" \
                   "\n<b>관리자:</b> {}" \
                   "\n<code>{}</code>개의 메시지들이 대량으로 제거되었어요.".format(html.escape(chat.title),
                                                               mention_html(user.id, user.first_name),
                                                               delete_to - message_id)

    else:
        msg.reply_text("답장 기능으로 삭제를 시작할 위치를 선택해 주세요.")

    return ""


@run_async
@user_admin
@loggable
def del_message(bot: Bot, update: Update) -> str:
    if update.effective_message.reply_to_message:
        user = update.effective_user  # type: Optional[User]
        chat = update.effective_chat  # type: Optional[Chat]
        if can_delete(chat, bot.id):
            update.effective_message.reply_to_message.delete()
            update.effective_message.delete()
            return "<b>{}:</b>" \
                   "\n#메시지_제거" \
                   "\n<b>관리자:</b> {}" \
                   "\n메시지 제거.".format(html.escape(chat.title),
                                               mention_html(user.id, user.first_name))
    else:
        update.effective_message.reply_text("어떤 메시지를 삭제하고 싶나요?")

    return ""


__help__ = """
*관리자용 명령어*
 - /del: 답장한 메시지를 제거해요.
 - /purge: 이 메시지와 답장한 메시지 사이의 모든 메시지를 삭제해요.
 - /purge <정수>: 답장한 메시지로부터 정수만큼의 상위 메시지가 삭제돼요
"""

__mod_name__ = "메시지 제거"

DELETE_HANDLER = CommandHandler("del", del_message, filters=Filters.group)
PURGE_HANDLER = CommandHandler("purge", purge, filters=Filters.group, pass_args=True)

dispatcher.add_handler(DELETE_HANDLER)
dispatcher.add_handler(PURGE_HANDLER)
