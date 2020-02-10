import json
from io import BytesIO
from typing import Optional

from telegram import Message, Chat, Update, Bot
from telegram.error import BadRequest
from telegram.ext import CommandHandler, run_async

from tg_bot import dispatcher, LOGGER
from tg_bot.__main__ import DATA_IMPORT
from tg_bot.modules.helper_funcs.chat_status import user_admin


@run_async
@user_admin
def import_data(bot: Bot, update):
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    # TODO: 답장뿐만 아니라 명령으로 문서 업로드 허용
    # 문서 작업만!
    if msg.reply_to_message and msg.reply_to_message.document:
        try:
            file_info = bot.get_file(msg.reply_to_message.document.file_id)
        except BadRequest:
            msg.reply_text("가져오기 전에 파일을 다운로드하여 자기것 처럼 다시 업로드해 보세요 - 이 파일은 너무 많은 것 같아요!")
            return

        with BytesIO() as file:
            file_info.download(out=file)
            file.seek(0)
            data = json.load(file)

        # only import one group
        if len(data) > 1 and str(chat.id) not in data:
            msg.reply_text("이 파일에 그룹이 두 개 이상 있지만, 이 그룹과 동일한 채팅 ID를 가진 그룹이 없어요. "
                           "- 가져올 항목을 선택하려면 제가 어떻게 해야 할까요?")
            return

        # 데이터 소스 선택
        if str(chat.id) in data:
            data = data[str(chat.id)]['hashes']
        else:
            data = data[list(data.keys())[0]]['hashes']

        try:
            for mod in DATA_IMPORT:
                mod.__import_data__(str(chat.id), data)
        except Exception:
            msg.reply_text("데이터를 복원하는 동안 오류가 발생하였어요. 절차가 완전하지 않을 수도 있어요. 만약 "
                           "이것에 문제가 있는 경우 문제 해결을 위해 @MarieSupport에 백업파일을 보내주세요. "
                           "제 주인은 이것을 꼭 해결해줄 것이고 오류를 보고해주시면 제가 좀 더 나아질 거에요! "
                           "감사합니다 :)")
            LOGGER.exception("아이디 : %s, 이름 : %s \n불러오기를 실패했어요.", str(chat.id), str(chat.title))
            return

        # TODO: some of that link logic
        # NOTE: consider default permissions stuff?
        msg.reply_text("백업을 완전히 가져왔어요. 다시 돌아온 걸 환영해요! :D")


@run_async
@user_admin
def export_data(bot: Bot, update: Update):
    msg = update.effective_message  # type: Optional[Message]
    msg.reply_text("")


__mod_name__ = "백업"

__help__ = """
*관리자용 명령어*
 - /import: 그룹 버틀러 백업 파일에 답장 처리된 메시지를 다른 곳으로 불러와요. 변환을 매우 쉽게 할 수 있는 기능이지만, \
 텔레그램 규칙에 따라 사진과 파일은 이 기능으로 옮길 수 없어요.
 - /export: !!! 아직 명령어는 아니지만, 곧 출시될 거예요.
"""
IMPORT_HANDLER = CommandHandler("import", import_data)
EXPORT_HANDLER = CommandHandler("export", export_data)

dispatcher.add_handler(IMPORT_HANDLER)
# dispatcher.add_handler(EXPORT_HANDLER)
