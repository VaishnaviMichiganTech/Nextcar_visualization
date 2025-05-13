#!/usr/bin/env python2
# -*- coding: utf-8 -*-
from __future__ import print_function

def run_command(command, shell=False):
    """Run a command and return the process object"""
    if shell:
        return subprocess.Popen(command, shell=True, preexec_fn=os.setsid)
    else:
        return subprocess.Popen(command.split(), preexec_fn=os.setsid)

def cleanup_processes(process_list):
    """Cleanup all running processes"""
    for process in process_list:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except:
            pass

import rospy
import subprocess
import sys
import os
import signal
import time
from visualization_msgs.msg import MarkerArray, Marker
from geometry_msgs.msg import TwistStamped
import rosbag
import tf2_ros
import geometry_msgs.msg

# Import apsrc_msgs - Fixed import for all needed message types
from apsrc_msgs.msg import VehicleIntelInfo
# Note: You may need to individually import sub-messages if they're not nested
# Uncomment these if needed:
# from apsrc_msgs.msg import ecoMode, ecoCruise, ecoDrive


try:
    from jsk_rviz_plugins.msg import OverlayText
    jsk_available = True
except ImportError:
    jsk_available = False
    print("WARNING: jsk_rviz_plugins not available. UI overlays will not display properly.")
    print("To install: sudo apt-get install ros-<distro>-jsk-rviz-plugins")

