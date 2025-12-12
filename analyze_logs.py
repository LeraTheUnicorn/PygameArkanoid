import json
import sys
from collections import defaultdict

# Загружаем лог-файл
log_file = "src/ai/logs/session_20251212_173956_396.json"

try:
    with open(log_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
except Exception as e:
    print(f"Ошибка при загрузке лог-файла: {e}")
    sys.exit(1)

actions = data.get("actions", [])
print(f"Всего действий: {len(actions)}")

# Находим все потери мяча
ball_lost_actions = []
for i, action in enumerate(actions):
    if action.get("type") == "ball_lost" or action.get("action_type") == "ball_lost":
        ball_lost_actions.append((i, action))

print(f"\nКоличество потерь мяча: {len(ball_lost_actions)}")

if ball_lost_actions:
    print("\n=== АНАЛИЗ ПОТЕРЬ МЯЧА ===")
    
    # Анализируем каждую потерю
    for idx, (action_idx, action) in enumerate(ball_lost_actions):
        print(f"\n--- Потеря #{idx + 1} (действие {action_idx}) ---")
        print(f"Время: {action.get('session_time', 0):.2f}с")
        
        # Ищем последние позиции мяча и платформы перед потерей
        # Ищем последние 50 действий перед потерей
        start_idx = max(0, action_idx - 50)
        
        print(f"\nПоследние действия перед потерей:")
        found_positions = []
        for i in range(start_idx, action_idx):
            if i < len(actions):
                a = actions[i]
                if a.get("type") == "ball_paddle_positions":
                    ball = a.get("ball", {})
                    paddle = a.get("paddle", {})
                    distance = a.get("distance", {})
                    found_positions.append({
                        "idx": i,
                        "ball_x": ball.get("centerx", 0),
                        "ball_y": ball.get("centery", 0),
                        "vel_x": ball.get("velocity_x", 0),
                        "vel_y": ball.get("velocity_y", 0),
                        "paddle_x": paddle.get("centerx", 0),
                        "paddle_y": paddle.get("y", 0),
                        "horizontal_distance": distance.get("horizontal_distance", 0),
                        "ball_above_paddle": distance.get("ball_above_paddle", True)
                    })
        
        # Показываем последние 10 позиций
        for pos in found_positions[-10:]:
            print(f"  Действие {pos['idx']}: ball=({pos['ball_x']:.1f}, {pos['ball_y']:.1f}), "
                  f"vel=({pos['vel_x']:.1f}, {pos['vel_y']:.1f}), "
                  f"paddle=({pos['paddle_x']:.1f}, {pos['paddle_y']:.1f}), "
                  f"horiz_dist={pos['horizontal_distance']:.1f}, "
                  f"above={pos['ball_above_paddle']}")
        
        # Анализ последней позиции перед потерей
        if found_positions:
            last_pos = found_positions[-1]
            print(f"\nПоследняя позиция перед потерей:")
            print(f"  Мяч: ({last_pos['ball_x']:.1f}, {last_pos['ball_y']:.1f})")
            print(f"  Скорость мяча: ({last_pos['vel_x']:.1f}, {last_pos['vel_y']:.1f})")
            print(f"  Платформа: ({last_pos['paddle_x']:.1f}, {last_pos['paddle_y']:.1f})")
            print(f"  Горизонтальное расстояние: {last_pos['horizontal_distance']:.1f}px")
            
            # Вычисляем, могла ли платформа добраться до мяча
            if last_pos['vel_y'] > 0:  # Мяч движется вниз
                time_to_paddle = (last_pos['paddle_y'] - last_pos['ball_y']) / last_pos['vel_y'] if last_pos['vel_y'] > 0 else 0
                if time_to_paddle > 0:
                    predicted_x = last_pos['ball_x'] + last_pos['vel_x'] * time_to_paddle
                    distance_to_travel = abs(predicted_x - last_pos['paddle_x'])
                    paddle_speed = 10  # Предполагаемая скорость платформы
                    time_needed = distance_to_travel / paddle_speed if paddle_speed > 0 else float('inf')
                    
                    print(f"  Время до платформы: {time_to_paddle:.2f}с")
                    print(f"  Предсказанная X: {predicted_x:.1f}")
                    print(f"  Расстояние для платформы: {distance_to_travel:.1f}px")
                    print(f"  Время для платформы: {time_needed:.2f}с")
                    print(f"  Доступно времени: {'ДА' if time_needed <= time_to_paddle else 'НЕТ'} "
                          f"(разница: {abs(time_to_paddle - time_needed):.2f}с)")

# Ищем действия с информацией о движении платформы
paddle_movements = []
for i, action in enumerate(actions):
    if "paddle_movement" in action or "movement" in action:
        paddle_movements.append((i, action))

print(f"\nДействий с движением платформы: {len(paddle_movements)}")

# Статистика по game_results
game_results = data.get("game_results", [])
if game_results:
    print(f"\n=== РЕЗУЛЬТАТЫ ИГРЫ ===")
    for i, result in enumerate(game_results):
        print(f"Игра #{i+1}:")
        print(f"  Очки: {result.get('score', 0)}")
        print(f"  Потеряно жизней: {result.get('lives_lost', 0)}")
        print(f"  Время: {result.get('duration', 0):.2f}с")
