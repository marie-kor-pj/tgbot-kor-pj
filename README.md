# tgbot

이 봇은 [Marie 봇](https://github.com/PaulSonOfLars/tgbot) 을 한글화한것 입니다.

* 원본 봇은 [Marie](https://t.me/BanhammerMarie_bot) 입니다.
* 원본 Marie 봇에 대한 궁금한 점은 [support group](https://t.me/MarieSupport) 에서 물어주세요.
* Marie 봇에 대한 새 소식은 [news channel](https://t.me/MarieNews) 에서 확인하세요.

## Credit

  1. [천상의나무](https://github.com/NewPremium)
  2. [KCPIT](https://github.com/kgu090716)
  3. [i0N](https://github.com/i0Ni0N)
  4. [SongJH](https://github.com/KRSongJH)

## 봇 시작.

데이터베이스 설정과 환경 설정을 끝마쳤다면, (하단 참고), 이 명령어를 실행하세요:

`python3 -m tg_bot`


## 봇 설정 (사용하기 전에 이 내용을 읽어보십시오!):
파이썬 3.6 사용을 권장합니다. 구버전 파이썬에서 모든것이 정상 작동하리라고는 장담할 수 없어요!
이건 마크다운 파싱이 dict를 통해 진행되었기 때문입니다. dict는 파이썬 3.6이 기본으로 합니다.

### 환경 설정

당신의 봇을 설정하는 방법으로는 두 가지가 있습니다. config.py를 사용하는 방법과 환경 변수를 사용하는 방법입니다.

권장하는 방법은 당신의 모든 설정을 한 곳에 모아 볼 수 있는 config.py를 사용하는 방법입니다.
이 파일은 __main__.py 파일과 함께 tg_bot 폴더에 있어야 합니다.
이곳은 당신의 봇 토큰이 로딩되는 곳이며, 당신의 데이터베이스 URL도 마찬가지입니다.(데이터베이스 사용중일 경우), 
그리고 대부분의 당신의 설정들이 이곳에 있습니다.

sample_config를 가져가서 Config 클래스를 확장하는것이 권장됩니다. 이렇게 하는 것으로, 당신의 Config이 sample_config 안에 있는 모든 기본 설정들을 포함한다는 것을 보장할 수 있습니다. 게다가 업그레이드까지 더 쉽게 해줍니다.

config.py 예시:
```
from tg_bot.sample_config import Config


class Development(Config):
    OWNER_ID = 254318997  # my telegram ID
    OWNER_USERNAME = "SonOfLars"  # my telegram username
    API_KEY = "your bot api key"  # my api key, as provided by the botfather
    SQLALCHEMY_DATABASE_URI = 'postgresql://username:password@localhost:5432/database'  # sample db credentials
    MESSAGE_DUMP = '-1234567890' # some group chat that your bot is a member of
    USE_MESSAGE_DUMP = True
    SUDO_USERS = [18673980, 83489514]  # List of id's for users which have sudo access to the bot.
    LOAD = []
    NO_LOAD = ['translation']
```

당신이 config.py 파일을 가지고 있지 않다면 (EG on heroku), 환경 변수를 사용하는 방법도 사용이 가능합니다.
다음 환경 변수들이 사용 가능합니다:
 - `ENV`: 이것을 무엇으로든 설정하는 것으로 환경 변수를 활성화할 수 있습니다.

 - `TOKEN`: 당신의 봇 토큰입니다.
 - `OWNER_ID`: 모두 숫자로 이루어진 당신의 ID 입니다. 
 - `OWNER_USERNAME`: 당신의 유저네임입니다.

 - `DATABASE_URL`: 당신의 데이터베이스 URL입니다. 
 - `MESSAGE_DUMP`: 선택 : 당신의 답장 처리된 메시지들이 보관된 채팅입니다. 이는 유저들이 이전 메시지를 삭제하는 것을 방지해줍니다.  
 - `LOAD`: 당신이 로드하고 싶은 모듈들의 분리된 리스트가 있는 공간.
 - `NO_LOAD`: 당신이 로드하고 싶지 않은 모듈들의 분리된 리스트가 있는 공간.
 - `WEBHOOK`: 환경 모드 메세지 안에 있을 때 이것을 무엇으로든 설정하는 것으로 Webhook의 활성화가 가능합니다. 
 - `URL`: 당신의 Webhook이 연결될 링크 (webhook 모드에만)

 - `SUDO_USERS`: Sudo 유저로 고려될 유저들의 분리된 리스트가 있는 공간.
 - `SUPPORT_USERS`: 서포트 유저로 고려되어야 할 유저 아이디들의 분리된 리스트가 있는 공간 (gban, ungban만 가능)
 - `WHITELIST_USERS`: A space separated list of user_ids which should be considered whitelisted - they can't be banned.
 - `DONATION_LINK`: Optional: link where you would like to receive donations.
 - `CERT_PATH`: Path to your webhook certificate
 - `PORT`: Port to use for your webhooks
 - `DEL_CMDS`: Whether to delete commands from users which don't have rights to use that command
 - `STRICT_GBAN`: Enforce gbans across new groups as well as old groups. When a gbanned user talks, he will be banned.
 - `WORKERS`: Number of threads to use. 8 is the recommended (and default) amount, but your experience may vary.
 __Note__ that going crazy with more threads wont necessarily speed up your bot, given the large amount of sql data 
 accesses, and the way python asynchronous calls work.
 - `BAN_STICKER`: Which sticker to use when banning people.
 - `ALLOW_EXCL`: Whether to allow using exclamation marks ! for commands as well as /.

### Python 의존성

프로젝트 디렉토리로 가서 다음 명령어를 입력하여 필수 파이썬 의존성 페키지들을 설치할 수 있습니다:

`pip3 install -r requirements.txt`.

이 명령어가 모든 필수 파이썬 패키지들을 설치할 것입니다. 

### 데이터베이스

If you wish to use a database-dependent module (eg: locks, notes, userinfo, users, filters, welcomes),
you'll need to have a database installed on your system. I use postgres, so I recommend using it for optimal compatibility.

In the case of postgres, this is how you would set up a the database on a debian/ubuntu system. Other distributions may vary.

- postgresql 설치:

`sudo apt-get update && sudo apt-get install postgresql`

- postgres 사용자 변경:

`sudo su - postgres`

- 새 데이터베이스 사용자 생성(적절하게 YOUR_USER 변경):

`createuser -P -s -e YOUR_USER`

This will be followed by you needing to input your password.

- create a new database table:

`createdb -O YOUR_USER YOUR_DB_NAME`

Change YOUR_USER and YOUR_DB_NAME appropriately.

- 마지막으로:

`psql YOUR_DB_NAME -h YOUR_HOST YOUR_USER`

This will allow you to connect to your database via your terminal.
By default, YOUR_HOST should be 0.0.0.0:5432.

You should now be able to build your database URI. This will be:

`sqldbtype://username:pw@hostname:port/db_name`

Replace sqldbtype with whichever db youre using (eg postgres, mysql, sqllite, etc)
repeat for your username, password, hostname (localhost?), port (5432?), and db name.

## 모듈들
### 로드 순서 설정.

The module load order can be changed via the `LOAD` and `NO_LOAD` configuration settings.
These should both represent lists.

If `LOAD` is an empty list, all modules in `modules/` will be selected for loading by default.

If `NO_LOAD` is not present, or is an empty list, all modules selected for loading will be loaded.

If a module is in both `LOAD` and `NO_LOAD`, the module will not be loaded - `NO_LOAD` takes priority.

### 자신만의 모듈 만들기.

Creating a module has been simplified as much as possible - but do not hesitate to suggest further simplification.

All that is needed is that your .py file be in the modules folder.

To add commands, make sure to import the dispatcher via

`from tg_bot import dispatcher`.

You can then add commands using the usual

`dispatcher.add_handler()`.

Assigning the `__help__` variable to a string describing this modules' available
commands will allow the bot to load it and add the documentation for
your module to the `/help` command. Setting the `__mod_name__` variable will also allow you to use a nicer, user
friendly name for a module.

The `__migrate__()` function is used for migrating chats - when a chat is upgraded to a supergroup, the ID changes, so 
it is necessary to migrate it in the db.

The `__stats__()` function is for retrieving module statistics, eg number of users, number of chats. This is accessed 
through the `/stats` command, which is only available to the bot owner.