class CleanedLidarVisualizer:
    def __init__(self):
        rospy.init_node('cleaned_lidar_visualizer', anonymous=True)
        
        # Publishers for standard visualization
        self.marker_pub = rospy.Publisher('/filtered_lidar_detections', MarkerArray, queue_size=10)
        self.ego_vehicle_pub = rospy.Publisher('/ego_vehicle', Marker, queue_size=10)
        self.speed_text_pub = rospy.Publisher('/speed_display', Marker, queue_size=10)
        
        # Publishers for UI overlays
        if jsk_available:
            self.energy_overlay_pub = rospy.Publisher('/energy_savings_overlay', OverlayText, queue_size=10)
            self.mode_overlay_pub = rospy.Publisher('/current_mode_overlay', OverlayText, queue_size=10)
            self.center_overlay_pub = rospy.Publisher('/center_info_overlay', OverlayText, queue_size=10)
        
        # TF2 broadcaster
        self.tf_broadcaster = tf2_ros.StaticTransformBroadcaster()
        
        # Parameters
        self.current_speed = 0.0
        
        # VehicleIntelInfo data storage
        self.vehicle_intel_data = {
            'ecoMode': {
                'enabled': False,
                'mode_in_use': 'UNAVAILABLE',
                'saving': 0.0
            },
            'ecoCruise': {
                'status': 'UNAVAILABLE',
                'saving': 0.0
            },
            'ecoDrive': {
                'status': 'UNAVAILABLE',
                'saving_per_signal': 0.0,
                'time_offset': 0.0
            }
        }
        
        # Status mappings for readable display
        self.status_mappings = {
            'ecoMode': {
                0: 'PRODUCTION',
                1: 'HYBRID',
                2: 'EV',
                255: 'UNAVAILABLE'
            },
            'ecoCruise': {
                0: 'OFF',
                1: 'INACTIVE',
                2: 'ACTIVE',
                255: 'UNAVAILABLE'
            },
            'ecoDrive': {
                0: 'OFF',
                1: 'INACTIVE',
                2: 'CRUISING',
                3: 'OPTIMIZING',
                4: 'STOPPING',
                5: 'DEPARTING',
                255: 'UNAVAILABLE'
            }
        }
        
        # Start publishing timers
        self.publish_ego_vehicle_timer = rospy.Timer(rospy.Duration(0.1), self.publish_ego_vehicle)
        self.publish_speed_timer = rospy.Timer(rospy.Duration(0.1), self.publish_speed_display)
        
        # Start overlay publishing timers
        if jsk_available:
            self.publish_energy_overlay_timer = rospy.Timer(rospy.Duration(0.1), self.publish_energy_overlay)
            self.publish_mode_overlay_timer = rospy.Timer(rospy.Duration(0.1), self.publish_mode_overlay)
            self.publish_center_overlay_timer = rospy.Timer(rospy.Duration(0.1), self.publish_center_overlay)

    def vehicle_intel_callback(self, msg):
        """Callback for VehicleIntelInfo topic"""
        # Extract ecoMode information
        if hasattr(msg, 'ecoMode'):
            self.vehicle_intel_data['ecoMode']['enabled'] = msg.ecoMode.ecoMode_enabled
            self.vehicle_intel_data['ecoMode']['saving'] = msg.ecoMode.ecoMode_saving
            
            # Map mode_in_use values to readable strings
            self.vehicle_intel_data['ecoMode']['mode_in_use'] = self.status_mappings['ecoMode'].get(
                msg.ecoMode.mode_in_use, 'UNKNOWN'
            )
        
        # Extract ecoCruise information
        if hasattr(msg, 'ecoCruise'):
            # Map ecoCruise status values to readable strings
            self.vehicle_intel_data['ecoCruise']['status'] = self.status_mappings['ecoCruise'].get(
                msg.ecoCruise.ecoCruise_status, 'UNKNOWN'
            )
            self.vehicle_intel_data['ecoCruise']['saving'] = msg.ecoCruise.ecoCruise_saving
        
        # Extract ecoDrive information
        if hasattr(msg, 'ecoDrive'):
            # Map ecoDrive status values to readable strings
            self.vehicle_intel_data['ecoDrive']['status'] = self.status_mappings['ecoDrive'].get(
                msg.ecoDrive.ecoDrive_status, 'UNKNOWN'
            )
            self.vehicle_intel_data['ecoDrive']['saving_per_signal'] = msg.ecoDrive.saving_per_signal_percentage
            self.vehicle_intel_data['ecoDrive']['time_offset'] = msg.ecoDrive.time_offset_per_signal

    def speed_callback(self, msg):
        """Callback for ego vehicle speed"""
        self.current_speed = msg.twist.linear.x * 3.6  # Convert m/s to km/h

    def create_ego_vehicle_marker(self):
        """Create a marker representing the ego vehicle"""
        marker = Marker()
        marker.header.frame_id = "map"
        marker.header.stamp = rospy.Time.now()
        marker.ns = "ego_vehicle"
        marker.id = 0
        marker.type = Marker.CUBE
        marker.action = Marker.ADD
        
        marker.pose.position.x = 0
        marker.pose.position.y = 0
        marker.pose.position.z = 0
        marker.pose.orientation.w = 1.0
        
        marker.scale.x = 4.5  # length
        marker.scale.y = 2.0  # width
        marker.scale.z = 1.5  # height
        
        marker.color.r = 0.0
        marker.color.g = 0.0
        marker.color.b = 1.0
        marker.color.a = 0.8
        
        return marker

    def create_speed_display(self):
        """Create text marker for speed display"""
        marker = Marker()
        marker.header.frame_id = "map"
        marker.header.stamp = rospy.Time.now()
        marker.ns = "speed"
        marker.id = 2
        marker.type = Marker.TEXT_VIEW_FACING
        marker.action = Marker.ADD
        
        marker.pose.position.x = 0
        marker.pose.position.y = 3
        marker.pose.position.z = 2
        
        marker.text = "Speed: {:.1f} km/h".format(self.current_speed)
        
        marker.scale.z = 1.0  # text size
        marker.color.r = 1.0
        marker.color.g = 1.0
        marker.color.b = 1.0
        marker.color.a = 1.0
        
        return marker

    def create_energy_overlay(self):
        """Create overlay text for energy savings using ecoMode saving"""
        if not jsk_available:
            return None
            
        msg = OverlayText()
        msg.width = 200
        msg.height = 80
        msg.left = 10
        msg.top = 10
        msg.text_size = 12
        msg.line_width = 2
        msg.font = "DejaVu Sans Mono"
        
        # Display ecoMode saving information
        energy_text = "ENERGY SAVINGS\n"
        if self.vehicle_intel_data['ecoMode']['enabled']:
            energy_text += "    {:.1f}%".format(self.vehicle_intel_data['ecoMode']['saving'])
        else:
            energy_text += "   DISABLED"
        
        msg.text = energy_text
        msg.bg_color.r = 0.1
        msg.bg_color.g = 0.3
        msg.bg_color.b = 0.1
        msg.bg_color.a = 0.7
        msg.fg_color.r = 0.2
        msg.fg_color.g = 0.8
        msg.fg_color.b = 0.2
        msg.fg_color.a = 1.0
        return msg

    def create_mode_overlay(self):
        """Create overlay text for current mode using ecoMode information"""
        if not jsk_available:
            return None
            
        msg = OverlayText()
        msg.width = 200
        msg.height = 100
        msg.left = 10
        msg.top = 100  # Position below energy savings
        msg.text_size = 12
        msg.line_width = 2
        msg.font = "DejaVu Sans Mono"
        
        # Display ecoMode information
        mode_text = "ECO MODE\n"
        if self.vehicle_intel_data['ecoMode']['enabled']:
            mode_text += " Status: ON\n"
            mode_text += " Mode: {}".format(self.vehicle_intel_data['ecoMode']['mode_in_use'])
        else:
            mode_text += " Status: OFF"
        
        msg.text = mode_text
        msg.bg_color.r = 0.1
        msg.bg_color.g = 0.1
        msg.bg_color.b = 0.3
        msg.bg_color.a = 0.7
        msg.fg_color.r = 0.2
        msg.fg_color.g = 0.2
        msg.fg_color.b = 0.8
        msg.fg_color.a = 1.0
        return msg

    def create_center_overlay(self):
        """Create overlay text for ecoCruise and ecoDrive information"""
        if not jsk_available:
            return None
            
        msg = OverlayText()
        msg.width = 250
        msg.height = 120
        msg.left = 250  # Center position
        msg.top = 10    # Same top position as energy savings
        msg.text_size = 11
        msg.line_width = 2
        msg.font = "DejaVu Sans Mono"
        
        # Display ecoCruise and ecoDrive information
        center_text = "ECO SYSTEMS\n"
        center_text += "Cruise: {}\n".format(self.vehicle_intel_data['ecoCruise']['status'])
        if self.vehicle_intel_data['ecoCruise']['status'] == 'ACTIVE':
            center_text += "  Saving: {:.1f}%\n".format(self.vehicle_intel_data['ecoCruise']['saving'])
        
        center_text += "Drive: {}\n".format(self.vehicle_intel_data['ecoDrive']['status'])
        if self.vehicle_intel_data['ecoDrive']['status'] not in ['OFF', 'UNAVAILABLE']:
            center_text += "  Signal: {:.1f}%".format(self.vehicle_intel_data['ecoDrive']['saving_per_signal'])
        
        msg.text = center_text
        msg.bg_color.r = 0.3
        msg.bg_color.g = 0.1
        msg.bg_color.b = 0.1
        msg.bg_color.a = 0.7
        msg.fg_color.r = 0.8
        msg.fg_color.g = 0.4
        msg.fg_color.b = 0.0
        msg.fg_color.a = 1.0
        return msg

    def filter_and_publish_markers(self, markers):
        """Process markers and publish them (simplified - no ROI filtering)"""
        # Simply publish markers as they are, without ROI filtering
        self.marker_pub.publish(markers)

    def publish_ego_vehicle(self, event=None):
        """Publish ego vehicle marker"""
        self.ego_vehicle_pub.publish(self.create_ego_vehicle_marker())

    def publish_speed_display(self, event=None):
        """Publish speed display"""
        self.speed_text_pub.publish(self.create_speed_display())
        
    def publish_energy_overlay(self, event=None):
        """Publish energy savings overlay"""
        if jsk_available:
            overlay = self.create_energy_overlay()
            if overlay:
                self.energy_overlay_pub.publish(overlay)
        
    def publish_mode_overlay(self, event=None):
        """Publish current mode overlay"""
        if jsk_available:
            overlay = self.create_mode_overlay()
            if overlay:
                self.mode_overlay_pub.publish(overlay)
                
    def publish_center_overlay(self, event=None):
        """Publish center info overlay"""
        if jsk_available:
            overlay = self.create_center_overlay()
            if overlay:
                self.center_overlay_pub.publish(overlay)

    def setup_transforms(self):
        """Setup static transforms"""
        transforms = []
        
        t1 = geometry_msgs.msg.TransformStamped()
        t1.header.stamp = rospy.Time.now()
        t1.header.frame_id = "map"
        t1.child_frame_id = "detection"
        t1.transform.translation.x = 0
        t1.transform.translation.y = 0
        t1.transform.translation.z = 0
        t1.transform.rotation.w = 1
        transforms.append(t1)
        
        t2 = geometry_msgs.msg.TransformStamped()
        t2.header.stamp = rospy.Time.now()
        t2.header.frame_id = "detection"
        t2.child_frame_id = "lidar"
        t2.transform.translation.x = 0
        t2.transform.translation.y = 0
        t2.transform.translation.z = 0
        t2.transform.rotation.w = 1
        transforms.append(t2)
        
        self.tf_broadcaster.sendTransform(transforms)

