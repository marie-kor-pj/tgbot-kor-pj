import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram import ParseMode, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import MessageHandler, Filters, CommandHandler, run_async
from telegram.utils.helpers import mention_markdown, mention_html, escape_markdown

import tg_bot.modules.sql.welcome_sql as sql
from tg_bot import dispatcher, OWNER_ID, LOGGER
from tg_bot.modules.helper_funcs.chat_status import user_admin
from tg_bot.modules.helper_funcs.misc import build_keyboard, revert_buttons
from tg_bot.modules.helper_funcs.msg_types import get_welcome_type
from tg_bot.modules.helper_funcs.string_handling import markdown_parser, \
    escape_invalid_curly_brackets
from tg_bot.modules.log_channel import loggable

VALID_WELCOME_FORMATTERS = ['first', 'last', 'fullname', 'username', 'id', 'count', 'chatname', 'mention']

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


# do not async
def send(update, message, keyboard, backup_message):
    try:
        msg = update.effective_message.reply_text(message, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    except IndexError:
        msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                  "\n메모: 현재 메시지가 표시 문제로 인해 "
                                                                  "유효하지 않습니다. 사용자 "
                                                                  "이름 때문일 수 있어요."),
                                                  parse_mode=ParseMode.MARKDOWN)
    except KeyError:
        msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                  "\n메모: 중괄호가 잘못 배치되어 현재 메시지가 "
                                                                  "유효하지 않아요. "
                                                                  "업데이트하세요"),
                                                  parse_mode=ParseMode.MARKDOWN)
    except BadRequest as excp:
        if excp.message == "Button_url_invalid":
            msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                      "\n메모: 현재 메시지의 버튼 중 하나에 잘못된 URL 이 "
                                                                      "있어요. 업데이트하세요."),
                                                      parse_mode=ParseMode.MARKDOWN)
        elif excp.message == "Unsupported url protocol":
            msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                      "\n메모: 현재 메시지에는 Telegram 에서 지원하지 "
                                                                      "않는 URL 프로토콜을 사용하는 버튼이 "
                                                                      "있어요. 업데이트하세요."),
                                                      parse_mode=ParseMode.MARKDOWN)
        elif excp.message == "Wrong url host":
            msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                      "\n메모: 현재 메시지에 잘못된 URL 들이 있어요. "
                                                                      "업데이트하세요."),
                                                      parse_mode=ParseMode.MARKDOWN)
            LOGGER.warning(message)
            LOGGER.warning(keyboard)
            LOGGER.exception("구문을 분석할 수 없어요! 잘못된 URL 호스트 오류가 발생했어요.")
        else:
            msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                      "\n메모: 사용자 지정 메시지를 보낼 때 오류가 발생했어요. "
                                                                      "업데이트하세요."),
                                                      parse_mode=ParseMode.MARKDOWN)
            LOGGER.exception()

    return msg


@run_async
def new_member(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]

    should_welc, cust_welcome, welc_type = sql.get_welc_pref(chat.id)
    if should_welc:
        sent = None
        new_members = update.effective_message.new_chat_members
        for new_mem in new_members:
            # Give the owner a special welcome
            if new_mem.id == OWNER_ID:
                update.effective_message.reply_text("관리자는 집에 있어요, 파티를 시작해요!")
                continue

            # Don't welcome yourself
            elif new_mem.id == bot.id:
                continue

            else:
                # If welcome message is media, send with appropriate function
                if welc_type != sql.Types.TEXT and welc_type != sql.Types.BUTTON_TEXT:
                    ENUM_FUNC_MAP[welc_type](chat.id, cust_welcome)
                    return
                # else, move on
                first_name = new_mem.first_name or "PersonWithNoName"  # edge case of empty name - occurs for some bugs.

                if cust_welcome:
                    if new_mem.last_name:
                        fullname = "{} {}".format(first_name, new_mem.last_name)
                    else:
                        fullname = first_name
                    count = chat.get_members_count()
                    mention = mention_markdown(new_mem.id, first_name)
                    if new_mem.username:
                        username = "@" + escape_markdown(new_mem.username)
                    else:
                        username = mention

                    valid_format = escape_invalid_curly_brackets(cust_welcome, VALID_WELCOME_FORMATTERS)
                    res = valid_format.format(first=escape_markdown(first_name),
                                              last=escape_markdown(new_mem.last_name or first_name),
                                              fullname=escape_markdown(fullname), username=username, mention=mention,
                                              count=count, chatname=escape_markdown(chat.title), id=new_mem.id)
                    buttons = sql.get_welc_buttons(chat.id)
                    keyb = build_keyboard(buttons)
                else:
                    res = sql.DEFAULT_WELCOME.format(first=first_name)
                    keyb = []

                keyboard = InlineKeyboardMarkup(keyb)

                sent = send(update, res, keyboard,
                            sql.DEFAULT_WELCOME.format(first=first_name))  # type: Optional[Message]

        prev_welc = sql.get_clean_pref(chat.id)
        if prev_welc:
            try:
                bot.delete_message(chat.id, prev_welc)
            except BadRequest as excp:
                pass

            if sent:
                sql.set_clean_welcome(chat.id, sent.message_id)


