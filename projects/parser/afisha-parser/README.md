# afisha-parser

Собирает события из открытых источников и сохраняет их в JSON. Дальше JSON забирает загрузчик в базу данных.
Источники: [KudaGo public API](https://docs.kudago.com/) и [Timepad API](https://dev.timepad.ru/api/get-v1-events/).
Фильмы в прокате и трейлеры — [TMDb](https://www.themoviedb.org/).

## Города

Справочник — `src/afisha_parser/cities.py`, посмотреть: `python -m afisha_parser cities`.
У каждого города наш slug (там, где город есть у KudaGo, он совпадает с кодом KudaGo), часовой пояс
и список источников. KudaGo есть в 10 городах из 16, Timepad — во всех.

| Источник | Города |
|---|---|
| KudaGo + Timepad | msk, spb, nsk, ekb, kzn, krasnoyarsk, nnv, ufa, krd, smr |
| только Timepad | chelyabinsk, rostov, omsk, voronezh, perm, volgograd |

В `.env` задаётся `AFISHA_CITIES=msk,spb,…` — для каждого города собираются все источники из
`AFISHA_SOURCES`, которые его знают. Результат по-прежнему раскладывается по `<источник>/<город>/`.

Timepad: у площадки нет названия, только адрес (он же `venue.name`); страница события на Timepad —
это страница регистрации, поэтому она же идёт в `ticket_url` / `ticketUrl`. Берутся только события,
прошедшие модерацию Timepad. Категории Timepad — свободные русские названия, в Evently они
сопоставляются по словам (`CATEGORY_KEYWORDS` в `exporters/evently.py`). Токен: dev.timepad.ru/api/oauth/
→ `AFISHA_TIMEPAD_TOKEN`.

Одно и то же событие может прийти и из KudaGo, и из Timepad (у них разные `source` + `externalId`).
Склейка дублей между источниками пока не делается.

Умеет работать полностью автономно: служба сама собирает данные по расписанию, отбрасывает
прошедшие события, чистит старые файлы, переживает перезагрузки и сбои сети.

## Быстрый старт на сервере (Ubuntu 24.04+)

```bash
unzip afisha-parser.zip && cd afisha-parser
sudo ./deploy/install.sh          # окружение, папка данных, служба systemd
nano ~/afisha-data/.env           # User-Agent, ключ TMDb, города — см. комментарии в файле
sudo systemctl start afisha-parser
journalctl -u afisha-parser -f    # смотреть, как идёт первый цикл
```

Раскладка после установки (пути можно поменять переменными `AFISHA_USER`, `AFISHA_VENV`, `AFISHA_DATA`):

```
~/.venvs/afisha-parser/   окружение Python с установленным парсером
~/afisha-data/.env        все настройки
~/afisha-data/output/     результат (см. ниже)
/etc/systemd/system/afisha-parser.service
```

Папка с исходниками службе после установки не нужна. Повторный `sudo ./deploy/install.sh` из новой
версии обновляет код и перезапускает службу, не трогая `.env` и данные. Удалить службу:
`sudo ./deploy/uninstall.sh`.

### Вариант с Docker

```bash
cp .env.example .env && nano .env
docker compose up -d --build
docker compose logs -f
docker compose exec parser python -m afisha_parser status
```

Данные — в `./data/output`.

## Автономный режим

Служба запускает `python -m afisha_parser daemon`. Каждые `AFISHA_INTERVAL_MINUTES` минут (по умолчанию 180) цикл:

1. для каждой пары из `AFISHA_TARGETS` (`kudago:msk,kudago:spb`) собирает события, отбрасывает прошедшие,
   качает только новые картинки, пишет универсальный дамп и файл Evently;
2. если источник недоступен, берёт последний сохранённый дамп и заново фильтрует его — прошедшие события
   всё равно уходят из файла Evently, даже когда сети нет;
3. если задан `AFISHA_EVENTLY_IMPORT_URL`, отправляет события в бэкенд;
4. обновляет трейлеры к кинопоказам и афишу проката TMDb (если есть ключ);
5. удаляет старые снимки, сырые ответы и картинки, на которые больше никто не ссылается;
6. пишет итоги в `output/status.json`.

Ошибка на любом шаге не останавливает остальные. После неудачного цикла следующий будет через
`AFISHA_RETRY_MINUTES`. После перезапуска служба не дёргает источник заново, если свежий цикл уже был.
Два цикла одновременно не идут: ручные `run` и `fetch` при работающем цикле службы откажутся запускаться.

```bash
python -m afisha_parser status   # итоги последнего цикла; код 1 — ошибки или служба давно молчит
python -m afisha_parser run      # один цикл прямо сейчас (например, из cron вместо службы)
python -m afisha_parser cleanup  # уборка вручную
```

Команды нужно запускать из папки, где лежит `.env` (`~/afisha-data`), иначе парсер не найдёт настройки.

## Фильтр прошедших событий

Применяется везде: сразу после сбора, в команде `evently`, в каждом цикле службы, перед поиском трейлеров.

- сеанс с временем окончания актуален, пока оно не наступило (выставка «до 30 ноября» видна до 30 ноября);
- сеанс только с началом — пока не начался (плюс `AFISHA_PAST_GRACE_MINUTES`, по умолчанию 0);
- бессрочный сеанс (без дат) актуален всегда;
- у события убираются прошедшие сеансы; если не осталось ни одного — событие выбрасывается целиком;
- событие, у которого дат не было вовсе («дата уточняется»), остаётся — решение за бэкендом.

Бэкенду: из файла прошедшие события пропадают, но уже загруженные в БД записи сами не удалятся.
Их нужно скрывать по датам `occurrences` на стороне бэкенда.

## Установка для разработки (Windows)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env   # и впишите свой User-Agent
pytest
```

На Linux/macOS то же самое, только `python3.12 -m venv .venv` и `source .venv/bin/activate`.

## Команды

```bash
# какие города есть у источника — начните с этого
python -m afisha_parser cities kudago

# пробный прогон: 20 событий
python -m afisha_parser fetch kudago --city msk --limit 20

# полный сбор на 30 дней вперёд со скачиванием картинок
python -m afisha_parser fetch kudago --city msk --days 30 --download-images

# JSON Schema универсального дампа
python -m afisha_parser schema
```

Код выхода `1` означает, что источник не вернул ни одного события. В этом случае `latest.json` не перезаписывается.

## Что появляется в output/

```
output/
├── events/kudago/msk/
│   ├── 2026-09-17T12-00-00Z.json   ← результат каждого запуска
│   └── latest.json                  ← копия последнего
├── raw/kudago/msk/2026-09-17T12-00-00Z/
│   └── events-page-001.json         ← сырые ответы API, для отладки
├── evently/kudago/msk/latest.json   ← файл для бэкенда Evently (только актуальные события)
├── movies/kudago/msk/latest.json    ← трейлеры к кинопоказам KudaGo
├── movies/tmdb/ru/latest.json       ← фильмы в прокате и премьеры с трейлерами
├── images/ab/abcdef….jpg            ← картинки, имя = SHA-256 содержимого
├── images/index.json                ← какие ссылки уже скачаны
├── trailers/<id>.mp4                ← файлы трейлеров (если включено скачивание)
└── status.json                      ← итоги последнего цикла службы
```

Снимки прошлых запусков хранятся `AFISHA_KEEP_DAYS` дней (но не меньше трёх последних), сырые
ответы — `AFISHA_RAW_KEEP_DAYS`. `latest.json` не удаляется никогда.

## Контракт JSON

Полная схема: `schema/event-batch.schema.json` (генерируется командой `schema`). Источник правды — `src/afisha_parser/models.py`.

```json
{
  "schema_version": "1.1",
  "source": "kudago",
  "city": "msk",
  "fetched_at": "2026-09-17T12:00:00Z",
  "count": 1,
  "events": [
    {
      "source": "kudago",
      "source_id": "101",
      "source_url": "https://kudago.com/msk/event/…/",
      "ticket_url": null,
      "city": "msk",
      "title": "Концерт группы «Пример»",
      "short_title": "«Пример»",
      "tagline": null,
      "description": "Короткое описание",
      "full_text": "Полное описание",
      "categories": ["concert"],
      "tags": ["рок"],
      "age_restriction": "16+",
      "price": {"text": "от 1 500 до 3 000 рублей", "min": 1500, "max": 3000, "currency": "RUB", "is_free": false},
      "venue": {"source_id": "555", "name": "…", "address": "…", "lat": 55.75, "lon": 37.61, "subway": "…", "url": "…"},
      "sessions": [{"starts_at": "2026-09-25T19:00:00+03:00", "ends_at": "2026-09-25T22:00:00+03:00"}],
      "images": [{"url": "https://…", "credit_name": "…", "credit_url": null, "local_path": "images/ab/ab….jpg"}],
      "content_hash": "…"
    }
  ]
}
```

Договорённости:

- **Уникальный ключ** события — пара `source` + `source_id`. По нему делать upsert.
- **`content_hash`** не изменился — событие можно не обновлять.
- **Время** всегда ISO 8601 со смещением пояса города. `null` в `starts_at`/`ends_at` — дата не указана или событие бессрочное.
- **`sessions`** содержит только сеансы, которые ещё не закончились.
- **`local_path`** указывается относительно `output/`. Заполнен только при запуске с `--download-images` и успешном скачивании.
- **Изменения контракта.** Несовместимое изменение формата — повышаем `schema_version` и предупреждаем друг друга.

## Формат Evently

Универсальный дамп остаётся как есть. Формат импорта Evently строится из него отдельным слоем
`src/afisha_parser/exporters/evently.py` и сохраняется в `output/evently/<source>/<city>/`.

```bash
# собрать и сразу сохранить оба формата
python -m afisha_parser fetch kudago --city msk --evently

# перегнать уже собранный дамп, не обращаясь к источнику
python -m afisha_parser evently output/events/kudago/msk/latest.json

# JSON Schema формата Evently
python -m afisha_parser schema --format evently
```

Файл имеет вид `{"events": [...]}`. Соответствие полей:

| Универсальный дамп | Evently |
|---|---|
| `source_id` | `externalId` |
| `description` (короткое) | `shortDescription` |
| `full_text` | `description` |
| `source_url` | `sourceUrl` |
| `price.min` / `price.max` / `price.currency` / `price.is_free` | `priceMin` / `priceMax` / `currency` / `isFree` |
| `age_restriction` `"18+"` | `ageRating` `18` |
| `categories` | `categories` через таблицу `CATEGORY_MAPS` |
| `venue.source_id` / `lat` / `lon` | `venue.externalId` / `latitude` / `longitude` |
| `city` (slug) | `venue.city` (название) |
| `sessions[]` с известной датой начала | `occurrences[]` (`startsAt`, `endsAt`) |
| `images[].url` | `images[].url` |

Не передаются: `short_title`, `tagline`, `tags`, `subway`, `credit_*`, `local_path`, `content_hash`.
`ticketUrl` берётся из `ticket_url` (у KudaGo его нет — `null`, у Timepad — страница события). Сеансы без даты начала отбрасываются, у постоянных выставок `occurrences: []`.
Категории, которых нет в таблице, отбрасываются и перечисляются в логе — по нему таблицу и дополнять.
Стендап у KudaGo отдельной категорией не приходит, поэтому `standup` определяется по названию события.
Квизы и квесты в общей категории `entertainment` определяются по названию и тегам и попадают в `games`.
`stock` — не тема, а пометка «акция/скидка»: она игнорируется, а событие, у которого нет других категорий,
в файл Evently не попадает.

## Даты KudaGo

Адаптер запрашивает даты с `expand=dates` и разбирает их по флагам `is_startless` / `is_endless`.
Регулярные события с расписанием (`schedules`: дни недели и время) разворачиваются в конкретные сеансы
на горизонт `--days`. Нумерация дней недели задаётся константой `WEEKDAY_OFFSET` в `sources/kudago.py`.

## Афиша проката и трейлеры (TMDb)

KudaGo актуальный прокат не отдаёт, поэтому список фильмов в кинотеатрах берётся у TMDb:
`/movie/now_playing` и `/movie/upcoming` для региона `AFISHA_TMDB_REGION`. Для каждого фильма —
описание, жанры, длительность, возрастной рейтинг региона, постер и лучший трейлер
(сначала именно трейлер, а не тизер; сначала на языке `AFISHA_TMDB_LANGUAGE`).

```bash
python -m afisha_parser now-playing
jq -r '.movies[] | "\(.status) | \(.title) | \(.age_rating) | \(.trailer.url // "нет трейлера")"' \
  output/movies/tmdb/ru/latest.json
```

Результат — `output/movies/tmdb/ru/latest.json`. Сеансов кинотеатров там нет: расписаний кино
в открытом доступе нет, это отдельная задача.

У каждого трейлера есть `url` (страница YouTube) и `embed_url` (официальный плеер YouTube
для встраивания в приложение) — это основной способ показывать ролики.

### Скачивание файлов трейлеров

Включается `AFISHA_TRAILERS_DOWNLOAD=true` (нужен пакет `yt-dlp`: `pip install ".[trailers]"`,
для 720p — ещё `ffmpeg`). Файлы — `output/trailers/<id ролика>.mp4`, путь проставляется в
`trailer.local_path`. Каждый ролик качается один раз; за цикл не больше `AFISHA_TRAILERS_PER_RUN`;
ролик, который не скачался `MAX_FAILURES` раз подряд, больше не пробуется.

```bash
python -m afisha_parser now-playing --download-trailers
python -m afisha_parser trailers output/movies/tmdb/ru/latest.json --limit 3
```

**Права.** Трейлер — произведение прокатчика. Встраивать через `embed_url` можно без разрешений.
Хранить файл у себя и раздавать его пользователям можно только с разрешения правообладателя,
плюс это противоречит условиям YouTube. Поэтому скачивание по умолчанию выключено. Кроме того,
YouTube может блокировать загрузку с серверов (особенно из России), тогда в журнале будут
ошибки `Sign in to confirm you're not a bot` или таймауты.

## Трейлеры к кинопоказам источника

Для событий категории «кино» (`cinema` у KudaGo, «кино» у Timepad) парсер угадывает название фильма
по заголовку и ищет его в TMDb. Результат — `output/movies/<источник>/<город>/latest.json`.

Как угадывается название (`enrichers/title_guess.py`), от надёжного к менее надёжному:

- **надёжно** — кавычки сразу после «фильм», «показ», «кинопоказ», «сериал» и т. п.:
  «Кинопоказ фильма «ИДИОТ»» → «Идиот»;
- **угадано** — кусок заголовка Timepad между « | », который не дата, не площадка и не программа:
  «Программа «Мой музей» | ДВОРЕЦ ГРЕЗ | 3 октября | Киноцентр «ВАВИЛОН»» → «Дворец грез»;
  название до года без кавычек: «Сумерки: Сага (2008)».

Кавычки после «программа», «фестиваль», «центр», «клуб», «лекторий» и т. п. — не фильм и не ищутся.

Как принимается совпадение (`enrichers/tmdb_trailers.py`):

1. Точное совпадение с фильмом из текущего проката (`movies/tmdb/ru`) — сразу, без поиска (`matched_by: "catalog"`).
2. Иначе поиск в TMDb. Для надёжного названия нужно сходство ≥ `MIN_TITLE_SCORE` (0.72), для угаданного —
   ≥ `MIN_SCORE_MEDIUM` (0.9, почти точное). Регистр, «ё» и знаки препинания при сравнении не учитываются.
3. Год из заголовка сверяется с годом выхода; одноимённые фильмы без года — по правилам ниже.
4. Если в заголовке «сериал» или «N сезон» — сначала ищется сериал (`media_type: "tv"`).

Один и тот же фильм в разных городах и источниках ищется в TMDb один раз за цикл (кеш).
В `movies` каждого совпадения есть `guess_strength` и `match_score` — по ним удобно проверять качество.
Пропуски с причиной пишутся в журнал: `journalctl -u afisha-parser | grep "нет уверенного"`.

Одноимённые фильмы («Вий» 1909, 1967 и 2014) различаются по году из заголовка события.
Если года нет: у показа с тегом «ретро» рассматриваются только фильмы до 2000 года,
из оставшихся берётся самый известный по числу голосов в TMDb — но только если он
явно лидирует. Иначе совпадение считается неоднозначным и пропускается.

## Как добавить источник

1. Создать `src/afisha_parser/sources/<имя>.py` с классом-наследником `SourceAdapter`: атрибут `name` и метод `fetch_events`, который отдаёт `Event`.
2. Разбор одной записи вынести в чистую функцию (как `parse_event` у KudaGo), чтобы тестировать её на сохранённом ответе без сети.
3. Добавить класс в `ADAPTERS` в `sources/__init__.py`.
4. Положить пример ответа в `tests/fixtures/` и написать тесты.
