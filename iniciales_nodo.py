import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from turtlesim.srv import TeleportAbsolute, SetPen
import math
import time
import tkinter as tk
from tkinter import messagebox

def mostrar_mensaje(letra):
    """Genera un pop-up nativo que bloquea la ejecución hasta que se presione OK"""
    root = tk.Tk()
    root.withdraw() # Oculta la ventana principal
    root.attributes('-topmost', True) # Fuerza que el pop-up salga al frente
    messagebox.showinfo("Siguiente Trayectoria", f"Se va a simular la letra: {letra}")
    root.destroy()

class GeneradorIniciales(Node):
    def __init__(self):
        super().__init__('generador_iniciales')
        self.publisher_ = self.create_publisher(Twist, '/turtle1/cmd_vel', 10)

        # Clientes para gestionar el lápiz y la posición inicial sin dejar rastro
        self.pen_client = self.create_client(SetPen, '/turtle1/set_pen')
        self.teleport_client = self.create_client(TeleportAbsolute, '/turtle1/teleport_absolute')

        while not self.pen_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Esperando servicio set_pen...')
        while not self.teleport_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Esperando servicio teleport_absolute...')

    def mover_pen(self, r, g, b, width, off):
        req = SetPen.Request()
        req.r, req.g, req.b, req.width, req.off = r, g, b, width, off
        self.pen_client.call_async(req)
        time.sleep(0.2)

    def teletransportar(self, x, y, theta):
        req = TeleportAbsolute.Request()
        req.x, req.y, req.theta = float(x), float(y), float(theta)
        self.teleport_client.call_async(req)
        time.sleep(0.5)

    def ejecutar_movimiento(self, v_x, v_theta, duracion):
        """Publica comandos de velocidad en bucle abierto durante el tiempo especificado"""
        msg = Twist()
        msg.linear.x = float(v_x)
        msg.angular.z = float(v_theta)

        t_end = time.time() + duracion
        while time.time() < t_end:
            self.publisher_.publish(msg)
            time.sleep(0.05) 

        # Frenar la tortuga al terminar el trazo
        msg.linear.x = 0.0
        msg.angular.z = 0.0
        self.publisher_.publish(msg)
        time.sleep(0.5)

    def dibujar_M(self):
        mostrar_mensaje('M')
        self.get_logger().info('Trazando la letra M...')
        
        # Levantar lápiz y ubicar tortuga
        self.mover_pen(0, 0, 0, 2, 1)
        self.teletransportar(2.0, 4.0, math.pi/2) # (2,4) apuntando hacia arriba
        self.mover_pen(255, 0, 0, 3, 0) # Lápiz rojo grueso

        # Cinemática de la 'M'
        self.ejecutar_movimiento(2.0, 0.0, 1.0)                 # Trazo 1: Arriba
        self.ejecutar_movimiento(0.0, -math.radians(135), 1.0)  # Giro 1: -135°
        self.ejecutar_movimiento(1.41, 0.0, 1.0)                # Trazo 2: Diagonal baja
        self.ejecutar_movimiento(0.0, math.radians(90), 1.0)    # Giro 2: +90°
        self.ejecutar_movimiento(1.41, 0.0, 1.0)                # Trazo 3: Diagonal alta
        self.ejecutar_movimiento(0.0, -math.radians(135), 1.0)  # Giro 3: -135°
        self.ejecutar_movimiento(2.0, 0.0, 1.0)                 # Trazo 4: Abajo

    def dibujar_C(self):
        mostrar_mensaje('C')
        self.get_logger().info('Trazando la letra C...')
        
        # Levantar lápiz y ubicar tortuga a la derecha
        self.mover_pen(0, 0, 0, 2, 1)
        self.teletransportar(8.0, 6.0, math.pi) # (8,6) apuntando a la izquierda
        self.mover_pen(0, 0, 255, 3, 0) # Lápiz azul grueso

        # Cinemática de la 'C' (Semicírculo)
        # Velocidad lineal = 1.5, Velocidad angular = 1.5 -> Radio = 1.0
        # Tiempo para 180 grados (pi radianes) = pi / w
        self.ejecutar_movimiento(1.5, 1.5, math.pi / 1.5)

def main(args=None):
    rclpy.init(args=args)
    nodo = GeneradorIniciales()

    nodo.dibujar_M()
    nodo.dibujar_C()

    nodo.get_logger().info('Simulación de trayectorias completada.')
    
    nodo.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
