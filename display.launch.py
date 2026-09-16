import os
from launch import LaunchDescription
from launch.substitutions import Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():
    # Obtener el directorio actual donde se encuentra este archivo launch
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Rutas relativas a los archivos Xacro y de configuración de RViz
    xacro_file = os.path.join(current_dir, 'dif_bot_description.urdf.xacro')
    rviz_config_file = os.path.join(current_dir, 'urdf_config.rviz')

    # Comando para compilar el Xacro a URDF estándar en tiempo de ejecución
    robot_description = ParameterValue(Command(['xacro ', xacro_file]), value_type=str)

    # 1. Nodo: Robot State Publisher
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description}]
    )

    # 2. Nodo: Joint State Publisher GUI
    joint_state_publisher_gui_node = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui'
    )

    # 3. Nodo: RViz2
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config_file] # Carga el archivo de configuración
    )

    return LaunchDescription([
        robot_state_publisher_node,
        joint_state_publisher_gui_node,
        rviz_node
    ])
