from tg_bot.sample_config import Config


class Development(Config):
    OWNER_ID = 79673869  # 자신의 Telegram ID
    OWNER_USERNAME = "ৡۣۜ͜͡✵͡천상의나무ۣۜৡ"  # 자신의 Telegram 닉네임
    API_KEY = "871587380:AAH73KD9QGteyu4bdRe0gAiV3VB4bK1yz0o"  # botfather 로 부터 받은 봇의 api 키
    SQLALCHEMY_DATABASE_URI = 'postgresql://username:password@localhost:5432/database'  # sample db credentials
    MESSAGE_DUMP = '-1001362111314' # some group chat that your bot is a member of
    USE_MESSAGE_DUMP = True
    SUDO_USERS = [79673869]  # 봇에 액세스할 수 있는 사용자의 ID 목록
    LOAD = []
    NO_LOAD = ['translation']
