import html
from io import BytesIO
from typing import Optional, List

from telegram import Message, Update, Bot, User, Chat, ParseMode
from telegram.error import BadRequest, TelegramError
from telegram.ext import run_async, CommandHandler, MessageHandler, Filters
from telegram.utils.helpers import mention_html

import tg_bot.modules.sql.global_bans_sql as sql
from tg_bot import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, STRICT_GBAN
from tg_bot.modules.helper_funcs.chat_status import user_admin, is_user_admin
from tg_bot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from tg_bot.modules.helper_funcs.filters import CustomFilters
from tg_bot.modules.helper_funcs.misc import send_to_list
from tg_bot.modules.sql.users_sql import get_all_chats

GBAN_ENFORCE_GROUP = 6

GBAN_ERRORS = {
    "사용자는 채팅방의 관리자예요",
    "채팅을 찾을 수 없어요",
    "대화 구성원을 제한/제한할 권한이 부족해요",
    "참가하지_않은_사용자예요",
    "잘못된_Peer_id",
    "그룹 채팅이 비활성화되었어요",
    "베이직 그룹에서 내보내려면 사용자의 초청자가 되어야 해요",
    "관리자_권한이_필요",
    "베이직 그룹의 소유자만이 그룹 관리자를 내보낼 수 있습니다",
    "Private_채널",
    "채팅방에 없어요"
}

UNGBAN_ERRORS = {
    "사용자는 채팅방의 관리자예요",
    "채팅을 찾을 수 없어요",
    "대화 구성원을 제한/제한할 권한이 부족해요",
    "참가하지 않은 사용자예요",
    "Method 은(는) 슈퍼 그룹 및 채널 채팅에만 사용하실 수 있어요",
    "채팅방에 없어요",
    "Private_채널",
    "관리자_권한이_필요",
    "잘못된_Peer_id",
}


@run_async
def gban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("사용자를 지칭하는 것 같지 않아요.")
        return

    if int(user_id) in SUDO_USERS:
        message.reply_text("전 제 작은 눈으로 관리자 전쟁을 봤어요... 왜 서로 등을 돌리세요?")
        return

    if int(user_id) in SUPPORT_USERS:
        message.reply_text("어머... 누군가가 SUPPORT 유저를 글로벌 밴하려고 하고 있네요!")
        return

    if user_id == bot.id:
        message.reply_text("-_- 저를 GBAN 하려고 한 거예요...? ㅠㅠ")
        return

    try:
        user_chat = bot.get_chat(user_id)
    except BadRequest as excp:
        message.reply_text(excp.message)
        return

    if user_chat.type != 'private':
        message.reply_text("유저가 아니에요!")
        return

    if sql.is_user_gbanned(user_id):
        if not reason:
            message.reply_text("이 사용자는 이미 글로벌 밴 당했어요; 제가 이유를 바꾸긴 할 거지만 당신은 저에게 아무 이유도 알려주지 않았어요!!! ㅠㅠ")
            return

        old_reason = sql.update_gban_reason(user_id, user_chat.username or user_chat.first_name, reason)
        if old_reason:
            message.reply_text("이 유저는 이미 이 이유에 따라 글로벌 밴 당했어요:\n"
                               "<code>{}</code>\n"
                               "제가 가서 새로운 이유로 업데이트했어요!".format(html.escape(old_reason)),
                               parse_mode=ParseMode.HTML)
        else:
            message.reply_text("이 유저는 이미 글로벌 밴 당했지만, 이유를 나타내지 않았어요; 제가 가서 업데이트했어요!")

        return

    message.reply_text("*GBAN 예정이에요! 안녕히가세요!* ;)")

    banner = update.effective_user  # type: Optional[User]
    send_to_list(bot, SUDO_USERS + SUPPORT_USERS,
                 "{} is gbanning user {} "
                 "because:\n{}".format(mention_html(banner.id, banner.first_name),
                                       mention_html(user_chat.id, user_chat.first_name), reason or "No reason given"),
                 html=True)

    sql.gban_user(user_id, user_chat.username or user_chat.first_name, reason)

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            bot.kick_chat_member(chat_id, user_id)
        except BadRequest as excp:
            if excp.message in GBAN_ERRORS:
                pass
            else:
                message.reply_text("다음 이유로 인해 GBAN 할 수 없어요 : {}".format(excp.message))
                send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "다음 이유로 인해 GBAN 할 수 없어요: {}".format(excp.message))
                sql.ungban_user(user_id)
                return
        except TelegramError:
            pass

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "GBAN 완료!")
    message.reply_text("그 사람은 GBAN 되었어요.")


@run_async
def ungban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("사용자를 알려주세요!")
        return

    user_chat = bot.get_chat(user_id)
    if user_chat.type != 'private':
        message.reply_text("사용자가 아니에요!")
        return

    if not sql.is_user_gbanned(user_id):
        message.reply_text("이 사용자는 GBAN 상태가 아니에요!")
        return

    banner = update.effective_user  # type: Optional[User]

    message.reply_text("제가 {} 님에게 글로벌 밴으로부터 기회를 한번 더 드릴게요.".format(user_chat.first_name))

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS,
                 "{} UNBAN 사용자. {}".format(mention_html(banner.id, banner.first_name),
                                                   mention_html(user_chat.id, user_chat.first_name)),
                 html=True)

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            member = bot.get_chat_member(chat_id, user_id)
            if member.status == 'kicked':
                bot.unban_chat_member(chat_id, user_id)

        except BadRequest as excp:
            if excp.message in UNGBAN_ERRORS:
                pass
            else:
                message.reply_text("다음 이유로 인해 BAN 을 해제하실 수 없어요 : {}".format(excp.message))
                bot.send_message(OWNER_ID, "다음 이유로 인해 BAN 을 해제하실 수 없어요 : {}".format(excp.message))
                return
        except TelegramError:
            pass

    sql.ungban_user(user_id)

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "un-gban 완료!")

    message.reply_text("글로벌 밴이 해제되었어요.")


