if not __name__.endswith("sample_config"):
    import sys
    print("README 는 읽기 전용입니다. 이 샘플 Config 를 Config 파일로 확장하되, 그냥 이름만 바꾸고 여기에 있는 요소들을 바꿔서는 안 됩니다. "
          "만약 이 경고를 무시할 경우, 당신에게 나쁜 영향을 끼칠 것이란 것을 알려드립니다.\n봇 종료.", file=sys.stderr)
    quit(1)


# Create a new config.py file in same dir and import, then extend this class.
class Config(object):
    LOGGER = True

    # REQUIRED
    API_KEY = "봇 토큰"
    OWNER_ID = "당신의 ID"  # 잘 모르겠다면, 봇을 실행하여 DM으로 /id in your private chat with it
    OWNER_USERNAME = "당신의 닉네임"

    # RECOMMENDED
    SQLALCHEMY_DATABASE_URI = 'sqldbtype://username:pw@hostname:port/db_name'  # DB를 사용하는 모듈들에게 필요합니다.
    MESSAGE_DUMP = None  # needed to make sure 'save from' messages persist
    LOAD = []
    # sed 는 장기간 실행되는 명령으로 CPU 사용량 100% 찍고 bot이 종료된다는 사실이 발견된 이후 비활성화되었습니다.
    # 다시 활성화하는 데 주의해야 합니다!
    NO_LOAD = ['translation', 'rss', 'sed']
    WEBHOOK = False
    URL = None

    # 옵션
    
    # 리스트를 모르는 사람들을 위해!
    # ['리스트1', '리스트2', '리스트3'] 형식으로 사용하시면 됩니다!
    # 정수값으로 리스트를 만드시려면?(SUDO_USERS, SUPPORT_USERS, WHITELIST_USERS 등에 사용됨)
    # [1234, 5678, 9123] 형식으로 사용하시면 됩니다!
    
    SUDO_USERS = []  # 봇의 관리자 권한을 가지는 유저들의 id 의 리스트(닉네임 아닙니다).
    SUPPORT_USERS = []  # List of id's (닉네임 아닙니다) for users which are allowed to gban, but can also be banned.
    WHITELIST_USERS = []  # List of id's (닉네임 아닙니다) for users which WONT be banned/kicked by the bot.
    DONATION_LINK = None  # EG, paypal
    CERT_PATH = None
    PORT = 5000
    DEL_CMDS = False  # Whether or not you should delete "blue text must click" commands
    STRICT_GBAN = False
    WORKERS = 8  # Number of subthreads to use. This is the recommended amount - see for yourself what works best!
    BAN_STICKER = 'CAACAgQAAxkBAAED4_FeQq0f3uGjymyvbnn9he5hJCJOTgAC0wIAAqN9MRWXv1dilHR9NhgE'  # 밴 스티커 ID
    ALLOW_EXCL = False  # / 커맨드 뿐만 아닌 ! 커맨드도 쓰기 위해서는 Allow 로 변경하세요


class Production(Config):
    LOGGER = False


class Development(Config):
    LOGGER = True
