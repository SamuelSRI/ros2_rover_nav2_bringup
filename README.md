# ros2_rover_nav2_bringup

ROS 2 bringup package for running Nav2 on a tracked rover.

This package starts the Nav2 navigation stack using the rover TF tree, filtered odometry, a `map -> odom` transform, a 360° LiDAR obstacle layer, and an AS-DT1 traversability grid.

Nav2 publishes velocity commands on `/cmd_vel`, which can then be converted into left and right track commands by a lower-level tracked-drive controller.

## Overview

The rover navigation stack uses two complementary perception sources:

```text
360° LiDAR
  -> /scan
  -> Nav2 obstacle layer
  -> obstacle detection around the rover

AS-DT1 front LiDAR
  -> /lidar/points
  -> elevation mapping node
  -> /traversability_grid
  -> Nav2 traversability layer
  -> terrain traversability in front of the rover
```

The 360° LiDAR is used as the main obstacle source around the rover.

The AS-DT1 is used to analyse the terrain in front of the rover and mark non-traversable areas such as steep slopes, steps, rough ground, holes, or dangerous terrain.

Nav2 fuses both sources into its costmaps and outputs velocity commands on `/cmd_vel`.

## Features

* Nav2 bringup for a tracked rover
* Uses the TF chain `map -> odom -> base_link`
* Uses filtered odometry from `/odometry/filtered`
* Uses a 360° LiDAR `LaserScan` topic for obstacle detection
* Uses an AS-DT1 traversability grid for terrain-aware navigation
* Publishes velocity commands on `/cmd_vel`
* Compatible with a lower-level `cmd_vel_to_tracks` controller
* Designed for outdoor rover navigation experiments

## Package structure

```text
ros2_rover_nav2_bringup
├── CMakeLists.txt
├── package.xml
├── config
│   └── nav2_params.yaml
├── launch
│   └── nav2_bringup.launch.py
├── README.md
└── LICENSE
```

## Expected rover stack

This package assumes that the rest of the rover stack is already running.

### Robot description and TF

The rover must publish the robot model and sensor transforms.

Expected TF tree:

```text
map
└── odom
    └── base_link
        ├── lidar_360_link
        └── asdt1_link
```

The exact sensor frame names can be different, but the TF tree must allow Nav2 to transform sensor data into the costmap frames.

Typical required nodes:

```text
robot_state_publisher
static transform publishers or URDF joints
map -> odom localization node
odometry / EKF node
```

### Localization

The rover stack must provide filtered odometry:

```text
/odometry/filtered
```

Expected type:

```text
nav_msgs/msg/Odometry
```

The rover stack must also provide the TF transform:

```text
map -> odom
```

This transform can come from GPS localization, SLAM, map localization, or a dedicated global localization node.

The odometry or EKF system must provide:

```text
odom -> base_link
```

The complete navigation TF chain is therefore:

```text
map -> odom -> base_link
```

### 360° LiDAR

The 360° LiDAR driver must publish a `LaserScan` topic.

Default topic:

```text
/scan
```

Expected type:

```text
sensor_msgs/msg/LaserScan
```

This topic is used by the Nav2 obstacle layer to mark and clear obstacles around the rover.

### AS-DT1 elevation mapping

The AS-DT1 LiDAR produces a front point cloud:

```text
/lidar/points
```

This point cloud is processed by the elevation mapping node, which publishes:

```text
/traversability_grid
```

Expected type:

```text
nav_msgs/msg/OccupancyGrid
```

The traversability grid should encode terrain as:

```text
0   = free / traversable
100 = occupied / non-traversable
-1  = unknown
```

### Motor control

Nav2 publishes:

```text
/cmd_vel
```

Expected type:

```text
geometry_msgs/msg/Twist
```

For a tracked rover, `/cmd_vel` can be converted into left and right track commands:

```text
Nav2
  -> /cmd_vel
  -> cmd_vel_to_tracks
  -> left and right track speeds
  -> motor controllers
```

## Architecture