@run_async
def gbanlist(bot: Bot, update: Update):
    banned_users = sql.get_gban_list()

    if not banned_users:
        update.effective_message.reply_text("GBAN 당한 유저가 없어요! 저보다 착하신 것 같네요...")
        return

    banfile = 'Screw these guys.\n'
    for user in banned_users:
        banfile += "[x] {} - {}\n".format(user["name"], user["user_id"])
        if user["reason"]:
            banfile += "Reason: {}\n".format(user["reason"])

    with BytesIO(str.encode(banfile)) as output:
        output.name = "gbanlist.txt"
        update.effective_message.reply_document(document=output, filename="gbanlist.txt",
                                                caption="여기에는 현재 글로벌 밴을 당한 사용자의 목록이 있어요.")


def check_and_ban(update, user_id, should_message=True):
    if sql.is_user_gbanned(user_id):
        update.effective_chat.kick_member(user_id)
        if should_message:
            update.effective_message.reply_text("이 사람은 나쁜 사람이라 여기 있으면 안돼요!")


@run_async
def enforce_gban(bot: Bot, update: Update):
    # Not using @restrict handler to avoid spamming - just ignore if cant gban.
    if sql.does_chat_gban(update.effective_chat.id) and update.effective_chat.get_member(bot.id).can_restrict_members:
        user = update.effective_user  # type: Optional[User]
        chat = update.effective_chat  # type: Optional[Chat]
        msg = update.effective_message  # type: Optional[Message]

        if user and not is_user_admin(chat, user.id):
            check_and_ban(update, user.id)

        if msg.new_chat_members:
            new_members = update.effective_message.new_chat_members
            for mem in new_members:
                check_and_ban(update, mem.id)

        if msg.reply_to_message:
            user = msg.reply_to_message.from_user  # type: Optional[User]
            if user and not is_user_admin(chat, user.id):
                check_and_ban(update, user.id, should_message=False)


@run_async
@user_admin
def gbanstat(bot: Bot, update: Update, args: List[str]):
    if len(args) > 0:
        if args[0].lower() in ["on", "yes"]:
            sql.enable_gbans(update.effective_chat.id)
            update.effective_message.reply_text("이 그룹에서 GBAN을 활성화했어요. 스팸 발송자, 불친절한 사람들 "
                                                "등에서부터 자신을 보호할 수 있어요.")
        elif args[0].lower() in ["off", "no"]:
            sql.disable_gbans(update.effective_chat.id)
            update.effective_message.reply_text("이 그룹에서 글로벌 밴을 비활성화했어요. GBAN이 더 이상 사용자에게 영향을 주지 "
                                                "않아요. 스팸 발송자, 불친절한 사람들로부터 보호받지 못할 거예요!")
    else:
        update.effective_message.reply_text("설정을 주기 위해서 on/off, yes/no!라고 해주세요.\n\n"
                                            "현재는 다음으로 설정되어 있어요: {}\n"
                                            "True 상대이면, 그룹에서 GBAN을 사용하실 수 있어요. "
                                            "False 상대이면, GBAN을 사용하실 수 없고, 스팸 발송자로부터 메시지를 "
                                            "계속 받을 거예요!".format(sql.does_chat_gban(update.effective_chat.id)))


def __stats__():
    return "{}명이 글로벌 밴 당했어요.".format(sql.num_gbanned_users())


def __user_info__(user_id):
    is_gbanned = sql.is_user_gbanned(user_id)

    text = "글로벌 밴 : <b>{}</b>"
    if is_gbanned:
        text = text.format("Yes")
        user = sql.get_gbanned_user(user_id)
        if user.reason:
            text += "\n이유: {}".format(html.escape(user.reason))
    else:
        text = text.format("No")
    return text


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return "이 채팅방은 *gbans*을(를) 시행하고 있어요: `{}`.".format(sql.does_chat_gban(chat_id))


__help__ = """
*관리자용 명령어*
 - /gbanstat <on/off/yes/no>: 글로벌 밴을 활성화 하거나 비활성화해요.

전 세계 사용자를 금지시킬 수 있는 Gbans 는 모든 그룹의 스팸메일을 금지하기 위해 저를 만드신 분에 의해 사용돼요. \
그래서 스팸 발송자를 최대한 빨리 제거하여 사용자와 그룹을 보호할 수 있는 기능이에요. 만약 GBAN 을 사용하고 싶지 않으신 분은 \
/gbanstat 명령어를 통해 GBAN 을 비활성화하실 수 있어요!
"""

__mod_name__ = "글로벌 밴"

GBAN_HANDLER = CommandHandler("gban", gban, pass_args=True,
                              filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
UNGBAN_HANDLER = CommandHandler("ungban", ungban, pass_args=True,
                                filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
GBAN_LIST = CommandHandler("gbanlist", gbanlist,
                           filters=CustomFilters.sudo_filter | CustomFilters.support_filter)

GBAN_STATUS = CommandHandler("gbanstat", gbanstat, pass_args=True, filters=Filters.group)

GBAN_ENFORCER = MessageHandler(Filters.all & Filters.group, enforce_gban)

dispatcher.add_handler(GBAN_HANDLER)
dispatcher.add_handler(UNGBAN_HANDLER)
dispatcher.add_handler(GBAN_LIST)
dispatcher.add_handler(GBAN_STATUS)

if STRICT_GBAN:  # enforce GBANS if this is set
    dispatcher.add_handler(GBAN_ENFORCER, GBAN_ENFORCE_GROUP)
