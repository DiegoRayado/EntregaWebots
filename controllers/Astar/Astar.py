from controller import Robot
import heapq
import math

# Configuración del robot
time_step = 16
robot = Robot()

# Sensores de proximidad (solo los frontales)
ps = []
sensor_indices = [0, 1, 7]  # Sensores frontales
for i in sensor_indices:
    sensor = robot.getDevice(f'ps{i}')
    if sensor:
        ps.append(sensor)
        sensor.enable(time_step)
    else:
        print(f"Advertencia: Sensor ps{i} no encontrado")

# Sensores de posición
left_position_sensor = robot.getDevice('left wheel sensor')
right_position_sensor = robot.getDevice('right wheel sensor')
left_position_sensor.enable(time_step)
right_position_sensor.enable(time_step)

# Motores
left_motor = robot.getDevice('left wheel motor')
right_motor = robot.getDevice('right wheel motor')
left_motor.setPosition(float('inf'))
right_motor.setPosition(float('inf'))
left_motor.setVelocity(0)
right_motor.setVelocity(0)

# Parámetros geométricos del e-puck
WHEEL_RADIUS = 0.0205
AXLE_LENGTH = 0.0585

# Laberinto (1 = obstáculo, 0 = libre)
maze = [[0]*12 for _ in range(10)]  # Se debe rellenar con los obstáculos conocidos

# Conversión de coordenadas
start = (1, 1)  # Casilla B2
goal = (9, 10)  # Casilla J11

# Variables para odometría
x, y, theta = 1.5, 1.5, 0.0
robot.step(time_step)  # Asegurar actualización de sensores
prev_left_pos = left_position_sensor.getValue()
prev_right_pos = right_position_sensor.getValue()

def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def is_valid_cell(cell):
    return 0 <= cell[0] < 10 and 0 <= cell[1] < 12 and maze[cell[0]][cell[1]] == 0

def a_star_search(start, goal, maze):
    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    cost_so_far = {start: 0}
    
    while open_set:
        _, current = heapq.heappop(open_set)
        if current == goal:
            break
        
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            next_cell = (current[0] + dx, current[1] + dy)
            if is_valid_cell(next_cell):
                new_cost = cost_so_far[current] + 1
                if next_cell not in cost_so_far or new_cost < cost_so_far[next_cell]:
                    cost_so_far[next_cell] = new_cost
                    priority = new_cost + heuristic(goal, next_cell)
                    heapq.heappush(open_set, (priority, next_cell))
                    came_from[next_cell] = current
    
    if goal not in came_from:
        return None  # No se encontró un camino

    path = []
    cell = goal
    while cell in came_from:
        path.append(cell)
        cell = came_from[cell]
    path.append(start)
    path.reverse()
    return path

def update_odometry():
    global x, y, theta, prev_left_pos, prev_right_pos
    left_pos = left_position_sensor.getValue()
    right_pos = right_position_sensor.getValue()
    
    if math.isnan(left_pos) or math.isnan(right_pos):
        print("Error: Sensores de posición devuelven NaN")
        return

    d_left = (left_pos - prev_left_pos) * WHEEL_RADIUS
    d_right = (right_pos - prev_right_pos) * WHEEL_RADIUS
    prev_left_pos = left_pos
    prev_right_pos = right_pos
    
    d_center = (d_left + d_right) / 2.0
    d_theta = (d_right - d_left) / AXLE_LENGTH
    
    theta += d_theta
    x += d_center * math.cos(theta)
    y -= d_center * math.sin(theta)

def detect_obstacles():
    obstacles = set()
    for i, sensor in enumerate(ps):
        value = sensor.getValue()
        if value > 100:  # Ajusta este valor según sea necesario
            obstacles.add(sensor_indices[i])
    return obstacles

def calculate_angle_to_target(current_x, current_y, target_x, target_y):
    dx = target_x - current_x
    dy = -(target_y - current_y)
    return math.atan2(dy, dx)

