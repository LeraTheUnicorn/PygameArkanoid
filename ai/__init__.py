"""
AI-система для авторежима игры Арканоид

Этот пакет содержит компоненты системы машинного обучения
для улучшения авторежима игры.
"""

from .ai_player import AIPlayer
from .trajectory_predictor import TrajectoryPredictor
from .position_optimizer import PositionOptimizer
from .learning_system import LearningSystem
from .performance_logger import PerformanceLogger
from .game_state import GameState

__version__ = "1.0.0"
__author__ = "AI System Developer"

__all__ = [
    "AIPlayer",
    "TrajectoryPredictor", 
    "PositionOptimizer",
    "LearningSystem",
    "PerformanceLogger",
    "GameState"
]