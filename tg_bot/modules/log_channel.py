from functools import wraps
from typing import Optional

from tg_bot.modules.helper_funcs.misc import is_module_loaded

FILENAME = __name__.rsplit(".", 1)[-1]

if is_module_loaded(FILENAME):
    from telegram import Bot, Update, ParseMode, Message, Chat
    from telegram.error import BadRequest, Unauthorized
    from telegram.ext import CommandHandler, run_async
    from telegram.utils.helpers import escape_markdown

    from tg_bot import dispatcher, LOGGER
    from tg_bot.modules.helper_funcs.chat_status import user_admin
    from tg_bot.modules.sql import log_channel_sql as sql


    def loggable(func):
        @wraps(func)
        def log_action(bot: Bot, update: Update, *args, **kwargs):
            result = func(bot, update, *args, **kwargs)
            chat = update.effective_chat  # type: Optional[Chat]
            message = update.effective_message  # type: Optional[Message]
            if result:
                if chat.type == chat.SUPERGROUP and chat.username:
                    result += "\n<b>링크:</b> " \
                              "<a href=\"http://telegram.me/{}/{}\">여기를 눌러주세요.</a>".format(chat.username,
                                                                                           message.message_id)
                log_chat = sql.get_chat_log_channel(chat.id)
                if log_chat:
                    send_log(bot, log_chat, chat.id, result)
            elif result == "":
                pass
            else:
                LOGGER.warning("%s 로그가 가능하도록 되어있지만 반환 문장이 없어요.", func)

            return result

        return log_action


    def send_log(bot: Bot, log_chat_id: str, orig_chat_id: str, result: str):
        try:
            bot.send_message(log_chat_id, result, parse_mode=ParseMode.HTML)
        except BadRequest as excp:
            if excp.message == "Chat not found":
                bot.send_message(orig_chat_id, "이 로그 채널이 삭제되었어요 - 설정되지 않음")
                sql.stop_chat_logging(orig_chat_id)
            else:
                LOGGER.warning(excp.message)
                LOGGER.warning(result)
                LOGGER.exception("Could not parse")

                bot.send_message(log_chat_id, result + "\n\n예기치 않은 오류로 인해 포맷이 비활성화되었어요.")


    @run_async
    @user_admin
    def logging(bot: Bot, update: Update):
        message = update.effective_message  # type: Optional[Message]
        chat = update.effective_chat  # type: Optional[Chat]

        log_channel = sql.get_chat_log_channel(chat.id)
        if log_channel:
            log_channel_info = bot.get_chat(log_channel)
            message.reply_text(
                "해당 그룹으로부터 전송된 모든 로그가 여기에 있어요 : {} (`{}`)".format(escape_markdown(log_channel_info.title),
                                                                         log_channel),
                parse_mode=ParseMode.MARKDOWN)

        else:
            message.reply_text("이 그룹에 대해 설정된 로그 채널이 없어요!")


    @run_async
    @user_admin
    def setlog(bot: Bot, update: Update):
        message = update.effective_message  # type: Optional[Message]
        chat = update.effective_chat  # type: Optional[Chat]
        if chat.type == chat.CHANNEL:
            message.reply_text("이제, 이 채널을 연결할 그룹으로 /setlog 를 전달해주세요!")

        elif message.forward_from_chat:
            sql.set_chat_log_channel(chat.id, message.forward_from_chat.id)
            try:
                message.delete()
            except BadRequest as excp:
                if excp.message == "Message to delete not found":
                    pass
                else:
                    LOGGER.exception("로그 채널에서 메시지를 삭제하는 동안 오류가 발생했어요. 어쨌든 잘 될 거예요.")

            try:
                bot.send_message(message.forward_from_chat.id,
                                 "{} 채널이 로그 채널로 설정되었어요.".format(
                                     chat.title or chat.first_name))
            except Unauthorized as excp:
                if excp.message == "Forbidden: bot is not a member of the channel chat":
                    bot.send_message(chat.id, "로그 채널 설정이 완료되었어요!")
                else:
                    LOGGER.exception("로그 채널을 설정하는 데에 오류가 발생했어요!")

            bot.send_message(chat.id, "로그 채널 설정이 완료되었어요!")

        else:
            message.reply_text("로그 채널 설정하는 방법:\n"
                               " - 원하는 채널에 봇을 추가해주세요.\n"
                               " - 채널에 /setlog 를 입력해 주세요\n"
                               " - 로그 채널을 설정하고자 하는 그룹에 채널에서 적었던 /setlog 를 전달해 주세요.\n")


    @run_async
    @user_admin
    def unsetlog(bot: Bot, update: Update):
        message = update.effective_message  # type: Optional[Message]
        chat = update.effective_chat  # type: Optional[Chat]

        log_channel = sql.stop_chat_logging(chat.id)
        if log_channel:
            bot.send_message(log_channel, "채널이 {} 에서 연결이 해제되었어요!".format(chat.title))
            message.reply_text("로그 채널이 해제되었어요.")

        else:
            message.reply_text("로그 채널이 아직 설정되지 않았어요!")


    def __stats__():
        return "{}개의 채팅방에서 로그 채널을 설정했어요.".format(sql.num_logchannels())


    def __migrate__(old_chat_id, new_chat_id):
        sql.migrate_chat(old_chat_id, new_chat_id)


    def __chat_settings__(chat_id, user_id):
        log_channel = sql.get_chat_log_channel(chat_id)
        if log_channel:
            log_channel_info = dispatcher.bot.get_chat(log_channel)
            return "이 그룹에 모든 로그가 전송되었어요 : {} (`{}`)".format(escape_markdown(log_channel_info.title),
                                                                            log_channel)
        return "이 그룹에 설정된 로그 채널이 없어요."


    __help__ = """
*관리자용 명령어*
- /logchannel: 로그 채널 정보를 가져와요.
- /setlog: 로그 채널을 설정해요.
- /unsetlog: 로그 채널을 비활성화해요.

로그 채널 설정하는 방법 :
- 원하는 채널에 봇을 추가해주세요. (봇에게 관리자 권한을 주세요!)
- 채널에 /setlog 을(를) 입력해주세요.
- 로그 채널을 설정하고자 하는 그룹에 채널에서 적었던 /setlog 을(를) 전달해주세요.
"""

    __mod_name__ = "로그 채널"

    LOG_HANDLER = CommandHandler("logchannel", logging)
    SET_LOG_HANDLER = CommandHandler("setlog", setlog)
    UNSET_LOG_HANDLER = CommandHandler("unsetlog", unsetlog)

    dispatcher.add_handler(LOG_HANDLER)
    dispatcher.add_handler(SET_LOG_HANDLER)
    dispatcher.add_handler(UNSET_LOG_HANDLER)

else:
    # run anyway if module not loaded
    def loggable(func):
        return func
