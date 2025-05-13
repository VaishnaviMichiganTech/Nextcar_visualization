# VehicleIntelInfo Visualization - README

## Overview
This visualization system subscribes to VehicleIntelInfo topic and displays eco-driving system data in RViz overlays. It includes a dummy data publisher for testing.

## System Architecture

```
Dummy Publisher → /vehicel_intel → Visualization Node → RViz Overlays
[Publishes data]              [Processes data]     [Displays data]
```

## Workspace Structure

```
nextcar_workspace/
├── build/                    # Compiled binaries (auto-generated)
├── devel/                    # Development workspace (auto-generated)
├── config/                   # Configuration files
├── README.md                 # Project documentation
└── src/                      # Source code
    ├── CMakeLists.txt       # Top-level CMake file
    ├── apsrc_msgs/          # Custom message definitions
    │   ├── CMakeLists.txt
    │   ├── package.xml
    │   └── msg/             # Message definition files
    │       ├── nextcar_technologies/
    │       │   ├── VehicleIntelInfo.msg
    │       │   ├── ecoMode.msg
    │       │   ├── ecoCruise.msg
    │       │   ├── ecoDrive.msg
    │       │   └── ...
    │       └── ...
    └── visualization/       # Visualization scripts
        ├── visualization_test.py
        └── dummy_vehicle_intel_publisher.py
```

## Running the System

### Prerequisites
1. **Install ROS Melodic** (or your distro)
2. **Install jsk_rviz_plugins** (for overlays):
   ```bash
   sudo apt-get install ros-melodic-jsk-rviz-plugins
   ```
3. **Build the workspace**:
   ```bash
   cd ~/nextcar_workspace
   catkin_make
   ```

### Execution Steps

**Terminal 1 - ROS Core:**
```bash
cd ~/nextcar_workspace
source /opt/ros/melodic/setup.bash  # Source ROS
source devel/setup.bash             # Source workspace
roscore
```

**Terminal 2 - Dummy Publisher:**
```bash
cd ~/nextcar_workspace
source /opt/ros/melodic/setup.bash
source devel/setup.bash
cd src/visualization/               # Navigate to scripts folder
python dummy_vehicle_intel_publisher.py
```

**Terminal 3 - Main Visualization:**
```bash
cd ~/nextcar_workspace
source /opt/ros/melodic/setup.bash
source devel/setup.bash
cd src/visualization/
python visualization_test.py ~/Desktop/Greenlight_workspae/playmouthRD-20250211T175532Z-002/playmouthRD/2023-11-01-15-30-48.bag
```

### What You Should See

1. **Terminal 1**: ROS core starts successfully
2. **Terminal 2**: Dummy publisher outputs:
   ```
   Dummy VehicleIntelInfo publisher started
   Publishing to topic: /vehicel_intel
   Published dummy data - Time: 5s
     EcoMode: HYBRID (22.3%)
     EcoCruise: ACTIVE
     EcoDrive: CRUISING
   ```
3. **Terminal 3**: RViz opens with three overlay boxes showing eco system data
4. **RViz Window**: Shows blue ego vehicle, speed display, and three overlay texts in the top area

## Topic Subscription & Processing

### 1. Topic Subscription
```python
# Topic name (note the typo - this is intentional)
rospy.Subscriber('/vehicel_intel', VehicleIntelInfo, visualizer.vehicle_intel_callback)
```
- **Topic**: `/vehicel_intel` 
- **Message Type**: `VehicleIntelInfo` (from apsrc_msgs)
- **Callback**: `vehicle_intel_callback()` function

### 2. Message Processing
When a message arrives, the callback function extracts data:

```python
def vehicle_intel_callback(self, msg):
    # Extract ecoMode data
    if hasattr(msg, 'ecoMode'):
        self.vehicle_intel_data['ecoMode']['enabled'] = msg.ecoMode.ecoMode_enabled
        self.vehicle_intel_data['ecoMode']['saving'] = msg.ecoMode.ecoMode_saving
        # Map numeric codes to readable strings
        mode_map = {0: 'PRODUCTION', 1: 'HYBRID', 2: 'EV', 255: 'UNAVAILABLE'}
        self.vehicle_intel_data['ecoMode']['mode_in_use'] = mode_map.get(msg.ecoMode.mode_in_use)
    
    # Extract ecoCruise data
    if hasattr(msg, 'ecoCruise'):
        cruise_status_map = {0: 'OFF', 1: 'INACTIVE', 2: 'ACTIVE', 255: 'UNAVAILABLE'}
        self.vehicle_intel_data['ecoCruise']['status'] = cruise_status_map.get(msg.ecoCruise.ecoCruise_status)
        self.vehicle_intel_data['ecoCruise']['saving'] = msg.ecoCruise.ecoCruise_saving
    
    # Extract ecoDrive data
    if hasattr(msg, 'ecoDrive'):
        drive_status_map = {0: 'OFF', 1: 'INACTIVE', 2: 'CRUISING', 3: 'OPTIMIZING', 4: 'STOPPING', 5: 'DEPARTING', 255: 'UNAVAILABLE'}
        self.vehicle_intel_data['ecoDrive']['status'] = drive_status_map.get(msg.ecoDrive.ecoDrive_status)
        self.vehicle_intel_data['ecoDrive']['saving_per_signal'] = msg.ecoDrive.saving_per_signal_percentage
        self.vehicle_intel_data['ecoDrive']['time_offset'] = msg.ecoDrive.time_offset_per_signal
```

### 3. Data Storage
Extracted data is stored in a class variable for easy access:

```python
self.vehicle_intel_data = {
    'ecoMode': {'enabled': False, 'mode_in_use': 'UNAVAILABLE', 'saving': 0.0},
    'ecoCruise': {'status': 'UNAVAILABLE', 'saving': 0.0},
    'ecoDrive': {'status': 'UNAVAILABLE', 'saving_per_signal': 0.0, 'time_offset': 0.0}
}
```

### 4. Overlay Display
Timer-based functions create and publish overlay texts:

```python
# Timer publishes overlays at 10Hz
self.publish_energy_overlay_timer = rospy.Timer(rospy.Duration(0.1), self.publish_energy_overlay)

def publish_energy_overlay(self, event=None):
    overlay = self.create_energy_overlay()  # Create overlay message
    if overlay:
        self.energy_overlay_pub.publish(overlay)  # Publish to RViz
```

## Dummy Publisher Operation

### Purpose
The dummy publisher generates fake VehicleIntelInfo messages for testing when real data isn't available.

### How It Works

1. **Initialization**
```python
# Publishes to the same topic the visualizer subscribes to
self.publisher = rospy.Publisher('/vehicel_intel', VehicleIntelInfo, queue_size=10)
```

2. **Data Generation**
```python
def publish_dummy_data(self, event):
    msg = VehicleIntelInfo()
    
    # Create ecoMode data
    msg.ecoMode = ecoMode()
    msg.ecoMode.ecoMode_enabled = True
    # Cycle through modes every 10 seconds
    mode_states = [1, 2, 0]  # HYBRID, EV, PRODUCTION
    msg.ecoMode.mode_in_use = mode_states[(self.time_counter // 10) % len(mode_states)]
    # Vary energy savings using sine wave
    msg.ecoMode.ecoMode_saving = 15.0 + 20.0 * (0.5 + 0.5 * math.sin(self.time_counter * 0.1))
    
    # Create ecoCruise data
    msg.ecoCruise = ecoCruise()
    cruise_states = [0, 1, 2]  # Cycle every 5 seconds
    msg.ecoCruise.ecoCruise_status = cruise_states[(self.time_counter // 5) % len(cruise_states)]
    
    # Create ecoDrive data
    msg.ecoDrive = ecoDrive()
    drive_states = [0, 1, 2, 3, 4, 5]  # Cycle every 3 seconds
    msg.ecoDrive.ecoDrive_status = drive_states[(self.time_counter // 3) % len(drive_states)]
    
    # Publish the complete message
    self.publisher.publish(msg)
```

