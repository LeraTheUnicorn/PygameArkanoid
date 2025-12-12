import json
import sys

log_file = "src/ai/logs/session_20251212_173956_396.json"

with open(log_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

actions = data.get("actions", [])

# Находим потерю мяча
ball_lost_idx = None
for i, action in enumerate(actions):
    if action.get("type") == "ball_lost" or action.get("action_type") == "ball_lost":
        ball_lost_idx = i
        break

if ball_lost_idx is None:
    print("Потеря мяча не найдена")
    sys.exit(1)

print(f"Потеря мяча найдена на действии {ball_lost_idx}\n")

# Анализируем последние 30 действий перед потерей
start_idx = max(0, ball_lost_idx - 30)
PADDLE_SPEED = 45  # пикселей за кадр

print("=== ДЕТАЛЬНЫЙ АНАЛИЗ ПОСЛЕДНИХ 30 ДЕЙСТВИЙ ПЕРЕД ПОТЕРЬЮ ===\n")

for i in range(start_idx, ball_lost_idx):
    action = actions[i]
    if action.get("type") == "ball_paddle_positions":
        ball = action.get("ball", {})
        paddle = action.get("paddle", {})
        
        ball_x = ball.get("centerx", 0)
        ball_y = ball.get("centery", 0)
        vel_x = ball.get("velocity_x", 0)
        vel_y = ball.get("velocity_y", 0)
        paddle_x = paddle.get("centerx", 0)
        paddle_y = paddle.get("y", 0)
        
        # Вычисляем предсказание
        if vel_y > 0:  # Мяч движется вниз
            distance_to_paddle_y = paddle_y - ball_y
            if distance_to_paddle_y > 0:
                time_to_paddle_frames = distance_to_paddle_y / vel_y  # кадры
                
                # Предсказываем X с учетом отскоков от стен
                predicted_x = ball_x
                remaining_time = time_to_paddle_frames
                sim_x = ball_x
                sim_vel_x = vel_x
                ball_radius = 8
                
                # Симулируем отскоки
                while remaining_time > 0:
                    if sim_vel_x > 0:
                        distance_to_right = 800 - ball_radius - sim_x
                        time_to_wall = distance_to_right / sim_vel_x if sim_vel_x > 0 else float('inf')
                    elif sim_vel_x < 0:
                        distance_to_left = sim_x - ball_radius
                        time_to_wall = distance_to_left / abs(sim_vel_x) if sim_vel_x < 0 else float('inf')
                    else:
                        time_to_wall = float('inf')
                    
                    if time_to_wall > 0 and time_to_wall <= remaining_time:
                        sim_x += sim_vel_x * time_to_wall
                        remaining_time -= time_to_wall
                        sim_vel_x = -sim_vel_x
                        sim_x = max(ball_radius, min(800 - ball_radius, sim_x))
                    else:
                        sim_x += sim_vel_x * remaining_time
                        remaining_time = 0
                        break
                
                predicted_x = sim_x
                predicted_x = max(ball_radius, min(800 - ball_radius, predicted_x))
                
                # Расстояние для платформы
                distance_to_target = abs(predicted_x - paddle_x)
                frames_to_reach = distance_to_target / PADDLE_SPEED if PADDLE_SPEED > 0 else float('inf')
                
                # Проверка достижимости
                safety_margin = 1.5
                is_reachable = frames_to_reach <= time_to_paddle_frames * safety_margin
                
                print(f"Действие {i}:")
                print(f"  Мяч: ({ball_x:.1f}, {ball_y:.1f}), vel=({vel_x:.1f}, {vel_y:.1f})")
                print(f"  Платформа: ({paddle_x:.1f}, {paddle_y:.1f})")
                print(f"  Время до платформы: {time_to_paddle_frames:.2f} кадров")
                print(f"  Предсказанная X: {predicted_x:.1f}")
                print(f"  Расстояние для платформы: {distance_to_target:.1f}px")
                print(f"  Кадров для платформы: {frames_to_reach:.2f}")
                print(f"  Достижимо: {'ДА' if is_reachable else 'НЕТ'} "
                      f"(нужно {frames_to_reach:.2f} <= {time_to_paddle_frames * safety_margin:.2f})")
                print()