def create_enhanced_rviz_config():
    """Create an enhanced RViz configuration with overlay support."""
    config = """
Panels:
  - Class: rviz/Displays
    Help Height: 78
    Name: Displays
    Property Tree Widget:
      Expanded:
        - /Global Options1
        - /Status1
        - /Grid1
        - /MarkerArray1
        - /Marker1
        - /Speed1
        - /Camera Image1
        - /Energy Overlay1
        - /Mode Overlay1
        - /Center Info1
      Splitter Ratio: 0.5
    Tree Height: 775
Visualization Manager:
  Class: ""
  Displays:
    - Alpha: 0.5
      Cell Size: 10
      Class: rviz/Grid
      Color: 160; 160; 164
      Enabled: true
      Line Style:
        Line Width: 0.03
        Value: Lines
      Name: Grid
      Normal Cell Count: 0
      Offset:
        X: 0
        Y: 0
        Z: 0
      Plane: XY
      Plane Cell Count: 100
      Reference Frame: map
      Value: true
    - Class: rviz/MarkerArray
      Enabled: true
      Marker Topic: /filtered_lidar_detections
      Name: MarkerArray
      Namespaces:
        {}
      Queue Size: 100
      Value: true
    - Class: rviz/Marker
      Enabled: true
      Marker Topic: /ego_vehicle
      Name: Marker
      Namespaces:
        {}
      Queue Size: 100
      Value: true
    - Class: rviz/Marker
      Enabled: true
      Marker Topic: /speed_display
      Name: Speed
      Namespaces:
        {}
      Queue Size: 100
      Value: true
    - Class: rviz/Image
      Enabled: true
      Image Topic: /camera_fl/image_raw
      Name: Camera Image
      Transport Hint: theora
      Queue Size: 5
      Unreliable: false
    - Class: jsk_rviz_plugin/OverlayText
      Enabled: true
      Name: Energy Overlay
      Topic: /energy_savings_overlay
      Value: true
      alpha: 0.8
      bg_color: 0; 0; 0
      text_size: 12
      top: 10
      left: 10
      width: 200
      height: 80
      font: DejaVu Sans Mono
      text_color: 51; 204; 51
    - Class: jsk_rviz_plugin/OverlayText
      Enabled: true
      Name: Mode Overlay
      Topic: /current_mode_overlay
      Value: true
      alpha: 0.8
      bg_color: 0; 0; 0
      text_size: 12
      top: 100
      left: 10
      width: 200
      height: 100
      font: DejaVu Sans Mono
      text_color: 51; 51; 204
    - Class: jsk_rviz_plugin/OverlayText
      Enabled: true
      Name: Center Info
      Topic: /center_info_overlay
      Value: true
      alpha: 0.8
      bg_color: 0; 0; 0
      text_size: 11
      top: 10
      left: 250
      width: 250
      height: 120
      font: DejaVu Sans Mono
      text_color: 204; 102; 0
  Enabled: true
  Global Options:
    Background Color: 48; 48; 48
    Fixed Frame: map
    Frame Rate: 30
  Name: root
  Tools:
    - Class: rviz/Interact
      Hide Inactive Objects: true
    - Class: rviz/MoveCamera
    - Class: rviz/Select
    - Class: rviz/FocusCamera
    - Class: rviz/Measure
    - Class: rviz/SetInitialPose
      Topic: /initialpose
    - Class: rviz/SetGoal
      Topic: /move_base_simple/goal
    - Class: rviz/PublishPoint
      Single click: true
      Topic: /clicked_point
  Value: true
  Views:
    Current:
      Class: rviz/Orbit
      Distance: 100
      Enable Stereo Rendering:
        Stereo Eye Separation: 0.06
        Stereo Focal Distance: 1
        Swap Stereo Eyes: false
        Value: false
      Focal Point:
        X: 0
        Y: 0
        Z: 0
      Name: Current View
      Near Clip Distance: 0.01
      Pitch: 0.785398
      Target Frame: map
      Value: Orbit (rviz)
      Yaw: 0.785398
    Saved: ~
"""
    config_path = "/tmp/cleaned_lidar_viz.rviz"
    with open(config_path, 'w') as f:
        f.write(config)
    return config_path


