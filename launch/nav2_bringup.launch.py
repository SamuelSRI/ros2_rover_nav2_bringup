from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource

from ament_index_python.packages import get_package_share_directory

import os


def generate_launch_description():
    package_name = "ros2_rover_nav2_bringup"

    nav2_bringup_dir = get_package_share_directory("nav2_bringup")
    rover_bringup_dir = get_package_share_directory(package_name)

    params_file = LaunchConfiguration("params_file")
    use_sim_time = LaunchConfiguration("use_sim_time")

    declare_params_file = DeclareLaunchArgument(
        "params_file",
        default_value=os.path.join(
            rover_bringup_dir,
            "config",
            "nav2_params.yaml"
        ),
        description="Full path to the ROS 2 parameters file for Nav2"
    )

    declare_use_sim_time = DeclareLaunchArgument(
        "use_sim_time",
        default_value="false",
        description="Use simulation time"
    )

    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                nav2_bringup_dir,
                "launch",
                "navigation_launch.py"
            )
        ),
        launch_arguments={
            "use_sim_time": use_sim_time,
            "params_file": params_file,
            "autostart": "true"
        }.items()
    )

    return LaunchDescription([
        declare_params_file,
        declare_use_sim_time,
        nav2_launch
    ])
