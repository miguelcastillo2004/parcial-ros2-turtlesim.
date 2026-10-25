#!/usr/bin/env python3

import time
import threading

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy

from std_msgs.msg import Float64MultiArray, Bool
from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint
from builtin_interfaces.msg import Duration


class PickPlaceNode(Node):

    def __init__(self):
        super().__init__('pick_place_node')

        # Cliente de acción para el brazo
        self.arm_action_client = ActionClient(
            self,
            FollowJointTrajectory,
            '/scaled_joint_trajectory_controller/follow_joint_trajectory'
        )

        # Publisher del gripper
        self.gripper_pub = self.create_publisher(
            Float64MultiArray,
            '/gripper_controller/commands',
            10
        )

        # Publisher salida digital
        self.digital_output_pub = self.create_publisher(
            Bool,
            '/digital_output',
            10
        )

        # Subscriber entrada digital
        qos = QoSProfile(
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE
        )

        self.digital_input_sub = self.create_subscription(
            Bool,
            '/digital_input',
            self.digital_input_callback,
            qos
        )

        self.digital_input_received = False

        self.get_logger().info('Nodo Pick and Place iniciado.')
        self.get_logger().info('Esperando acción del brazo...')

        self.arm_action_client.wait_for_server()

        self.get_logger().info('Servidor de acción del brazo disponible.')

        self.start_timer = self.create_timer(
            2.0,
            lambda: threading.Thread(
                target=self.run_routine_once,
                daemon=True
            ).start()
        )

    def digital_input_callback(self, msg):
        if msg.data:
            self.digital_input_received = True
            self.get_logger().info(
                'Entrada digital recibida (True). Continuando...'
            )

    def move_arm(self, joint_positions, duration_sec=3.0):

        goal = FollowJointTrajectory.Goal()

        goal.trajectory.joint_names = [
            'shoulder_pan_joint',
            'shoulder_lift_joint',
            'elbow_joint',
            'wrist_1_joint',
            'wrist_2_joint',
            'wrist_3_joint'
        ]

        point = JointTrajectoryPoint()
        point.positions = joint_positions
        point.velocities = [0.0] * 6
        point.accelerations = [0.0] * 6

        point.time_from_start = Duration(
            sec=int(duration_sec),
            nanosec=int((duration_sec % 1) * 1e9)
        )

        goal.trajectory.points = [point]

        self.get_logger().info(
            f'Enviando brazo a: {joint_positions}'
        )

        future = self.arm_action_client.send_goal_async(goal)

        while not future.done():
            time.sleep(0.1)

        goal_handle = future.result()

        if not goal_handle.accepted:
            self.get_logger().error(
                'Objetivo del brazo rechazado.'
            )
            return False

        result_future = goal_handle.get_result_async()

        while not result_future.done():
            time.sleep(0.1)

        result = result_future.result()

        self.get_logger().info(
            f'Brazo llegó. Código: {result.status}'
        )

        return True

    def gripper_open(self):
        msg = Float64MultiArray()
        msg.data = [0.042, 0.042]
        self.gripper_pub.publish(msg)
        self.get_logger().info('Gripper ABIERTO.')

    def gripper_close(self):
        msg = Float64MultiArray()
        msg.data = [0.002, 0.002]
        self.gripper_pub.publish(msg)
        self.get_logger().info('Gripper CERRADO.')

    def set_digital_output(self, value):

        msg = Bool()
        msg.data = value

        self.digital_output_pub.publish(msg)

        estado = 'ON' if value else 'OFF'

        self.get_logger().info(
            f'Salida digital: {estado}'
        )

    def wait_for_digital_input(self, timeout_sec=10.0):

        self.digital_input_received = False

        self.get_logger().info(
            f'Esperando entrada digital en /digital_input '
            f'(timeout {timeout_sec}s)...'
        )

        start = time.time()

        while not self.digital_input_received:

            if (time.time() - start) > timeout_sec:
                self.get_logger().warn(
                    'Timeout esperando entrada digital. '
                    'Continuando de todos modos.'
                )
                return False

            time.sleep(0.1)

        self.get_logger().info(
            'Entrada digital confirmada.'
        )

        return True

    def run_routine_once(self):

        self.start_timer.cancel()

        self.get_logger().info(
            '=== INICIO RUTINA PICK AND PLACE ==='
        )

        self.get_logger().info(
            '--- Punto 1: Aproximación ---'
        )

        self.move_arm(
            [0.0, -1.57, 0.0, -1.57, 0.0, 0.0],
            duration_sec=3.0
        )

        self.set_digital_output(True)
        self.wait_for_digital_input(timeout_sec=5.0)
        self.set_digital_output(False)

        self.gripper_open()

        self.get_logger().info(
            'Punto 1 completado.'
        )

        self.get_logger().info(
            '--- Punto 2: Recogida ---'
        )

        self.move_arm(
            [0.5, -1.2, 0.3, -1.8, 0.2, 0.0],
            duration_sec=3.0
        )

        self.gripper_close()

        self.wait_for_digital_input(timeout_sec=5.0)

        self.get_logger().info(
            'Punto 2 completado.'
        )

        self.get_logger().info(
            '--- Punto 3: Colocación ---'
        )

        self.move_arm(
            [-0.5, -1.2, 0.3, -1.8, -0.2, 0.0],
            duration_sec=3.0
        )

        self.set_digital_output(True)

        self.gripper_open()

        self.wait_for_digital_input(timeout_sec=5.0)

        self.set_digital_output(False)

        self.get_logger().info(
            'Punto 3 completado.'
        )

        self.get_logger().info(
            '--- Regresando a posición inicial ---'
        )

        self.move_arm(
            [0.0, -1.57, 0.0, -1.57, 0.0, 0.0],
            duration_sec=3.0
        )

        self.get_logger().info(
            '=== RUTINA PICK AND PLACE FINALIZADA ==='
        )


def main(args=None):

    rclpy.init(args=args)

    node = PickPlaceNode()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()