```text
                         +----------------------+
                         |   map -> odom TF     |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | /odometry/filtered   |
                         | odom -> base_link    |
                         +----------+-----------+
                                    |
                                    v
                               Nav2 stack

+----------------+        +---------------------+
| 360° LiDAR     | -----> | obstacle_layer_360  |
| /scan          |        | Nav2 costmap        |
+----------------+        +----------+----------+
                                      |
                                      v
                               +-------------+
                               | Nav2 fused  |
                               | costmaps    |
                               +-------------+
                                      ^
                                      |
+----------------+        +----------+----------+
| AS-DT1 LiDAR   | -----> | traversability_layer|
| /lidar/points  |        | /traversability_grid|
+----------------+        +---------------------+

Nav2 planner/controller
  -> /cmd_vel
  -> tracked drive controller
```

## Topics

### Subscribed topics

#### `/odometry/filtered`

Filtered rover odometry.

Type:

```text
nav_msgs/msg/Odometry
```

#### `/tf`

Dynamic transforms.

Type:

```text
tf2_msgs/msg/TFMessage
```

Required dynamic transforms include:

```text
map -> odom
odom -> base_link
```

#### `/tf_static`

Static transforms.

Type:

```text
tf2_msgs/msg/TFMessage
```

Required static transforms usually include:

```text
base_link -> lidar_360_link
base_link -> asdt1_link
```

#### `/scan`

360° LiDAR scan used by the obstacle layer.

Type:

```text
sensor_msgs/msg/LaserScan
```

If your LiDAR publishes on another topic, update `config/nav2_params.yaml`.

Example:

```yaml
lidar_360:
  topic: /ldlidar_node/scan
```

#### `/traversability_grid`

Traversability grid produced from the AS-DT1 elevation mapping pipeline.

Type:

```text
nav_msgs/msg/OccupancyGrid
```

This grid is used to add terrain-aware constraints to the Nav2 costmaps.

### Published topics

#### `/cmd_vel`

Velocity command generated by Nav2.

Type:

```text
geometry_msgs/msg/Twist
```

#### `/local_costmap/costmap`

Local Nav2 costmap.

Type:

```text
nav_msgs/msg/OccupancyGrid
```

#### `/global_costmap/costmap`

Global Nav2 costmap.

Type:

```text
nav_msgs/msg/OccupancyGrid
```

## Frames

Recommended frame setup:

```text
map
└── odom
    └── base_link
        ├── lidar_360_link
        └── asdt1_link
```

Recommended Nav2 frame usage:

```text
bt_navigator.global_frame: map
behavior_server.global_frame: map
global_costmap.global_frame: map
local_costmap.global_frame: odom
robot_base_frame: base_link
odom_topic: /odometry/filtered
```

The global costmap and planner use `map`.

The local costmap uses `odom` to remain smooth and locally stable.

## Costmap configuration

The costmaps fuse three layers:

```text
obstacle_layer_360
  -> source: /scan
  -> role: obstacle detection and clearing around the rover

traversability_layer
  -> source: /traversability_grid
  -> role: terrain traversability from the AS-DT1 elevation map

inflation_layer
  -> role: safety margin around obstacles and non-traversable cells
```

The 360° LiDAR obstacle layer uses:

```text
marking: true
clearing: true
```

The traversability grid is fused with:

```text
use_maximum: true
```

This allows the AS-DT1 traversability grid to add dangerous terrain areas without erasing obstacles detected by the 360° LiDAR.

## Important parameters

Main configuration file:

```text
config/nav2_params.yaml
```

Important parameters:

| Parameter                            | Description                                |
| ------------------------------------ | ------------------------------------------ |
| `bt_navigator.global_frame`          | Global navigation frame, recommended `map` |
| `global_costmap.global_frame`        | Global costmap frame, recommended `map`    |
| `local_costmap.global_frame`         | Local costmap frame, recommended `odom`    |
| `robot_base_frame`                   | Rover base frame, usually `base_link`      |
| `odom_topic`                         | Filtered odometry topic                    |
| `robot_radius`                       | Approximate rover radius used by costmaps  |
| `max_vel_x`                          | Maximum forward velocity                   |
| `max_vel_theta`                      | Maximum angular velocity                   |
| `local_costmap.width`                | Width of the local costmap                 |
| `local_costmap.height`               | Height of the local costmap                |
| `obstacle_layer_360.lidar_360.topic` | 360° LiDAR scan topic                      |
| `traversability_layer.map_topic`     | AS-DT1 traversability grid topic           |
| `inflation_radius`                   | Safety inflation radius around obstacles   |

## Dependencies

Install Nav2 if it is not already installed.

For ROS 2 Lyrical:

