import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, RegisterEventHandler, EmitEvent
from launch.substitutions import LaunchConfiguration
from launch.event_handlers import OnProcessStart, OnProcessExit
from launch.events import Shutdown
from launch_ros.actions import Node

def generate_launch_description():
    # 1. Declarar argumentos (namespace y colores de fondo)
    ns_arg = DeclareLaunchArgument('namespace', default_value='sim1', description='Namespace del nodo')
    bg_r_arg = DeclareLaunchArgument('bg_r', default_value='0', description='Fondo Rojo')
    bg_g_arg = DeclareLaunchArgument('bg_g', default_value='0', description='Fondo Verde')
    bg_b_arg = DeclareLaunchArgument('bg_b', default_value='255', description='Fondo Azul')

    # 2. Configurar el nodo vinculando sus parámetros a los argumentos
    turtlesim_node = Node(
        package='turtlesim',
        executable='turtlesim_node',
        namespace=LaunchConfiguration('namespace'),
        name='turtlesim',
        parameters=[{
            'background_r': LaunchConfiguration('bg_r'),
            'background_g': LaunchConfiguration('bg_g'),
            'background_b': LaunchConfiguration('bg_b'),
        }]
    )

    # 3. EVENTO 1: Inicio de nodo (Imprime un mensaje en terminal)
    on_start_event = RegisterEventHandler(
        OnProcessStart(
            target_action=turtlesim_node,
            on_start=[LogInfo(msg="\n---> EVENTO: ¡El nodo turtlesim ha iniciado exitosamente! <---\n")]
        )
    )

    # 4. EVENTO 2: Finalización de proceso (Si cierras la ventana, apaga todo el sistema Launch)
    on_exit_event = RegisterEventHandler(
        OnProcessExit(
            target_action=turtlesim_node,
            on_exit=[
                LogInfo(msg="\n---> EVENTO: Ventana de turtlesim cerrada. Apagando sistema... <---\n"),
                EmitEvent(event=Shutdown())
            ]
        )
    )

    return LaunchDescription([
        ns_arg, bg_r_arg, bg_g_arg, bg_b_arg,
        turtlesim_node,
        on_start_event,
        on_exit_event
    ])
