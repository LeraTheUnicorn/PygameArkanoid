"""
Модуль для предсказания траектории мяча
"""

import pygame
from typing import List, Tuple, Optional
import math
from .game_state import Point, GameState


class TrajectoryPredictor:
    """Класс для предсказания траектории мяча"""
    
    def __init__(self, screen_width: int = 800, screen_height: int = 600):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.gravity = 0.5  # Гравитация для более реалистичной траектории
        
    def predict_trajectory(self, game_state: GameState, max_points: int = 50) -> List[Point]:
        """
        Предсказывает траекторию мяча
        
        Args:
            game_state: Текущее состояние игры
            max_points: Максимальное количество точек в траектории
            
        Returns:
            Список точек траектории
        """
        trajectory = []
        current_pos = Point(game_state.ball_position.x, game_state.ball_position.y)
        current_vel = Point(game_state.ball_velocity.x, game_state.ball_velocity.y)
        
        # Создаем копию состояния для симуляции
        sim_ball = current_pos
        sim_vel = current_vel
        
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
            
            # Обновляем позицию
            sim_ball = Point(next_x, next_y)
            
            # Если мяч достиг дна экрана, останавливаемся
            if next_y >= self.screen_height:
                break
                
        return trajectory
    
    def predict_paddle_intersection(self, game_state: GameState, paddle_y: float) -> Optional[Point]:
        """
        Предсказывает точку пересечения мяча с платформой (улучшенная версия)
        
        Args:
            game_state: Текущее состояние игры
            paddle_y: Y-координата платформы
            
        Returns:
            Точка пересечения или None если пересечения не будет
        """
        if game_state.ball_velocity.y <= 0:
            return None  # Мяч не падает
        
        # Получаем текущие параметры
        ball_x = game_state.ball_position.x
        ball_y = game_state.ball_position.y
        vel_x = game_state.ball_velocity.x
        vel_y = game_state.ball_velocity.y
        
        # Рассчитываем время до достижения платформы
        time_to_paddle = (paddle_y - ball_y) / vel_y
        
        if time_to_paddle <= 0:
            return None
        
        # Создаем копию мяча для симуляции
        sim_x = ball_x
        sim_vel_x = vel_x
        sim_time = 0
        max_simulations = 50  # Максимум итераций для предотвращения зацикливания
        
        # Симулируем движение с учетом отскоков от стен
        for _ in range(max_simulations):
            # Рассчитываем следующую позицию
            next_x = sim_x + sim_vel_x
            
            # Проверяем отскок от стен
            if next_x <= 0 or next_x >= self.screen_width:
                sim_vel_x *= -1
                next_x = max(0, min(self.screen_width, next_x))
            
            # Обновляем симуляцию
            sim_time += 1  # Одна итерация = 1 кадр
            sim_x = next_x
            
            # Если достигли платформы
            if sim_time >= time_to_paddle:
                break
            
            # Защита от бесконечного цикла
            if sim_time > time_to_paddle * 3:
                break
        
        return Point(sim_x, paddle_y)
    
    def predict_after_bounce_trajectory(self, game_state: GameState, bounce_point: Point, 
                                      bounce_x: float) -> List[Point]:
        """
        Предсказывает траекторию мяча после отскока от платформы
        
        Args:
            game_state: Текущее состояние игры
            bounce_point: Точка отскока
            bounce_x: X-координата точки отскока на платформе
            
        Returns:
            Траектория после отскока
        """
        # Рассчитываем новую скорость после отскока
        new_vel_x = self._calculate_bounce_velocity_x(game_state, bounce_x)
        new_vel_y = -abs(game_state.ball_velocity.y)  # Мяч всегда летит вверх после отскока
        
        # Создаем состояние для симуляции после отскока
        after_bounce_state = GameState(
            ball_position=bounce_point,
            ball_velocity=Point(new_vel_x, new_vel_y),
            paddle_position=game_state.paddle_position,
            paddle_width=game_state.paddle_width,
            remaining_bricks=game_state.remaining_bricks,
            game_score=game_state.game_score,
            game_time=game_state.game_time,
            ball_speed=game_state.ball_speed
        )
        
        # Предсказываем траекторию после отскока
        return self.predict_trajectory(after_bounce_state, max_points=30)
    
    def _calculate_bounce_velocity_x(self, game_state: GameState, bounce_x: float) -> float:
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
    
    def find_optimal_bounce_position(self, game_state: GameState, paddle_y: float) -> Optional[float]:
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
            test_x = max(0, min(self.screen_width - 1, test_x))  # Ограничиваем границами экрана
            
            # Рассчитываем траекторию после отскока с этой позицией
            after_bounce_trajectory = self.predict_after_bounce_trajectory(
                game_state, intersection_point, test_x
            )
            
            # Оцениваем, сколько кубиков попадет в траекторию
            score = self._evaluate_trajectory_effectiveness(after_bounce_trajectory, game_state.remaining_bricks)
            
            if score > best_score:
                best_score = score
                best_position = test_x
        
        return best_position
    
    def _evaluate_trajectory_effectiveness(self, trajectory: List[Point], bricks: List[pygame.Rect]) -> float:
        """
        Оценивает эффективность траектории по количеству кубиков, в которые попадет мяч
        
        Args:
            trajectory: Траектория мяча
            bricks: Список оставшихся кубиков
            
        Returns:
            Оценка эффективности (больше = лучше)
        """
        hit_count = 0
        
        for point in trajectory:
            # Проверяем пересечение с каждым кубиком
            for brick in bricks:
                if (brick.left <= point.x <= brick.right and 
                    brick.top <= point.y <= brick.bottom):
                    hit_count += 1
                    break  # Считаем только первое попадание в кубик
        
        return hit_count
    
    def visualize_trajectory(self, screen: pygame.Surface, trajectory: List[Point], color=(255, 255, 0)):
        """
        Визуализирует траекторию на экране (для отладки)
        
        Args:
            screen: Surface для отрисовки
            trajectory: Траектория для отрисовки
            color: Цвет линии траектории
        """
        if len(trajectory) < 2:
            return
        
        # Рисуем линии между точками траектории
        for i in range(len(trajectory) - 1):
            start_point = (int(trajectory[i].x), int(trajectory[i].y))
            end_point = (int(trajectory[i + 1].x), int(trajectory[i + 1].y))
            pygame.draw.line(screen, color, start_point, end_point, 2)
        
        # Рисуем точки траектории
        for point in trajectory[::5]:  # Рисуем каждую 5-ю точку
            pygame.draw.circle(screen, color, (int(point.x), int(point.y)), 3)