3. **Dynamic Behavior to show the changing overlay capabilities**
- **ecoMode**: Cycles through HYBRID→EV→PRODUCTION every 10s
- **Energy Savings**: Varies 15-35% using sine wave
- **ecoCruise**: Changes OFF→INACTIVE→ACTIVE every 5s
- **ecoDrive**: Cycles through all states every 3s
- **Values**: Random values for savings, times, etc.

## Message Flow

```
Dummy Publisher (1Hz)
    ↓
Creates VehicleIntelInfo message
    ↓
Publishes to /vehicel_intel
    ↓
Visualization node receives message
    ↓
Processes and stores data
    ↓
Overlay timers (10Hz) create JSK overlay messages
    ↓
RViz displays overlays with eco system data
```



### Verification Commands
```bash
# Check if messages are being published
rostopic echo /vehicel_intel

# List all active topics
rostopic list

# Check message structure
rosmsg show apsrc_msgs/VehicleIntelInfo
```

## Notes
- The topic name contains a  typo (`/vehicel_intel`) to match the original implementation
- Rosbag errors about `detected_objects_visualizer` are due to mismatch in topic name

### 1. Topic Subscription
```python
# Topic name (note the typo - this is intentional)
rospy.Subscriber('/vehicel_intel', VehicleIntelInfo, visualizer.vehicle_intel_callback)
```
- **Topic**: `/vehicel_intel` (not `/vehicle_intel` - typo in original code)
- **Message Type**: `VehicleIntelInfo` (from apsrc_msgs)
- **Callback**: `vehicle_intel_callback()` function

### 2. Message Processing
When a message arrives, the callback function extracts data:

```python
def vehicle_intel_callback(self, msg):
    # Extract ecoMode data
    if hasattr(msg, 'ecoMode'):
        self.vehicle_intel_data['ecoMode']['enabled'] = msg.ecoMode.ecoMode_enabled
        self.vehicle_intel_data['ecoMode']['saving'] = msg.ecoMode.ecoMode_saving
        # Map numeric codes to readable strings
        mode_map = {0: 'PRODUCTION', 1: 'HYBRID', 2: 'EV', 255: 'UNAVAILABLE'}
        self.vehicle_intel_data['ecoMode']['mode_in_use'] = mode_map.get(msg.ecoMode.mode_in_use)
    
    # Extract ecoCruise data
    if hasattr(msg, 'ecoCruise'):
        cruise_status_map = {0: 'OFF', 1: 'INACTIVE', 2: 'ACTIVE', 255: 'UNAVAILABLE'}
        self.vehicle_intel_data['ecoCruise']['status'] = cruise_status_map.get(msg.ecoCruise.ecoCruise_status)
        self.vehicle_intel_data['ecoCruise']['saving'] = msg.ecoCruise.ecoCruise_saving
    
    # Extract ecoDrive data
    if hasattr(msg, 'ecoDrive'):
        drive_status_map = {0: 'OFF', 1: 'INACTIVE', 2: 'CRUISING', 3: 'OPTIMIZING', 4: 'STOPPING', 5: 'DEPARTING', 255: 'UNAVAILABLE'}
        self.vehicle_intel_data['ecoDrive']['status'] = drive_status_map.get(msg.ecoDrive.ecoDrive_status)
        self.vehicle_intel_data['ecoDrive']['saving_per_signal'] = msg.ecoDrive.saving_per_signal_percentage
        self.vehicle_intel_data['ecoDrive']['time_offset'] = msg.ecoDrive.time_offset_per_signal
```

### 3. Data Storage
Extracted data is stored in a class variable for easy access:

```python
self.vehicle_intel_data = {
    'ecoMode': {'enabled': False, 'mode_in_use': 'UNAVAILABLE', 'saving': 0.0},
    'ecoCruise': {'status': 'UNAVAILABLE', 'saving': 0.0},
    'ecoDrive': {'status': 'UNAVAILABLE', 'saving_per_signal': 0.0, 'time_offset': 0.0}
}
```

