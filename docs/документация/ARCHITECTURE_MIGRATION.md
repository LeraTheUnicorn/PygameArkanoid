# Руководство по миграции на новую архитектуру

## Обзор изменений

Проект был рефакторирован с применением следующих паттернов и улучшений:

1. **Централизованная конфигурация** - все константы вынесены в `game_config.py`
2. **MVC архитектура** - разделение на модели, представления и контроллеры
3. **Оптимизация отрисовки** - система "грязных прямоугольников" (dirty rects)
4. **Dependency Injection** - контейнер зависимостей для улучшения тестируемости

## Структура файлов

### Новые файлы

- `game_config.py` - все константы игры
- `game_models.py` - модели данных (Ball, Paddle, GameState)
- `game_views.py` - представления для отрисовки
- `game_controllers.py` - контроллеры игровой логики
- `dirty_rects.py` - система оптимизации отрисовки
- `di_container.py` - контейнер для Dependency Injection

### Основной файл

- `PyGameBall.py` - обновлен для использования констант из `game_config.py`

## Использование новой архитектуры

### Пример 1: Использование DI контейнера

```python
from di_container import DIContainer

# Инициализация
container = DIContainer()
container.init_pygame()

# Получение зависимостей
screen = container.get_screen()
game_controller = container.get_game_controller()
bricks_view = container.get_bricks_view()
```

### Пример 2: Использование контроллеров

```python
from game_controllers import GameController
from game_models import Ball, GameState, Paddle
from settings import SettingsManager

# Создание объектов
game_state = GameState()
ball = Ball()
paddle = Paddle()
settings_manager = SettingsManager()

# Создание контроллера
controller = GameController(game_state, ball, paddle, settings_manager)

# Использование
controller.build_bricks()
controller.update_ball()
controller.handle_ball_brick_collision()
```

### Пример 3: Использование представлений с оптимизацией

```python
from dirty_rects import DirtyRectManager
from game_views import BricksView, BallView, PaddleView, HUDView

# Создание менеджера грязных прямоугольников
dirty_rects = DirtyRectManager(800, 600)

# Создание представлений
bricks_view = BricksView(screen, dirty_rects)
ball_view = BallView(screen, dirty_rects)
paddle_view = PaddleView(screen, dirty_rects)

# Отрисовка
bricks_view.draw(bricks)
ball_view.draw(ball, old_ball_rect)
paddle_view.draw(paddle, old_paddle_rect)

# Обновление экрана (только измененные области)
dirty_rects.update_display(screen)
```

## Постепенная миграция

Текущий код в `PyGameBall.py` продолжает работать, но теперь использует константы из `game_config.py`.

Для полной миграции на новую архитектуру:

1. Замените прямые вызовы функций на использование контроллеров
2. Замените функции отрисовки на использование View классов
3. Используйте DI контейнер для управления зависимостями
4. Включите оптимизацию отрисовки через DirtyRectManager

## Преимущества новой архитектуры

1. **Тестируемость** - легко создавать mock объекты через DI
2. **Поддерживаемость** - четкое разделение ответственности
3. **Производительность** - оптимизация отрисовки через dirty rects
4. **Гибкость** - легко изменять конфигурацию в одном месте

## Обратная совместимость

Старый код продолжает работать. Все константы доступны через импорт из `game_config.py`.
