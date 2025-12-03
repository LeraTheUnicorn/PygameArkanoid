# Диаграмма архитектуры AI-системы

```mermaid
classDiagram
    class AIPlayer {
        -trajectory_predictor: TrajectoryPredictor
        -position_optimizer: PositionOptimizer
        -learning_system: LearningSystem
        -performance_logger: PerformanceLogger
        -game_state: GameState
        -targeting_system: dict
        -loop_prevention_system: dict
        +update_game_state(ball, paddle, bricks)
        +get_optimal_position(): int
        +learn_from_action(success: bool)
        +log_performance()
        +_find_best_target_brick(): Dict
        +_detect_loop_pattern(): bool
        +_change_strategy_if_looping()
    }

    class TrajectoryPredictor {
        -physics: PhysicsEngine
        +predict_trajectory(ball, paddle_position): List[Point]
        +calculate_bounce_point(ball, paddle_position): Point
        +predict_after_bounce(ball, bounce_point): List[Point]
    }

    class PositionOptimizer {
        -target_cubes: List[pygame.Rect]
        +find_optimal_position(ball, bricks): int
        +calculate_bounce_angle(target_brick): float
        +evaluate_success_probability(position, target_brick): float
    }

    class LearningSystem {
        -model_data: dict
        -learning_rate: float
        +update_strategy(action_result: dict)
        +get_strategy_adjustment(): dict
        +save_model()
        +load_model()
    }

    class PerformanceLogger {
        -log_file: str
        -session_data: dict
        +log_action(action: dict)
        +log_result(result: dict)
        +analyze_performance()
        +generate_report()
        +test_json_serialization()
    }

    class TargetingSystem {
        -target_brick: Dict
        -optimal_offset: float
        -successful_hits: List[Dict]
        -brick_map: Dict
        -brick_coordinates: List[Dict]
        -visible_targets: List[Dict]
        -hit_patterns: Dict
        +_update_brick_map()
        +_update_visible_targets()
        +_find_best_target_brick(): Dict
        +_find_best_target_for_few_bricks(): Dict
        +_calculate_optimal_offset(): float
        +_adjust_offset_from_history(): float
        +record_hit_result()
    }

    class LoopPreventionSystem {
        -movement_history: List[int]
        -position_history: List[int]
        -trajectory_history: List[Dict]
        -alternative_strategies: List[str]
        -loop_detection_threshold: int
        -strategy_change_cooldown: int
        +_detect_loop_pattern(): bool
        +_change_strategy_if_looping()
        +_apply_alternative_strategy(): int
        +_reevaluate_after_bounce()
        +_update_loop_tracking()
    }

    class CeilingBounceSystem {
        +_handle_ceiling_bounce_positioning(): int
        +_track_ball_position(): float
    }

    class GameState {
        +ball_position: Point
        +ball_velocity: Point
        +paddle_position: Point
        +remaining_bricks: List[pygame.Rect]
        +game_score: int
        +game_time: int
    }

    AIPlayer --> TrajectoryPredictor
    AIPlayer --> PositionOptimizer
    AIPlayer --> LearningSystem
    AIPlayer --> PerformanceLogger
    AIPlayer --> GameState
    AIPlayer --> TargetingSystem
    AIPlayer --> LoopPreventionSystem
    AIPlayer --> CeilingBounceSystem
    PositionOptimizer --> GameState
    TrajectoryPredictor --> GameState
    TargetingSystem --> GameState
    LoopPreventionSystem --> GameState
    CeilingBounceSystem --> GameState
```

## Поток данных в системе

```mermaid
flowchart TD
     A[Обновление состояния игры] --> B[AIPlayer.update_game_state]
     B --> C[_update_brick_map]
     B --> D[_update_visible_targets]
     C --> E[TrajectoryPredictor.predict_trajectory]
     D --> E

     E --> F[Расчет траектории падения]
     F --> G[Предсказание отскока]
     G --> H[Траектория после отскока]

     H --> I{Мяч от потолка?}
     I -->|Да| J[CeilingBounceSystem.handle_positioning]
     I -->|Нет| K[PositionOptimizer.find_optimal_position]

     K --> L[Анализ целевых кубиков]
     L --> M{Мало кубиков ≤5?}
     M -->|Да| N[_find_best_target_for_few_bricks]
     M -->|Нет| O[Анализ видимых целей]
     N --> P[Расчет оптимального угла]
     O --> P
     P --> Q[Выбор лучшей позиции]

     Q --> R[Предотвращение вертикальных ударов]
     R --> S[Проверка зацикливания]
     S --> T{Зацикливание?}
     T -->|Да| U[Смена стратегии с кулдауном]
     T -->|Нет| V[Применение текущей стратегии]
     U --> W[Применение альтернативной стратегии]
     V --> W
     W --> X[Строгое ограничение границ]

     J --> X
     X --> Y[Получение команды движения]

     H --> Y
     Y --> Z[Движение платформы]

     Z --> AA[Выполнение действия]
     AA --> BB[Оценка результата]
     BB --> CC[Переоценка после отбития]
     CC --> DD[LearningSystem.update_strategy]
     DD --> EE[PerformanceLogger.log_action]

     EE --> FF[Проверка условий игры]
     FF --> GG{Игра завершена?}
     GG -->|Нет| A
     GG -->|Да| HH[Сохранение итогов]
     HH --> II[Генерация отчета]
```

