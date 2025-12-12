#!/usr/bin/env python3
"""
Универсальный скрипт для анализа потери мяча из логов AI игрока.

Использование:
    python analyze_ball_loss.py                    # Анализирует последнюю директорию с логами
    python analyze_ball_loss.py <путь_к_директории>  # Анализирует указанную директорию
    python analyze_ball_loss.py <путь_к_файлу>       # Анализирует конкретный файл
"""

import re
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict


def find_latest_log_directory(logs_base_dir: Path) -> Optional[Path]:
    """Находит последнюю директорию с логами по дате в названии"""
    if not logs_base_dir.exists():
        return None
    
    # Ищем директории с паттерном даты YYYY-MM-DD_HH-MM-SS
    date_dirs = []
    for item in logs_base_dir.iterdir():
        if item.is_dir() and re.match(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}', item.name):
            date_dirs.append(item)
    
    if not date_dirs:
        return None
    
    # Сортируем по имени (которое содержит дату) и возвращаем последнюю
    date_dirs.sort(key=lambda x: x.name, reverse=True)
    return date_dirs[0]


def parse_log_file(file_path: Path) -> List[Dict]:
    """Парсит лог-файл и извлекает события"""
    events = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                # Извлекаем временную метку
                timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                timestamp = timestamp_match.group(1) if timestamp_match else ""
                
                # Ищем события NEW TARGET
                new_target_match = re.search(
                    r'\[NEW TARGET\].*current_x=([\d.]+).*target_pos=([\d.]+).*distance=([\d.]+)px',
                    line
                )
                if new_target_match:
                    ball_y_match = re.search(r'ball_y=([\d.]+)', line)
                    ball_vel_y_match = re.search(r'ball_vel_y=(-?\d+\.?\d*)', line)
                    
                    events.append({
                        'timestamp': timestamp,
                        'type': 'NEW_TARGET',
                        'current_x': float(new_target_match.group(1)),
                        'target_pos': float(new_target_match.group(2)),
                        'distance': float(new_target_match.group(3)),
                        'ball_y': float(ball_y_match.group(1)) if ball_y_match else None,
                        'ball_vel_y': float(ball_vel_y_match.group(1)) if ball_vel_y_match else None,
                        'line': line
                    })
                    continue
                
                # Ищем события FIXED TARGET
                fixed_target_match = re.search(
                    r'\[FIXED TARGET\].*current_x=([\d.]+).*target_pos=([\d.]+).*distance=([\d.]+)px.*ball_y=([\d.]+)',
                    line
                )
                if fixed_target_match:
                    ball_vel_y_match = re.search(r'ball_vel_y=(-?\d+\.?\d*)', line)
                    
                    events.append({
                        'timestamp': timestamp,
                        'type': 'FIXED_TARGET',
                        'current_x': float(fixed_target_match.group(1)),
                        'target_pos': float(fixed_target_match.group(2)),
                        'distance': float(fixed_target_match.group(3)),
                        'ball_y': float(fixed_target_match.group(4)),
                        'ball_vel_y': float(ball_vel_y_match.group(1)) if ball_vel_y_match else None,
                        'line': line
                    })
                    continue
                
                # Ищем отскоки
                bounce_match = re.search(
                    r'\[EARLY BOUNCE DETECTION\].*vel_y изменился с ([\d.]+) \(вниз\) на (-?\d+\.?\d*) \(вверх\)',
                    line
                )
                if bounce_match:
                    events.append({
                        'timestamp': timestamp,
                        'type': 'BOUNCE',
                        'vel_y_before': float(bounce_match.group(1)),
                        'vel_y_after': float(bounce_match.group(2)),
                        'line': line
                    })
                    continue
    except Exception as e:
        print(f"Ошибка при чтении файла {file_path}: {e}")
    
    return events


