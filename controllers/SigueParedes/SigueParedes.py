from controller import Robot, Camera, GPS

# Configuración
TIME_STEP = 32
MAX_SPEED = 6.28  # Velocidad máxima del e-puck
GREEN_THRESHOLD = 0.5  # 80% de la imagen debe ser verde para detenerse

# Inicializar robot y sensores
robot = Robot()
camera = robot.getDevice("camera")
camera.enable(TIME_STEP)

ps = []
for i in range(8):
    sensor_name = f"ps{i}"
    ps.append(robot.getDevice(sensor_name))
    ps[-1].enable(TIME_STEP)

left_motor = robot.getDevice("left wheel motor")
right_motor = robot.getDevice("right wheel motor")
left_motor.setPosition(float('inf'))
right_motor.setPosition(float('inf'))
left_motor.setVelocity(0)
right_motor.setVelocity(0)

# Inicializar GPS
gps = robot.getDevice("gps")
gps.enable(TIME_STEP)

def detect_green():
    """Detecta la presencia, posición y porcentaje de verde en la imagen."""
    width = camera.getWidth()
    height = camera.getHeight()
    image = camera.getImage()  # Obtener la imagen como un buffer de bytes

    green_pixels = []
    total_pixels = width * height
    
    for y in range(height):
        for x in range(width):
            index = (y * width + x) * 4  # Cada píxel tiene 4 bytes (RGBA)
            r = image[index]     # Rojo
            g = image[index + 1] # Verde
            b = image[index + 2] # Azul
            
            if g > 1.5 * r and g > 1.5 * b:  # Filtro para detectar verde
                green_pixels.append(x)

    green_ratio = len(green_pixels) / total_pixels  # Porcentaje de verde en la imagen

    if green_pixels:  # Si hay píxeles verdes detectados
        center_x = sum(green_pixels) / len(green_pixels)  # Centroide del objeto verde
        return center_x, green_ratio
    return None, 0  # No se detectó verde

# Estado del robot
following_green = False

# Bucle de control
while robot.step(TIME_STEP) != -1:
    green_x, green_ratio = detect_green()

    if green_ratio >= GREEN_THRESHOLD:
        print("Pelota detectada!!!")
        left_motor.setVelocity(0)
        right_motor.setVelocity(0)
        break  # Detener el robot completamente

    if green_x is not None:  # Solo cambiar de estado si se detectó verde
        following_green = True  

    if following_green and green_x is not None:
        width = camera.getWidth()
        if green_x < width / 3:  # El objeto está a la izquierda
            left_motor.setVelocity(MAX_SPEED / 4)
            right_motor.setVelocity(MAX_SPEED / 1.5)  # Gira a la izquierda
        elif green_x > 2 * width / 3:  # El objeto está a la derecha
            left_motor.setVelocity(MAX_SPEED / 1.5)
            right_motor.setVelocity(MAX_SPEED / 4)  # Gira a la derecha
        else:  # El objeto está al frente
            left_motor.setVelocity(MAX_SPEED / 1.5)
            right_motor.setVelocity(MAX_SPEED / 1.5)  # Avanzar recto
        continue  # Saltar lógica de seguir la pared

    # Leer sensores de proximidad
    front_obstacle = ps[7].getValue() > 100 or ps[0].getValue() > 100
    right_obstacle = ps[1].getValue() > 100 or ps[2].getValue() > 100
    left_obstacle = ps[5].getValue() > 100 or ps[6].getValue() > 100

    # Obtener la posición GPS del robot
    gps_values = gps.getValues()
    x_pos = gps_values[0]
    y_pos = gps_values[1]
    z_pos = gps_values[2]

    # Imprimir la posición GPS y la posición de la pelota
    print(f"Posición del robot (GPS): x={x_pos}, y={y_pos}, z={z_pos}")
    
    # Si la bola está detectada, calcula su posición en relación con el robot
    if green_x is not None:
        # Posición de la pelota en el plano XY en relación con la cámara
        ball_x_pos = x_pos + (green_x - width / 2) * 0.1  # Estimación simple, escala de acuerdo a la distancia
        ball_y_pos = y_pos
        print(f"Posición estimada de la pelota: x={ball_x_pos}, y={ball_y_pos}")

    # Seguir la pared de la derecha
    if front_obstacle:
        left_motor.setVelocity(MAX_SPEED / 2)
        right_motor.setVelocity(-MAX_SPEED / 2)  # Girar a la izquierda
    elif right_obstacle:
        left_motor.setVelocity(MAX_SPEED)
        right_motor.setVelocity(MAX_SPEED / 2)  # Mantenerse pegado a la pared derecha
    elif not right_obstacle:  # Si no hay pared a la derecha, girar a la derecha
        left_motor.setVelocity(MAX_SPEED / 2)
        right_motor.setVelocity(MAX_SPEED)
    else:
        left_motor.setVelocity(MAX_SPEED)
        right_motor.setVelocity(MAX_SPEED)  
