import re
import sre_constants

import telegram
from telegram import Update, Bot
from telegram.ext import run_async

from tg_bot import dispatcher, LOGGER
from tg_bot.modules.disable import DisableAbleRegexHandler

DELIMITERS = ("/", ":", "|", "_")


def separate_sed(sed_string):
    if len(sed_string) >= 3 and sed_string[1] in DELIMITERS and sed_string.count(sed_string[1]) >= 2:
        delim = sed_string[1]
        start = counter = 2
        while counter < len(sed_string):
            if sed_string[counter] == "\\":
                counter += 1

            elif sed_string[counter] == delim:
                replace = sed_string[start:counter]
                counter += 1
                start = counter
                break

            counter += 1

        else:
            return None

        while counter < len(sed_string):
            if sed_string[counter] == "\\" and counter + 1 < len(sed_string) and sed_string[counter + 1] == delim:
                sed_string = sed_string[:counter] + sed_string[counter + 1:]

            elif sed_string[counter] == delim:
                replace_with = sed_string[start:counter]
                counter += 1
                break

            counter += 1
        else:
            return replace, sed_string[start:], ""

        flags = ""
        if counter < len(sed_string):
            flags = sed_string[counter:]
        return replace, replace_with, flags.lower()


@run_async
def sed(bot: Bot, update: Update):
    sed_result = separate_sed(update.effective_message.text)
    if sed_result and update.effective_message.reply_to_message:
        if update.effective_message.reply_to_message.text:
            to_fix = update.effective_message.reply_to_message.text
        elif update.effective_message.reply_to_message.caption:
            to_fix = update.effective_message.reply_to_message.caption
        else:
            return

        repl, repl_with, flags = sed_result

        if not repl:
            update.effective_message.reply_to_message.reply_text("당신은 아마 아무것도 아닌걸요... "
                                                                 "어떤 걸로 덮어쓰시려구요?")
            return

        try:
            check = re.match(repl, to_fix, flags=re.IGNORECASE)

            if check and check.group(0).lower() == to_fix.lower():
                update.effective_message.reply_to_message.reply_text("안녕하세요 여러분, {} 은(는) 제가 하고 싶지 "
                                                                     "않은 말을 하게 하는 "
                                                                     "거예요!".format(update.effective_user.first_name))
                return

            if 'i' in flags and 'g' in flags:
                text = re.sub(repl, repl_with, to_fix, flags=re.I).strip()
            elif 'i' in flags:
                text = re.sub(repl, repl_with, to_fix, count=1, flags=re.I).strip()
            elif 'g' in flags:
                text = re.sub(repl, repl_with, to_fix).strip()
            else:
                text = re.sub(repl, repl_with, to_fix, count=1).strip()
        except sre_constants.error:
            LOGGER.warning(update.effective_message.text)
            LOGGER.exception("SRE constant 에러")
            update.effective_message.reply_text("혹시 SED 해보셨나요? 아마 아닌 것 같아요.")
            return

        # empty string errors -_-
        if len(text) >= telegram.MAX_MESSAGE_LENGTH:
            update.effective_message.reply_text("sed 명령의 결과가 Telegram 에게는 너무 \
                                                길어요!")
        elif text:
            update.effective_message.reply_to_message.reply_text(text)


__help__ = """
 - s/<text1>/<text2>(/<flag>): SED 작업을 하고 싶은 메시지에 , 'text1'의 \ 발생들을 모두 'text2'를 사용하여 대체합니다. 
Flags는 선택이며, 현재는 'i' 는 ignore case, 'g'는 global, \
또는 아무것도 뜻하지 않습니다. Delimiters는 `/`, `_`, `|`와, `:`를 포함합니다. Text grouping 은 지원됩니다. 결과 메시지는 \가 {}보다 커질 수 없습니다.

*한 가지 더* Sed는 좀 어려운 문자들은 쉽게 보려고 쓰여요. 예를 들어서 : `+*.?\\`
만약 여러분이 이러한 문자들을 쓰고 싶으시다면, 
그것들을 피하세요!
예시: \\?.
""".format(telegram.MAX_MESSAGE_LENGTH)

__mod_name__ = "Sed/Regex"


SED_HANDLER = DisableAbleRegexHandler(r's([{}]).*?\1.*'.format("".join(DELIMITERS)), sed, friendly="sed")

dispatcher.add_handler(SED_HANDLER)