def analyze_ball_loss(events: List[Dict]) -> Dict[str, Any]:
    """Анализирует события для выявления причины потери мяча"""
    analysis: Dict[str, Any] = {
        'targets_set': [],
        'bounces': [],
        'issues': []
    }
    
    # Находим все установки целей
    for event in events:
        if event['type'] == 'NEW_TARGET':
            analysis['targets_set'].append({
                'target_pos': event['target_pos'],
                'ball_y': event['ball_y'],
                'ball_vel_y': event['ball_vel_y'],
                'timestamp': event['timestamp']
            })
        elif event['type'] == 'BOUNCE':
            analysis['bounces'].append({
                'vel_y_before': event['vel_y_before'],
                'vel_y_after': event['vel_y_after'],
                'timestamp': event['timestamp']
            })
    
    # Анализируем последнюю установку цели перед потерей мяча
    if analysis['targets_set']:
        last_target = analysis['targets_set'][-1]
        
        # Ищем события FIXED TARGET после последней установки цели
        last_target_time = last_target['timestamp']
        subsequent_events = [
            e for e in events 
            if e['timestamp'] >= last_target_time and e['type'] == 'FIXED_TARGET'
        ]
        
        # Проверяем, была ли целевая позиция обновлена
        target_changed = False
        for event in subsequent_events:
            if abs(event['target_pos'] - last_target['target_pos']) > 10:
                target_changed = True
                break
        
        if not target_changed and subsequent_events:
            # Целевая позиция не обновлялась, но мяч был потерян
            # Проверяем, был ли отскок после установки цели
            bounces_after_target = [
                b for b in analysis['bounces']
                if b['timestamp'] >= last_target_time
            ]
            
            if bounces_after_target:
                ball_y_str = f"{last_target['ball_y']:.1f}" if last_target['ball_y'] is not None else "N/A"
                analysis['issues'].append({
                    'type': 'TARGET_NOT_UPDATED_AFTER_BOUNCE',
                    'severity': 'HIGH',
                    'description': (
                        f"Целевая позиция {last_target['target_pos']:.1f} была установлена "
                        f"при ball_y={ball_y_str}, но не обновлялась после "
                        f"{len(bounces_after_target)} отскоков. Мяч мог изменить траекторию."
                    ),
                    'last_target': last_target,
                    'bounces_after': bounces_after_target
                })
            else:
                # Проверяем, была ли целевая позиция правильной
                # Если мяч был потерян в позиции x=784, а целевая была 710, это ошибка предсказания
                analysis['issues'].append({
                    'type': 'PREDICTION_ERROR',
                    'severity': 'HIGH',
                    'description': (
                        f"Целевая позиция {last_target['target_pos']:.1f} была установлена, "
                        f"но мяч был потерян в другой позиции. Возможно, ошибка предсказания траектории."
                    ),
                    'last_target': last_target
                })
    
    return analysis


def analyze_file(file_path: Path, detailed: bool = False) -> Dict[str, Any]:
    """Анализирует один файл и возвращает результаты"""
    events = parse_log_file(file_path)
    
    if not events:
        return {
            'file': file_path.name,
            'file_path': file_path,
            'events_count': 0,
            'analysis': None
        }
    
    analysis = analyze_ball_loss(events)
    
    result: Dict[str, Any] = {
        'file': file_path.name,
        'file_path': file_path,
        'events_count': len(events),
        'analysis': analysis
    }
    
    if detailed and analysis['targets_set']:
        # Находим все уникальные целевые позиции
        unique_targets = {}
        for target in analysis['targets_set']:
            target_pos = target['target_pos']
            if target_pos not in unique_targets:
                unique_targets[target_pos] = {
                    'target_pos': target_pos,
                    'count': 0,
                    'first_occurrence': target['timestamp'],
                    'ball_y_values': []
                }
            unique_targets[target_pos]['count'] += 1
            if target['ball_y'] is not None:
                unique_targets[target_pos]['ball_y_values'].append(target['ball_y'])
        
        result['unique_targets'] = unique_targets
    
    return result


