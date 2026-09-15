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
    def __init__(self):
        super().__init__('turtle_controller')
        
        # Máquina de estados: 1 = Manual, 2 = Círculos, 3 = Trayectoria
        self.mode = 1 
        self.direction = 1 # 1 = Antihorario, -1 = Horario
        self.current_pose = Pose()

        # Grupo de callbacks reentrante para permitir procesamiento en paralelo (necesario para Action Servers)
        self.cb_group = ReentrantCallbackGroup()

        # Publicador y Suscriptor
        self.cmd_pub = self.create_publisher(Twist, '/turtle1/cmd_vel', 10)
        self.pose_sub = self.create_subscription(Pose, '/turtle1/pose', self.pose_callback, 10, callback_group=self.cb_group)

        # Servicios
        self.set_mode_srv = self.create_service(SetMode, 'set_mode', self.set_mode_cb, callback_group=self.cb_group)
        self.get_mode_srv = self.create_service(GetMode, 'get_mode', self.get_mode_cb, callback_group=self.cb_group)

        # Action Server
        self.action_server = ActionServer(
            self,
            Navigate,
            'execute_trajectory',
            execute_callback=self.execute_trajectory_cb,
            cancel_callback=self.cancel_trajectory_cb,
            callback_group=self.cb_group
        )

        # Timer para el modo de círculos a 10Hz
        self.timer = self.create_timer(0.1, self.timer_callback, callback_group=self.cb_group)
        self.get_logger().info('Nodo controlador iniciado en Modo Manual.')

    def pose_callback(self, msg):
        self.current_pose = msg

    def set_mode_cb(self, request, response):
        if request.mode in [1, 2]:
            self.mode = request.mode
            if self.mode == 2:
                self.direction = request.direction
            self.cmd_pub.publish(Twist()) # Detener la tortuga al cambiar de modo
            response.success = True
            self.get_logger().info(f'Cambiado a modo: {self.mode}')
        else:
            response.success = False
        return response

    def get_mode_cb(self, request, response):
        response.current_mode = self.mode
        return response

    def timer_callback(self):
        # Modo Manual: No publicamos nada, para que el teleop pueda funcionar sin conflicto
        if self.mode == 1:
            pass 
        
        # Modo Círculos: Publicamos velocidades constantes
        elif self.mode == 2:
            msg = Twist()
            msg.linear.x = 2.0
            msg.angular.z = 2.0 * self.direction
            self.cmd_pub.publish(msg)

    def cancel_trajectory_cb(self, goal_handle):
        self.get_logger().info('¡Solicitud de cancelación recibida!')
        return CancelResponse.ACCEPT

    def execute_trajectory_cb(self, goal_handle):
        self.get_logger().info('Iniciando modo trayectoria...')
        self.mode = 3 # Cambia a modo trayectoria
        waypoints = goal_handle.request.waypoints
        feedback_msg = Navigate.Feedback()
        result = Navigate.Result()

        for i, wp in enumerate(waypoints):
            feedback_msg.current_point_index = i
            goal_handle.publish_feedback(feedback_msg)
            self.get_logger().info(f'Navegando al punto {i+1}: X={wp.x}, Y={wp.y}')

            while rclpy.ok():
                # Verificar si el usuario canceló la acción
                if goal_handle.is_cancel_requested:
                    goal_handle.canceled()
                    self.mode = 1 # Retorna a manual
                    self.cmd_pub.publish(Twist()) # Frenado de emergencia
                    result.success = False
                    return result

                # Control Cinemático Proporcional (P)
                dx = wp.x - self.current_pose.x
                dy = wp.y - self.current_pose.y
                distance = math.sqrt(dx**2 + dy**2)

                # Condición de llegada al waypoint
                if distance < 0.1:
                    break

                angle_to_goal = math.atan2(dy, dx)
                angle_error = angle_to_goal - self.current_pose.theta

                # Normalización del ángulo entre -pi y pi
                angle_error = math.atan2(math.sin(angle_error), math.cos(angle_error))

                cmd = Twist()
                cmd.linear.x = 1.5 * distance
                cmd.angular.z = 4.0 * angle_error
                self.cmd_pub.publish(cmd)
                
                time.sleep(0.05) # Iteración de control a ~20Hz

        self.get_logger().info('Trayectoria completada. Retornando a modo Manual.')
        self.mode = 1
        self.cmd_pub.publish(Twist()) # Detenerse al finalizar
        goal_handle.succeed()
        result.success = True
        return result

def main(args=None):
    rclpy.init(args=args)
    node = TurtleController()
    
    # Es obligatorio usar MultiThreadedExecutor para Actions y Services concurrentes
    executor = MultiThreadedExecutor()
    rclpy.spin(node, executor=executor)
    
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()