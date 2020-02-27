import html
import json
import random
from datetime import datetime
from typing import Optional, List

import requests
from telegram import Message, Chat, Update, Bot, MessageEntity
from telegram import ParseMode
from telegram.ext import CommandHandler, run_async, Filters
from telegram.utils.helpers import escape_markdown, mention_html

from tg_bot import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, WHITELIST_USERS, BAN_STICKER
from tg_bot.__main__ import GDPR
from tg_bot.__main__ import STATS, USER_INFO
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.extraction import extract_user
from tg_bot.modules.helper_funcs.filters import CustomFilters

RUN_STRINGS = (
    "어디로 갈 것 같아요?",
    "네? 뭐라고요? 도망갔어요??",
    "ZZzzZZzz... 네...? 뭐라고요? 아! 신경 쓰지 마세요.",
    "다시 돌아오세요!",
    "그렇게 빠르지 않아요...",
    "벽을 조심하세요!",
    "저를 내버려 두지 마세요!!",
    "도망치면 죽어요",
    "농담이에요, 전 어디에나 있어요",
    "후회하게 될 거예요...",
    "/kickme 도 해 보세요. 재미있다고 들었어요.",
    "가서 다른 사람 괴롭혀요. 여기선 아무도 신경 안 써요",
    "도망칠 수는 있지만 숨을 수는 없어요.",
    "그게 네가 가진 전부예요?",
    "전 당신 뒤에 있어요...",
    "단체가 있으시군요!",
    "우리는 이것을 쉬운 방법으로, 또는 어려운 방법으로 할 수 있어요.",
    "당신은 그냥 이해를 못하는군요, 맞죠?",
    "네, 도망가는 게 좋을 거예요!",
    "제발, 제가 얼마나 신경 쓰는지 알려주세요.",
    "제가 당신이라면 더 빨리 달릴 텐데요.",
    "우리가 찾는 안드로이드가 분명해요",
    "승산이 있으시기를 빌어요.",
    "유명한 유언.",
    "그리고 그들은 영원히 사라졌고, 다시는 볼 수 없었습니다.",
    "\"오, 절 봐요! 전 너무 멋져요, 전 봇으로부터 달릴 수 있어요\" - 사람",
    "네, /kickme 을(를) 누르세요.",
    "여기, 이 반지를 가져다가 모르도르로 가세요.",
    "전설에 따르면, 그들은 여전히 달리고 있어요...",
    "해리 포터와 달리, 당신의 부모님은 당신을 저로부터 보호할 수 없어요.",
    "두려움은 분노로 이어집니다. 분노는 증오로 이어집니다. 증오는 고통으로 이어집니다. 겁에 질려 계속 도망가면 "
    "계속 뛰면 제2의 베이더(Vader)가 될지도 몰라요.",
    "여러 번 계산한 후에, 나는 당신의 속임수에 대한 나의 관심을 정확히 0으로 결정했어요.",
    "전설에 따르면, 그들은 여전히 달리고 있어요.",
    "계속하세요, 당신이 여기 오길 바라는지 모르겠어요.",
    "당신은 마법사인 거예요 - 잠깐만, 당신은 해리가 아니에요. 계속 움직이세요.",
    "해프닝은 금지!",
    "안녕, 자기야?",
    "누가 개를 풀어줬나요?",
    "아무도 신경 안 써서 웃겨요.",
    "아, 정말 아깝네요. 그거 마음에 들었어요.",
    "솔직히 말씀해서, 전 개의치 않아요.",
    "제 밀크셰이크가 모든 아이들을 마당으로 데려왔어요! 그러니 더 빨리 달려요!",
    "당신은 진실을 감당하지 못해요!",
    "오래전에, 멀리 있는 은하계에서... 누군가 신경 썼을 거예요. 하지만 이젠 아니에요.",
    "저 사람들 좀 봐요! 그들은 피할 수 없는 망령에서 도망치고 있어요... 귀여워요.",
    "한 형이 먼저 쐈어요. 저도 그럴까요?",
    "흰 토끼야 뭘 쫓고 있는 거야?",
    "의사가 말하듯이... 빨리 피해요.",
)