def main() -> None:
    """Главная функция"""
    parser = argparse.ArgumentParser(
        description='Анализ потери мяча из логов AI игрока',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python analyze_ball_loss.py                          # Анализирует последнюю директорию
  python analyze_ball_loss.py logs/2025-12-12_18-03-44 # Анализирует конкретную директорию
  python analyze_ball_loss.py logs/ai_player_5.log      # Анализирует конкретный файл
  python analyze_ball_loss.py --detailed               # Подробный анализ с деталями по целям
        """
    )
    parser.add_argument(
        'path',
        nargs='?',
        help='Путь к директории с логами или к конкретному лог-файлу'
    )
    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Показать подробный анализ с деталями по целевым позициям'
    )
    parser.add_argument(
        '--target',
        type=float,
        help='Показать детальный анализ для конкретной целевой позиции'
    )
    
    args = parser.parse_args()
    
    # Определяем базовую директорию логов
    script_dir = Path(__file__).parent
    logs_base_dir = script_dir
    
    # Определяем, что анализировать
    if args.path:
        input_path = Path(args.path)
        if not input_path.is_absolute():
            input_path = script_dir / input_path
        
        if input_path.is_file():
            # Анализируем один файл
            log_files = [input_path]
            session_name = input_path.stem
        elif input_path.is_dir():
            # Анализируем директорию
            log_files = sorted(input_path.glob("ai_player_*.log"))
            session_name = input_path.name
        else:
            print(f"Ошибка: путь {args.path} не существует!")
            return
    else:
        # Ищем последнюю директорию с логами
        log_dir = find_latest_log_directory(logs_base_dir)
        if not log_dir:
            print("Не найдено директорий с логами!")
            print(f"Искал в: {logs_base_dir}")
            return
        
        log_files = sorted(log_dir.glob("ai_player_*.log"))
        session_name = log_dir.name
    
    if not log_files:
        print(f"Не найдено лог-файлов для анализа!")
        if args.path:
            print(f"Искал в: {input_path}")
        return
    
    print("=" * 80)
    print(f"АНАЛИЗ ПОТЕРИ МЯЧА - {session_name}")
    print("=" * 80)
    print()
    
    all_issues = []
    all_results = []
    
    for log_file in log_files:
        result = analyze_file(log_file, detailed=args.detailed)
        all_results.append(result)
        
        if result['events_count'] == 0:
            print(f"Пропуск: {log_file.name} (нет событий)")
            continue
        
        print(f"Обработка: {log_file.name}")
        analysis = result['analysis']
        
        if analysis and analysis['issues']:
            print(f"  Найдено проблем: {len(analysis['issues'])}")
            for issue in analysis['issues']:
                print(f"    [{issue['severity']}] {issue['type']}")
                print(f"      {issue['description']}")
                all_issues.append({
                    'file': log_file.name,
                    'issue': issue
                })
        
        if analysis:
            if analysis['targets_set']:
                print(f"  Установок цели: {len(analysis['targets_set'])}")
                last_target = analysis['targets_set'][-1]
                ball_y_str = f"{last_target['ball_y']:.1f}" if last_target['ball_y'] is not None else "N/A"
                print(f"    Последняя цель: {last_target['target_pos']:.1f} при ball_y={ball_y_str}")
            
            if analysis['bounces']:
                print(f"  Отскоков: {len(analysis['bounces'])}")
        
        # Показываем уникальные цели, если запрошен подробный анализ
        if args.detailed and 'unique_targets' in result:
            print(f"  Уникальных целевых позиций: {len(result['unique_targets'])}")
            for target_pos, info in sorted(result['unique_targets'].items()):
                avg_ball_y = sum(info['ball_y_values']) / len(info['ball_y_values']) if info['ball_y_values'] else None
                avg_y_str = f"{avg_ball_y:.1f}" if avg_ball_y is not None else "N/A"
                print(f"    Цель {target_pos:.1f}: установлена {info['count']} раз(а), "
                      f"средний ball_y={avg_y_str}")
    
    print()
    print("=" * 80)
    print("СВОДКА ПРОБЛЕМ")
    print("=" * 80)
    
    if all_issues:
        for i, item in enumerate(all_issues, 1):
            print(f"\n{i}. Файл: {item['file']}")
            issue = item['issue']
            print(f"   Тип: {issue['type']}")
            print(f"   Серьезность: {issue['severity']}")
            print(f"   Описание: {issue['description']}")
    else:
        print("\nСерьезных проблем не обнаружено в логах.")
    
    # Детальный анализ для конкретной целевой позиции
    if args.target is not None:
        print()
        print("=" * 80)
        print(f"ДЕТАЛЬНЫЙ АНАЛИЗ ДЛЯ ЦЕЛЕВОЙ ПОЗИЦИИ {args.target}")
        print("=" * 80)
        
        for result in all_results:
            if not result['analysis'] or not result['analysis']['targets_set']:
                continue
            
            # Находим события с указанной целевой позицией
            target_events = [
                e for e in result['analysis']['targets_set']
                if abs(e['target_pos'] - args.target) < 1.0
            ]
            
            if target_events:
                print(f"\nФайл: {result['file']}")
                target_event = target_events[0]
                print(f"  Цель {args.target:.1f} установлена:")
                print(f"    Время: {target_event['timestamp']}")
                ball_y_str = f"{target_event['ball_y']:.1f}" if target_event['ball_y'] is not None else "N/A"
                ball_vel_y_str = f"{target_event['ball_vel_y']:.1f}" if target_event['ball_vel_y'] is not None else "N/A"
                print(f"    ball_y: {ball_y_str}")
                print(f"    ball_vel_y: {ball_vel_y_str}")
                
                # Находим все события после установки цели
                events = parse_log_file(result['file_path'])
                subsequent = [
                    e for e in events 
                    if e['timestamp'] >= target_event['timestamp'] and e['type'] == 'FIXED_TARGET'
                ]
                
                print(f"\n  События после установки цели ({len(subsequent)}):")
                for i, event in enumerate(subsequent[:20], 1):  # Первые 20
                    event_ball_y_str = f"{event['ball_y']:.1f}" if event['ball_y'] is not None else "N/A"
                    print(f"    {i}. ball_y={event_ball_y_str}, target={event['target_pos']:.1f}, "
                          f"current_x={event['current_x']:.1f}, distance={event['distance']:.1f}px")
                
                # Проверяем, была ли цель обновлена
                target_updated = any(
                    abs(e['target_pos'] - args.target) > 10 for e in subsequent
                )
                
                if not target_updated and subsequent:
                    start_y = target_event['ball_y'] if target_event['ball_y'] is not None else 0
                    end_y = subsequent[-1]['ball_y'] if subsequent[-1]['ball_y'] is not None else 0
                    print(f"\n  ⚠️  ПРОБЛЕМА: Целевая позиция НЕ обновлялась после установки!")
                    print(f"     Мяч двигался от y={start_y:.1f} до y={end_y:.1f}")
                    print(f"     но целевая позиция оставалась {args.target:.1f}")
                    print(f"     Если мяч отскочил от блока, траектория могла измениться!")


if __name__ == "__main__":
    main()