### 4. Overlay Display
Timer-based functions create and publish overlay texts:

```python
# Timer publishes overlays at 10Hz
self.publish_energy_overlay_timer = rospy.Timer(rospy.Duration(0.1), self.publish_energy_overlay)

def publish_energy_overlay(self, event=None):
    overlay = self.create_energy_overlay()  # Create overlay message
    if overlay:
        self.energy_overlay_pub.publish(overlay)  # Publish to RViz
```

## Dummy Publisher Operation

### Purpose
The dummy publisher generates fake VehicleIntelInfo messages for testing when real data isn't available.

### How It Works

1. **Initialization**
```python
# Publishes to the same topic the visualizer subscribes to
self.publisher = rospy.Publisher('/vehicel_intel', VehicleIntelInfo, queue_size=10)
```

2. **Data Generation**
```python
def publish_dummy_data(self, event):
    msg = VehicleIntelInfo()
    
    # Create ecoMode data
    msg.ecoMode = ecoMode()
    msg.ecoMode.ecoMode_enabled = True
    # Cycle through modes every 10 seconds
    mode_states = [1, 2, 0]  # HYBRID, EV, PRODUCTION
    msg.ecoMode.mode_in_use = mode_states[(self.time_counter // 10) % len(mode_states)]
    # Vary energy savings using sine wave
    msg.ecoMode.ecoMode_saving = 15.0 + 20.0 * (0.5 + 0.5 * math.sin(self.time_counter * 0.1))
    
    # Create ecoCruise data
    msg.ecoCruise = ecoCruise()
    cruise_states = [0, 1, 2]  # Cycle every 5 seconds
    msg.ecoCruise.ecoCruise_status = cruise_states[(self.time_counter // 5) % len(cruise_states)]
    
    # Create ecoDrive data
    msg.ecoDrive = ecoDrive()
    drive_states = [0, 1, 2, 3, 4, 5]  # Cycle every 3 seconds
    msg.ecoDrive.ecoDrive_status = drive_states[(self.time_counter // 3) % len(drive_states)]
    
    # Publish the complete message
    self.publisher.publish(msg)
```

3. **Dynamic Behavior**
- **ecoMode**: Cycles through HYBRID→EV→PRODUCTION every 10s
- **Energy Savings**: Varies 15-35% using sine wave
- **ecoCruise**: Changes OFF→INACTIVE→ACTIVE every 5s
- **ecoDrive**: Cycles through all states every 3s
- **Values**: Random values for savings, times, etc.

## Message Flow

```
Dummy Publisher (1Hz)
    ↓
Creates VehicleIntelInfo message
    ↓
Publishes to /vehicel_intel
    ↓
Visualization node receives message
    ↓
Processes and stores data
    ↓
Overlay timers (10Hz) create JSK overlay messages
    ↓
RViz displays overlays with eco system data
```

## Key Features

### Robust Message Handling
- Uses `hasattr()` to check if sub-messages exist
- Won't crash if message structure changes
- Graceful handling of missing data

### Data Mapping
- Converts numeric status codes to readable strings
- Centralized mapping dictionaries for easy modification

### Modular Design
- Separate functions for each eco system
- Easy to add new overlays or modify existing ones
- Clean separation of concerns

## Running the System

1. **Terminal 1**: Start ROS core
2. **Terminal 2**: Run dummy publisher (simulates real data)
3. **Terminal 3**: Run visualization with rosbag
4. **Result**: RViz shows three overlay boxes with dynamic eco system data

## Troubleshooting

- **No overlays visible**: Check if jsk_rviz_plugins is installed
- **Empty overlays**: Verify dummy publisher is running and publishing
- **Import errors**: Ensure workspace is built with `catkin_make`
- **Topic name mismatch**: Verify using the typo `/vehicel_intel`
