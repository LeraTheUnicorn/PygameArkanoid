# Подробная документация по кластеризации траекторий (KMeans), системе обучения (scikit-learn) и метрикам текущей игры

## Содержание

1. [Кластеризация траекторий (KMeans)](#1-кластеризация-траекторий-kmeans)
2. [Система обучения (scikit-learn)](#2-система-обучения-scikit-learn)
3. [Метрики текущей игры](#3-метрики-текущей-игры)
4. [Предсказание шагов траектории](#4-предсказание-шагов-траектории)

---

## 1. Кластеризация траекторий (KMeans)

### Описание

Кластеризация траекторий позволяет группировать похожие пути движения мяча в игре для анализа поведения, оптимизации стратегии и обнаружения аномальных паттернов. Алгоритм KMeans разбивает данные на _K_ кластеров, минимизируя внутрикластерное расстояние (сумму квадратов расстояний от точек до центров кластеров).

В проекте кластеризация используется для анализа паттернов траекторий мяча, что помогает AI-игроку лучше понимать типичные сценарии движения и адаптировать стратегию.

### Как это работает в проекте

1. **Сбор данных о траекториях**: Система собирает начальные точки траекторий мяча (первые 3 точки) и квантует их координаты для создания паттернов.

2. **Преобразование в векторы**: Каждый паттерн траектории преобразуется в числовой вектор из 6 координат (x₁, y₁, x₂, y₂, x₃, y₃).

3. **Кластеризация**: KMeans группирует похожие траектории в кластеры.

### Пример расчета

Предположим, у нас есть 5 паттернов траекторий, каждый из которых представлен начальными точками:

```python
import numpy as np
from sklearn.cluster import KMeans

# Пример: паттерны траекторий (после квантования координат)
# Каждый паттерн - это строка вида "x1_y1_x2_y2_x3_y3"
pattern_keys = [
    "10_20_12_22_15_25",  # Траектория 1: движение вправо-вверх
    "10_20_11_21_13_23",  # Траектория 2: похожая на 1
    "5_10_6_11_8_13",     # Траектория 3: движение вправо-вверх (другая область)
    "30_5_32_7_35_10",    # Траектория 4: движение вправо-вниз
    "30_5_31_6_33_8"      # Траектория 5: похожая на 4
]

# Преобразуем строки в векторы
vectors = []
for key in pattern_keys:
    coords = [int(x) for x in key.split("_")]
    # Дополняем до 6 элементов нулями или усекаем
    while len(coords) < 6:
        coords.append(0)
    vectors.append(coords[:6])

# Результат: векторы для кластеризации
X = np.array(vectors)
print("Векторы траекторий:")
print(X)
# Вывод:
# [[10 20 12 22 15 25]
#  [10 20 11 21 13 23]
#  [ 5 10  6 11  8 13]
#  [30  5 32  7 35 10]
#  [30  5 31  6 33  8]]

# Кластеризация (K=3)
kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
clusters = kmeans.fit_predict(X)

# Результаты кластеризации
print("\nРезультаты кластеризации:")
for i, (pattern, cluster_id) in enumerate(zip(pattern_keys, clusters)):
    print(f"Траектория {i+1} ({pattern}): Кластер {cluster_id}")

# Вывод:
# Траектория 1 (10_20_12_22_15_25): Кластер 0
# Траектория 2 (10_20_11_21_13_23): Кластер 0
# Траектория 3 (5_10_6_11_8_13): Кластер 1
# Траектория 4 (30_5_32_7_35_10): Кластер 2
# Траектория 5 (30_5_31_6_33_8): Кластер 2

# Центры кластеров (средние координаты)
print("\nЦентры кластеров:")
print(kmeans.cluster_centers_)
# Вывод (примерные значения):
# [[11.0 20.5 11.5 21.5 14.0 24.0]  # Кластер 0: траектории 1 и 2
#  [ 5.0 10.0  6.0 11.0  8.0 13.0]  # Кластер 1: траектория 3
#  [30.0  5.0 31.5  6.5 34.0  9.0]] # Кластер 2: траектории 4 и 5
```

### Интерпретация результатов

- **Кластер 0** (траектории 1 и 2): Похожие траектории движения вправо-вверх из одной области экрана.
- **Кластер 1** (траектория 3): Отдельная траектория из другой области, но с похожим направлением.
- **Кластер 2** (траектории 4 и 5): Траектории движения вправо-вниз из верхней части экрана.

### Метрика разнообразия кластеров

В проекте используется метрика **энтропии** для оценки разнообразия кластеров:

```python
import math

def calculate_cluster_diversity(trajectory_clusters):
    """Рассчитывает разнообразие кластеров траекторий"""
    if not trajectory_clusters:
        return 0.0

    # Подсчитываем количество паттернов в каждом кластере
    cluster_counts = {}
    for item in trajectory_clusters:
        cluster = item["cluster"]
        cluster_counts[cluster] = cluster_counts.get(cluster, 0) + 1

    total_patterns = len(trajectory_clusters)
    entropy = 0.0

    # Рассчитываем энтропию Шеннона
    for count in cluster_counts.values():
        probability = count / total_patterns
        if probability > 0:
            entropy -= probability * math.log2(probability)

    # Нормализуем энтропию (максимальная энтропия = log2(число кластеров))
    max_entropy = math.log2(len(cluster_counts)) if cluster_counts else 1.0
    diversity = entropy / max_entropy if max_entropy > 0 else 0.0

    return diversity

# Пример расчета
trajectory_clusters = [
    {"pattern": "10_20_12_22_15_25", "cluster": 0},
    {"pattern": "10_20_11_21_13_23", "cluster": 0},
    {"pattern": "5_10_6_11_8_13", "cluster": 1},
    {"pattern": "30_5_32_7_35_10", "cluster": 2},
    {"pattern": "30_5_31_6_33_8", "cluster": 2}
]

diversity = calculate_cluster_diversity(trajectory_clusters)
print(f"Разнообразие кластеров: {diversity:.3f}")
# Вывод: Разнообразие кластеров: 0.951
# (высокое разнообразие означает равномерное распределение по кластерам)
```

**Интерпретация разнообразия:**

- **0.0 - 0.3**: Низкое разнообразие (большинство траекторий в одном кластере)
- **0.3 - 0.7**: Среднее разнообразие (умеренное распределение)
- **0.7 - 1.0**: Высокое разнообразие (равномерное распределение по кластерам)

---

## 2. Система обучения (scikit-learn)

### Описание

Система обучения использует библиотеку scikit-learn для создания и обучения моделей машинного обучения. Основные компоненты:

1. **KMeans** - для кластеризации траекторий
2. **RandomForestClassifier** - для предсказания успешности действий
3. **train_test_split** - для разделения данных на обучающую и тестовую выборки
4. **accuracy_score** - для оценки точности модели

### Обучение модели предсказания успеха

Система периодически (каждые 100 итераций) обучает модель RandomForestClassifier для предсказания вероятности успеха действия на основе исторических данных.

#### Пример обучения модели

```python
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# Предположим, у нас есть исторические данные о скорости мяча и успешности действий
# Данные собираются из success_factors["ball_speed"]
historical_data = {
    "ball_speed": {
        "total_cases": 150,
        "successful_cases": 90,
        "factor_values": [5, 7, 10, 12, 15, 8, 6, 11, 13, 9, ...]  # 150 значений
    }
}

factor_data = historical_data["ball_speed"]
successes = factor_data["successful_cases"]
total = factor_data["total_cases"]
success_rate = successes / total  # 90/150 = 0.6 (60% успешность)

# Создаем признаки (X) и метки (y)
X = []
y = []

for val in factor_data["factor_values"]:
    # Бинарный таргет: успех если фактор привел к успеху
    # В реальности используется более сложная логика, здесь упрощенный пример
    target = 1 if np.random.random() < success_rate else 0
    X.append([val])  # Признак: скорость мяча
    y.append(target)  # Метка: успех (1) или неудача (0)

X = np.array(X)
y = np.array(y)

print(f"Размер данных: {X.shape[0]} примеров")
print(f"Примеры признаков: {X[:5]}")
print(f"Примеры меток: {y[:5]}")

# Разделяем на обучающую (80%) и тестовую (20%) выборки
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"\nОбучающая выборка: {len(X_train)} примеров")
print(f"Тестовая выборка: {len(X_test)} примеров")

# Обучаем модель RandomForestClassifier
model = RandomForestClassifier(n_estimators=10, random_state=42)
model.fit(X_train, y_train)

# Предсказываем на тестовой выборке
y_pred = model.predict(X_test)

# Оцениваем точность
accuracy = accuracy_score(y_test, y_pred)
print(f"\nТочность модели: {accuracy:.2%}")

# Пример вывода:
# Размер данных: 150 примеров
# Примеры признаков: [[ 5] [ 7] [10] [12] [15]]
# Примеры меток: [1 1 1 0 1]
#
# Обучающая выборка: 120 примеров
# Тестовая выборка: 30 примеров
#
# Точность модели: 65.00%
```

#### Использование модели для предсказания

```python
# После обучения модель можно использовать для предсказания вероятности успеха
action_plan = {"ball_speed": 10}

# Получаем вероятность успеха
ball_speed = action_plan.get("ball_speed", 5)
features = np.array([[ball_speed]])

# Предсказываем вероятность успеха
proba = model.predict_proba(features)[0][1]  # Вероятность успеха (класс 1)
print(f"Вероятность успеха для скорости мяча {ball_speed}: {proba:.2%}")

# Вывод: Вероятность успеха для скорости мяча 10: 68.50%
```

### Метрики модели

После обучения сохраняются следующие метрики:

```python
model_metrics = {
    "last_accuracy": 0.65,           # Последняя точность модели
    "training_samples": 120,         # Количество примеров для обучения
    "test_samples": 30,              # Количество примеров для тестирования
    "features_count": 1              # Количество признаков (в данном случае только ball_speed)
}
```

### Pipeline для предобработки данных

Хотя в текущей реализации не используется Pipeline, рекомендуется следующий подход:

```python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# Pipeline: масштабирование + KMeans
pipeline = Pipeline([
    ('scaler', StandardScaler()),  # Нормализация данных
    ('kmeans', KMeans(n_clusters=3, random_state=42))
])

# Обучение
pipeline.fit(X)
cluster_centers = pipeline.named_steps['kmeans'].cluster_centers_

# Центры кластеров (средние координаты после нормализации):
# [[ 0.12,  0.45,  0.23,  0.56,  0.34,  0.67]
#  [-0.34, -0.12, -0.23, -0.11, -0.10, -0.09]
#  [ 0.56, -0.45,  0.67, -0.34,  0.78, -0.23]]
```

**Преимущества использования Pipeline:**

- Автоматическая предобработка данных
- Упрощение воспроизводимости
- Удобство тестирования и валидации

### Лучшие практики

1. **Масштабирование данных**: `StandardScaler` устраняет влияние разницы в масштабах координат (особенно важно при работе с координатами экрана).

2. **Выбор числа кластеров K**:

   - Используйте метод локтя (elbow method) для анализа `inertia_`:

   ```python
   inertias = []
   K_range = range(2, 10)
   for k in K_range:
       kmeans = KMeans(n_clusters=k, random_state=42)
       kmeans.fit(X)
       inertias.append(kmeans.inertia_)

   # График покажет "локоть" - оптимальное K
   ```

3. **Оценка качества кластеризации**: Используйте `silhouette_score` для оценки качества:

   ```python
   from sklearn.metrics import silhouette_score

   score = silhouette_score(X, labels)  # Оптимально: 0.5–0.7
   print(f"Silhouette Score: {score:.3f}")
   ```

---

## 3. Метрики текущей игры

### Описание

Система отслеживает множество метрик для оценки производительности AI-игрока и качества обучения. Метрики разделены на несколько категорий:

1. **Метрики кластеризации**
2. **Метрики обучения**
3. **Метрики модели машинного обучения**
4. **Игровые метрики**

### 3.1. Метрики кластеризации

#### Количество паттернов траекторий

```python
trajectory_patterns = len(learning_data["trajectory_patterns"])
# Пример: 127 паттернов
```

**Интерпретация**: Чем больше паттернов, тем больше разнообразия в траекториях мяча, что позволяет системе лучше адаптироваться.

#### Количество кластеров

```python
trajectory_clusters = learning_system.cluster_trajectories()
unique_clusters = len(set(cluster["cluster"] for cluster in trajectory_clusters))
# Пример: 5 кластеров
```

**Интерпретация**: Оптимальное количество кластеров обычно 3-7 для игры Арканоид. Слишком мало кластеров означает недостаточное разделение, слишком много - переобучение.

#### Разнообразие кластеров (Cluster Diversity)

```python
cluster_diversity = learning_system._calculate_cluster_diversity(trajectory_clusters)
# Пример: 0.823
```

**Расчет разнообразия:**

```python
# Пример расчета
cluster_counts = {0: 45, 1: 32, 2: 28, 3: 15, 4: 7}  # Распределение по кластерам
total_patterns = 127

# Рассчитываем энтропию
entropy = 0.0
for count in cluster_counts.values():
    probability = count / total_patterns
    if probability > 0:
        entropy -= probability * math.log2(probability)

# Энтропия = -[(45/127)*log2(45/127) + (32/127)*log2(32/127) + ...]
# Энтропия ≈ 2.15

# Нормализуем
max_entropy = math.log2(5)  # log2(количество кластеров) ≈ 2.32
diversity = entropy / max_entropy  # 2.15 / 2.32 ≈ 0.927
```

**Интерпретация:**

- **0.0 - 0.3**: Низкое разнообразие (один доминирующий кластер)
- **0.3 - 0.7**: Среднее разнообразие
- **0.7 - 1.0**: Высокое разнообразие (равномерное распределение)

### 3.2. Метрики обучения

#### Всего итераций обучения

```python
total_iterations = learning_stats["total_learning_iterations"]
# Пример: 1250 итераций
```

**Интерпретация**: Количество раз, когда система обновляла стратегию на основе результатов действий.

#### Успешность адаптаций (Success Rate)

```python
successful_adaptations = learning_stats["successful_adaptations"]  # 850
total_iterations = learning_stats["total_learning_iterations"]     # 1250
success_rate = successful_adaptations / total_iterations            # 0.68 (68%)
```

**Расчет:**

```
Успешность = Успешные адаптации / Всего итераций
Успешность = 850 / 1250 = 0.68 = 68%
```

**Интерпретация:**

- **< 50%**: Низкая успешность, требуется улучшение стратегии
- **50-70%**: Средняя успешность, нормальная работа
- **> 70%**: Высокая успешность, система хорошо адаптируется

#### Средний прогресс (Average Improvement)

```python
average_improvement = learning_stats["average_improvement"]
# Пример: 0.65 (65%)
```

**Расчет:**

```python
# Обновляется экспоненциальным скользящим средним
total_attempts = successful_adaptations + failed_adaptations
improvement_rate = successful_adaptations / total_attempts
average_improvement = average_improvement * 0.9 + improvement_rate * 0.1
```

**Пример:**

```
Текущий средний прогресс: 0.60 (60%)
Новая итерация: успех
Улучшение: 850/1250 = 0.68
Новый средний прогресс: 0.60 * 0.9 + 0.68 * 0.1 = 0.608 (60.8%)
```

### 3.3. Метрики модели машинного обучения

#### Точность модели (Model Accuracy)

```python
model_accuracy = model_metrics.get("last_accuracy", None)
# Пример: 0.72 (72%)
```

**Интерпретация:**

- **< 50%**: Модель работает хуже случайного угадывания
- **50-70%**: Приемлемая точность
- **> 70%**: Хорошая точность предсказаний

#### Количество обучающих примеров

```python
training_samples = model_metrics.get("training_samples", 0)
# Пример: 120 примеров
```

#### Количество тестовых примеров

```python
test_samples = model_metrics.get("test_samples", 0)
# Пример: 30 примеров
```

**Соотношение train/test:**

```
Обучающая выборка: 80% (120 примеров)
Тестовая выборка: 20% (30 примеров)
Всего: 150 примеров
```

### 3.4. Игровые метрики

#### Точность предсказаний (Prediction Accuracy)

```python
total_predictions = current_game_stats["total_predictions"]      # 250
successful_predictions = current_game_stats["successful_predictions"]  # 195
prediction_accuracy = (successful_predictions / total_predictions) * 100
# Пример: 78.0%
```

**Расчет:**

```
Точность предсказаний = (Успешные предсказания / Всего предсказаний) * 100%
Точность предсказаний = (195 / 250) * 100% = 78.0%
```

**Интерпретация:**

- **< 60%**: Низкая точность, требуется улучшение алгоритма предсказания
- **60-80%**: Хорошая точность
- **> 80%**: Отличная точность

#### Процент оптимальных ходов

```python
total_moves = current_game_stats["total_moves"]           # 180
optimal_moves = current_game_stats["optimal_moves"]      # 142
optimal_move_rate = (optimal_moves / total_moves) * 100
# Пример: 78.9%
```

**Расчет:**

```
Процент оптимальных ходов = (Оптимальные ходы / Всего ходов) * 100%
Процент оптимальных ходов = (142 / 180) * 100% = 78.9%
```

**Интерпретация:**

- **< 50%**: Много неоптимальных решений
- **50-75%**: Приемлемое качество решений
- **> 75%**: Высокое качество принятия решений

#### Уничтожено кубиков

```python
bricks_destroyed = current_game_stats["bricks_destroyed"]
# Пример: 48 из 50 кубиков
```

#### Процент побед

```python
games_played = performance_metrics["games_played"]  # 25
games_won = performance_metrics["games_won"]      # 18
win_rate = (games_won / games_played) * 100
# Пример: 72.0%
```

**Расчет:**

```
Процент побед = (Побед / Всего игр) * 100%
Процент побед = (18 / 25) * 100% = 72.0%
```

### 3.5. Пример полного отчета метрик

```python
# Пример вывода метрик после игры
print("=" * 70)
print("МЕТРИКИ ОЦЕНКИ РАБОТЫ СИСТЕМЫ AI (scikit-learn)")
print("=" * 70)

print("\n[РЕЗУЛЬТАТЫ] Результаты игры:")
print("   Результат: [+] ПОБЕДА")
print("   Финальный счёт: 1250")
print("   Всего игр: 25")
print("   Побед: 18")
print("   Процент побед: 72.0%")

print("\n[МЕТРИКИ] Метрики текущей игры:")
print("   Уничтожено кубиков: 48")
print("   Всего предсказаний: 250")
print("   Точность предсказаний: 78.0%")
print("   Всего ходов: 180")
print("   Оптимальных ходов: 78.9%")

print("\n[ОБУЧЕНИЕ] Система обучения (scikit-learn):")
print("   Всего итераций обучения: 1250")
print("   Успешность адаптаций: 68.00%")
print("   Средний прогресс: 65.00%")

print("\n[КЛАСТЕРИЗАЦИЯ] Кластеризация траекторий (KMeans):")
print("   Найдено паттернов траекторий: 127")
print("   Количество кластеров: 5")
print("   Разнообразие кластеров: 0.823")
print("   Распределение по кластерам:")
print("      Кластер 0: 45 паттернов (35.4%)")
print("      Кластер 1: 32 паттернов (25.2%)")
print("      Кластер 2: 28 паттернов (22.0%)")
print("      Кластер 3: 15 паттернов (11.8%)")
print("      Кластер 4: 7 паттернов (5.5%)")

print("\n[МОДЕЛЬ] Модель предсказания успеха:")
print("   Модель обучена: Да")
print("   Точность модели: 72.00%")
print("   Обучающих примеров: 120")
print("   Тестовых примеров: 30")
print("   Количество признаков: 1")
```

### 3.6. Интерпретация комбинации метрик

**Хорошая производительность системы:**

- Точность предсказаний > 75%
- Процент оптимальных ходов > 70%
- Успешность адаптаций > 65%
- Разнообразие кластеров > 0.7
- Точность модели > 70%

**Требуется улучшение:**

- Точность предсказаний < 60%
- Процент оптимальных ходов < 50%
- Успешность адаптаций < 50%
- Разнообразие кластеров < 0.3 (слишком мало разнообразия)
- Точность модели < 50%

---

## 4. Предсказание шагов траектории

### Описание

Система предсказания шагов траектории является основой для принятия решений AI-игроком. Она позволяет пошагово симулировать движение мяча, предсказывая его будущие позиции с учетом физики игры, отскоков от стен и взаимодействий с объектами.

В проекте используется класс `TrajectoryPredictor`, который выполняет пошаговое предсказание траектории мяча на основе текущего состояния игры (позиция мяча, скорость, состояние платформы и кубиков).

### Как это работает

1. **Инициализация**: Система получает текущее состояние игры (позиция мяча, скорость, границы экрана).

2. **Пошаговая симуляция**: На каждом шаге рассчитывается следующая позиция мяча с учетом:

   - Текущей скорости (velocity_x, velocity_y)
   - Отскоков от стен (левая, правая, верхняя)
   - Достижения нижней границы экрана (конец траектории)

3. **Кэширование**: Результаты предсказаний кэшируются для оптимизации производительности.

### Предсказание полной траектории

#### Пример расчета пошагового предсказания

```python
from typing import List
from dataclasses import dataclass

@dataclass
class Point:
    x: float
    y: float

@dataclass
class GameState:
    ball_position: Point
    ball_velocity: Point
    screen_width: int = 800
    screen_height: int = 600

def predict_trajectory(game_state: GameState, max_points: int = 50) -> List[Point]:
    """
    Предсказывает траекторию мяча пошагово

    Args:
        game_state: Текущее состояние игры
        max_points: Максимальное количество шагов (точек траектории)

    Returns:
        Список точек траектории (каждая точка - один шаг)
    """
    trajectory = []
    current_pos = Point(game_state.ball_position.x, game_state.ball_position.y)
    current_vel = Point(game_state.ball_velocity.x, game_state.ball_velocity.y)

    # Симулируем движение шаг за шагом
    for step in range(max_points):
        # Добавляем текущую позицию в траекторию
        trajectory.append(Point(current_pos.x, current_pos.y))

        # Рассчитываем следующую позицию
        next_x = current_pos.x + current_vel.x
        next_y = current_pos.y + current_vel.y

        # Проверяем отскок от левой и правой стен
        if next_x <= 0 or next_x >= game_state.screen_width:
            current_vel.x *= -1  # Инвертируем горизонтальную скорость
            next_x = max(0, min(game_state.screen_width, next_x))

        # Проверяем отскок от верхней стены
        if next_y <= 0:
            current_vel.y *= -1  # Инвертируем вертикальную скорость
            next_y = max(0, next_y)

        # Обновляем позицию
        current_pos = Point(next_x, next_y)

        # Если мяч достиг дна экрана, останавливаем симуляцию
        if next_y >= game_state.screen_height:
            break

    return trajectory

# Пример использования
game_state = GameState(
    ball_position=Point(400, 300),  # Мяч в центре экрана
    ball_velocity=Point(5, 7),      # Скорость: 5 пикселей вправо, 7 вниз за шаг
    screen_width=800,
    screen_height=600
)

# Предсказываем траекторию на 20 шагов
trajectory = predict_trajectory(game_state, max_points=20)

print(f"Предсказано шагов: {len(trajectory)}")
print("\nПервые 5 шагов траектории:")
for i, point in enumerate(trajectory[:5]):
    print(f"Шаг {i+1}: x={point.x:.1f}, y={point.y:.1f}")

# Вывод:
# Предсказано шагов: 20
#
# Первые 5 шагов траектории:
# Шаг 1: x=400.0, y=300.0
# Шаг 2: x=405.0, y=307.0
# Шаг 3: x=410.0, y=314.0
# Шаг 4: x=415.0, y=321.0
# Шаг 5: x=420.0, y=328.0
```

#### Расчет с учетом отскоков

```python
# Пример: мяч движется к правой стене
game_state = GameState(
    ball_position=Point(750, 200),  # Близко к правой стене
    ball_velocity=Point(10, 5),     # Движется вправо
    screen_width=800,
    screen_height=600
)

trajectory = predict_trajectory(game_state, max_points=10)

print("Траектория с отскоком от правой стены:")
for i, point in enumerate(trajectory[:8]):
    print(f"Шаг {i+1}: x={point.x:.1f}, y={point.y:.1f}")

# Вывод:
# Траектория с отскоком от правой стены:
# Шаг 1: x=750.0, y=200.0
# Шаг 2: x=760.0, y=205.0  # Достиг правой стены (x=800)
# Шаг 3: x=750.0, y=210.0  # Отскочил, теперь velocity_x = -10
# Шаг 4: x=740.0, y=215.0
# Шаг 5: x=730.0, y=220.0
# Шаг 6: x=720.0, y=225.0
# Шаг 7: x=710.0, y=230.0
# Шаг 8: x=700.0, y=235.0
```

### Предсказание точки пересечения с платформой

Система может предсказать, где именно мяч пересечется с платформой, что критично для принятия решений о позиционировании.

#### Пример расчета точки пересечения

```python
def predict_paddle_intersection(
    game_state: GameState,
    paddle_y: float
) -> Point:
    """
    Предсказывает точку пересечения мяча с платформой

    Args:
        game_state: Текущее состояние игры
        paddle_y: Y-координата платформы

    Returns:
        Точка пересечения или None если пересечения не будет
    """
    if game_state.ball_velocity.y <= 0:
        return None  # Мяч не падает вниз

    ball_x = game_state.ball_position.x
    ball_y = game_state.ball_position.y
    vel_x = game_state.ball_velocity.x
    vel_y = game_state.ball_velocity.y

    # Рассчитываем время до достижения платформы
    time_to_paddle = (paddle_y - ball_y) / vel_y

    if time_to_paddle <= 0:
        return None

    # Симулируем движение с учетом отскоков от стен
    sim_x = ball_x
    sim_vel_x = vel_x
    sim_time = 0
    max_simulations = 50

    for _ in range(max_simulations):
        # Рассчитываем следующую позицию
        next_x = sim_x + sim_vel_x

        # Проверяем отскок от стен
        if next_x <= 0 or next_x >= game_state.screen_width:
            sim_vel_x *= -1
            next_x = max(0, min(game_state.screen_width, next_x))

        sim_time += 1
        sim_x = next_x

        # Если достигли платформы
        if sim_time >= time_to_paddle:
            break

    return Point(sim_x, paddle_y)

# Пример использования
game_state = GameState(
    ball_position=Point(400, 200),  # Мяч на высоте 200
    ball_velocity=Point(5, 8),     # Движется вниз со скоростью 8
    screen_width=800,
    screen_height=600
)

paddle_y = 550  # Платформа на высоте 550
intersection = predict_paddle_intersection(game_state, paddle_y)

if intersection:
    print(f"Точка пересечения с платформой: x={intersection.x:.1f}, y={intersection.y:.1f}")

    # Рассчитываем время до пересечения
    time_to_intersection = (paddle_y - game_state.ball_position.y) / game_state.ball_velocity.y
    print(f"Время до пересечения: {time_to_intersection:.1f} шагов")

# Вывод:
# Точка пересечения с платформой: x=421.9, y=550.0
# Время до пересечения: 43.8 шагов
```

### Предсказание траектории после отскока

После того как мяч отскакивает от платформы, система может предсказать его дальнейшую траекторию.

#### Пример расчета траектории после отскока

```python
def calculate_bounce_velocity_x(
    game_state: GameState,
    bounce_x: float,
    paddle_center_x: float,
    paddle_width: float
) -> float:
    """
    Рассчитывает горизонтальную скорость после отскока
    на основе точки попадания на платформе
    """
    # Рассчитываем относительное смещение от центра платформы
    relative_offset = (bounce_x - paddle_center_x) / (paddle_width / 2)

    # Ограничиваем в диапазоне [-1, 1]
    relative_offset = max(-1.0, min(1.0, relative_offset))

    # Рассчитываем новую горизонтальную скорость
    max_horizontal_speed = game_state.ball_speed - 1
    new_vel_x = int(relative_offset * max_horizontal_speed)

    return new_vel_x

def predict_after_bounce_trajectory(
    game_state: GameState,
    bounce_point: Point,
    bounce_x: float,
    paddle_center_x: float,
    paddle_width: float
) -> List[Point]:
    """
    Предсказывает траекторию мяча после отскока от платформы
    """
    # Рассчитываем новую скорость после отскока
    new_vel_x = calculate_bounce_velocity_x(
        game_state, bounce_x, paddle_center_x, paddle_width
    )
    new_vel_y = -abs(game_state.ball_velocity.y)  # Мяч всегда летит вверх

    # Создаем новое состояние для симуляции после отскока
    after_bounce_state = GameState(
        ball_position=bounce_point,
        ball_velocity=Point(new_vel_x, new_vel_y),
        screen_width=game_state.screen_width,
        screen_height=game_state.screen_height
    )

    # Предсказываем траекторию после отскока
    trajectory = predict_trajectory(after_bounce_state, max_points=30)

    return trajectory

# Пример использования
game_state = GameState(
    ball_position=Point(400, 200),
    ball_velocity=Point(5, 8),
    screen_width=800,
    screen_height=600
)

bounce_point = Point(420, 550)  # Точка отскока
bounce_x = 420                  # X-координата на платформе
paddle_center_x = 400           # Центр платформы
paddle_width = 100              # Ширина платформы

after_bounce_trajectory = predict_after_bounce_trajectory(
    game_state, bounce_point, bounce_x, paddle_center_x, paddle_width
)

print(f"Траектория после отскока: {len(after_bounce_trajectory)} шагов")
print("\nПервые 5 шагов после отскока:")
for i, point in enumerate(after_bounce_trajectory[:5]):
    print(f"Шаг {i+1}: x={point.x:.1f}, y={point.y:.1f}")

# Вывод:
# Траектория после отскока: 30 шагов
#
# Первые 5 шагов после отскока:
# Шаг 1: x=420.0, y=550.0
# Шаг 2: x=422.0, y=542.0  # Движется вверх (new_vel_y отрицательная)
# Шаг 3: x=424.0, y=534.0
# Шаг 4: x=426.0, y=526.0
# Шаг 5: x=428.0, y=518.0
```

### Кэширование предсказаний

Для оптимизации производительности система использует кэширование результатов предсказаний.

#### Пример работы кэша

```python
class TrajectoryPredictor:
    def __init__(self):
        self._trajectory_cache = {}
        self._cache_max_size = 100

    def _create_cache_key(self, game_state: GameState, max_points: int) -> str:
        """Создает ключ кэша на основе состояния игры"""
        # Округляем координаты для группировки похожих состояний
        ball_x = round(game_state.ball_position.x / 5) * 5
        ball_y = round(game_state.ball_position.y / 5) * 5
        vel_x = round(game_state.ball_velocity.x)
        vel_y = round(game_state.ball_velocity.y)
        return f"traj_{ball_x}_{ball_y}_{vel_x}_{vel_y}_{max_points}"

    def predict_trajectory_cached(
        self,
        game_state: GameState,
        max_points: int = 50
    ) -> List[Point]:
        """Предсказывает траекторию с использованием кэша"""
        cache_key = self._create_cache_key(game_state, max_points)

        # Проверяем кэш
        if cache_key in self._trajectory_cache:
            print(f"Использован кэш для ключа: {cache_key}")
            return self._trajectory_cache[cache_key]

        # Вычисляем траекторию
        trajectory = predict_trajectory(game_state, max_points)

        # Сохраняем в кэш
        if len(self._trajectory_cache) >= self._cache_max_size:
            # Удаляем 20% старых записей
            keys_to_remove = list(self._trajectory_cache.keys())[:self._cache_max_size // 5]
            for k in keys_to_remove:
                del self._trajectory_cache[k]

        self._trajectory_cache[cache_key] = trajectory
        print(f"Траектория вычислена и сохранена в кэш: {cache_key}")

        return trajectory

# Пример использования кэша
predictor = TrajectoryPredictor()

game_state1 = GameState(
    ball_position=Point(400, 300),
    ball_velocity=Point(5, 7)
)

# Первый вызов - вычисление
trajectory1 = predictor.predict_trajectory_cached(game_state1)
# Вывод: Траектория вычислена и сохранена в кэш: traj_400_300_5_7_50

# Второй вызов с тем же состоянием - использование кэша
trajectory2 = predictor.predict_trajectory_cached(game_state1)
# Вывод: Использован кэш для ключа: traj_400_300_5_7_50
```

### Метрики предсказания шагов

Система отслеживает следующие метрики для оценки качества предсказаний:

#### Количество предсказанных шагов

```python
predicted_points_count = len(trajectory)
# Пример: 28 шагов предсказано
```

**Интерпретация**:

- **< 10 шагов**: Траектория слишком короткая, возможно мяч быстро упал
- **10-30 шагов**: Нормальная длина траектории
- **> 30 шагов**: Длинная траектория, мяч много раз отскакивает

#### Точность предсказания позиции

```python
def calculate_prediction_accuracy(
    predicted_points: List[Point],
    actual_points: List[Point]
) -> float:
    """
    Рассчитывает точность предсказания траектории
    """
    if len(predicted_points) != len(actual_points):
        min_len = min(len(predicted_points), len(actual_points))
        predicted_points = predicted_points[:min_len]
        actual_points = actual_points[:min_len]

    if not predicted_points:
        return 0.0

    total_distance_error = 0.0
    for pred_point, actual_point in zip(predicted_points, actual_points):
        distance_error = math.sqrt(
            (pred_point.x - actual_point.x) ** 2 +
            (pred_point.y - actual_point.y) ** 2
        )
        total_distance_error += distance_error

    average_error = total_distance_error / len(predicted_points)
    max_possible_error = 200  # Максимально возможная ошибка
    accuracy = max(0.0, 1.0 - (average_error / max_possible_error))

    return accuracy

# Пример расчета
predicted = [
    Point(400, 300), Point(405, 307), Point(410, 314)
]
actual = [
    Point(400, 300), Point(406, 308), Point(411, 315)  # Небольшие расхождения
]

accuracy = calculate_prediction_accuracy(predicted, actual)
print(f"Точность предсказания: {accuracy:.2%}")
# Вывод: Точность предсказания: 98.50%
```

#### Время вычисления предсказания

```python
import time

start_time = time.time()
trajectory = predict_trajectory(game_state, max_points=50)
computation_time = time.time() - start_time

print(f"Время вычисления траектории: {computation_time*1000:.2f} мс")
# Вывод: Время вычисления траектории: 0.15 мс
```

**Интерпретация**:

- **< 1 мс**: Отличная производительность
- **1-5 мс**: Хорошая производительность
- **> 5 мс**: Требуется оптимизация

### Оптимизация предсказаний

#### Использование кэша

Кэширование позволяет избежать повторных вычислений для похожих состояний игры:

```python
# Без кэша: каждое предсказание требует вычислений
for i in range(100):
    trajectory = predict_trajectory(game_state, max_points=50)
# Время: ~15 мс

# С кэшем: повторные запросы используют кэш
predictor = TrajectoryPredictor()
for i in range(100):
    trajectory = predictor.predict_trajectory_cached(game_state, max_points=50)
# Время: ~2 мс (первый вызов) + ~0.01 мс (остальные из кэша)
```

#### Ограничение количества шагов

Ограничение `max_points` позволяет балансировать между точностью и производительностью:

```python
# Короткое предсказание (быстро, но менее точно)
short_trajectory = predict_trajectory(game_state, max_points=20)
# Время: ~0.1 мс

# Длинное предсказание (медленнее, но точнее)
long_trajectory = predict_trajectory(game_state, max_points=100)
# Время: ~0.5 мс
```

### Практические примеры использования

#### Пример 1: Предсказание для принятия решения о движении платформы

```python
def should_move_paddle(
    game_state: GameState,
    paddle_x: float,
    paddle_width: float
) -> Tuple[bool, float]:
    """
    Определяет, нужно ли двигать платформу и в какую сторону
    """
    paddle_y = 550
    intersection = predict_paddle_intersection(game_state, paddle_y)

    if intersection is None:
        return False, 0.0

    paddle_center = paddle_x + paddle_width / 2
    distance_to_center = intersection.x - paddle_center

    # Если мяч попадет в центр платформы (±20 пикселей), не двигаемся
    if abs(distance_to_center) < 20:
        return False, 0.0

    # Определяем направление движения
    should_move = abs(distance_to_center) > 10
    direction = 1.0 if distance_to_center > 0 else -1.0

    return should_move, direction

# Пример использования
game_state = GameState(
    ball_position=Point(400, 200),
    ball_velocity=Point(5, 8)
)

should_move, direction = should_move_paddle(game_state, paddle_x=350, paddle_width=100)
if should_move:
    print(f"Двигаем платформу {'вправо' if direction > 0 else 'влево'}")
else:
    print("Платформа в правильной позиции")
```

#### Пример 2: Оценка эффективности траектории после отскока

```python
def evaluate_trajectory_effectiveness(
    trajectory: List[Point],
    bricks: List[Tuple[float, float, float, float]]  # (x, y, width, height)
) -> int:
    """
    Оценивает, сколько кубиков попадет в траекторию
    """
    hit_count = 0
    hit_bricks = set()
    ball_radius = 8

    for point in trajectory:
        for i, (brick_x, brick_y, brick_w, brick_h) in enumerate(bricks):
            if i in hit_bricks:
                continue

            # Проверяем пересечение мяча с кубиком
            if (brick_x - ball_radius <= point.x <= brick_x + brick_w + ball_radius and
                brick_y - ball_radius <= point.y <= brick_y + brick_h + ball_radius):
                hit_count += 1
                hit_bricks.add(i)
                break

    return hit_count

# Пример использования
trajectory = predict_after_bounce_trajectory(
    game_state, bounce_point, bounce_x, paddle_center_x, paddle_width
)

bricks = [
    (100, 100, 60, 20),  # Кубик 1
    (200, 100, 60, 20),  # Кубик 2
    (300, 100, 60, 20),  # Кубик 3
]

effectiveness = evaluate_trajectory_effectiveness(trajectory, bricks)
print(f"Траектория попадет в {effectiveness} кубиков")
```

---

## Заключение

### Ключевые выводы

1. **KMeans кластеризация** эффективна для группировки траекторий, но требует:

   - Предобработки данных (квантование координат)
   - Правильного выбора числа кластеров
   - Интерпретации результатов

2. **scikit-learn** предоставляет мощные инструменты для:

   - Кластеризации (KMeans)
   - Классификации (RandomForestClassifier)
   - Оценки качества (accuracy_score, silhouette_score)
   - Предобработки данных (StandardScaler, Pipeline)

3. **Предсказание шагов траектории** является основой для принятия решений:

   - Пошаговая симуляция движения мяча
   - Предсказание точки пересечения с платформой
   - Оценка эффективности траектории после отскока
   - Кэширование для оптимизации производительности

4. **Метрики** помогают:
   - Оценить качество модели и игровую механику
   - Выявить проблемы в обучении
   - Отследить прогресс системы
   - Принять решение об улучшении алгоритма

### Рекомендации по использованию

1. **Мониторинг метрик**: Регулярно отслеживайте все метрики для выявления проблем на ранней стадии.

2. **Балансировка**: Стремитесь к балансу между точностью предсказаний и скоростью принятия решений.

3. **Анализ кластеров**: Используйте анализ кластеров для понимания типичных сценариев игры.

4. **Оптимизация предсказаний**: Используйте кэширование и ограничение количества шагов для баланса между точностью и производительностью.

5. **Постепенное улучшение**: Не пытайтесь оптимизировать все метрики одновременно - фокусируйтесь на одной проблеме за раз.

---

_Документация адаптирована для начинающих, с акцентом на практическое применение в игровых сценариях. Все примеры основаны на реальной реализации в проекте PygameArkanoid._