SLAP_TEMPLATES = (
    "{user1} 님은 {user2} 님을 {item}(으)로 {hits}어요.",
    "{user1} 님은 {user2} 님의 얼굴을 {item}(으)로 {hits}어요.",
    "{user1} 님은 {item} (으)로 {user2} 님을 조금 {hits}어요.",
    "{user1} 님은 {user2} 님에게 {item} 을(를) {throws}어요.",
    "{user1} 님은 {item} 을(를) 잡고 {user2} 님의 얼굴에 {throws}어요.",
    "{user1} 님은 {item} 을(를) {user2} 님의 정면으로 발사했어요.",
    "{user1} 님은 {item} 을(를) 사용하여 {user2} 님의 뺨을 때리기 시작했어요.",
    "{user1} 님은 {user2} 님을 묶고 {item}(으)로 계속 {hits}어요.",
    "{user1} 님은 {item} 을(를) 들었고 그걸로 {user2} 님을(를) {hits}어요.",
    "{user1} 님은 {user2} 님을 의자에 묶었고 {item}(으)로 {throws}어요.",
    "{user1} 님은 {user2} 님이 용암에서 수영하는 법을 배울 수 있도록 우호적으로 밀어주었어요."
)

ITEMS = (
    "철냄비",
    "큰 송어",
    "야구 방망이",
    "크리켓 방망이",
    "나무 지팡이",
    "못",
    "프린터기",
    "삽",
    "CRT 모니터",
    "물리학 교과서",
    "토스터기",
    "Richard Stallman의 초상화",
    "텔레비전",
    "5톤 트럭",
    "강력 접착테이프",
    "책",
    "노트북",
    "오래된 텔레비전",
    "돌무더기",
    "무지개 송어",
    "고무 치킨",
    "뾰족한 방망이",
    "소화기",
    "무거운 바위",
    "흙덩어리",
    "벌집",
    "썩은 고기 조각",
    "곰",
    "벽돌 1톤",
    "김장김치",
)

THROW = (
    "던졌",
	"화가나서 던졌",
	"거칠게 던졌",
)

HIT = (
    "때렸",
    "세게쳤",
    "철석 때렸",
    "손바닥으로 때렸",
    "후려쳤",
)

GMAPS_LOC = "https://maps.googleapis.com/maps/api/geocode/json"
GMAPS_TIME = "https://maps.googleapis.com/maps/api/timezone/json"


@run_async
def runs(bot: Bot, update: Update):
    update.effective_message.reply_text(random.choice(RUN_STRINGS))


@run_async
def slap(bot: Bot, update: Update, args: List[str]):
    msg = update.effective_message  # type: Optional[Message]

    # 올바른 메시지에 답장
    reply_text = msg.reply_to_message.reply_text if msg.reply_to_message else msg.reply_text

    # 누가 메시지를 보냈는지 확인
    if msg.from_user.username:
        curr_user = "@" + escape_markdown(msg.from_user.username)
    else:
        curr_user = "[{}](tg://user?id={})".format(msg.from_user.first_name, msg.from_user.id)

    user_id = extract_user(update.effective_message, args)
    if user_id:
        slapped_user = bot.get_chat(user_id)
        user1 = curr_user
        if slapped_user.username:
            user2 = "@" + escape_markdown(slapped_user.username)
        else:
            user2 = "[{}](tg://user?id={})".format(slapped_user.first_name,
                                                   slapped_user.id)

    # 대상을 찾을 수 없는 경우 봇은 보낸 사람을 대상으로 한다
    else:
        user1 = "[{}](tg://user?id={})".format(bot.first_name, bot.id)
        user2 = curr_user

    temp = random.choice(SLAP_TEMPLATES)
    item = random.choice(ITEMS)
    hit = random.choice(HIT)
    throw = random.choice(THROW)

    repl = temp.format(user1=user1, user2=user2, item=item, hits=hit, throws=throw)

    reply_text(repl, parse_mode=ParseMode.MARKDOWN)