def reorient_to_target(target_x, target_y):
    global theta
    target_angle = calculate_angle_to_target(x, y, target_x, target_y)
    angle_diff = target_angle - theta

    # Normalizar ángulo entre -pi y pi
    while angle_diff > math.pi:
        angle_diff -= 2 * math.pi
    while angle_diff < -math.pi:
        angle_diff += 2 * math.pi

    while abs(angle_diff) > 0.003:  # Precisión mejorada
        # Ajustar velocidad de giro de forma proporcional al error
        turn_speed = max(0.03, min(0.8, abs(angle_diff)))  # Velocidad más baja en giros finos
        turn_direction = 1 if angle_diff > 0 else -1  # Determinar dirección de giro

        left_motor.setVelocity(-turn_direction * turn_speed)
        right_motor.setVelocity(turn_direction * turn_speed)

        robot.step(time_step)
        update_odometry()

        # Recalcular el error
        target_angle = calculate_angle_to_target(x, y, target_x, target_y)
        angle_diff = target_angle - theta

        # Normalizar ángulo de nuevo
        while angle_diff > math.pi:
            angle_diff -= 2 * math.pi
        while angle_diff < -math.pi:
            angle_diff += 2 * math.pi

    left_motor.setVelocity(0)
    right_motor.setVelocity(0)


def move_to_next_cell(target):
    x_target, y_target = (target[1] + 0.5, target[0] + 0.5)
    print(f"Intentando mover a casilla {chr(65 + target[0])}{target[1] + 1} ({x_target}, {y_target})")
    
    reorient_to_target(x_target, y_target)
    
    left_motor.setVelocity(6.28)
    right_motor.setVelocity(6.28)
    
    while robot.step(time_step) != -1:
        update_odometry()
        obstacles = detect_obstacles()
        
       # print ("Y:", y)
        
        
        if obstacles:
            print(f"¡Obstáculo detectado! Sensores: {obstacles}")
            return False
        
        if abs(x - x_target) < 0.05 and abs(abs(y) - abs(y_target)) < 0.05:
            break
    
    left_motor.setVelocity(0)
    right_motor.setVelocity(0)
    return True

def move_back():
    print("Retrocediendo...")
    left_motor.setVelocity(-6.0)
    right_motor.setVelocity(-6.0)
    
    start_x, start_y = x, y
    while robot.step(time_step) != -1:
        update_odometry()
        if math.sqrt((x - start_x)**2 + (y - start_y)**2) > 0.5:  # Retrocede 10 cm
            break
    
    left_motor.setVelocity(0)
    right_motor.setVelocity(0)
    return (int(y), int(x))  # Devuelve la nueva posición

# Planificación inicial del camino
path = a_star_search(start, goal, maze)
print("Camino inicial calculado:", path)

# Movimiento del robot
current_index = 0
while current_index < len(path):

    cell = path[current_index]
    if move_to_next_cell(cell):
        print(f"Llegado a casilla {chr(65 + cell[0])}{cell[1] + 1}")
        current_index += 1
    else:
        print("Obstáculo encontrado. Retrocediendo y recalculando ruta.")
        current_cell = move_back()  # Obtiene la nueva posición después de retroceder
        # Marcar la celda como obstáculo en el mapa
        maze[cell[0]][cell[1]] = 1
        # Recalcular el camino desde la posición actual
        new_path = a_star_search(current_cell, goal, maze)
        if new_path is None:
            print("No se puede encontrar un camino al objetivo. Explorando alternativas...")
            # Intenta encontrar una celda cercana libre
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                alt_cell = (current_cell[0] + dx, current_cell[1] + dy)
                if is_valid_cell(alt_cell):
                    new_path = a_star_search(alt_cell, goal, maze)
                    if new_path:
                        print(f"Nuevo camino encontrado desde {alt_cell}")
                        break
        if new_path:
            path = new_path  # Usar el nuevo camino
            current_index = 0
        else:
            print("No se puede encontrar un nuevo camino.")
            break

