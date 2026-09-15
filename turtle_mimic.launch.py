from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # Primer nodo turtlesim en su propio namespace
        Node(
            package='turtlesim',
            executable='turtlesim_node',
            name='sim',
            namespace='turtlesim1'
        ),
        
        # Segundo nodo turtlesim en un namespace distinto
        Node(
            package='turtlesim',
            executable='turtlesim_node',
            name='sim',
            namespace='turtlesim2'
        ),
        
        # Nodo mimic que lee la posición de la tortuga 1 y mueve la tortuga 2
        Node(
            package='turtlesim',
            executable='mimic',
            name='mimic',
            remappings=[
                ('/input/pose', '/turtlesim1/turtle1/pose'),
                ('/output/cmd_vel', '/turtlesim2/turtle1/cmd_vel')
            ]
        )
    ])