```bash
sudo apt update
sudo apt install ros-lyrical-navigation2 ros-lyrical-nav2-bringup
```

For a generic ROS 2 distribution:

```bash
sudo apt update
sudo apt install ros-$ROS_DISTRO-navigation2 ros-$ROS_DISTRO-nav2-bringup
```

This package also expects the rest of the rover stack to provide:

* robot description and TF
* filtered odometry
* `map -> odom` transform
* 360° LiDAR scan
* AS-DT1 traversability grid
* lower-level velocity or track controller

## Build

From your ROS 2 workspace:

```bash
cd ~/ros2_ws

source /opt/ros/lyrical/setup.bash

colcon build --packages-select ros2_rover_nav2_bringup

source install/setup.bash
```

Or with `$ROS_DISTRO`:

```bash
cd ~/ros2_ws

source /opt/ros/$ROS_DISTRO/setup.bash

colcon build --packages-select ros2_rover_nav2_bringup

source install/setup.bash
```

## Run

Before starting this package, make sure the required rover nodes are already running:

```text
robot_state_publisher
map -> odom localization node
odometry / EKF node
360° LiDAR driver
AS-DT1 elevation mapping node
motor command interface
```

Then launch Nav2:

```bash
ros2 launch ros2_rover_nav2_bringup nav2_bringup.launch.py
```

## Testing before launch

Check filtered odometry:

```bash
ros2 topic echo /odometry/filtered --once
```

Check the TF chain:

```bash
ros2 run tf2_ros tf2_echo map odom
```

```bash
ros2 run tf2_ros tf2_echo odom base_link
```

Check the 360° LiDAR scan:

```bash
ros2 topic info /scan
ros2 topic hz /scan
```

Expected type:

```text
sensor_msgs/msg/LaserScan
```

Check the LiDAR frame:

```bash
ros2 topic echo /scan --once | grep frame_id
```

Then verify the TF from the rover base to the LiDAR:

```bash
ros2 run tf2_ros tf2_echo base_link lidar_360_link
```

Replace `lidar_360_link` with the real frame name if needed.

Check the AS-DT1 traversability grid:

```bash
ros2 topic info /traversability_grid
ros2 topic echo /traversability_grid --once
```

Expected type:

```text
nav_msgs/msg/OccupancyGrid
```

## Testing after launch

After launching Nav2, check the lifecycle nodes:

```bash
ros2 lifecycle nodes
```

Check the costmap topics:

```bash
ros2 topic list | grep costmap
```

Expected topics include:

```text
/local_costmap/costmap
/global_costmap/costmap
```

Check the velocity command topic:

```bash
ros2 topic list | grep cmd_vel
```

Expected topic:

```text
/cmd_vel
```

Check whether Nav2 publishes commands after sending a goal:

```bash
ros2 topic echo /cmd_vel
```

## RViz

Start RViz:

```bash
rviz2
```

Recommended fixed frame:

```text
map
```

Useful displays:

```text
TF
RobotModel
LaserScan: /scan
Map: /traversability_grid
Map: /local_costmap/costmap
Map: /global_costmap/costmap
Path
Pose
```

You can send a navigation goal using the `2D Goal Pose` tool.

## Safety note

For the first tests, keep the rover lifted, disable motor power, or limit the motor controller output.

Nav2 can publish velocity commands on `/cmd_vel` as soon as a goal is sent.

Recommended first test configuration:

```text
low max_vel_x
low max_vel_theta
short test distance
emergency stop available
```

## Current limitations

This package only starts and configures Nav2.

It depends on external packages for:

* robot description
* TF publication
* filtered odometry
* `map -> odom` transform
* 360° LiDAR driver
* AS-DT1 elevation mapping
* traversability grid generation
* low-level motor control

The traversability grid integration may need tuning depending on how the grid is published.

If `/traversability_grid` is a local grid that moves with the rover, a custom Nav2 costmap layer may be a better long-term solution than a static-style layer.

## Future improvements

Possible future improvements include:

* custom Nav2 traversability costmap layer
* GPS waypoint navigation
* better tracked rover controller tuning
* improved recovery behavior tuning for outdoor terrain
* dedicated launch file for the complete rover stack
* RViz configuration file
* simulation launch file
* launch arguments for LiDAR and traversability topics
* parameter profiles for indoor and outdoor testing

## License

This project is licensed under the MIT License.
