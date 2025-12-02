"""
Модуль для оптимизации позиции платформы
"""

import pygame
from typing import List, Tuple, Optional
import math
from .game_state import GameState, Point


class PositionOptimizer:
    """Класс для оптимизации позиции платформы"""
    
    def __init__(self, screen_width: int = 800, screen_height: int = 600):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.paddle_safety_margin = 20  # Безопасный отступ от краев экрана
        
    def find_optimal_position(self, game_state: GameState, trajectory_predictor) -> int:
        """
        Находит оптимальную позицию платформы
        
        Args:
            game_state: Текущее состояние игры
            trajectory_predictor: Предсказатель траектории
            
        Returns:
            Оптимальная X-координата центра платформы
        """
        try:
            # Если мяч не падает, просто следуем за ним
            if not game_state.is_ball_falling():
                return self._follow_ball_position(game_state)
            
            # Находим оптимальную позицию для отскока
            paddle_y = game_state.paddle_position.y
            optimal_bounce_x = trajectory_predictor.find_optimal_bounce_position(game_state, paddle_y)
            
            if optimal_bounce_x is not None:
                # Переводим X-координату отскока в позицию центра платформы
                return self._bounce_x_to_paddle_x(optimal_bounce_x, game_state.paddle_width)
            
            # Если не удалось найти оптимальную позицию, используем предсказанную траекторию
            return self._fallback_position(game_state)
            
        except Exception as e:
            # Fallback при ошибках - просто следуем за мячом
            print(f"Ошибка при поиске оптимальной позиции: {e}")
            return self._follow_ball_position(game_state)
    
    def _follow_ball_position(self, game_state: GameState) -> int:
        """
        Улучшенное следование за мячом с точным предсказанием
        """
        ball_x = game_state.ball_position.x
        ball_y = game_state.ball_position.y
        vel_x = game_state.ball_velocity.x
        vel_y = game_state.ball_velocity.y
        paddle_y = game_state.paddle_position.y
        
        # Если мяч падает вниз, используем точное предсказание траектории
        if vel_y > 0:
            time_to_paddle = (paddle_y - ball_y) / vel_y
            
            if time_to_paddle > 0:
                # Предсказываем точку пересечения с платформой
                predicted_x = ball_x + vel_x * time_to_paddle
                
                # Учитываем отскоки от стен
                screen_width = self.screen_width
                ball_radius = 8  # Примерный радиус мяча
                
                # Математическое моделирование отскоков от стен
                while predicted_x < ball_radius or predicted_x > screen_width - ball_radius:
                    if predicted_x < ball_radius:
                        # Отражение от левой стены
                        predicted_x = ball_radius + (ball_radius - predicted_x)
                        vel_x = abs(vel_x)
                    elif predicted_x > screen_width - ball_radius:
                        # Отражение от правой стены
                        predicted_x = (screen_width - ball_radius) - (predicted_x - (screen_width - ball_radius))
                        vel_x = -abs(vel_x)
                
                return int(predicted_x)
        
        # Для мяча, который движется вверх, просто следим за ним
        # Добавляем упреждающее движение в зависимости от скорости
        prediction_distance = abs(vel_x) * 3  # Предсказание на 3 шага вперед
        
        if vel_x > 0:
            target_x = ball_x + prediction_distance
        elif vel_x < 0:
            target_x = ball_x - prediction_distance
        else:
            target_x = ball_x  # Если мяч не движется по горизонтали
        
        # Ограничиваем движение границами экрана
        min_x = game_state.paddle_width // 2 + self.paddle_safety_margin
        max_x = self.screen_width - game_state.paddle_width // 2 - self.paddle_safety_margin
        
        return max(min_x, min(max_x, int(target_x)))
    
    def _bounce_x_to_paddle_x(self, bounce_x: float, paddle_width: int) -> int:
        """
        Преобразует X-координату точки отскока в позицию центра платформы
        """
        # Центр платформы должен быть там, где планируется отскок
        paddle_center_x = bounce_x
        
        # Ограничиваем границами экрана
        min_x = paddle_width // 2 + self.paddle_safety_margin
        max_x = self.screen_width - paddle_width // 2 - self.paddle_safety_margin
        
        return max(min_x, min(max_x, paddle_center_x))
    
    def _fallback_position(self, game_state: GameState) -> int:
        """
        Резервная позиция, если не удалось найти оптимальную
        """
        # Предсказываем точку пересечения с платформой
        paddle_y = game_state.paddle_position.y
        
        # Используем центр экрана как резервную позицию
        return self.screen_width // 2
    
    def calculate_paddle_movement(self, current_x: int, target_x: int, paddle_speed: int) -> int:
        """
        Рассчитывает точное движение платформы к целевой позиции
        
        Args:
            current_x: Текущая X-координата платформы
            target_x: Целевая X-координата платформы
            paddle_speed: Скорость платформы
            
        Returns:
            Смещение платформы (-1, 0, 1)
        """
        distance = target_x - current_x
        
        # Более чувствительная настройка для точного отслеживания
        tolerance = 5  # Точность попадания в 5 пикселей
        
        if abs(distance) <= tolerance:
            return 0  # Достаточно близко
        elif distance > 0:
            # Двигаемся вправо, но убеждаемся что действительно нужно двигаться
            return 1
        else:
            # Двигаемся влево
            return -1
    
    def evaluate_position_quality(self, game_state: GameState, paddle_x: int) -> float:
        """
        Оценивает качество позиции платформы
        
        Args:
            game_state: Текущее состояние игры
            paddle_x: X-координата платформы
            
        Returns:
            Оценка качества (больше = лучше)
        """
        if not game_state.remaining_bricks:
            return 0.0
        
        score = 0.0
        
        # Оцениваем позицию относительно ближайших кубиков
        nearest_bricks = game_state.get_nearest_bricks(5)
        
        for brick, distance in nearest_bricks:
            # Рассчитываем расстояние от платформы до кубика
            brick_center_x = brick.centerx
            distance_to_brick = abs(paddle_x - brick_center_x)
            
            # Чем ближе к кубику, тем лучше
            proximity_score = max(0, 100 - distance_to_brick) / 100.0
            
            # Вес кубика (можно сделать разным для разных рядов)
            brick_weight = self._get_brick_weight(brick)
            
            score += proximity_score * brick_weight
        
        # Добавляем бонус за центральное расположение
        center_bonus = 1.0 - abs(paddle_x - self.screen_width // 2) / (self.screen_width // 2)
        score += center_bonus * 0.1
        
        return score
    
    def _get_brick_weight(self, brick: pygame.Rect) -> float:
        """
        Определяет вес кубика для приоритизации
        
        Args:
            brick: Кубик для оценки
            
        Returns:
            Вес кубика
        """
        # Верхние кубики получают больший вес (их сложнее достать)
        if brick.top < 200:
            return 1.5
        elif brick.top < 300:
            return 1.2
        else:
            return 1.0
    
    def find_target_bricks(self, game_state: GameState, paddle_x: int) -> List[pygame.Rect]:
        """
        Находит целевые кубики для данной позиции платформы
        
        Args:
            game_state: Текущее состояние игры
            paddle_x: X-координата платформы
            
        Returns:
            Список целевых кубиков
        """
        target_bricks = []
        
        for brick in game_state.remaining_bricks:
            # Проверяем, может ли мяч от платформы достичь этого кубика
            if self._can_reach_brick(game_state, paddle_x, brick):
                target_bricks.append(brick)
        
        # Сортируем по приоритету
        target_bricks.sort(key=self._get_brick_weight, reverse=True)
        
        return target_bricks[:3]  # Берем топ-3 кубика
    
    def _can_reach_brick(self, game_state: GameState, paddle_x: int, brick: pygame.Rect) -> bool:
        """
        Проверяет, может ли мяч от платформы достичь кубика
        
        Args:
            game_state: Текущее состояние игры
            paddle_x: X-координата платформы
            brick: Целевой кубик
            
        Returns:
            True если кубик достижим
        """
        # Упрощенная проверка - если кубик находится выше платформы и не слишком далеко
        if brick.bottom >= game_state.paddle_position.y:
            return False
        
        # Проверяем горизонтальную доступность
        paddle_reach = game_state.paddle_width // 2 + 150  # Примерный радиус достижения
        brick_distance = abs(paddle_x - brick.centerx)
        
        return brick_distance <= paddle_reach
    
    def optimize_for_multiple_shots(self, game_state: GameState, trajectory_predictor) -> int:
        """
        Оптимизирует позицию для серии выстрелов (продвинутый алгоритм)
        
        Args:
            game_state: Текущее состояние игры
            trajectory_predictor: Предсказатель траектории
            
        Returns:
            Оптимальная X-координата платформы
        """
        if not game_state.remaining_bricks:
            return self.screen_width // 2
        
        best_position = game_state.paddle_position.x
        best_score = -1
        
        # Проверяем несколько позиций
        for test_x in range(50, self.screen_width - 50, 25):
            score = self._evaluate_position_for_sequence(game_state, test_x, trajectory_predictor)
            
            if score > best_score:
                best_score = score
                best_position = test_x
        
        return best_position
    
    def _evaluate_position_for_sequence(self, game_state: GameState, paddle_x: int, 
                                       trajectory_predictor) -> float:
        """
        Оценивает позицию для серии выстрелов
        
        Args:
            game_state: Текущее состояние игры
            paddle_x: X-координата платформы
            trajectory_predictor: Предсказатель траектории
            
        Returns:
            Оценка позиции
        """
        # Находим целевые кубики
        target_bricks = self.find_target_bricks(game_state, paddle_x)
        
        if not target_bricks:
            return 0.0
        
        total_score = 0.0
        
        for brick in target_bricks:
            # Рассчитываем оптимальную позицию для попадания в этот кубик
            optimal_pos = self._calculate_optimal_bounce_position(game_state, brick, trajectory_predictor)
            
            if optimal_pos is not None:
                # Оцениваем близость текущей позиции к оптимальной
                distance_penalty = abs(paddle_x - optimal_pos) / 100.0
                brick_weight = self._get_brick_weight(brick)
                
                total_score += brick_weight / (1 + distance_penalty)
        
        return total_score
    
    def _calculate_optimal_bounce_position(self, game_state: GameState, brick: pygame.Rect, 
                                         trajectory_predictor) -> Optional[float]:
        """
        Рассчитывает оптимальную позицию отскока для попадания в кубик
        
        Args:
            game_state: Текущее состояние игры
            brick: Целевой кубик
            trajectory_predictor: Предсказатель траектории
            
        Returns:
            Оптимальная X-координата отскока
        """
        # Упрощенный расчет - используем геометрию
        paddle_y = game_state.paddle_position.y
        
        # Рассчитываем угол для достижения кубика
        brick_center = Point(brick.centerx, brick.centery)
        
        # Упрощенная формула для расчета траектории
        # В реальной реализации здесь была бы более сложная физика
        dx = abs(brick_center.x - game_state.ball_position.x)
        dy = abs(brick_center.y - game_state.ball_position.y)
        
        if dy == 0:
            return None
        
        # Примерный расчет угла отскока
        angle_ratio = dx / dy
        
        # Находим точку на платформе, которая даст нужный угол
        # Это упрощенная модель
        paddle_center_x = game_state.paddle_position.x
        max_offset = game_state.paddle_width // 2
        
        required_offset = angle_ratio * 50  # Коэффициент для настройки
        bounce_x = paddle_center_x + max(-max_offset, min(max_offset, required_offset))
        
        return bounce_x