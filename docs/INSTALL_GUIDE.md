# 📋 Полная инструкция по установке зависимостей для игры Арканоид

## 🎯 Проблема
Вы скачали проект игры Арканоид, но он не запускается? Это происходит потому, что не установлены необходимые зависимости (библиотеки Python). Мы создали автоматические скрипты для решения этой проблемы.

## 🚀 Быстрая установка (РЕКОМЕНДУЕТСЯ)

### Для Windows:
1. **Скачайте и установите Python** (если еще не установлен):
   - Перейдите на https://www.python.org/downloads/
   - Скачайте последнюю версию Python
   - **ВАЖНО**: При установке обязательно поставьте галочку "Add Python to PATH"
   - Перезапустите компьютер после установки

2. **Запустите автоматический скрипт**:
   - Дважды щёлкните по файлу `install_dependencies.bat`
   - Следуйте инструкциям на экране
   - Дождитесь завершения установки

**⚠️ Если нет интерпретатора bash (Windows без WSL/Git Bash):**
Используйте командную строку Windows:
```cmd
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```
2. **Сделайте скрипт исполняемым и запустите**:
   ```bash
   chmod +x install_dependencies.sh
   ./install_dependencies.sh
   ```

## 🔧 Ручная установка (если автоматические скрипты не работают)

### Шаг 1: Обновите pip
```bash
python -m pip install --upgrade pip
```
или для Linux/Mac:
```bash
python3 -m pip install --upgrade pip
```

### Шаг 2: Установите зависимости
```bash
python -m pip install -r requirements.txt
```

### Ошибка: "Failed to build 'pygame'" (Python 3.14)

Эта ошибка возникает на Python 3.14, потому что pygame еще не имеет готовых бинарных пакетов для этой версии.

**Решения:**

**1. Используйте совместимую версию Python (рекомендуется):**
```bash
# Установите Python 3.11 или 3.12
# Скачайте с: https://www.python.org/downloads/
```

**2. Установите готовый .exe файл (самый простой способ):**
- Запустите: `Arkanoid_v2.2.0001.exe` (или последнюю версию)
- Не требует установки Python или зависимостей!

**3. Установите Anaconda:**
```bash
# Скачайте с: https://www.anaconda.com/
# Включает готовые пакеты для научных вычислений
```


## 📦 Список зависимостей
В проекте используются следующие библиотеки:
- **pygame** (2.5.2) - для создания игр
- **numpy** (2.1.0) - для математических вычислений
- **pytest** (7.4.4) - для тестирования (опционально)

## ⚡ Альтернативный способ через Poetry

Если вы хотите использовать Poetry (как задумано изначально):

1. **Установите Poetry**:
   ```bash
   # Windows
   (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
   
   # Linux/Mac
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. **Установите зависимости**:
   ```bash
   poetry install
   ```

3. **Активируйте виртуальное окружение**:
   ```bash
   poetry shell
   ```

4. **Запустите игру**:
   ```bash
   poetry run python PyGameBall.py
   ```

## 🎮 Запуск игры

После успешной установки зависимостей запустите игру:

### Способ 1: Обычная игра
```bash
python PyGameBall.py
```

### Способ 2: Игра с ИИ
```bash
python PyGameBall.py --ai
```

## 🆘 Устранение неполадок

### Ошибка: "Python не найден"
- Убедитесь, что Python установлен
- При установке отметьте "Add Python to PATH"
- Перезапустите командную строку после установки

### Ошибка: "pip не найден"
```bash
python -m ensurepip --upgrade
```

### Ошибка: "Отказано в доступе"
- **Windows**: Запустите командную строку от имени администратора
- **Linux/Mac**: Добавьте `sudo` перед командами pip

### Ошибка: "Модуль не найден"
- Убедитесь, что вы в правильной папке проекта
- Переустановите зависимости:
  ```bash
  python -m pip install --force-reinstall -r requirements.txt
  ```

### Ошибка: "Нет модуля pygame"
```bash
python -m pip install pygame --upgrade
```

## 📋 Проверка установки

Выполните эти команды для проверки:
```bash
python -m pip list | findstr pygame  # Windows
python -m pip list | grep pygame     # Linux/Mac
```

Должно показать установленную версию pygame.

## 💡 Полезные команды

### Создание виртуального окружения (рекомендуется)
```bash
python -m venv venv

# Активация:
# Windows:
venv\\Scripts\\activate
# Linux/Mac:
source venv/bin/activate

# Установка в окружение:
pip install -r requirements.txt
```

### Обновление всех пакетов
```bash
python -m pip install --upgrade -r requirements.txt
```

### Удаление всех пакетов проекта
```bash
python -m pip uninstall -r requirements.txt -y
```

## 📞 Нужна помощь?

Если ничего не помогает:
1. Убедитесь, что используете последнюю версию Python (3.11+)
2. Попробуйте переустановить Python с опцией "Add to PATH"
3. Проверьте интернет-соединение
4. Запустите от имени администратора (Windows)

---

**Примечание**: Эта игра написана на Python с использованием библиотеки Pygame. Все необходимые файлы включены в архив проекта.