def main():
    if len(sys.argv) != 2:
        print("Usage: {} <path_to_bagfile>".format(sys.argv[0]))
        sys.exit(1)
        
    bag_path = os.path.abspath(os.path.expanduser(sys.argv[1]))
    
    if not os.path.exists(bag_path):
        print("Error: Bag file not found: {}".format(bag_path))
        sys.exit(1)

    processes = []
    try:
        # Start roscore
        print("Starting roscore...")
        roscore = run_command('roscore')
        processes.append(roscore)
        time.sleep(2)

        # Initialize the visualizer node
        visualizer = CleanedLidarVisualizer()
        visualizer.setup_transforms()

        # Create RViz config and start RViz
        rviz_config = create_enhanced_rviz_config()
        print("Starting rviz...")
        rviz = run_command('rviz -d {} _image_transport:=theora'.format(rviz_config))
        processes.append(rviz)
        time.sleep(1)
        
        # Print info about jsk installation if needed
        if not jsk_available:
            print("\n" + "="*80)
            print("NOTE: To see fixed UI boxes at the top of the screen, install jsk_rviz_plugins:")
            print("  sudo apt-get install ros-$(rosversion -d)-jsk-rviz-plugins")
            print("="*80 + "\n")

        # Subscribe to topics
        rospy.Subscriber('/detection/lidar_detector/objects_markers', 
                        MarkerArray, visualizer.filter_and_publish_markers)
        rospy.Subscriber('/current_velocity',
                        TwistStamped, visualizer.speed_callback)
        
        # Subscribe to VehicleIntelInfo topic (note the typo in the topic name)
        rospy.Subscriber('/vehicel_intel',
                        VehicleIntelInfo, visualizer.vehicle_intel_callback)

        # Play the rosbag
        print("Playing rosbag: {}".format(bag_path))
        # Play the rosbag at 0.7x speed
        rosbag_process = run_command('rosbag play -r 0.7 {}'.format(bag_path), shell=True)
        processes.append(rosbag_process)

        # Keep the script running
        rospy.spin()

    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print("Error: {}".format(e))
    finally:
        cleanup_processes(processes)
        print("All processes terminated")

if __name__ == '__main__':
    main()
