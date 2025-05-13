#!/usr/bin/env python2
# -*- coding: utf-8 -*-
from __future__ import print_function

import rospy
import time
import random
import math

# Import the VehicleIntelInfo message and all sub-messages
# Using absolute import path for your workspace structure
from apsrc_msgs.msg import (
    VehicleIntelInfo,
    ecoMode,
    ecoRoute,
    ecoDrive,
    ecoCruise,
    MassLearn,
    RoadLoadLearn,
    ReducedOrderModel,
    Range,
)

class DummyVehicleIntelPublisher:
    def __init__(self):
        rospy.init_node('dummy_vehicle_intel_publisher', anonymous=True)
        
        # Publisher for the VehicleIntelInfo topic
        # Note: Using the same typo as in the main code
        self.publisher = rospy.Publisher('/vehicel_intel', VehicleIntelInfo, queue_size=10)
        
        # Variables to simulate changing states
        self.time_counter = 0
        self.eco_mode_cycle = 0
        self.eco_drive_cycle = 0
        self.eco_cruise_cycle = 0
        
        # Timer to publish at 1 Hz (once per second)
        self.timer = rospy.Timer(rospy.Duration(1.0), self.publish_dummy_data)
        
        print("Dummy VehicleIntelInfo publisher started")
        print("Publishing to topic: /vehicel_intel")

    def publish_dummy_data(self, event):
        """Publish dummy VehicleIntelInfo data with realistic values"""
        msg = VehicleIntelInfo()
        
        # Header
        msg.header.stamp = rospy.Time.now()
        msg.header.frame_id = "base_link"
        
        # ==== CREATE ECO MODE DATA ====
        msg.ecoMode = ecoMode()
        msg.ecoMode.ecoMode_enabled = True  # Always enabled for testing
        
        # Cycle through different eco modes every 10 seconds
        mode_states = [1, 2, 0]  # HYBRID, EV, PRODUCTION
        msg.ecoMode.mode_in_use = mode_states[(self.time_counter // 10) % len(mode_states)]
        
        # Simulate energy savings (varying between 15-35%)
        msg.ecoMode.ecoMode_saving = 15.0 + 20.0 * (0.5 + 0.5 * math.sin(self.time_counter * 0.1))
        
        # ==== CREATE ECO ROUTE DATA ====
        msg.ecoRoute = ecoRoute()
        msg.ecoRoute.ecoRoute_enabled = True
        msg.ecoRoute.optimum_route = random.randint(1, 3)
        msg.ecoRoute.default_route_energy = 45.5  # kWh
        msg.ecoRoute.default_route_time = 32.5    # minutes
        msg.ecoRoute.saving_time = random.uniform(2.0, 5.0)  # minutes saved
        msg.ecoRoute.saving_energy = random.uniform(3.0, 8.0)  # kWh saved
        msg.ecoRoute.saving_energy_percent = (msg.ecoRoute.saving_energy / msg.ecoRoute.default_route_energy) * 100
        
        # ==== CREATE ECO CRUISE DATA ====
        msg.ecoCruise = ecoCruise()
        # Cycle through cruise states every 5 seconds
        cruise_states = [0, 1, 2]  # OFF, INACTIVE, ACTIVE
        msg.ecoCruise.ecoCruise_status = cruise_states[(self.time_counter // 5) % len(cruise_states)]
        
        # Only have saving when active
        if msg.ecoCruise.ecoCruise_status == 2:  # ACTIVE
            msg.ecoCruise.ecoCruise_saving = random.uniform(8.0, 15.0)
        else:
            msg.ecoCruise.ecoCruise_saving = 0.0
        
        # ==== CREATE ECO DRIVE DATA ====
        msg.ecoDrive = ecoDrive()
        # Cycle through various drive states every 3 seconds
        drive_states = [0, 1, 2, 3, 4, 5]  # OFF, INACTIVE, CRUISING, OPTIMIZING, STOPPING, DEPARTING
        msg.ecoDrive.ecoDrive_status = drive_states[(self.time_counter // 3) % len(drive_states)]
        
        # Only have savings when not OFF or UNAVAILABLE
        if msg.ecoDrive.ecoDrive_status not in [0, 255]:
            msg.ecoDrive.saving_per_signal_percentage = random.uniform(5.0, 12.0)
            msg.ecoDrive.time_offset_per_signal = random.uniform(-2.0, 3.0)
        else:
            msg.ecoDrive.saving_per_signal_percentage = 0.0
            msg.ecoDrive.time_offset_per_signal = 0.0
        
        # ==== CREATE MASS LEARN DATA ====
        msg.massLearn = MassLearn()
        # Simulate learning progression
        mass_states = [0, 1, 2, 3]  # OFF, ACTIVE, LEARNING, LEARNED
        msg.massLearn.mass_learn_status = mass_states[(self.time_counter // 15) % len(mass_states)]
        
        if msg.massLearn.mass_learn_status in [2, 3]:  # LEARNING or LEARNED
            msg.massLearn.mass = 1850.0 + random.uniform(-50.0, 50.0)  # kg
            msg.massLearn.mass_change_from_base_percentage = random.uniform(-5.0, 10.0)
        else:
            msg.massLearn.mass = 0.0
            msg.massLearn.mass_change_from_base_percentage = 0.0
        
        # ==== CREATE ROAD LOAD LEARN DATA ====
        msg.roadLoadLearn = RoadLoadLearn()
        # Similar progression for road load learning
        msg.roadLoadLearn.road_load_learn_status = mass_states[(self.time_counter // 12) % len(mass_states)]
        
        # Note: The actual field names might be different in your message definition
        # You may need to adjust these based on the actual field names
        if msg.roadLoadLearn.road_load_learn_status in [2, 3]:  # LEARNING or LEARNED
            # Check if the message has the expected fields
            try:
                # Create F0, F1, F2 coefficients (adjust field names as needed)
                msg.roadLoadLearn.F0.coefficient = 120.0 + random.uniform(-10.0, 10.0)
                msg.roadLoadLearn.F0.EPA_offset_percentage = random.uniform(-5.0, 5.0)
                
                msg.roadLoadLearn.F1.coefficient = 1.5 + random.uniform(-0.2, 0.2)
                msg.roadLoadLearn.F1.EPA_offset_percentage = random.uniform(-3.0, 3.0)
                
                msg.roadLoadLearn.F2.coefficient = 0.04 + random.uniform(-0.01, 0.01)
                msg.roadLoadLearn.F2.EPA_offset_percentage = random.uniform(-2.0, 2.0)
            except AttributeError:
                # Fields might have different names, print available fields for debugging
                print("Available RoadLoadLearn fields:", dir(msg.roadLoadLearn))
        
        # ==== CREATE REDUCED ORDER MODEL DATA ====
        msg.reducedOrderModel = ReducedOrderModel()
        # Cycle through model states
        model_states = [0, 1, 2]  # OFF, INACTIVE, ACTIVE
        msg.reducedOrderModel.reduced_order_model_status = model_states[(self.time_counter // 8) % len(model_states)]
        
        if msg.reducedOrderModel.reduced_order_model_status == 2:  # ACTIVE
            msg.reducedOrderModel.reduced_order_model_accuracy = random.uniform(85.0, 98.0)
        else:
            msg.reducedOrderModel.reduced_order_model_accuracy = 0.0
        
        # ==== CREATE RANGE DATA ====
        # Range is imported from the nextcar_technologies folder
        try:
            msg.range = Range()
            msg.range.range_is_available = True
            msg.range.required_energy = random.uniform(15.0, 25.0)  # kWh
            msg.range.range_if_required_energy_is_not_met = random.uniform(80.0, 120.0)  # km
            msg.range.required_energy_is_met = random.choice([True, False])
        except AttributeError:
            # Range fields might have different names
            print("Available Range fields:", dir(msg.range) if hasattr(msg, 'range') else "Range not found")
        
        # Publish the message
        self.publisher.publish(msg)
        
        # Update counters
        self.time_counter += 1
        
        # Print status every 5 seconds
        if self.time_counter % 5 == 0:
            print("Published dummy data - Time: {}s".format(self.time_counter))
            print("  EcoMode: {} ({:.1f}%)".format(
                ['PRODUCTION', 'HYBRID', 'EV'][msg.ecoMode.mode_in_use],
                msg.ecoMode.ecoMode_saving
            ))
            print("  EcoCruise: {}".format(['OFF', 'INACTIVE', 'ACTIVE'][msg.ecoCruise.ecoCruise_status]))
            print("  EcoDrive: {}".format(['OFF', 'INACTIVE', 'CRUISING', 'OPTIMIZING', 'STOPPING', 'DEPARTING'][msg.ecoDrive.ecoDrive_status]))

def main():
    try:
        publisher = DummyVehicleIntelPublisher()
        print("\nDummy publisher running. Press Ctrl+C to stop.")
        print("You can now run your main visualization script in another terminal.")
        print("The main script will receive these dummy VehicleIntelInfo messages.")
        rospy.spin()
    except rospy.ROSInterruptException:
        print("\nDummy publisher stopped.")

if __name__ == '__main__':
    main()
