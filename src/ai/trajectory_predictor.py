"""
Модуль для предсказания траектории мяча
"""

import pygame
from typing import List, Tuple, Optional, Any, Dict
import math
from .game_state import Point, GameState


class TrajectoryPredictor:
    """Класс для предсказания траектории мяча"""

    def __init__(self, screen_width: int = 800, screen_height: int = 600) -> None:
        self.screen_width: int = screen_width
        self.screen_height: int = screen_height
        self.gravity: float = 0.5  # Гравитация для более реалистичной траектории
        
        # Кэш для результатов расчетов траекторий
        # Ключ: хеш состояния игры, Значение: результат расчета
        self._trajectory_cache: Dict[str, List[Point]] = {}
        self._intersection_cache: Dict[str, Optional[Point]] = {}
        self._after_bounce_cache: Dict[str, List[Point]] = {}
        self._cache_max_size: int = 200  # УВЕЛИЧЕНО с 100 до 200 для лучшего кэширования
        self._cache_access_order: Dict[str, List[str]] = {
            "trajectory": [],
            "intersection": [],
            "after_bounce": []
        }  # Отслеживание порядка доступа для LRU стратегии

    def predict_trajectory(
        self, game_state: GameState, max_points: int = 75
    ) -> List[Point]:
        """
        Предсказывает траекторию мяча с кэшированием результатов

        Args:
            game_state: Текущее состояние игры
            max_points: Максимальное количество точек в траектории

        Returns:
            Список точек траектории
        """
        # Создаем ключ кэша на основе состояния игры
        cache_key = self._create_cache_key(game_state, max_points)
        
        # Проверяем кэш
        if cache_key in self._trajectory_cache:
            # Обновляем порядок доступа для LRU
            if cache_key in self._cache_access_order["trajectory"]:
                self._cache_access_order["trajectory"].remove(cache_key)
            self._cache_access_order["trajectory"].append(cache_key)
            return self._trajectory_cache[cache_key]
        
        trajectory = []
        current_pos = Point(game_state.ball_position.x, game_state.ball_position.y)
        current_vel = Point(game_state.ball_velocity.x, game_state.ball_velocity.y)

        # Создаем копию состояния для симуляции
        sim_ball = current_pos
        sim_vel = current_vel
        
        # КРИТИЧНО: Создаем копию списка блоков для симуляции
        # Удаляем блоки из симуляции после столкновения, чтобы не учитывать их повторно
        sim_bricks = []
        if game_state.remaining_bricks:
            # Создаем копии блоков для симуляции
            for brick in game_state.remaining_bricks:
                # Создаем простой объект с координатами блока
                brick_data = {
                    'left': getattr(brick, 'left', getattr(brick, 'x', 0)),
                    'right': getattr(brick, 'right', getattr(brick, 'left', getattr(brick, 'x', 0)) + getattr(brick, 'width', 60)),
                    'top': getattr(brick, 'top', getattr(brick, 'y', 0)),
                    'bottom': getattr(brick, 'bottom', getattr(brick, 'top', getattr(brick, 'y', 0)) + getattr(brick, 'height', 20))
                }
                sim_bricks.append(brick_data)
        
        ball_radius = 8  # Радиус мяча (BALL_SIZE / 2)

        for i in range(max_points):
            trajectory.append(Point(sim_ball.x, sim_ball.y))

            # Обновляем позицию
            next_x = sim_ball.x + sim_vel.x
            next_y = sim_ball.y + sim_vel.y

            # Проверяем отскок от стен
            if next_x <= 0 or next_x >= self.screen_width:
                sim_vel.x *= -1
                next_x = max(0, min(self.screen_width, next_x))

            # Проверяем отскок от верхней стены
            if next_y <= 0:
                sim_vel.y *= -1
                next_y = max(0, next_y)

            # КРИТИЧНО: Проверяем столкновение с блоками
            # Это исправляет проблему, когда предсказание не учитывает отскоки от блоков
            if sim_bricks:
                for brick_data in sim_bricks[:]:  # Используем копию списка для безопасного удаления
                    brick_left = brick_data['left']
                    brick_right = brick_data['right']
                    brick_top = brick_data['top']
                    brick_bottom = brick_data['bottom']
                    
                    # Проверяем, попадает ли мяч в область блока (с учетом радиуса)
                    if (brick_left - ball_radius <= next_x <= brick_right + ball_radius and
                        brick_top - ball_radius <= next_y <= brick_bottom + ball_radius):
                        # Дополнительная проверка: мяч действительно попадает в блок
                        center_in_brick = (
                            brick_left <= next_x <= brick_right and
                            brick_top <= next_y <= brick_bottom
                        )
                        
                        # Проверяем расстояние от центра мяча до ближайшей точки блока
                        closest_x = max(brick_left, min(next_x, brick_right))
                        closest_y = max(brick_top, min(next_y, brick_bottom))
                        distance_to_brick = math.sqrt(
                            (next_x - closest_x) ** 2 + (next_y - closest_y) ** 2
                        )
                        
                        if center_in_brick or distance_to_brick <= ball_radius:
                            # Мяч отскочил от блока - инвертируем вертикальную скорость
                            sim_vel.y *= -1
                            # Удаляем блок из симуляции, чтобы не учитывать его повторно
                            sim_bricks.remove(brick_data)
                            break  # Обрабатываем только одно столкновение за шаг

            # Обновляем позицию
            sim_ball = Point(next_x, next_y)

            # Если мяч достиг дна экрана, останавливаемся
            if next_y >= self.screen_height:
                break

        # Сохраняем в кэш
        self._cache_result(self._trajectory_cache, cache_key, trajectory)
        
        return trajectory

    def predict_paddle_intersection(
        self, game_state: GameState, paddle_y: float
    ) -> Optional[Point]:
        """
        Предсказывает точку пересечения мяча с платформой (улучшенная версия) с кэшированием
        и учетом близости к границам.

        Args:
            game_state: Текущее состояние игры
            paddle_y: Y-координата платформы

        Returns:
            Точка пересечения или None если пересечения не будет
        """
        if game_state.ball_velocity.y <= 0:
            return None  # Мяч не падает
        
        # Создаем ключ кэша
        cache_key = self._create_intersection_cache_key(game_state, paddle_y)
        
        # Проверяем кэш
        if cache_key in self._intersection_cache:
            # Обновляем порядок доступа для LRU
            if cache_key in self._cache_access_order["intersection"]:
                self._cache_access_order["intersection"].remove(cache_key)
            self._cache_access_order["intersection"].append(cache_key)
            return self._intersection_cache[cache_key]

        # Получаем текущие параметры
        ball_x = game_state.ball_position.x
        ball_y = game_state.ball_position.y
        vel_x = game_state.ball_velocity.x
        vel_y = game_state.ball_velocity.y

        # КРИТИЧНО: Проверяем близость к верхней границе и учитываем вероятность отскока
        # Если мяч близко к верхней границе и движется вверх, он может отскочить
        top_boundary_buffer = 50  # Буферная зона для учета отскока
        if ball_y < top_boundary_buffer and vel_y < 0:
            # Мяч близко к верхней границе и движется вверх - вероятен отскок
            # Рассчитываем время до отскока
            time_to_bounce = abs(ball_y / vel_y) if vel_y < 0 else float('inf')
            
            # Если отскок произойдет до достижения платформы, учитываем его
            time_to_paddle_initial = (paddle_y - ball_y) / abs(vel_y) if vel_y != 0 else float('inf')
            
            if time_to_bounce < time_to_paddle_initial:
                # Отскок произойдет раньше - пересчитываем с учетом отскока
                # Позиция после отскока
                bounce_y = 0  # Верхняя граница
                bounce_x = ball_x + vel_x * time_to_bounce
                
                # Новая скорость после отскока (инвертированная)
                new_vel_y = abs(vel_y)  # Мяч теперь движется вниз
                
                # Оставшееся время до платформы после отскока
                remaining_time = time_to_paddle_initial - time_to_bounce
                
                # Используем новую скорость для расчета
                vel_y = new_vel_y
                ball_y = bounce_y
                ball_x = bounce_x
                time_to_paddle = remaining_time
            else:
                # Отскок не произойдет до достижения платформы
                time_to_paddle = time_to_paddle_initial
        else:
            # Обычный расчет
            time_to_paddle = (paddle_y - ball_y) / vel_y

        if time_to_paddle <= 0:
            return None

        # КРИТИЧНО: Улучшенная симуляция с учетом отскоков от боковых стен И блоков
        # Используем непрерывную симуляцию вместо дискретных шагов для точности
        ball_radius = 8  # Радиус мяча (BALL_SIZE / 2)
        sim_x = float(ball_x)
        sim_y = float(ball_y)
        sim_vel_x = float(vel_x)
        sim_vel_y = float(vel_y)
        remaining_time = float(time_to_paddle)
        max_iterations = 200  # УВЕЛИЧЕНО с 100 до 200 для более точной симуляции множественных отскоков
        
        # КРИТИЧНО: Создаем копию списка блоков для симуляции
        sim_bricks = []
        if game_state.remaining_bricks:
            for brick in game_state.remaining_bricks:
                brick_data = {
                    'left': getattr(brick, 'left', getattr(brick, 'x', 0)),
                    'right': getattr(brick, 'right', getattr(brick, 'left', getattr(brick, 'x', 0)) + getattr(brick, 'width', 60)),
                    'top': getattr(brick, 'top', getattr(brick, 'y', 0)),
                    'bottom': getattr(brick, 'bottom', getattr(brick, 'top', getattr(brick, 'y', 0)) + getattr(brick, 'height', 20))
                }
                sim_bricks.append(brick_data)

        # Симулируем движение с учетом отскоков от стен И блоков
        for iteration in range(max_iterations):
            if remaining_time <= 0:
                break
            
            # Рассчитываем время до следующего отскока от стены
            if sim_vel_x > 0:
                # Движение вправо - проверяем правую стену
                distance_to_right_wall = self.screen_width - ball_radius - sim_x
                time_to_wall = distance_to_right_wall / sim_vel_x if sim_vel_x > 0 else float('inf')
            elif sim_vel_x < 0:
                # Движение влево - проверяем левую стену
                distance_to_left_wall = sim_x - ball_radius
                time_to_wall = distance_to_left_wall / abs(sim_vel_x) if sim_vel_x < 0 else float('inf')
            else:
                # Мяч не движется горизонтально
                time_to_wall = float('inf')
            
            # КРИТИЧНО: Рассчитываем время до столкновения с блоком
            time_to_brick = float('inf')
            hit_brick = None
            if sim_bricks and sim_vel_y > 0:  # Мяч движется вниз (может столкнуться с блоком)
                for brick_data in sim_bricks:
                    brick_left = brick_data['left']
                    brick_right = brick_data['right']
                    brick_top = brick_data['top']
                    brick_bottom = brick_data['bottom']
                    
                    # Проверяем, может ли мяч столкнуться с этим блоком
                    # Блок должен быть ниже текущей позиции мяча и в горизонтальном диапазоне
                    if (brick_top >= sim_y and 
                        brick_left - ball_radius <= sim_x <= brick_right + ball_radius):
                        # Рассчитываем время до столкновения
                        distance_to_brick_y = brick_top - ball_radius - sim_y
                        if distance_to_brick_y > 0 and sim_vel_y > 0:
                            time_to_this_brick = distance_to_brick_y / sim_vel_y
                            if time_to_this_brick < time_to_brick:
                                time_to_brick = time_to_this_brick
                                hit_brick = brick_data
            
            # Определяем, что произойдет раньше: стена, блок или платформа
            next_event_time = min(time_to_wall, time_to_brick, remaining_time)
            
            if next_event_time <= 0:
                # Мяч достиг платформы
                sim_x += sim_vel_x * remaining_time
                remaining_time = 0
                break
            elif time_to_brick > 0 and time_to_brick <= time_to_wall and time_to_brick <= remaining_time:
                # Мяч отскочит от блока раньше, чем от стены
                sim_x += sim_vel_x * time_to_brick
                sim_y += sim_vel_y * time_to_brick
                remaining_time -= time_to_brick
                sim_vel_y = -sim_vel_y  # Отскок от блока (вертикальный)
                # Удаляем блок из симуляции
                if hit_brick and hit_brick in sim_bricks:
                    sim_bricks.remove(hit_brick)
            elif time_to_wall > 0 and time_to_wall <= remaining_time:
                # Мяч отскочит от стены до достижения платформы
                sim_x += sim_vel_x * time_to_wall
                sim_y += sim_vel_y * time_to_wall
                remaining_time -= time_to_wall
                sim_vel_x = -sim_vel_x  # Отскок
                # Корректируем позицию, чтобы мяч не вышел за границы
                sim_x = max(ball_radius, min(self.screen_width - ball_radius, sim_x))
            else:
                # Мяч достигнет платформы раньше, чем отскочит от стены или блока
                sim_x += sim_vel_x * remaining_time
                remaining_time = 0
                break

        # Ограничиваем результат границами экрана
        sim_x = max(ball_radius, min(self.screen_width - ball_radius, sim_x))
        result = Point(int(sim_x), int(paddle_y))
        
        # Сохраняем в кэш
        self._cache_result(self._intersection_cache, cache_key, result)
        
        return result

    def predict_after_bounce_trajectory(
        self, game_state: GameState, bounce_point: Point, bounce_x: float
    ) -> List[Point]:
        """
        Предсказывает траекторию мяча после отскока от платформы с кэшированием

        Args:
            game_state: Текущее состояние игры
            bounce_point: Точка отскока
            bounce_x: X-координата точки отскока на платформе

        Returns:
            Траектория после отскока
        """
        # Создаем ключ кэша
        cache_key = self._create_after_bounce_cache_key(game_state, bounce_point, bounce_x)
        
        # Проверяем кэш
        if cache_key in self._after_bounce_cache:
            # Обновляем порядок доступа для LRU
            if cache_key in self._cache_access_order["after_bounce"]:
                self._cache_access_order["after_bounce"].remove(cache_key)
            self._cache_access_order["after_bounce"].append(cache_key)
            return self._after_bounce_cache[cache_key]
        
        # Рассчитываем новую скорость после отскока
        new_vel_x = self._calculate_bounce_velocity_x(game_state, bounce_x)
        new_vel_y = -abs(
            game_state.ball_velocity.y
        )  # Мяч всегда летит вверх после отскока

        # Создаем состояние для симуляции после отскока
        after_bounce_state = GameState(
            ball_position=bounce_point,
            ball_velocity=Point(new_vel_x, new_vel_y),
            paddle_position=game_state.paddle_position,
            paddle_width=game_state.paddle_width,
            remaining_bricks=game_state.remaining_bricks,
            game_score=game_state.game_score,
            game_time=game_state.game_time,
            ball_speed=game_state.ball_speed,
        )

        # Предсказываем траекторию после отскока
        trajectory = self.predict_trajectory(after_bounce_state, max_points=40)
        
        # Сохраняем в кэш
        self._cache_result(self._after_bounce_cache, cache_key, trajectory)
        
        return trajectory

    def _calculate_bounce_velocity_x(
        self, game_state: GameState, bounce_x: float
    ) -> float:
        """
        Рассчитывает горизонтальную скорость после отскока
        на основе точки попадания на платформе
        """
        paddle_center = game_state.paddle_position.x
        relative_offset = (bounce_x - paddle_center) / (game_state.paddle_width / 2)

        # Ограничиваем offset в диапазоне [-1, 1]
        relative_offset = max(-1.0, min(1.0, relative_offset))

        # Рассчитываем новую горизонтальную скорость
        max_horizontal_speed = game_state.ball_speed - 1
        new_vel_x = int(relative_offset * max_horizontal_speed)

        # Добавляем случайность для избежания слишком предсказуемого поведения
        if abs(relative_offset) < 0.2:
            import random

            new_vel_x += random.choice([-1, 1]) * random.randint(1, 2)

        # Ограничиваем горизонтальную скорость
        new_vel_x = max(-max_horizontal_speed, min(max_horizontal_speed, new_vel_x))

        return new_vel_x

    def find_optimal_bounce_position(
        self, game_state: GameState, paddle_y: float
    ) -> Optional[float]:
        """
        Находит оптимальную позицию на платформе для отскока

        Args:
            game_state: Текущее состояние игры
            paddle_y: Y-координата платформы

        Returns:
            Оптимальная X-координата для отскока или None
        """
        intersection_point = self.predict_paddle_intersection(game_state, paddle_y)
        if intersection_point is None:
            return None

        # Если нет кубиков, просто направляем в центр
        if not game_state.remaining_bricks:
            return intersection_point.x

        # Ищем лучшую позицию для попадания в кубики
        best_position = intersection_point.x
        best_score = -1

        # Проверяем несколько позиций вокруг предсказанной точки
        for offset in range(-50, 51, 10):  # Проверяем позиции с шагом 10 пикселей
            test_x = intersection_point.x + offset
            test_x = max(
                0, min(self.screen_width - 1, test_x)
            )  # Ограничиваем границами экрана

            # Рассчитываем траекторию после отскока с этой позицией
            after_bounce_trajectory = self.predict_after_bounce_trajectory(
                game_state, intersection_point, test_x
            )

            # Оцениваем, сколько кубиков попадет в траекторию
            score = self._evaluate_trajectory_effectiveness(
                after_bounce_trajectory, game_state.remaining_bricks
            )

            if score > best_score:
                best_score = score
                best_position = test_x

        return best_position

    def _evaluate_trajectory_effectiveness(
        self, trajectory: List[Point], bricks: List[pygame.Rect]
    ) -> float:
        """
        Оценивает эффективность траектории по количеству кубиков, в которые попадет мяч.
        Использует точные координаты кубиков для более точной оценки.

        Args:
            trajectory: Траектория мяча
            bricks: Список оставшихся кубиков

        Returns:
            Оценка эффективности (больше = лучше)
        """
        hit_count = 0
        hit_bricks = set()
        ball_radius = 8  # Радиус мяча

        for point in trajectory:
            if not hasattr(point, "x") or not hasattr(point, "y"):
                continue

            # Проверяем пересечение с каждым кубиком
            for brick in bricks:
                brick_id = id(brick)
                if brick_id in hit_bricks:
                    continue

                # Точные границы кубика
                brick_left = getattr(
                    brick, "left", brick.x if hasattr(brick, "x") else 0
                )
                brick_right = getattr(
                    brick, "right", brick_left + getattr(brick, "width", 60)
                )
                brick_top = getattr(brick, "top", brick.y if hasattr(brick, "y") else 0)
                brick_bottom = getattr(
                    brick, "bottom", brick_top + getattr(brick, "height", 20)
                )

                # Точная проверка пересечения мяча (с учетом радиуса) с границами кубика
                if (
                    brick_left - ball_radius <= point.x <= brick_right + ball_radius
                    and brick_top - ball_radius <= point.y <= brick_bottom + ball_radius
                ):
                    # Дополнительная проверка: мяч действительно попадает в кубик
                    center_in_brick = (
                        brick_left <= point.x <= brick_right
                        and brick_top <= point.y <= brick_bottom
                    )

                    # Проверяем расстояние от центра мяча до ближайшей точки кубика
                    closest_x = max(brick_left, min(point.x, brick_right))
                    closest_y = max(brick_top, min(point.y, brick_bottom))
                    distance_to_brick = math.sqrt(
                        (point.x - closest_x) ** 2 + (point.y - closest_y) ** 2
                    )

                    if center_in_brick or distance_to_brick <= ball_radius:
                        hit_count += 1
                        hit_bricks.add(brick_id)
                        break  # Считаем только первое попадание в кубик

        return hit_count

    def visualize_trajectory(
        self, screen: pygame.Surface, trajectory: List[Point], color: Tuple[int, int, int] = (255, 255, 0)
    ) -> None:
        """
        Визуализирует траекторию на экране (для отладки)

        Args:
            screen: Surface для отрисовки
            trajectory: Траектория для отрисовки
            color: Цвет линии траектории
        """
        if len(trajectory) < 2:
            return

        # Линии траектории отключены по запросу пользователя
        # Рисуем линии между точками траектории
        # for i in range(len(trajectory) - 1):
        #     start_point = (int(trajectory[i].x), int(trajectory[i].y))
        #     end_point = (int(trajectory[i + 1].x), int(trajectory[i + 1].y))
        #     pygame.draw.line(screen, color, start_point, end_point, 2)

        # Рисуем точки траектории
        # for point in trajectory[::5]:  # Рисуем каждую 5-ю точку
        #     pygame.draw.circle(screen, color, (int(point.x), int(point.y)), 3)
    
    def _create_cache_key(self, game_state: GameState, max_points: int) -> str:
        """Создает ключ кэша для траектории"""
        # Используем ключевые параметры состояния игры
        ball_x = round(game_state.ball_position.x / 5) * 5  # Округляем для группировки
        ball_y = round(game_state.ball_position.y / 5) * 5
        vel_x = round(game_state.ball_velocity.x)
        vel_y = round(game_state.ball_velocity.y)
        # КРИТИЧНО: Добавляем количество блоков в ключ кэша
        # Это необходимо, так как траектория зависит от блоков, от которых мяч может отскочить
        brick_count = len(game_state.remaining_bricks) if game_state.remaining_bricks else 0
        return f"traj_{ball_x}_{ball_y}_{vel_x}_{vel_y}_{brick_count}_{max_points}"
    
    def _create_intersection_cache_key(self, game_state: GameState, paddle_y: float) -> str:
        """Создает ключ кэша для пересечения с платформой"""
        ball_x = round(game_state.ball_position.x / 5) * 5
        ball_y = round(game_state.ball_position.y / 5) * 5
        vel_x = round(game_state.ball_velocity.x)
        vel_y = round(game_state.ball_velocity.y)
        paddle_y_rounded = round(paddle_y / 5) * 5
        # КРИТИЧНО: Добавляем количество блоков в ключ кэша
        # Это необходимо, так как пересечение с платформой зависит от блоков, от которых мяч может отскочить
        brick_count = len(game_state.remaining_bricks) if game_state.remaining_bricks else 0
        return f"intersect_{ball_x}_{ball_y}_{vel_x}_{vel_y}_{brick_count}_{paddle_y_rounded}"
    
    def _create_after_bounce_cache_key(self, game_state: GameState, bounce_point: Point, bounce_x: float) -> str:
        """Создает ключ кэша для траектории после отскока"""
        bounce_x_rounded = round(bounce_point.x / 5) * 5
        bounce_y_rounded = round(bounce_point.y / 5) * 5
        bounce_x_pos = round(bounce_x / 5) * 5
        vel_y = round(game_state.ball_velocity.y)
        return f"after_bounce_{bounce_x_rounded}_{bounce_y_rounded}_{bounce_x_pos}_{vel_y}"
    
    def _cache_result(self, cache_dict: Dict[str, Any], key: str, value: Any) -> None:
        """Сохраняет результат в кэш с ограничением размера (LRU стратегия)"""
        # Определяем тип кэша для обновления порядка доступа
        cache_type = None
        if cache_dict is self._trajectory_cache:
            cache_type = "trajectory"
        elif cache_dict is self._intersection_cache:
            cache_type = "intersection"
        elif cache_dict is self._after_bounce_cache:
            cache_type = "after_bounce"
        
        # Если кэш переполнен, удаляем наименее используемые записи (LRU)
        if len(cache_dict) >= self._cache_max_size:
            if cache_type and self._cache_access_order[cache_type]:
                # Удаляем 25% наименее используемых записей (старейшие в порядке доступа)
                keys_to_remove = self._cache_access_order[cache_type][:self._cache_max_size // 4]
                for k in keys_to_remove:
                    if k in cache_dict:
                        del cache_dict[k]
                    if k in self._cache_access_order[cache_type]:
                        self._cache_access_order[cache_type].remove(k)
            else:
                # Fallback: удаляем старые записи если нет информации о порядке доступа
                keys_to_remove = list(cache_dict.keys())[:self._cache_max_size // 4]
                for k in keys_to_remove:
                    del cache_dict[k]
        
        # Добавляем новую запись в кэш и обновляем порядок доступа
        cache_dict[key] = value
        if cache_type:
            if key in self._cache_access_order[cache_type]:
                self._cache_access_order[cache_type].remove(key)
            self._cache_access_order[cache_type].append(key)
    
    def clear_cache(self) -> None:
        """Очищает все кэши"""
        self._trajectory_cache.clear()
        self._intersection_cache.clear()
        self._after_bounce_cache.clear()
        # Очищаем порядок доступа
        self._cache_access_order = {
            "trajectory": [],
            "intersection": [],
            "after_bounce": []
        }
    
    def get_optimized_trajectory(
        self, game_state: GameState, max_relevant_points: int = 40
    ) -> List[Point]:
        """
        Получает оптимизированную траекторию, используя только нужные точки.
        Это позволяет использовать полную траекторию из кэша, но возвращать только
        релевантные точки для текущей ситуации.
        
        Args:
            game_state: Текущее состояние игры
            max_relevant_points: Максимальное количество релевантных точек для возврата
        
        Returns:
            Список точек траектории (оптимизированный)
        """
        # Получаем полную траекторию (использует кэш)
        full_trajectory = self.predict_trajectory(game_state)
        
        # Если траектория короче запрошенного количества, возвращаем всю
        if len(full_trajectory) <= max_relevant_points:
            return full_trajectory
        
        # Возвращаем первые N точек (наиболее релевантные для ближайшего будущего)
        return full_trajectory[:max_relevant_points]
    
    def get_adaptive_trajectory(
        self, game_state: GameState, ball_y: float, paddle_y: float
    ) -> List[Point]:
        """
        Получает адаптивную траекторию в зависимости от расстояния мяча до платформы.
        Когда мяч близко - используем больше точек для точности.
        Когда мяч далеко - используем меньше точек для производительности.
        
        Args:
            game_state: Текущее состояние игры
            ball_y: Y-координата мяча
            paddle_y: Y-координата платформы
        
        Returns:
            Список точек траектории (адаптивный размер)
        """
        distance_to_paddle = paddle_y - ball_y if ball_y < paddle_y else 0
        
        # Адаптивное количество точек на основе расстояния
        if distance_to_paddle < 50:
            # Мяч очень близко - используем максимум точек для точности
            max_points = 60
        elif distance_to_paddle < 150:
            # Мяч близко - используем много точек
            max_points = 50
        elif distance_to_paddle < 300:
            # Мяч на среднем расстоянии - используем среднее количество
            max_points = 35
        else:
            # Мяч далеко - используем минимум точек для производительности
            max_points = 25
        
        # Получаем полную траекторию и обрезаем до нужного размера
        full_trajectory = self.predict_trajectory(game_state)
        return full_trajectory[:max_points]