@run_async
def get_bot_ip(bot: Bot, update: Update):
    """ 필요한 경우 SSH 접속을 하기 위해서 봇의 IP주소를 보낸다.
        봇 주인만 .
    """
    res = requests.get("http://ipinfo.io/ip")
    update.message.reply_text(res.text)


@run_async
def get_id(bot: Bot, update: Update, args: List[str]):
    user_id = extract_user(update.effective_message, args)
    if user_id:
        if update.effective_message.reply_to_message and update.effective_message.reply_to_message.forward_from:
            user1 = update.effective_message.reply_to_message.from_user
            user2 = update.effective_message.reply_to_message.forward_from
            update.effective_message.reply_text(
                "원래 보낸사람, {}, 아이디 `{}`.\n전달자, {},  `{}`.".format(
                    escape_markdown(user2.first_name),
                    user2.id,
                    escape_markdown(user1.first_name),
                    user1.id),
                parse_mode=ParseMode.MARKDOWN)
        else:
            user = bot.get_chat(user_id)
            update.effective_message.reply_text("{}'의 ID는 `{}` 예요.".format(escape_markdown(user.first_name), user.id),
                                                parse_mode=ParseMode.MARKDOWN)
    else:
        chat = update.effective_chat  # type: Optional[Chat]
        if chat.type == "private":
            update.effective_message.reply_text("당신의 ID는 `{}` 예요.".format(chat.id),
                                                parse_mode=ParseMode.MARKDOWN)

        else:
            update.effective_message.reply_text("이 그룹의 ID는 `{}` 예요.".format(chat.id),
                                                parse_mode=ParseMode.MARKDOWN)


@run_async
def info(bot: Bot, update: Update, args: List[str]):
    msg = update.effective_message  # type: Optional[Message]
    user_id = extract_user(update.effective_message, args)

    if user_id:
        user = bot.get_chat(user_id)

    elif not msg.reply_to_message and not args:
        user = msg.from_user

    elif not msg.reply_to_message and (not args or (
            len(args) >= 1 and not args[0].startswith("@") and not args[0].isdigit() and not msg.parse_entities(
        [MessageEntity.TEXT_MENTION]))):
        msg.reply_text("사용자의 ID를 추출할 수 없어요.")
        return

    else:
        return

    text = "<b>사용자 정보</b>:" \
           "\nID: <code>{}</code>" \
           "\n이름: {}".format(user.id, html.escape(user.first_name))

    if user.last_name:
        text += "\n성: {}".format(html.escape(user.last_name))

    if user.username:
        text += "\n닉네임: @{}".format(html.escape(user.username))

    text += "\n영구 사용자 링크: {}".format(mention_html(user.id, "link"))

    if user.id == OWNER_ID:
        text += "\n\n이 사람은 저의 주인이에요. - 전 그 상대로 아무것도 할 수가 없어요!"
    else:
        if user.id in SUDO_USERS:
            text += "\n이 사람은 저의 관리자들 중 한 명이예요! " \
                    "그들은 제 주인만큼 강력해요."
        else:
            if user.id in SUPPORT_USERS:
                text += "\n이 사람은 제 후원자 중 한 명이예요! " \
                        "해당 사용자가 관리자 아니지만, 글로벌 밴을 할 수는 있어요."

            if user.id in WHITELIST_USERS:
                text += "\n이 사람은 화이트리스트에 속해있으신 분이에요! " \
                        "ban/kick 등의 명령어는 이분에게 사용하실 수 없어요."

    for mod in USER_INFO:
        mod_info = mod.__user_info__(user.id).strip()
        if mod_info:
            text += "\n\n" + mod_info

    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