## Алгоритм принятия решений

```mermaid
flowchart TD
     A[Получение текущего состояния] --> B{Мяч падает?}
     B -->|Да| C[Анализ траектории и карты кубиков]
     B -->|Нет| D{Мяч у потолка?}
     D -->|Да| E[Специальная логика отскоков от потолка]
     D -->|Нет| F[Следим за мячом с упреждением]

     C --> G[Обновление видимых целей]
     G --> H[Поиск оптимальной позиции]
     H --> I{Мало кубиков ≤5?}
     I -->|Да| J[Приоритет нижним кубикам]
     I -->|Нет| K[Анализ по видимости и расстоянию]
     J --> L[Расчет смещения для прицеливания]
     K --> L

     L --> M[Предотвращение вертикальных ударов]
     M --> N[Проверка зацикливания 80%]
     N --> O{Зацикливание?}
     O -->|Да| P[Смена стратегии с кулдауном]
     O -->|Нет| Q[Применение текущей стратегии]
     P --> R[Альтернативная стратегия]
     Q --> R

     R --> S[Строгое ограничение границ ±5px]
     S --> T[Расчет пути движения]

     E --> T
     F --> T
     T --> U[Движение к цели]
     U --> V[Корректировка позиции]
     V --> W[Отскок мяча]

     W --> X[Оценка результата]
     X --> Y{Попали в кубик?}
     Y -->|Да| Z[Запись успешного удара]
     Y -->|Нет| AA[Анализ неудачи]
     Z --> BB[Обновление паттернов попаданий]
     AA --> BB
     BB --> CC[Переоценка после отбития]
     CC --> DD[Корректировка стратегии]
     DD --> EE[Сохранение данных обучения]
     EE --> FF[Следующий ход]
```

## Физическая модель траектории и система предотвращения зацикливания

```mermaid
graph TB
     subgraph "Разделительная зона"
         A[Мяч в движении] --> B[Расчет траектории с отскоками от стен]
         B --> C[Определение точки пересечения]
         C --> D[Точка контакта с платформой]
     end

     subgraph "Анализ состояния"
         D --> E[Обновление карты кубиков]
         E --> F[Определение видимых целей]
         F --> G[Анализ отскока от потолка]
     end

     subgraph "Отскок и прицеливание"
         G --> H{От потолка?}
         H -->|Да| I[Специальная логика потолка]
         H -->|Нет| J[Расчет угла отражения]
         I --> K[Предотвращение симметрии]
         J --> K
         K --> L[Новая траектория]
         L --> M[Поиск целевых кубиков]
     end

     subgraph "Интеллектуальный выбор цели"
         M --> N{≤5 кубиков?}
         N -->|Да| O[Приоритет нижним кубикам]
         N -->|Нет| P[Анализ по видимости]
         O --> Q[Расчет смещения для завершения]
         P --> Q
         Q --> R[Предотвращение вертикальных ударов]
     end

     subgraph "Усиленная проверка зацикливания"
         R --> S[Анализ паттернов 80%]
         S --> T[Проверка позиционной стагнации]
         T --> U[Анализ вертикальных траекторий]
         U --> V{Зацикливание?}
         V -->|Да| W[Смена стратегии с кулдауном]
         V -->|Нет| X[Текущая стратегия]
         W --> Y[Альтернативная стратегия]
         X --> Y
     end

     subgraph "Финальная оптимизация"
         Y --> Z[Строгое ограничение границ ±5px]
         Z --> AA[Выбор оптимальной позиции]
         AA --> BB[Корректировка стратегии]
         BB --> CC[Обучение на результате]
     end
```

Эти диаграммы показывают:

1. **Структуру классов** - как компоненты системы взаимодействуют друг с другом
1. **Поток данных** - как информация движется через систему с учетом новых компонентов
1. **Алгоритм принятия решений** - обновленную логику работы AIPlayer с версией 2.1.0
1. **Физическую модель** - расширенную модель траектории с анализом отскоков от потолка

Ключевые принципы версии 2.1.0:

- **Модульность** - каждый компонент отвечает за свою область с четким разделением ответственности
- **Обучение** - система улучшается на основе опыта с сохранением паттернов попаданий
- **Физическая точность** - используются реальные законы физики с учетом отскоков от потолка
- **Оптимизация** - поиск наилучших решений на основе вероятностей и видимости целей
- **Устойчивость** - предотвращение зацикливания с порогом 80% и позиционной стагнацией
- **Адаптивность** - специальная логика для различных сценариев (мало кубиков, отскоки от потолка)
- **Точность** - строгое ограничение границ экрана и предотвращение вертикальных ударов
