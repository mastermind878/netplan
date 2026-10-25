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
процесса Git/MSYS. Поэтому проверена чистая копия из git archive; установка после
клонирования с GitHub и Linux CI пока не подтверждены.

Для публикации ещё требуется доступ к GitHub владельца. Публичность репозитория,
зелёный Actions run и наличие удалённого artifact пока не подтверждены.