@run_async
def left_member(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    should_goodbye, cust_goodbye, goodbye_type = sql.get_gdbye_pref(chat.id)
    if should_goodbye:
        left_mem = update.effective_message.left_chat_member
        if left_mem:
            # Ignore bot being kicked
            if left_mem.id == bot.id:
                return

            # Give the owner a special goodbye
            if left_mem.id == OWNER_ID:
                update.effective_message.reply_text("주인님 강퇴...ㅠㅠ")
                return

            # if media goodbye, use appropriate function for it
            if goodbye_type != sql.Types.TEXT and goodbye_type != sql.Types.BUTTON_TEXT:
                ENUM_FUNC_MAP[goodbye_type](chat.id, cust_goodbye)
                return

            first_name = left_mem.first_name or "PersonWithNoName"  # edge case of empty name - occurs for some bugs.
            if cust_goodbye:
                if left_mem.last_name:
                    fullname = "{} {}".format(first_name, left_mem.last_name)
                else:
                    fullname = first_name
                count = chat.get_members_count()
                mention = mention_markdown(left_mem.id, first_name)
                if left_mem.username:
                    username = "@" + escape_markdown(left_mem.username)
                else:
                    username = mention

                valid_format = escape_invalid_curly_brackets(cust_goodbye, VALID_WELCOME_FORMATTERS)
                res = valid_format.format(first=escape_markdown(first_name),
                                          last=escape_markdown(left_mem.last_name or first_name),
                                          fullname=escape_markdown(fullname), username=username, mention=mention,
                                          count=count, chatname=escape_markdown(chat.title), id=left_mem.id)
                buttons = sql.get_gdbye_buttons(chat.id)
                keyb = build_keyboard(buttons)

            else:
                res = sql.DEFAULT_GOODBYE
                keyb = []

            keyboard = InlineKeyboardMarkup(keyb)

            send(update, res, keyboard, sql.DEFAULT_GOODBYE)


@run_async
@user_admin
def welcome(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    # if no args, show current replies.
    if len(args) == 0 or args[0].lower() == "noformat":
        noformat = args and args[0].lower() == "noformat"
        pref, welcome_m, welcome_type = sql.get_welc_pref(chat.id)
        update.effective_message.reply_text(
            "이 방의 환영인사 메시지는 다음과 같이 설정되어 있어요: `{}`\n*환영인사 메시지"
            "(not filling the {{}}) :*".format(pref),
            parse_mode=ParseMode.MARKDOWN)

        if welcome_type == sql.Types.BUTTON_TEXT:
            buttons = sql.get_welc_buttons(chat.id)
            if noformat:
                welcome_m += revert_buttons(buttons)
                update.effective_message.reply_text(welcome_m)

            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                send(update, welcome_m, keyboard, sql.DEFAULT_WELCOME)

        else:
            if noformat:
                ENUM_FUNC_MAP[welcome_type](chat.id, welcome_m)

            else:
                ENUM_FUNC_MAP[welcome_type](chat.id, welcome_m, parse_mode=ParseMode.MARKDOWN)

    elif len(args) >= 1:
        if args[0].lower() in ("on", "yes"):
            sql.set_welc_preference(str(chat.id), True)
            update.effective_message.reply_text("저는 앞으로 예의 발라질게요!")

        elif args[0].lower() in ("off", "no"):
            sql.set_welc_preference(str(chat.id), False)
            update.effective_message.reply_text("더 이상 환영인사를 안 할 꺼예요! 흥!")

        else:
            # idek what you're writing, say yes or no
            update.effective_message.reply_text("전 'on/yes' 또는 'off/no'만 이해해요!")


@run_async
@user_admin
def goodbye(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]

    if len(args) == 0 or args[0] == "noformat":
        noformat = args and args[0] == "noformat"
        pref, goodbye_m, goodbye_type = sql.get_gdbye_pref(chat.id)
        update.effective_message.reply_text(
            "이 방의 작별인사 메시지는 다음과 같이 설정되어 있어요: `{}`.\n*작별인사 메시지"
            "(not filling the {{}}) :*".format(pref),
            parse_mode=ParseMode.MARKDOWN)

        if goodbye_type == sql.Types.BUTTON_TEXT:
            buttons = sql.get_gdbye_buttons(chat.id)
            if noformat:
                goodbye_m += revert_buttons(buttons)
                update.effective_message.reply_text(goodbye_m)

            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                send(update, goodbye_m, keyboard, sql.DEFAULT_GOODBYE)

        else:
            if noformat:
                ENUM_FUNC_MAP[goodbye_type](chat.id, goodbye_m)

            else:
                ENUM_FUNC_MAP[goodbye_type](chat.id, goodbye_m, parse_mode=ParseMode.MARKDOWN)

    elif len(args) >= 1:
        if args[0].lower() in ("on", "yes"):
            sql.set_gdbye_preference(str(chat.id), True)
            update.effective_message.reply_text("사람들이 떠났다면 미안해요!")

        elif args[0].lower() in ("off", "no"):
            sql.set_gdbye_preference(str(chat.id), False)
            update.effective_message.reply_text("그들이 떠난다면 저에게 죽을 거예요.")

        else:
            # idek what you're writing, say yes or no
            update.effective_message.reply_text("전 'on/yes' 또는 'off/no'만 이해할 수 있어요!")


@run_async
@user_admin
@loggable
def set_welcome(bot: Bot, update: Update) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]

    text, data_type, content, buttons = get_welcome_type(msg)

    if data_type is None:
        msg.reply_text("답장할 대상을 지정하지 않았어요!")
        return ""

    sql.set_custom_welcome(chat.id, content or text, data_type, buttons)
    msg.reply_text("성공적으로 환영인사 메시지를 설정했어요!")

    return "<b>{}:</b>" \
           "\n#환영인사_메시지_설정" \
           "\n<b>관리자:</b> {}" \
           "\n환영인사 메시지를 설정했어요.".format(html.escape(chat.title),
                                               mention_html(user.id, user.first_name))


@run_async
@user_admin
@loggable
def reset_welcome(bot: Bot, update: Update) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    sql.set_custom_welcome(chat.id, sql.DEFAULT_WELCOME, sql.Types.TEXT)
    update.effective_message.reply_text("환영인사 메시지를 기본값으로 재설정했어요!")
    return "<b>{}:</b>" \
           "\n#환영인사_메시지_초기화" \
           "\n<b>관리자:</b> {}" \
           "\n환영인사 메시지를 초기화했어요.".format(html.escape(chat.title),
                                                            mention_html(user.id, user.first_name))


@run_async
@user_admin
@loggable
def set_goodbye(bot: Bot, update: Update) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    text, data_type, content, buttons = get_welcome_type(msg)

    if data_type is None:
        msg.reply_text("답장할 대상을 지정하지 않았어요!")
        return ""

    sql.set_custom_gdbye(chat.id, content or text, data_type, buttons)
    msg.reply_text("성공적으로 작별인사 메시지를 설정했어요!")
    return "<b>{}:</b>" \
           "\n#작별인사_메시지_설정" \
           "\n<b>관리자:</b> {}" \
           "\n작별인사 메시지를 설정했어요.".format(html.escape(chat.title),
                                               mention_html(user.id, user.first_name))


@run_async
@user_admin
@loggable
def reset_goodbye(bot: Bot, update: Update) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    sql.set_custom_gdbye(chat.id, sql.DEFAULT_GOODBYE, sql.Types.TEXT)
    update.effective_message.reply_text("성공적으로 작별인사 메시지를 기본값으로 초기화했어요!")
    return "<b>{}:</b>" \
           "\n#작별인사_메시지_초기화" \
           "\n<b>관리자:</b> {}" \
           "\n작별인사 메시지를 초기화했어요.".format(html.escape(chat.title),
                                                 mention_html(user.id, user.first_name))


@run_async
@user_admin
@loggable
def clean_welcome(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    if not args:
        clean_pref = sql.get_clean_pref(chat.id)
        if clean_pref:
            update.effective_message.reply_text("최대 이틀 전에 환영 메시지를 삭제해야 해요.")
        else:
            update.effective_message.reply_text("저는 지금 오래된 환영 메시지를 삭제하고 있지 않아요!")
        return ""

    if args[0].lower() in ("on", "yes"):
        sql.set_clean_welcome(str(chat.id), True)
        update.effective_message.reply_text("오래된 환영 메시지를 삭제할게요!")
        return "<b>{}:</b>" \
               "\n#오래된_환영인사_메시지_제거_여부" \
               "\n<b>관리자:</b> {}" \
               "\n환영 메시지 삭제가 <code>켜졌어요</code>.".format(html.escape(chat.title),
                                                                         mention_html(user.id, user.first_name))
    elif args[0].lower() in ("off", "no"):
        sql.set_clean_welcome(str(chat.id), False)
        update.effective_message.reply_text("너무 오래된 환영인사 메시지는 삭제하지 못해요.")
        return "<b>{}:</b>" \
               "\n#오래된_환영인사_메시지_제거_여부" \
               "\n<b>관리자:</b> {}" \
               "\n환영 메시지 삭제가 <code>꺼졌어요</code>.".format(html.escape(chat.title),
                                                                          mention_html(user.id, user.first_name))
    else:
        # idek what you're writing, say yes or no
        update.effective_message.reply_text("저는 'on/yes' 나 'off/no' 만 알아들어요!")
        return ""


WELC_HELP_TXT = "그룹의 환영인사/작별인사 메시지는 여러 가지 방법으로 바꿀 수 있어요. 만약 당신이 사람마다 다른" \
                " 환영 메시지를 원하신다면, 당신은 *이러한* 변수들을 사용하실 수 있어요:\n" \
                " - `{{first}}`: 사용자의 *이름* 을 말해줘요.\n" \
                " - `{{last}}`: 사용자의 *성* 을 말해줘요. 만약 사용자가 성을 설정하지 않으면 *이름*으로 " \
                "말해줘요.\n" \
                " - `{{fullname}}`: 이것은 사용자의 *전체* 이름을 말해줘요. 만약 사용자가 성을 설정하지 않으면 *이름*으로 " \
                "말해줘요.\n" \
                " - `{{username}}`: 이것은 사용자의 *사용자명* 을 말해줘요. 사용자명을 설정하지 않으면, 사용자의 이름으로 " \
                "말해줘요.\n" \
                " - `{{mention}}`: 그들의 이름으로 태그를 붙여서 간단히 사용자를 *언급* 해요.\n" \
                " - `{{id}}`: 사용자의 id를 말해줘요.\n" \
                " - `{{count}}`: 이것은 사용자의 *회원번호*를 말해줘요.\n" \
                " - `{{chatname}}`: 이것은 *현재 채팅방 이름* 을 말해줘요.\n" \
                "\n교체하려면 각 변수를 `{{}}` 로 둘러싸야해요.\n" \
                "환영인사 메시지 또한 마크다운을 지원하므로 모든 요소를 굵은 글씨/이탤릭체/코드/링크로 만들 수 있어요. " \
                "버튼도 지원되므로 멋진 소개 버튼을 사용하여 환영인사를 멋지게 연출할 수 " \
                "있어요.\n" \
                "규칙에 연결하는 단추를 만들려면 다음을 사용해요.: `[Rules](buttonurl://t.me/{}?start=group_id)`. " \
                "`group_id` 를  /id를 통해 얻을 수 있는 그룹 ID로 바꾸기만 하면 돼요. " \
                "그룹 ID에는 일반적으로 `-` 기호가 선행돼요; 이 기호는 필수이므로 " \
                "제거하지 마세요.\n" \
                "재미있다면 원하는 미디어에 회신하고 /setwelcome 을 눌러 이미지/gif/비디오/음성 메시지를 " \
                "환영 메시지로 설정할 수도 있어요.".format(dispatcher.bot.username)


@run_async
@user_admin
def welcome_help(bot: Bot, update: Update):
    update.effective_message.reply_text(WELC_HELP_TXT, parse_mode=ParseMode.MARKDOWN)


# TODO: get welcome data from group butler snap
# def __import_data__(chat_id, data):
#     welcome = data.get('info', {}).get('rules')
#     welcome = welcome.replace('$username', '{username}')
#     welcome = welcome.replace('$name', '{fullname}')
#     welcome = welcome.replace('$id', '{id}')
#     welcome = welcome.replace('$title', '{chatname}')
#     welcome = welcome.replace('$surname', '{lastname}')
#     welcome = welcome.replace('$rules', '{rules}')
#     sql.set_custom_welcome(chat_id, welcome, sql.Types.TEXT)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    welcome_pref, _, _ = sql.get_welc_pref(chat_id)
    goodbye_pref, _, _ = sql.get_gdbye_pref(chat_id)
    return "이 채팅의 환영인사 설정은 `{}` (으)로 설정되어 있어요.\n" \
           "작별인사 설정은 `{}` 입니다.".format(welcome_pref, goodbye_pref)


__help__ = """
{}

*관리자용 명령어*
 - /welcome <on/off>: 환영인사 메시지를 활성화 또는 비활성화해요.
 - /welcome: 현재 환영인사 메시지를 알려줘요.
 - /welcome noformat: 포맷 없이 현재 환영 설정을 보여줘요 - 환영 메시지를 다시 사용하는데 유용해요!
 - /goodbye -> /welcome 과 동일하게 사용돼요.
 - /setwelcome <환영하는 말>: 환영 인사를 설정해요. 만약 미디어를 답장하시면, 그 미디어가 환영인사로 사용돼요.
 - /setgoodbye <작별하는 말>: 작별 인사를 설정해요. 만약 미디어를 답장하시면, 그 미디어가 작별인사로 사용돼요.
 - /resetwelcome: 환영인사가 기본값으로 재설정돼요.
 - /resetgoodbye: 작별인사가 기본값으로 재설정돼요.
 - /cleanwelcome <on/off>: 새 멤버가 오면, 이전 환영 메시지를 삭제하여 스팸문자를 방지해요.
 - /welcomehelp: 커스텀 환영인사/작별인사 메시지에 대한 자세한 형식 정보를 봐요.
""".format(WELC_HELP_TXT)

__mod_name__ = "환영인사/작별인사"

NEW_MEM_HANDLER = MessageHandler(Filters.status_update.new_chat_members, new_member)
LEFT_MEM_HANDLER = MessageHandler(Filters.status_update.left_chat_member, left_member)
WELC_PREF_HANDLER = CommandHandler("welcome", welcome, pass_args=True, filters=Filters.group)
GOODBYE_PREF_HANDLER = CommandHandler("goodbye", goodbye, pass_args=True, filters=Filters.group)
SET_WELCOME = CommandHandler("setwelcome", set_welcome, filters=Filters.group)
SET_GOODBYE = CommandHandler("setgoodbye", set_goodbye, filters=Filters.group)
RESET_WELCOME = CommandHandler("resetwelcome", reset_welcome, filters=Filters.group)
RESET_GOODBYE = CommandHandler("resetgoodbye", reset_goodbye, filters=Filters.group)
CLEAN_WELCOME = CommandHandler("cleanwelcome", clean_welcome, pass_args=True, filters=Filters.group)
WELCOME_HELP = CommandHandler("welcomehelp", welcome_help)

dispatcher.add_handler(NEW_MEM_HANDLER)
dispatcher.add_handler(LEFT_MEM_HANDLER)
dispatcher.add_handler(WELC_PREF_HANDLER)
dispatcher.add_handler(GOODBYE_PREF_HANDLER)
dispatcher.add_handler(SET_WELCOME)
dispatcher.add_handler(SET_GOODBYE)
dispatcher.add_handler(RESET_WELCOME)
dispatcher.add_handler(RESET_GOODBYE)
dispatcher.add_handler(CLEAN_WELCOME)
dispatcher.add_handler(WELCOME_HELP)
