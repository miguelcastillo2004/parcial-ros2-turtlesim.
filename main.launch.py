import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition
from launch_ros.actions import Node

def generate_launch_description():
    # Obtener el directorio actual (asume que ambos archivos están en la misma carpeta)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    subs_events_path = os.path.join(current_dir, 'subs_events.launch.py')

    # 1. Argumento usado para una CONDICIÓN
    use_teleop_arg = DeclareLaunchArgument(
        'use_teleop',
        default_value='true',
        description='Si es true, lanza el nodo de control por teclado'
    )

    # 2. Inclusión del archivo Launch secundario + Paso de Argumentos
    included_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(subs_events_path),
        launch_arguments={
            'namespace': 'tortuga_jerarquica',
            'bg_r': '150',   # Cambiamos el color de fondo mediante argumentos
            'bg_g': '50',
            'bg_b': '100'
        }.items()
    )

    # 3. CONDICIÓN: Este nodo solo se ejecuta si 'use_teleop' es 'true'
    teleop_node = Node(
        package='turtlesim',
        executable='turtle_teleop_key',
        namespace='tortuga_jerarquica', # Mismo namespace que enviamos arriba
        name='teleop',
        condition=IfCondition(LaunchConfiguration('use_teleop')),
	prefix='xterm -e'
    )

    return LaunchDescription([
        use_teleop_arg,
        included_launch,
        teleop_node
    ])
