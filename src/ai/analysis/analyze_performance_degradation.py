#!/usr/bin/env python3
"""
Скрипт для анализа логов AI игрока и определения причин ухудшения производительности.
"""

import re
import os
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class MovementEvent:
    """Событие движения платформы"""
    timestamp: str
    current_x: float
    target_pos: Optional[float]
    distance: Optional[float]
    paddle_speed: int
    tolerance: Optional[float]
    buffer_zone: Optional[float]
    ball_y: float
    ball_vel_y: float
    movement_type: str  # 'NEW_TARGET', 'FIXED_TARGET', 'NORMAL'
    action: str  # 'moving', 'stopped', 'buffer_zone'
    movement_result: int  # -1, 0, 1

@dataclass
class BounceEvent:
    """Событие отскока мяча"""
    timestamp: str
    ball_y: float
    vel_y_before: float
    vel_y_after: float
    bounce_type: str  # 'top', 'wall'

class LogAnalyzer:
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.movement_events: List[MovementEvent] = []
        self.bounce_events: List[BounceEvent] = []
        self.metrics: Dict[str, any] = defaultdict(list)
        
    def parse_log_file(self, file_path: Path) -> None:
        """Парсит один лог-файл"""
        print(f"Обработка файла: {file_path.name}")
        
        last_vel_y: Optional[float] = None
        current_target: Optional[float] = None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                # Парсим временную метку
                timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                timestamp = timestamp_match.group(1) if timestamp_match else ""
                
                # Ищем события NEW TARGET
                new_target_match = re.search(
                    r'\[NEW TARGET\].*current_x=([\d.]+).*target_pos=([\d.]+).*distance=([\d.]+)px.*paddle_speed=(\d+)',
                    line
                )
                if new_target_match:
                    current_x = float(new_target_match.group(1))
                    target_pos = float(new_target_match.group(2))
                    distance = float(new_target_match.group(3))
                    paddle_speed = int(new_target_match.group(4))
                    current_target = target_pos
                    
                    # Извлекаем ball_y и ball_vel_y из предыдущих строк
                    ball_y, ball_vel_y = self._extract_ball_info_from_context(line)
                    
                    # Определяем действие
                    action_match = re.search(r'Расстояние до цели слишком мало.*?(\d+\.?\d*)px', line)
                    if action_match:
                        action = "stopped_small_distance"
                    else:
                        action = "moving"
                    
                    event = MovementEvent(
                        timestamp=timestamp,
                        current_x=current_x,
                        target_pos=target_pos,
                        distance=distance,
                        paddle_speed=paddle_speed,
                        tolerance=None,
                        buffer_zone=None,
                        ball_y=ball_y,
                        ball_vel_y=ball_vel_y,
                        movement_type="NEW_TARGET",
                        action=action,
                        movement_result=1 if target_pos > current_x else (-1 if target_pos < current_x else 0)
                    )
                    self.movement_events.append(event)
                
                # Ищем события FIXED TARGET
                fixed_target_match = re.search(
                    r'\[FIXED TARGET\].*current_x=([\d.]+).*target_pos=([\d.]+).*distance=([\d.]+)px.*tolerance=(\d+).*buffer_zone=([\d.]+).*ball_y=([\d.]+).*paddle_speed=(\d+)',
                    line
                )
                if fixed_target_match:
                    current_x = float(fixed_target_match.group(1))
                    target_pos = float(fixed_target_match.group(2))
                    distance = float(fixed_target_match.group(3))
                    tolerance = float(fixed_target_match.group(4))
                    buffer_zone = float(fixed_target_match.group(5))
                    ball_y = float(fixed_target_match.group(6))
                    paddle_speed = int(fixed_target_match.group(7))
                    
                    # Определяем действие
                    if "Достигли цели" in line:
                        action = "stopped_target_reached"
                        movement_result = 0
                    elif "В буферной зоне" in line:
                        action = "stopped_buffer_zone"
                        movement_result = 0
                    elif "Движение:" in line:
                        action_match = re.search(r'Движение: (-?\d+)', line)
                        movement_result = int(action_match.group(1)) if action_match else 0
                        action = "moving"
                    else:
                        action = "unknown"
                        movement_result = 0
                    
                    # Извлекаем ball_vel_y
                    ball_vel_y = self._extract_ball_vel_y_from_context(line)
                    
                    event = MovementEvent(
                        timestamp=timestamp,
                        current_x=current_x,
                        target_pos=target_pos,
                        distance=distance,
                        paddle_speed=paddle_speed,
                        tolerance=tolerance,
                        buffer_zone=buffer_zone,
                        ball_y=ball_y,
                        ball_vel_y=ball_vel_y,
                        movement_type="FIXED_TARGET",
                        action=action,
                        movement_result=movement_result
                    )
                    self.movement_events.append(event)
                
                # Ищем отскоки
                if last_vel_y is not None:
                    ball_vel_match = re.search(r'ball_vel_y=(-?\d+\.?\d*)', line)
                    if ball_vel_match:
                        current_vel_y = float(ball_vel_match.group(1))
                        # Отскок от верхней границы (вниз -> вверх)
                        if last_vel_y > 0 and current_vel_y < 0:
                            ball_y = self._extract_ball_y_from_context(line)
                            bounce = BounceEvent(
                                timestamp=timestamp,
                                ball_y=ball_y,
                                vel_y_before=last_vel_y,
                                vel_y_after=current_vel_y,
                                bounce_type="top"
                            )
                            self.bounce_events.append(bounce)
                        last_vel_y = current_vel_y
                    elif "ball_vel_y=" in line:
                        last_vel_y = None
                else:
                    ball_vel_match = re.search(r'ball_vel_y=(-?\d+\.?\d*)', line)
                    if ball_vel_match:
                        last_vel_y = float(ball_vel_match.group(1))
    
    def _extract_ball_info_from_context(self, line: str) -> Tuple[float, float]:
        """Извлекает ball_y и ball_vel_y из контекста строки"""
        # Пытаемся найти в самой строке
        ball_y_match = re.search(r'ball_y=([\d.]+)', line)
        ball_vel_match = re.search(r'ball_vel_y=(-?\d+\.?\d*)', line)
        
        ball_y = float(ball_y_match.group(1)) if ball_y_match else 0.0
        ball_vel_y = float(ball_vel_match.group(1)) if ball_vel_match else 0.0
        
        return ball_y, ball_vel_y
    
    def _extract_ball_y_from_context(self, line: str) -> float:
        """Извлекает ball_y из контекста"""
        ball_y_match = re.search(r'ball_y=([\d.]+)', line)
        return float(ball_y_match.group(1)) if ball_y_match else 0.0
    
    def _extract_ball_vel_y_from_context(self, line: str) -> float:
        """Извлекает ball_vel_y из контекста"""
        ball_vel_match = re.search(r'ball_vel_y=(-?\d+\.?\d*)', line)
        return float(ball_vel_match.group(1)) if ball_vel_match else 0.0
    
    def analyze_performance(self) -> Dict[str, any]:
        """Анализирует производительность на основе собранных данных"""
        analysis = {
            'total_movements': len(self.movement_events),
            'new_targets': len([e for e in self.movement_events if e.movement_type == 'NEW_TARGET']),
            'fixed_targets': len([e for e in self.movement_events if e.movement_type == 'FIXED_TARGET']),
            'bounces': len(self.bounce_events),
            'issues': []
        }
        
        # Анализ 1: Частота смены целей
        target_changes = []
        last_target = None
        for event in self.movement_events:
            if event.movement_type == 'NEW_TARGET' and event.target_pos is not None:
                if last_target is not None and abs(event.target_pos - last_target) > 50:
                    target_changes.append({
                        'from': last_target,
                        'to': event.target_pos,
                        'distance': abs(event.target_pos - last_target),
                        'ball_y': event.ball_y
                    })
                last_target = event.target_pos
        
        if len(target_changes) > len(self.movement_events) * 0.1:
            analysis['issues'].append({
                'type': 'excessive_target_changes',
                'severity': 'HIGH',
                'description': f'Слишком частые смены цели: {len(target_changes)} раз',
                'details': f'Среднее расстояние между сменами: {sum(tc["distance"] for tc in target_changes) / len(target_changes):.1f}px'
            })
        
        # Анализ 2: Большие расстояния до цели
        large_distances = [e for e in self.movement_events if e.distance and e.distance > 400]
        if large_distances:
            avg_large_distance = sum(e.distance for e in large_distances if e.distance) / len(large_distances)
            analysis['issues'].append({
                'type': 'large_target_distances',
                'severity': 'HIGH',
                'description': f'Много целей на большом расстоянии: {len(large_distances)} случаев',
                'details': f'Среднее расстояние: {avg_large_distance:.1f}px'
            })
        
        # Анализ 3: Проблемы с буферной зоной
        buffer_zone_stops = [e for e in self.movement_events 
                           if e.action == 'stopped_buffer_zone' and e.distance and e.distance > 20]
        if buffer_zone_stops:
            analysis['issues'].append({
                'type': 'excessive_buffer_zone_stops',
                'severity': 'MEDIUM',
                'description': f'Частые остановки в буферной зоне: {len(buffer_zone_stops)} раз',
                'details': f'Среднее расстояние при остановке: {sum(e.distance for e in buffer_zone_stops if e.distance) / len(buffer_zone_stops):.1f}px'
            })
        
        # Анализ 4: Проблемы с tolerance
        tolerance_issues = []
        for event in self.movement_events:
            if event.tolerance and event.paddle_speed:
                expected_tolerance = max(3, event.paddle_speed // 3)
                if abs(event.tolerance - expected_tolerance) > 2:
                    tolerance_issues.append({
                        'paddle_speed': event.paddle_speed,
                        'tolerance': event.tolerance,
                        'expected': expected_tolerance
                    })
        
        if tolerance_issues:
            analysis['issues'].append({
                'type': 'tolerance_mismatch',
                'severity': 'MEDIUM',
                'description': f'Несоответствие tolerance и paddle_speed: {len(tolerance_issues)} случаев'
            })
        
        # Анализ 5: Отскоки без реакции
        bounce_reactions = []
        for bounce in self.bounce_events:
            # Ищем события движения после отскока в течение следующих 10 событий
            bounce_idx = self.bounce_events.index(bounce)
            next_events = self.movement_events[bounce_idx:bounce_idx+10]
            
            # Проверяем, была ли сброшена цель после отскока
            target_reset = any(e.movement_type == 'NEW_TARGET' for e in next_events)
            if not target_reset:
                bounce_reactions.append({
                    'bounce': bounce,
                    'reaction_delay': len(next_events)
                })
        
        if bounce_reactions:
            analysis['issues'].append({
                'type': 'delayed_bounce_reaction',
                'severity': 'HIGH',
                'description': f'Медленная реакция на отскоки: {len(bounce_reactions)} случаев',
                'details': f'Средняя задержка реакции: {sum(br["reaction_delay"] for br in bounce_reactions) / len(bounce_reactions):.1f} событий'
            })
        
        # Анализ 6: Распределение скоростей платформы
        paddle_speeds = [e.paddle_speed for e in self.movement_events]
        if paddle_speeds:
            speed_counter = Counter(paddle_speeds)
            analysis['paddle_speed_distribution'] = dict(speed_counter)
        
        # Анализ 7: Статистика по расстояниям
        distances = [e.distance for e in self.movement_events if e.distance is not None]
        if distances:
            analysis['distance_stats'] = {
                'min': min(distances),
                'max': max(distances),
                'avg': sum(distances) / len(distances),
                'median': sorted(distances)[len(distances) // 2]
            }
        
        return analysis
    
    def generate_report(self) -> str:
        """Генерирует текстовый отчет"""
        analysis = self.analyze_performance()
        
        report = []
        report.append("=" * 80)
        report.append("АНАЛИЗ ПРОИЗВОДИТЕЛЬНОСТИ AI ИГРОКА")
        report.append("=" * 80)
        report.append("")
        
        report.append(f"Всего событий движения: {analysis['total_movements']}")
        report.append(f"  - Новых целей (NEW_TARGET): {analysis['new_targets']}")
        report.append(f"  - Зафиксированных целей (FIXED_TARGET): {analysis['fixed_targets']}")
        report.append(f"  - Отскоков мяча: {analysis['bounces']}")
        report.append("")
        
        if analysis.get('paddle_speed_distribution'):
            report.append("Распределение скоростей платформы:")
            for speed, count in sorted(analysis['paddle_speed_distribution'].items()):
                report.append(f"  - Скорость {speed}px: {count} событий")
            report.append("")
        
        if analysis.get('distance_stats'):
            stats = analysis['distance_stats']
            report.append("Статистика по расстояниям до цели:")
            report.append(f"  - Минимальное: {stats['min']:.1f}px")
            report.append(f"  - Максимальное: {stats['max']:.1f}px")
            report.append(f"  - Среднее: {stats['avg']:.1f}px")
            report.append(f"  - Медианное: {stats['median']:.1f}px")
            report.append("")
        
        if analysis['issues']:
            report.append("=" * 80)
            report.append("ОБНАРУЖЕННЫЕ ПРОБЛЕМЫ")
            report.append("=" * 80)
            report.append("")
            
            for i, issue in enumerate(analysis['issues'], 1):
                severity_mark = "[!!]" if issue['severity'] == 'HIGH' else "[!]"
                report.append(f"{i}. {severity_mark} [{issue['severity']}] {issue['type']}")
                report.append(f"   {issue['description']}")
                if 'details' in issue:
                    report.append(f"   Детали: {issue['details']}")
                report.append("")
        else:
            report.append("Серьезных проблем не обнаружено.")
            report.append("")
        
        return "\n".join(report)


def main():
    """Главная функция"""
    script_dir = Path(__file__).parent  # Каталог analysis
    # Лог-файлы находятся в каталоге logs (на уровень выше)
    ai_dir = script_dir.parent
    logs_dir = ai_dir / "logs"
    
    # Ищем лог-файлы в каталоге logs
    log_files = sorted([f for f in logs_dir.glob("**/ai_player_*.log")])
    
    if not log_files:
        print(f"Лог-файлы не найдены в {logs_dir}!")
        return
    
    print(f"Найдено {len(log_files)} лог-файлов")
    print("=" * 80)
    
    analyzer = LogAnalyzer(logs_dir)
    
    for log_file in log_files:
        try:
            analyzer.parse_log_file(log_file)
        except Exception as e:
            print(f"Ошибка при обработке {log_file.name}: {e}")
    
    report = analyzer.generate_report()
    print(report)
    
    # Сохраняем отчет в каталог analysis
    report_file = script_dir / "performance_analysis_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\nОтчет сохранен в: {report_file}")


if __name__ == "__main__":
    main()
