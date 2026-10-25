# Локальная проверка

Проверено 25 октября 2026 года на Windows, Python 3.12.14.

- Исходники извлечены через `git archive` в отдельную чистую папку.
- Создано отдельное виртуальное окружение без доступа к пакетам рабочего окружения.
- Зависимости установлены из requirements-dev.txt с constraints.txt.
- `python -m pytest -v`: 36 passed, 1 warning.
- `python scripts/smoke.py`: HTTP smoke check passed: health, split, version, docs.
- `pip check`: No broken requirements found.
- Предупреждение Starlette об устаревающем alias AnyIO не мешает тестам;
  оно не скрывается настройками pytest.

Особенность проверяющей среды: bundled Python не смог выполнить ensurepip,
поэтому pip другого Python использован с параметром --python для установки
в изолированное окружение. В обычной установке Python 3.12 используется
стандартная команда venv из README.

Команда git clone в проверяющей Windows-среде не выполнилась из-за ошибки прав
процесса Git/MSYS. Поэтому проверена чистая копия из git archive; проверка checkout, установки и запуска на Linux выполнена отдельно в GitHub Actions (см. ниже).

## Проверка на GitHub

Публичный репозиторий: https://github.com/mastermind878/netplan .
Успешный запуск на Ubuntu / Python 3.12 после checkout:
https://github.com/mastermind878/netplan/actions/runs/40232514724 .

Установка зависимостей, pip check, 36 тестов, HTTP smoke check и упаковка
завершились успешно. Artifact netplan-source создан, не просрочен.
Первый artifact: 12613467370, размер 17385 байт.

Локальные этапы разработки импортированы через GitHub API с указанием исходных
хешей в сообщениях. У удалённых коммитов другие хеши и время импорта.
Оригинальные локальные коммиты остаются в локальном архиве.