@run_async
def get_time(bot: Bot, update: Update, args: List[str]):
    location = " ".join(args)
    if location.lower() == bot.first_name.lower():
        update.effective_message.reply_text("누군가를 Ban 하는 것은 저에게는 항상 즐거운 시간이에요!")
        bot.send_sticker(update.effective_chat.id, BAN_STICKER)
        return

    res = requests.get(GMAPS_LOC, params=dict(address=location))

    if res.status_code == 200:
        loc = json.loads(res.text)
        if loc.get('status') == 'OK':
            lat = loc['results'][0]['geometry']['location']['lat']
            long = loc['results'][0]['geometry']['location']['lng']

            country = None
            city = None

            address_parts = loc['results'][0]['address_components']
            for part in address_parts:
                if 'country' in part['types']:
                    country = part.get('long_name')
                if 'administrative_area_level_1' in part['types'] and not city:
                    city = part.get('long_name')
                if 'locality' in part['types']:
                    city = part.get('long_name')

            if city and country:
                location = "{}, {}".format(city, country)
            elif country:
                location = country

            timenow = int(datetime.utcnow().timestamp())
            res = requests.get(GMAPS_TIME, params=dict(location="{},{}".format(lat, long), timestamp=timenow))
            if res.status_code == 200:
                offset = json.loads(res.text)['dstOffset']
                timestamp = json.loads(res.text)['rawOffset']
                time_there = datetime.fromtimestamp(timenow + timestamp + offset).strftime("%H:%M:%S on %A %d %B")
                update.message.reply_text("It's {} in {}".format(time_there, location))


@run_async
def echo(bot: Bot, update: Update):
    args = update.effective_message.text.split(None, 1)
    message = update.effective_message
    if message.reply_to_message:
        message.reply_to_message.reply_text(args[1])
    else:
        message.reply_text(args[1], quote=False)
    message.delete()


@run_async
def gdpr(bot: Bot, update: Update):
    update.effective_message.reply_text("식별 가능한 데이터 삭제")
    for mod in GDPR:
        mod.__gdpr__(update.effective_user.id)

    update.effective_message.reply_text("개인 데이터가 삭제되었어요.\n\n참고,  저의 데이터가 아닌 "
                                        "Telegram 의 데이터이기 때문에 어느 채팅방에서도 당신을 Unban 하지 않을 거예요. "
                                        "도배방지, 경고, 그리고 글로벌 밴도 계속 남아있을 거예요. "
                                        "[참고하세요](https://ico.org.uk/for-organisations/guide-to-the-general-data-protection-regulation-gdpr/individual-rights/right-to-erasure/), "
                                        "상기 데이터 조각과 같이 공공의 이익을 위해 수행된  "
                                        "\"과제에 대해 삭제권이 적용되지 않는다는 것\"을 명확히 "
                                        "기술하고 있습니다.",
                                        parse_mode=ParseMode.MARKDOWN)


