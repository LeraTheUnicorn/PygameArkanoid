"""
Инструмент для анализа логов движения платформы AI

Анализирует логи движения платформы, выявляет паттерны ошибок позиционирования
и предлагает корректировки алгоритма.
"""

import json
import os
from typing import List, Dict, Any, Optional, cast, DefaultDict
from collections import defaultdict
from pathlib import Path
import statistics


class LogAnalyzer:
    """Анализатор логов движения платформы"""
    
    def __init__(self, log_directory: str = "ai/logs"):
        """
        Инициализация анализатора
        
        Args:
            log_directory: Директория с логами
        """
        self.log_directory = log_directory
        self.movements: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []
        
    def load_logs(self, log_directory: Optional[str] = None) -> int:
        """
        Загружает все логи из директории
        
        Args:
            log_directory: Директория с логами (если не указана, используется self.log_directory)
        
        Returns:
            Количество загруженных записей
        """
        if log_directory:
            self.log_directory = log_directory
        
        if not os.path.exists(self.log_directory):
            return 0
        
        total_records = 0
        
        # Ищем все JSON файлы в директории
        for log_file in Path(self.log_directory).glob("*.json"):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    log_data = json.load(f)
                    
                    # Извлекаем движения платформы
                    if isinstance(log_data, list):
                        for entry in log_data:
                            if isinstance(entry, dict) and entry.get("type") == "paddle_movement":
                                self.movements.append(entry)
                                total_records += 1
                    elif isinstance(log_data, dict):
                        # Проверяем, есть ли список действий
                        actions = log_data.get("actions", [])
                        for action in actions:
                            if isinstance(action, dict) and action.get("type") == "paddle_movement":
                                self.movements.append(action)
                                total_records += 1
            except (json.JSONDecodeError, IOError) as e:
                print(f"Ошибка при загрузке {log_file}: {e}")
                continue
        
        return total_records
    
    def analyze_movement_patterns(self) -> Dict[str, Any]:
        """
        Анализирует паттерны движения платформы
        
        Returns:
            Словарь с результатами анализа
        """
        if not self.movements:
            return {"error": "Нет данных для анализа"}
        
        analysis = {
            "total_movements": len(self.movements),
            "average_distance": 0.0,
            "average_confidence": 0.0,
            "movement_reasons": defaultdict(int),
            "problematic_positions": [],
            "frequent_errors": [],
            "recommendations": []
        }
        
        # Анализ расстояний движения
        distances = [m.get("movement_distance", 0) for m in self.movements]
        if distances:
            analysis["average_distance"] = statistics.mean(distances)
            analysis["max_distance"] = max(distances)
            analysis["min_distance"] = min(distances)
        
        # Анализ уверенности
        confidences = [m.get("confidence", 0.5) for m in self.movements]
        if confidences:
            analysis["average_confidence"] = statistics.mean(confidences)
            analysis["low_confidence_count"] = sum(1 for c in confidences if c < 0.5)
        
        # Анализ причин движения
        movement_reasons = cast(DefaultDict[str, int], analysis["movement_reasons"])
        for movement in self.movements:
            reason: str = movement.get("reason", "unknown")
            movement_reasons[reason] += 1
        
        # Выявление проблемных позиций
        analysis["problematic_positions"] = self._find_problematic_positions()
        
        # Выявление частых ошибок
        analysis["frequent_errors"] = self._find_frequent_errors()
        
        # Генерация рекомендаций
        analysis["recommendations"] = self._generate_recommendations(analysis)
        
        return analysis
    
    def _find_problematic_positions(self) -> List[Dict[str, Any]]:
        """Выявляет проблемные позиции платформы"""
        problematic = []
        
        # Группируем движения по позициям
        position_stats: Dict[int, Dict[str, Any]] = defaultdict(lambda: {"count": 0, "low_confidence": 0, "distances": []})
        
        for movement in self.movements:
            from_pos = movement.get("from_position", 0)
            to_pos = movement.get("to_position", 0)
            confidence = movement.get("confidence", 0.5)
            distance = movement.get("movement_distance", 0)
            
            # Анализируем начальную позицию
            position_stats[from_pos]["count"] += 1
            if confidence < 0.5:
                position_stats[from_pos]["low_confidence"] += 1
            position_stats[from_pos]["distances"].append(distance)
        
        # Находим проблемные позиции
        for position, stats in position_stats.items():
            if stats["count"] >= 5:  # Минимум 5 движений для анализа
                low_conf_rate = stats["low_confidence"] / stats["count"]
                avg_distance = statistics.mean(stats["distances"]) if stats["distances"] else 0
                
                # Проблемная позиция: низкая уверенность или большие расстояния
                if low_conf_rate > 0.3 or avg_distance > 200:
                    problematic.append({
                        "position": position,
                        "movement_count": stats["count"],
                        "low_confidence_rate": low_conf_rate,
                        "average_distance": avg_distance
                    })
        
        # Сортируем по проблемности
        problematic.sort(key=lambda x: x["low_confidence_rate"] + (x["average_distance"] / 1000), reverse=True)
        
        return problematic[:10]  # Топ-10 проблемных позиций
    
    def _find_frequent_errors(self) -> List[Dict[str, Any]]:
        """Выявляет частые ошибки позиционирования"""
        errors: List[Dict[str, Any]] = []
        
        # Анализируем движения с низкой уверенностью
        low_confidence_movements = [
            m for m in self.movements 
            if m.get("confidence", 0.5) < 0.5
        ]
        
        if not low_confidence_movements:
            return errors
        
        # Группируем по причинам
        error_patterns: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"count": 0, "avg_confidence": [], "positions": []})
        
        for movement in low_confidence_movements:
            reason = movement.get("reason", "unknown")
            error_patterns[reason]["count"] += 1
            error_patterns[reason]["avg_confidence"].append(movement.get("confidence", 0.5))
            error_patterns[reason]["positions"].append(movement.get("from_position", 0))
        
        # Формируем список ошибок
        for reason, stats in error_patterns.items():
            if stats["count"] >= 3:  # Минимум 3 случая
                errors.append({
                    "reason": reason,
                    "frequency": stats["count"],
                    "average_confidence": statistics.mean(stats["avg_confidence"]),
                    "common_positions": self._find_common_positions(stats["positions"])
                })
        
        # Сортируем по частоте
        errors.sort(key=lambda x: x["frequency"], reverse=True)
        
        return errors
    
    def _find_common_positions(self, positions: List[int]) -> List[int]:
        """Находит наиболее частые позиции"""
        position_counts: Dict[int, int] = defaultdict(int)
        for pos in positions:
            # Округляем до ближайших 20 пикселей
            rounded_pos = (pos // 20) * 20
            position_counts[rounded_pos] += 1
        
        # Возвращаем топ-3 позиции
        sorted_positions = sorted(position_counts.items(), key=lambda x: x[1], reverse=True)
        return [pos for pos, count in sorted_positions[:3]]
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Генерирует рекомендации на основе анализа"""
        recommendations = []
        
        # Рекомендации по уверенности
        if analysis.get("low_confidence_count", 0) > len(self.movements) * 0.3:
            recommendations.append(
                "Более 30% движений имеют низкую уверенность. "
                "Рекомендуется улучшить алгоритм предсказания траектории."
            )
        
        # Рекомендации по расстояниям
        avg_distance = analysis.get("average_distance", 0)
        if avg_distance > 150:
            recommendations.append(
                f"Среднее расстояние движения ({avg_distance:.1f}px) слишком велико. "
                "Рекомендуется улучшить упреждение в расчетах позиции."
            )
        
        # Рекомендации по проблемным позициям
        problematic = analysis.get("problematic_positions", [])
        if problematic:
            recommendations.append(
                f"Обнаружено {len(problematic)} проблемных позиций. "
                "Рекомендуется добавить специальную логику для этих позиций."
            )
        
        # Рекомендации по частым ошибкам
        frequent_errors = analysis.get("frequent_errors", [])
        if frequent_errors:
            top_error = frequent_errors[0]
            recommendations.append(
                f"Частая ошибка: '{top_error['reason']}' ({top_error['frequency']} случаев). "
                "Рекомендуется улучшить логику для этого типа движения."
            )
        
        # Рекомендации по причинам движения
        reasons = analysis.get("movement_reasons", {})
        if "Простое движение к мячу" in reasons and reasons["Простое движение к мячу"] > len(self.movements) * 0.5:
            recommendations.append(
                "Более 50% движений - простые движения к мячу. "
                "Рекомендуется улучшить алгоритм прицеливания в блоки."
            )
        
        return recommendations
    
    def generate_report(self, output_file: Optional[str] = None) -> str:
        """
        Генерирует отчет об анализе
        
        Args:
            output_file: Путь к файлу для сохранения отчета (опционально)
        
        Returns:
            Текст отчета
        """
        analysis = self.analyze_movement_patterns()
        
        if "error" in analysis:
            return f"Ошибка: {analysis['error']}"
        
        report_lines = [
            "=" * 60,
            "ОТЧЕТ ОБ АНАЛИЗЕ ЛОГОВ ДВИЖЕНИЯ ПЛАТФОРМЫ AI",
            "=" * 60,
            "",
            f"Всего движений проанализировано: {analysis['total_movements']}",
            "",
            "СТАТИСТИКА ДВИЖЕНИЙ:",
            f"  Среднее расстояние: {analysis['average_distance']:.1f} пикселей",
            f"  Максимальное расстояние: {analysis.get('max_distance', 0):.1f} пикселей",
            f"  Минимальное расстояние: {analysis.get('min_distance', 0):.1f} пикселей",
            f"  Средняя уверенность: {analysis['average_confidence']:.2f}",
            f"  Движений с низкой уверенностью: {analysis.get('low_confidence_count', 0)}",
            "",
            "ПРИЧИНЫ ДВИЖЕНИЙ:",
        ]
        
        for reason, count in sorted(analysis['movement_reasons'].items(), key=lambda x: x[1], reverse=True):
            percentage = (count / analysis['total_movements']) * 100
            report_lines.append(f"  {reason}: {count} ({percentage:.1f}%)")
        
        if analysis['problematic_positions']:
            report_lines.extend([
                "",
                "ПРОБЛЕМНЫЕ ПОЗИЦИИ:",
            ])
            for pos_info in analysis['problematic_positions'][:5]:
                report_lines.append(
                    f"  Позиция {pos_info['position']}: "
                    f"{pos_info['movement_count']} движений, "
                    f"низкая уверенность: {pos_info['low_confidence_rate']:.1%}, "
                    f"среднее расстояние: {pos_info['average_distance']:.1f}px"
                )
        
        if analysis['frequent_errors']:
            report_lines.extend([
                "",
                "ЧАСТЫЕ ОШИБКИ:",
            ])
            for error in analysis['frequent_errors'][:5]:
                report_lines.append(
                    f"  {error['reason']}: {error['frequency']} случаев, "
                    f"средняя уверенность: {error['average_confidence']:.2f}"
                )
        
        if analysis['recommendations']:
            report_lines.extend([
                "",
                "РЕКОМЕНДАЦИИ:",
            ])
            for i, rec in enumerate(analysis['recommendations'], 1):
                report_lines.append(f"  {i}. {rec}")
        
        report_lines.extend([
            "",
            "=" * 60,
        ])
        
        report_text = "\n".join(report_lines)
        
        # Сохраняем отчет в файл, если указан
        if output_file:
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(report_text)
                report_lines.append(f"\nОтчет сохранен в: {output_file}")
            except IOError as e:
                report_lines.append(f"\nОшибка при сохранении отчета: {e}")
        
        return report_text


def main() -> None:
    """Основная функция для запуска анализатора из командной строки"""
    import sys
    
    log_dir = "ai/logs"
    if len(sys.argv) > 1:
        log_dir = sys.argv[1]
    
    analyzer = LogAnalyzer(log_dir)
    
    print("Загрузка логов...")
    records_count = analyzer.load_logs()
    print(f"Загружено записей: {records_count}")
    
    if records_count == 0:
        print("Логи не найдены. Убедитесь, что директория с логами существует и содержит JSON файлы.")
        return
    
    print("\nАнализ логов...")
    report = analyzer.generate_report("ai/logs/analysis_report.txt")
    print(report)


if __name__ == "__main__":
    main()

