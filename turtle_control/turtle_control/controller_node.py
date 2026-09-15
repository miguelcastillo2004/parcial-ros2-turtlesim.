#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, CancelResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

from geometry_msgs.msg import Twist
from turtlesim.msg import Pose
import math
import time

from turtlesim_interfaces.srv import SetMode, GetMode
from turtlesim_interfaces.action import Navigate

class TurtleController(Node):
    """
    Nodo controlador principal para la máquina de estados de turtlesim.
    Implementa 3 modos de operación:
    1. Manual (Teleoperación)
    2. Círculos (Autónomo mediante Servicio)
    3. Trayectoria por puntos (Autónomo mediante Acción con retroalimentación)
    """
    def __init__(self):
        super().__init__('turtle_controller')
        
        # Variables de estado interno
        self.mode = 1         # Inicializa en Modo Manual
        self.direction = 1    # 1 = Antihorario, -1 = Horario
        self.current_pose = Pose()

        # Callback group reentrante para permitir concurrencia (Action y Service Servers simultáneos)
        self.cb_group = ReentrantCallbackGroup()

        # --- SUSCRIPTORES Y PUBLICADORES ---
        self.cmd_pub = self.create_publisher(Twist, '/turtle1/cmd_vel', 10)
        self.pose_sub = self.create_subscription(Pose, '/turtle1/pose', self.pose_callback, 10, callback_group=self.cb_group)

        # --- SERVICIOS ---
        self.set_mode_srv = self.create_service(SetMode, 'set_mode', self.set_mode_cb, callback_group=self.cb_group)
        self.get_mode_srv = self.create_service(GetMode, 'get_mode', self.get_mode_cb, callback_group=self.cb_group)

        # --- ACCIONES ---
        self.action_server = ActionServer(
            self, Navigate, 'execute_trajectory',
            execute_callback=self.execute_trajectory_cb,
            cancel_callback=self.cancel_trajectory_cb,
            callback_group=self.cb_group
        )

        # Bucle de control a 10Hz para mantener la velocidad del modo círculos
        self.timer = self.create_timer(0.1, self.timer_callback, callback_group=self.cb_group)
        self.get_logger().info('Nodo controlador iniciado en Modo Manual.')

    def pose_callback(self, msg):
        """Actualiza la posición actual de la tortuga leyendo el tópico /turtle1/pose"""
        self.current_pose = msg

    def set_mode_cb(self, request, response):
        """
        Callback del servicio /set_mode. 
        Permite cambiar a modo 1 (Manual) o 2 (Círculos).
        """
        if request.mode in [1, 2]:
            self.mode = request.mode
            if self.mode == 2:
                self.direction = request.direction
            
            # Freno de seguridad al cambiar de modo
            self.cmd_pub.publish(Twist()) 
            response.success = True
            self.get_logger().info(f'Cambiado a modo: {self.mode}')
        else:
            response.success = False
        return response

    def get_mode_cb(self, request, response):
        """Devuelve el modo actual de operación de la máquina de estados"""
        response.current_mode = self.mode
        return response

    def timer_callback(self):
        """Bucle principal que evalúa qué acciones tomar según el modo actual"""
        if self.mode == 1:
            # En modo manual no publicamos nada para evitar conflictos con el teleop
            pass 
        elif self.mode == 2:
            # En modo círculos se publica velocidad constante lineal y angular
            msg = Twist()
            msg.linear.x = 2.0
            msg.angular.z = 2.0 * self.direction
            self.cmd_pub.publish(msg)

    def cancel_trajectory_cb(self, goal_handle):
        """Acepta solicitudes de cancelación (preemption) desde el cliente de la acción"""
        self.get_logger().info('¡Solicitud de cancelación recibida!')
        return CancelResponse.ACCEPT

    def execute_trajectory_cb(self, goal_handle):
        """
        Callback principal del servidor de acción.
        Implementa un Controlador Cinemático Proporcional (P) para guiar
        a la tortuga punto por punto.
        """
        self.get_logger().info('Iniciando modo trayectoria...')
        self.mode = 3 # Bloquea el estado en modo trayectoria
        waypoints = goal_handle.request.waypoints
        feedback_msg = Navigate.Feedback()
        result = Navigate.Result()

        # Recorrer cada punto enviado por el usuario
        for i, wp in enumerate(waypoints):
            feedback_msg.current_point_index = i
            goal_handle.publish_feedback(feedback_msg) # Enviar retroalimentación
            self.get_logger().info(f'Navegando al punto {i+1}: X={wp.x}, Y={wp.y}')

            while rclpy.ok():
                # Comprobar si el usuario canceló la acción externamente
                if goal_handle.is_cancel_requested:
                    goal_handle.canceled()
                    self.mode = 1 
                    self.cmd_pub.publish(Twist()) # Freno de emergencia
                    result.success = False
                    return result

                # --- Lógica de Control Proporcional ---
                dx = wp.x - self.current_pose.x
                dy = wp.y - self.current_pose.y
                distance = math.sqrt(dx**2 + dy**2)

                # Tolerancia de llegada (10 cm)
                if distance < 0.1:
                    break

                angle_to_goal = math.atan2(dy, dx)
                angle_error = angle_to_goal - self.current_pose.theta

                # Normalizar el error de ángulo entre -pi y pi
                angle_error = math.atan2(math.sin(angle_error), math.cos(angle_error))

                # Calcular y enviar velocidades
                cmd = Twist()
                cmd.linear.x = 1.5 * distance
                cmd.angular.z = 4.0 * angle_error
                self.cmd_pub.publish(cmd)
                
                time.sleep(0.05) # Iteración de control a 20Hz

        self.get_logger().info('Trayectoria completada. Retornando a modo Manual.')
        self.mode = 1
        self.cmd_pub.publish(Twist()) # Detener la tortuga
        goal_handle.succeed()
        result.success = True
        return result

def main(args=None):
    rclpy.init(args=args)
    node = TurtleController()
    
    # Ejecutor multihilo necesario para manejar Action Servers en ROS 2
    executor = MultiThreadedExecutor()
    rclpy.spin(node, executor=executor)
    
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()