MARKDOWN_HELP = """
마크다운은 telegram에서 지원되는 매우 강력한 도구예요. {} 저장된 메시지가 올바르게 구문 분석되었는지 확인하고 \
단추를 만들 수 있도록 몇 가지 향상된 기능이 있어요.

- <code>_italic_</code>: '_' 로 텍스트를 감싸면 기울어진 글자가 작성될 거예요. 
- <code>*bold*</code>: '*' 로 텍스트를 감싸면 굵은 글자가 작성될 거예요. 
- <code>`code`</code>: '`' 로 텍스트를 감싸면 'code'라고 하는 동일한 텍스트가 생성될 거예요.
- <code>[보여질 메시지](URL)</code>: 링크를 만들어줘요. - 메시지는 <code>보여질 메시지</code> 라고 보여질 거지만, \
그 메시지를 터치하면 <code>URL</code>로 들어가져요.
예: <code>[테스트](example.com)</code>

- <code>[버튼에 보여질 메시지](URL)</code>: 이것은 telegram이 가지고 있는 특별한 \
마크다운에서의 버튼 기능이에요. <code>버튼에 보여질 메시지</code> 가 버튼에 나타나고, 버튼을 누르면 <code>URL</code> \
로 들어가져요.
예: <code>[버튼](buttonurl:example.com)</code>

같은 줄에 여러 개의 버튼을 사용하려면 :same을 사용하세요 :
<code>[one](buttonurl://example.com)
[two](buttonurl://google.com:same)</code>
이렇게 하면 한 줄에 한 버튼이 아니라 한 줄에 두 개의 버튼이 생성돼요.

메시지에는 버튼이 아닌 텍스트가 포함되어야 해요!!!
""".format(dispatcher.bot.first_name)


@run_async
def markdown_help(bot: Bot, update: Update):
    update.effective_message.reply_text(MARKDOWN_HELP, parse_mode=ParseMode.HTML)
    update.effective_message.reply_text("다음 메시지를 제게 전달해 보세요. 그러면 알게 될 거예요!")
    update.effective_message.reply_text("/save 은(는) 마크다운을 테스트 할 수 있어요. _기울어진 글자_, *굵은글자*, `code`, "
                                        "[URL](example.com) [button](buttonurl:github.com) "
                                        "[button2](buttonurl://google.com:same)")


@run_async
def stats(bot: Bot, update: Update):
    update.effective_message.reply_text("현재 상황:\n" + "\n".join([mod.__stats__() for mod in STATS]))


# /ip is for private use
__help__ = """
 - /id: 현재 그룹 ID를 가져와요. 만약 다른 사용자의 메시지를 답장하면 해당 사용자의 ID를 가져와요.
 - /runs: 랜덤으로 아무 말을 해 드려요.
 - /slap: 사용자에게 뺨을 때리거나, 답장을 안 했을 경우 뺨을 맞아요.
 - /info: 사용자에 대한 정보를 가져와줘요.
 - /gdpr: 봇 데이터베이스에서 정보를 삭제해요. (사적인 대화만)

 - /markdownhelp: 마크다운에 대해서 알려줘요 - 비공개 채팅에서만 알려줄 수 있어요.
"""

__mod_name__ = "기타"

ID_HANDLER = DisableAbleCommandHandler("id", get_id, pass_args=True)
IP_HANDLER = CommandHandler("ip", get_bot_ip, filters=Filters.chat(OWNER_ID))

TIME_HANDLER = CommandHandler("time", get_time, pass_args=True)

RUNS_HANDLER = DisableAbleCommandHandler("runs", runs)
SLAP_HANDLER = DisableAbleCommandHandler("slap", slap, pass_args=True)
INFO_HANDLER = DisableAbleCommandHandler("info", info, pass_args=True)

ECHO_HANDLER = CommandHandler("echo", echo, filters=Filters.user(OWNER_ID))
MD_HELP_HANDLER = CommandHandler("markdownhelp", markdown_help, filters=Filters.private)

STATS_HANDLER = CommandHandler("stats", stats, filters=CustomFilters.sudo_filter)
GDPR_HANDLER = CommandHandler("gdpr", gdpr, filters=Filters.private)

dispatcher.add_handler(ID_HANDLER)
dispatcher.add_handler(IP_HANDLER)
# dispatcher.add_handler(TIME_HANDLER)
dispatcher.add_handler(RUNS_HANDLER)
dispatcher.add_handler(SLAP_HANDLER)
dispatcher.add_handler(INFO_HANDLER)
dispatcher.add_handler(ECHO_HANDLER)
dispatcher.add_handler(MD_HELP_HANDLER)
dispatcher.add_handler(STATS_HANDLER)
dispatcher.add_handler(GDPR_HANDLER)
