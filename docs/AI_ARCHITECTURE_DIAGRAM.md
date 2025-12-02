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
        -hit_patterns: Dict
        +_find_best_target_brick(): Dict
        +_calculate_optimal_offset(): float
        +_adjust_offset_from_history(): float
        +record_hit_result()
    }

    class LoopPreventionSystem {
        -movement_history: List[int]
        -position_history: List[int]
        -trajectory_history: List[Dict]
        -alternative_strategies: List[str]
        +_detect_loop_pattern(): bool
        +_change_strategy_if_looping()
        +_apply_alternative_strategy(): int
        +_reevaluate_after_bounce()
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
    PositionOptimizer --> GameState
    TrajectoryPredictor --> GameState
    TargetingSystem --> GameState
```

## Поток данных в системе

```mermaid
flowchart TD
    A[Обновление состояния игры] --> B[AIPlayer.update_game_state]
    B --> C[TrajectoryPredictor.predict_trajectory]
    B --> D[PositionOptimizer.find_optimal_position]
    
    C --> E[Расчет траектории падения]
    E --> F[Предсказание отскока]
    F --> G[Траектория после отскока]
    
    D --> H[Анализ целевых кубиков]
    H --> I[Расчет оптимального угла]
    I --> J[Выбор лучшей позиции]
    
    J --> K[Проверка зацикливания]
    K --> L{Зацикливание?}
    L -->|Да| M[Смена стратегии]
    L -->|Нет| N[Применение текущей стратегии]
    M --> O[Применение альтернативной стратегии]
    N --> O
    O --> P[Получение команды движения]
    
    G --> P
    P --> Q[Движение платформы]
    
    Q --> R[Выполнение действия]
    R --> S[Оценка результата]
    S --> T[Переоценка после отбития]
    T --> U[LearningSystem.update_strategy]
    U --> V[PerformanceLogger.log_action]
    
    V --> W[Проверка условий игры]
    W --> X{Игра завершена?}
    X -->|Нет| A
    X -->|Да| Y[Сохранение итогов]
    Y --> Z[Генерация отчета]
```

## Алгоритм принятия решений

```mermaid
flowchart TD
    A[Получение текущего состояния] --> B{Мяч падает?}
    B -->|Да| C[Анализ траектории]
    B -->|Нет| D[Ожидание]
    
    C --> E[Поиск оптимальной позиции]
    E --> F[Проверка доступности позиции]
    F --> G[Расчет пути движения]
    
    G --> H[Движение к цели]
    H --> I[Корректировка позиции]
    I --> J[Отскок мяча]
    
    J --> K[Оценка результата]
    K --> L{Попали в кубик?}
    L -->|Да| M[Обновление успешности]
    L -->|Нет| N[Обновление неудач]
    
    M --> O[Корректировка стратегии]
    N --> O
    O --> P[Сохранение данных]
    P --> Q[Следующий ход]
```

## Физическая модель траектории и система предотвращения зацикливания

```mermaid
graph TB
    subgraph "Разделительная зона"
        A[Мяч в движении] --> B[Расчет траектории]
        B --> C[Определение точки пересечения]
        C --> D[Точка контакта с платформой]
    end
    
    subgraph "Отскок"
        D --> E[Расчет угла отражения]
        E --> F[Новая траектория]
        F --> G[Поиск целевых кубиков]
    end
    
    subgraph "Прицеливание"
        G --> H[Анализ целевых кубиков]
        H --> I[Расчет оптимального смещения]
        I --> J[Проверка зацикливания]
    end
    
    subgraph "Предотвращение зацикливания"
        J --> K{Обнаружено зацикливание?}
        K -->|Да| L[Смена стратегии]
        K -->|Нет| M[Применение текущей стратегии]
        L --> N[Переоценка после отбития]
        M --> N
    end
    
    subgraph "Оптимизация"
        N --> O[Выбор оптимальной позиции]
        O --> P[Корректировка стратегии]
    end
```

Эти диаграммы показывают:

1. **Структуру классов** - как компоненты системы взаимодействуют друг с другом
1. **Поток данных** - как информация движется через систему
1. **Алгоритм принятия решений** - логику работы AIPlayer
1. **Физическую модель** - как рассчитывается траектория и отскок

Ключевые принципы:

- **Модульность** - каждый компонент отвечает за свою область
- **Обучение** - система улучшается на основе опыта
- **Физическая точность** - используются реальные законы физики
- **Оптимизация** - поиск наилучших решений на основе вероятностей
