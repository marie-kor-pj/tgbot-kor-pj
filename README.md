# tgbot

* 이 봇은 [Marie 봇](https://github.com/PaulSonOfLars/tgbot) 을 한글화한 것 입니다.
* 공식 사이트 : [https://marie-kor-pj.github.io/](https://marie-kor-pj.github.io/)
* 원본 봇은 [Marie](https://t.me/BanhammerMarie_bot) 입니다.
* ~~원본 [Marie](https://t.me/BanhammerMarie_bot) 봇에 대한 궁금한 점은 [support group](https://t.me/MarieSupport) 에서 물어주세요.~~ - 채널 아카이브됨
* [Marie](https://t.me/BanhammerMarie_bot) 봇에 대한 새 소식은 [news channel](https://t.me/MarieNews) 에서 확인하세요.
* 원본 [Marie](https://t.me/BanhammerMarie_bot) 봇은 업데이트가 중지되었습니다.

## Heroku Deploy

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/marie-kor-pj/tgbot-kor-pj)

## Credit

  1. [천상의나무](https://github.com/NewPremium)
  2. [KCPIT](https://github.com/kgu090716)
  3. [하정빈](https://github.com/Eli-sys)
  4. [Hyun Cha](https://github.com/RIPAngel)
  5. [SongJH](https://github.com/KRSongJH)
  6. [kongwoojin](https://github.com/kongwoojin)
  7. [Lee Kyong Hwan](https://github.com/TamTamBurin)

## 봇 시작.

데이터베이스 설정과 환경 설정을 끝마쳤다면(하단 참고), 이 명령어를 실행하세요:<br>

`python3 -m tg_bot`<br>


## 봇 설정 (사용하기 전에 이 내용을 읽어보십시오!):
파이썬 3.6 **이상** 버전의 사용을 권장합니다. 구버전 파이썬에서 모든 것이 정상 작동하리라고는 장담할 수 없어요!<br>
이건 마크다운 파싱이 dict를 통해 진행되었기 때문입니다. dict는 파이썬 3.6 을 기본으로 합니다.

### 환경 설정

당신의 봇을 설정하는 방법으로는 두 가지가 있습니다. config.py 를 사용하는 방법과 환경 변수를 사용하는 방법입니다.<br><br>

권장하는 방법은 당신의 모든 설정을 한 곳에 모아 볼 수 있는 config.py 를 사용하는 방법입니다.<br>
이 파일은 `__main__.py` 파일과 함께 tg_bot 폴더에 있어야 합니다.<br>
이곳은 당신의 봇 토큰이 로딩되는 곳이며, 당신의 데이터베이스 URL도 마찬가지입니다(데이터베이스 사용중일 경우), <br>
그리고 대부분의 당신의 설정들이 이곳에 있습니다.<br><br>

sample_config (을)를 가져가서 Config 클래스를 확장하는 것이 권장됩니다. 이렇게 하는 것으로, 당신의 Config이 sample_config 안에 있는 모든 기본 설정들을 포함한다는 것을 보장할 수 있습니다. 게다가 업그레이드까지 더 쉽게 해줍니다.<br><br>

config.py 예시:
```
from tg_bot.sample_config import Config


class Development(Config):
    OWNER_ID = 254318997  # 자신의 Telegram ID
    OWNER_USERNAME = "SonOfLars"  # 자신의 Telegram 닉네임
    API_KEY = "your bot api key"  # botfather 로 부터 받은 봇의 api 키
    SQLALCHEMY_DATABASE_URI = 'postgresql://username:password@localhost:5432/database'  # 샘플 db 인증서
    MESSAGE_DUMP = '-1234567890' # some group chat that your bot is a member of
    USE_MESSAGE_DUMP = True
    SUDO_USERS = [18673980, 83489514]  # 봇에 액세스할 수 있는 사용자의 ID 목록
    LOAD = []
    NO_LOAD = ['translation']
```

당신이 config.py 파일을 가지고 있지 않다면 (EG on heroku), 환경 변수를 사용하는 방법도 사용이 가능합니다.<br>
다음 환경 변수들이 사용 가능합니다:<br>
 - `ENV`: 이것을 무언가로 설정하는 것으로 환경 변수를 활성화할 수 있습니다.<br>

 - `TOKEN`: 당신의 봇 토큰입니다.
 - `OWNER_ID`: 정수로 이루어진 당신의 ID 입니다. 
 - `OWNER_USERNAME`: 당신의 닉네임입니다.

 - `DATABASE_URL`: 당신의 데이터베이스 URL입니다. 
 - `MESSAGE_DUMP`: 선택사항 : 당신의 답장 처리된 메시지들이 보관된 채팅입니다. 이는 유저들이 이전 메시지를 삭제하는 것을 방지해줍니다.  
 - `LOAD`: 당신이 로드하고 싶은 모듈들의 분리된 리스트가 있는 공간.
 - `NO_LOAD`: 당신이 로드하고 싶지 않은 모듈들의 분리된 리스트가 있는 공간.
 - `WEBHOOK`: 환경 모드 메세지 안에 있을 때 이것을 무엇으로든 설정하는 것으로 Webhook의 활성화가 가능합니다. 
 - `URL`: 당신의 Webhook이 연결될 링크 (webhook 모드에만)

 - `SUDO_USERS`: Sudo 유저로 간주되어야 하는 유저들의 리스트가 있는 공간.
 - `SUPPORT_USERS`: 서포트 유저로 간주되어야 하는 유저 아이디들의 분리된 리스트가 있는 공간 (gban, ungban만 가능)
 - `WHITELIST_USERS`: 화이트리스트로 간주되어야 하는 유저들의 분리된 리스트가 있는 공간 - 그들은 밴할 수 없습니다.
 - `DONATION_LINK`: 선택사항 : 기부금을 받을 링크.
 - `CERT_PATH`: webhook 인증 경로.
 - `PORT`: webhook를 위해 사용할 포트.
 - `DEL_CMDS`: 권한이 없는 유저들이 보낸 명령어를 삭제할지 여부를 확인합니다.
 - `STRICT_GBAN`: 새로운 그룹과 마찬가지로 오래된 그룹에서도 gban을 시행합니다. 만약 gban 당한 유저가 말을 한다면, 그는 밴 당할 것입니다.
 - `WORKERS`: 사용할 스레드의 개수입니다. 8개가 기본이자 권장하는 개수이지만, 당신의 경험은 다를 수 있으니 알아서 하시면 됩니다.
<br>__Note__ 미친듯이 스레드만 추가하는 것에 매달리는 것은 사실 봇 속도 향상에 큰 도움을 주지 못합니다. 많은 양의 sql 데이터 액세스와, 파이썬 asynchronous가 더 큰 분량을 차지합니다. 
 - `BAN_STICKER`: 유저를 밴할 때 사용할 스티커의 ID.
 - `ALLOW_EXCL`: /를 !와 같이 사용할 수 있도록 허용할지 결정하세요.

### Python 의존성

프로젝트 폴더로 가서 다음 명령어를 입력하여 필수 파이썬 패키지들을 설치할 수 있습니다:<br>

`pip3 install -r requirements.txt`.<br>

이 명령어가 모든 필수 파이썬 패키지들을 설치할 것입니다. 

### 데이터베이스

만약 당신이 데이터베이스 기반 모듈을 만들고 싶다면 (eg: locks, notes, userinfo, users, filters, welcomes),<br>
당신의 시스템에는 데이터베이스가 설치되어 있어야 합니다. 전 [potgres](https://www.postgresql.org) 를 사용하므로, 이것을 추천합니다.<br><br>

[potgres](https://www.postgresql.org) 사용시의 방법입니다. 데비안 계열에서의 방법이므로 다른 계열에선 다를 수 있습니다. <br>

- [postgresql](https://www.postgresql.org) 설치:

`sudo apt-get update && sudo apt-get install postgresql`<br>

- [postgres](https://www.postgresql.org) 사용자 변경:

`sudo su - postgres`<br>

- 새 데이터베이스 사용자 생성(적절하게 YOUR_USER 변경):

`createuser -P -s -e YOUR_USER`

이 뒤에는 비밀번호를 입력해야 할 것입니다. <br>

- 새 데이터베이스 테이블 생성:

`createdb -O YOUR_USER YOUR_DB_NAME`<br>

YOUR_USER와 YOUR_DB_NAME을 정확하게 바꾸세요.<br>

- 마지막으로:

`psql YOUR_DB_NAME -h YOUR_HOST YOUR_USER`

터미널을 통해 데이터베이스에 연결할 수 있습니다.<br>
YOUR_HOST의 기본 설정은 0.0.0.0:5432 입니다.<br><br>

이제 당신의 데이터베이스 URL을 빌드할 수 있게 되었습니다. 그것은 다음과 같습니다:

`sqldbtype://username:pw@hostname:port/db_name`

sqldbtype 을(를) 당신이 사용하는 DB에 따라 바꾸세요. (eg postgres, mysql, sqllite 등등...)<br>
당신의 유저네임, 비밀번호, 호스트 이름을 설정하세요 (localhost?), port (5432?), 그리고 DB 이름도요.

## 모듈들
### 로드 순서 설정.

이 모듈 로드 순서는 `LOAD` 와 `NO_LOAD` 환경 설정으로 변경이 가능합니다.<br>
이 모두는 리스트를 대표해야 합니다.<br><br>

만약 `LOAD` 가 빈 리스트라면, `modules/` 안에 있는 모든 것들은 기본 설정으로 로드될 것입니다.<br>

만약 `NO_LOAD` 가 최신이 아니라면, 또는 빈 리스트라면, 로딩되기로 선택된 것들은 모두 로드될 것입니다.<br>

만약 모듈이 `LOAD` 와 `NO_LOAD`에 모두 존재할 경우, 모듈은 로드되지 않습니다 - `NO_LOAD` 가 우선입니다.

### 자신만의 모듈 만들기.

모듈을 만드는 것은 많이 간단해졌습니다 - 그러니 더 간단한 방법을 요구하지는 마십시오.<br><br>

필요한 것은 .py 파일이 모듈 폴더 내에 있는 것뿐입니다.<br><br>

명령어를 추가하려면, 아래 명령어를 사용해 dispatcher 을(를) 불러오는 것을 잊지 마세요:<br>
`from tg_bot import dispatcher`.<br><br>

그럼 당신은 이제 전형적인 방법으로 명령어를 추가할 수 있습니다:<br>
`dispatcher.add_handler()`<br><br>

 `__help__` 변수에게 이 모듈을 설명하는 것을 맡기면 됩니다.
명령어가 봇이 이 모듈을 로드할 수 있고, 기록을 추가할 수 있게 해줄 것입니다.<br>
`__mod_name__` 변수를 설정하는 것은 더 좋고, 유저들에게 편리한 이름을 설정해 줍니다.<br><br>

`__migrate__()` 기능은 그룹을 옮기는 곳에 사용됩니다 - 그룹이 super 그룹으로 업그레이드될 경우, 아이디가 바뀌기 때문에, db 안에서 이동시키는 것이 중요합니다.<br><br>

`__stats__()` 기능은 모듈 통계를 되찾아 오는 곳에 사용됩니다. <br>
봇 주인만 사용할 수 있는 `/stats` 명령어를 통해 사용할 수 있습니다.
