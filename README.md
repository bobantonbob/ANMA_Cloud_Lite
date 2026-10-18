# ANMA Cloud Lite v0.3.0

Django-кабінет для моніторингу кількох Home Assistant через приватну мережу Tailscale. Публічний вхід — Google або пошта й пароль із підтвердженням пошти. Інтеграція ANMA видає одноразовий код; сайт підтверджує його на потрібній машині й створює окреме підключення лише для читання.

## Локальний сценарій

Детальна інструкція: [Google, встановлення інтеграції та прив’язка без термінала](docs/LOCAL_PAIRING.md).

- `/login/` — Google або пошта й пароль.
- `/register/` — реєстрація з підтвердженням пошти.
- `/accounts/password/reset/` — відновлення пароля.
- `/app/homes/` — власні будинки та доступні користувачу об’єкти.
- `/app/add/` — назва, Tailscale IP, код інтеграції.
- `/app/?plant=ID` — потоки енергії й показники вибраного будинку.
- `/admin/` — операційний центр ANMA: власники, машини, останні дані, пошук і доступи.

## Запуск розробника

Потрібні Python 3.13 та мережевий доступ із сервера до HA через Tailscale.

```sh
python -m venv .venv
# Активуйте .venv для вашої ОС.
python -m pip install -r requirements.txt
# Скопіюйте .env.example у .env та встановіть випадковий DJANGO_SECRET_KEY.
python manage.py prepare_local
python manage.py migrate --fake-initial
python manage.py collectstatic --noinput
python manage.py runserver 127.0.0.1:8095
```

`prepare_local` створює відсутній ключ шифрування підключень та резервну копію SQLite, не друкуючи секретів. Для Google заповніть `GOOGLE_CLIENT_ID` і `GOOGLE_CLIENT_SECRET`; callback для локального запуску — `http://127.0.0.1:8095/accounts/google/login/callback/`, для production — `https://cloud.anma-electric.com.ua/accounts/google/login/callback/`. Перезапустіть Django після зміни .env. Без OAuth-параметрів кнопка Google не активується; вхід поштою й паролем доступний окремо.

Для нової інсталяції адміністратора створюють `python manage.py createsuperuser`. Існуючих користувачів та адміністраторів міграції зберігають. `0001_initial` описує старі таблиці, створені раніше без міграцій; `--fake-initial` лише реєструє їх, коли вони вже існують. Наступна міграція додає таблиці, нічого не видаляючи.

`.env` автоматично читається через python-dotenv. У production використовуйте HTTPS, окремі секрети й налаштовані дозволені хости. Docker-файли збережені; конфігурація мережі Tailscale для контейнера потребує перевірки перед деплоєм. Деплой у цій версії не виконувався.

## Структура

- `dashboard/models.py`: Plant, EntityMapping, PlantAccess; нові HAConnection, PairingAttempt, TelemetrySample.
- `dashboard/services/pairing.py`: перевірка IP, обмін кодом, шифрування ключа, адаптер окремої машини.
- `dashboard/services/home_assistant.py`: збережений REST-адаптер старої локальної станції.
- `dashboard/auth.py`: перевірка підтвердженої Google-пошти; поштову реєстрацію та підтвердження обробляє allauth.
- `dashboard/admin_site.py`, `templates/admin/`: огляд адміністрування з перевіркою дозволів.
- `ha_integration/custom_components/anma_cloud/`: HA-інтеграція, пошук сутностей, поточні значення, код і scoped API.
- `templates/`, `static/`: наявний Django UI, без зміни frontend-фреймворку.

Ключі підключень зашифровані Fernet, код не зберігається сутністю HA. Google-паролі не передаються сайту; паролі адміністратора хешує Django. HTTP API приймає тільки Tailscale IPv4 на 8123, без redirects та проксі. Мережева ізоляція HA задається Tailscale ACL/firewall. Адреса сама собою не є доказом доступу.

## Сумісність і дані

Наявні Plant ID, власники, спільні доступи, URL та налаштування `HA_URL/HA_TOKEN/HA_PLANT_ID` збережені. Старе підключення обмежене одним явно вказаним об’єктом. Нові підключення не використовують його токен чи інверсію; знак нормалізує сама інтеграція.

Демо залишається явним режимом. Помилки Live ніколи не замінюються демо. Нові графіки накопичують тільки отримані сайтом знімки, а не імпортують минулу історію HA. Докладні обмеження — у локальній інструкції.

## Перевірки

```sh
python -m pip install -r requirements-dev.txt
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test dashboard
python ha_integration/tests/test_mapping.py
python ha_integration/tests/test_connector.py
python manage.py collectstatic --noinput
```

Тести HA використовують справжні обробники поверх aiohttp, але замінюють host API Home Assistant. Повний Google round trip і запуск інтеграції у другому реальному HA потрібно перевірити після налаштування OAuth та встановлення пакета.

## Пакети та майбутній репозиторій

```sh
python ha_integration/tools/build_release.py
python tools/build_source_release.py
```

Перша команда збирає лише компонент HA та інструкцію. Друга — allowlist вихідних файлів для майбутнього репозиторію. В архів не потрапляють .env, БД, резервні копії, .venv, тестові скриншоти та ключі. `requirements.lock` фіксує перевірені Python-залежності; `requirements-dev.txt` додає інструменти тестування.

GitHub Actions підготовлено для перевірок після створення репозиторію. Git/GitHub-репозиторій, HACS-публікація й production-деплой ще не створені. Не завантажуйте весь робочий каталог вручну: використайте підготовлений source ZIP або перевірений список файлів.

## Пошта для реєстрації

Парольна реєстрація вимагає підтвердження адреси. Налаштуйте EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, DEFAULT_FROM_EMAIL та TLS/SSL у локальній .env. Для SMTP встановіть DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend. При DEBUG=1 без цього параметра лист із посиланням друкується в консоль Django; це лише локальний режим, лист не надсилається. Секрети не додавайте до Git. Наявні користувачі та їхні будинки збережені.

## Server updates (one command)

From the existing Linux server checkout, run:

```sh
bash deploy.sh
```

For the first update that introduces this script, run:

```sh
git pull --ff-only && bash deploy.sh
```

The script updates the website from its upstream branch, checks out the integration release pinned in `integration-version.txt`, builds the Docker image (including static assets), checks Django, stops the web service, backs up SQLite into `.backups/`, applies migrations, and starts the service with a health check. Expect a short interruption during backup and migrations. Existing `.env`, database, port bindings, and credentials are preserved.

Requires Bash, Git, `flock`, and Docker Compose v2 with `up --wait`. Run as the server checkout owner with Docker permissions. Tracked local changes stop deployment rather than being overwritten. An existing `ha_integration` directory must be a clean clone of `https://github.com/bobantonbob/anma-cloud.git`.

If deployment fails after the service stops, inspect the reported error and backup path before restarting. Database rollback is deliberately manual. Keep `.backups/` private; backups contain account and connection data. This command does not configure DNS, HTTPS, Tailscale, or initial server setup.
