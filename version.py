"""
Централизованное управление версией проекта Арканоид

Этот файл является единственным источником истины для версии проекта.
Все остальные файлы должны импортировать версию отсюда.
"""

# Версия в формате X.Y.ZZZZ
# X - мажорная версия (революционные изменения)
# Y - минорная версия (новые функции, исправления UI)
# ZZZZ - 4-значный индекс сборки (увеличивается при каждом изменении)

VERSION = "2.2.0004"

# Разделение версии на компоненты для удобства
VERSION_MAJOR = 2
VERSION_MINOR = 2
VERSION_BUILD = 4  # 4-значный индекс, но храним как число

# Полная версия для отображения
VERSION_FULL = VERSION

# Версия для сборки (без точки перед индексом)
VERSION_BUILD_STRING = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_BUILD:04d}"

def get_version():
    """Возвращает текущую версию"""
    return VERSION

def get_version_tuple():
    """Возвращает версию как кортеж (major, minor, build)"""
    return (VERSION_MAJOR, VERSION_MINOR, VERSION_BUILD)

def get_version_string():
    """Возвращает версию как строку в формате X.Y.ZZZZ"""
    return VERSION_BUILD_STRING
