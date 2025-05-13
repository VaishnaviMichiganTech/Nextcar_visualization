#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import re
import yaml
import json
import argparse

class NextCARMsgConfig:
    def __init__(self, base_dir=None):
        """
        Initialize the NextCAR message configuration reader.
        
        Args:
            base_dir: Base directory where the msg files are located
        """
        self.base_dir = base_dir if base_dir else os.getcwd()
        self.msg_files = {
            'spat_n_map': 'msg/v2x/SPaTnMAP.msg',
            'eco_cruise': 'msg/nextcar_technologies/ecoCruise.msg',
            'eco_drive': 'msg/nextcar_technologies/ecoDrive.msg',
            'eco_mode': 'msg/nextcar_technologies/ecoMode.msg',
            'eco_route': 'msg/nextcar_technologies/ecoRoute.msg',
            'vehicle_intel_info': 'msg/nextcar_technologies/VehicleIntelInfo.msg'
        }
        self.msg_contents = {}
        self.processed_config = {}
        
    def read_all_msg_files(self):
        """Read all the specified .msg files"""
        for key, file_path in self.msg_files.items():
            full_path = os.path.join(self.base_dir, file_path)
            try:
                with open(full_path, 'r') as f:
                    self.msg_contents[key] = f.read()
                print("Successfully read: %s" % file_path)
            except FileNotFoundError:
                print("Warning: File not found: %s" % file_path)
                self.msg_contents[key] = None
        
        return self.msg_contents
    
    def extract_field_value(self, content, field_name):
        """
        Extract a field's default value from the message content.
        
        Args:
            content: The message content string
            field_name: The name of the field to extract
            
        Returns:
            The default value as a string, or None if not found or no default
        """
        if not content:
            return None
            
        # Look for field name in the content with a default value
        # This regex matches patterns like: type field_name = value
        pattern = r'(\w+)\s+' + re.escape(field_name) + r'\s*=\s*([^#\n]*)'
        match = re.search(pattern, content)
        
        if match:
            return match.group(2).strip()
        return None
    
    def extract_value_by_type(self, content, field_type, field_name):
        """
        Extract a field value by its type and name.
        
        Args:
            content: The message content string
            field_type: The field type (e.g., bool, uint8)
            field_name: The field name
            
        Returns:
            The field value or None if not found
        """
        if not content:
            return None
            
        pattern = r'' + re.escape(field_type) + r'\s+' + re.escape(field_name) + r'(?:\s*=\s*([^#\n]*))?'
        match = re.search(pattern, content)
        
        if match and match.group(1):
            return match.group(1).strip()
        return None
    
    def extract_constants(self, content):
        """
        Extract constant definitions from message content.
        
        Args:
            content: The message content string
            
        Returns:
            A dictionary of constant name -> value
        """
        if not content:
            return {}
            
        constants = {}
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                # This pattern matches constant definitions like: uint8 CONSTANT = value
                pattern = r'(\w+)\s+(\w+)\s*=\s*([^#\n]*)'
                match = re.match(pattern, line)
                
                if match:
                    type_name = match.group(1)
                    const_name = match.group(2)
                    const_value = match.group(3).strip()
                    
                    # Only add if it looks like a constant (all caps by convention)
                    if const_name.isupper():
                        constants[const_name] = {
                            'type': type_name,
                            'value': const_value
                        }
        
        return constants
    
    def process_eco_mode(self):
        """Process ecoMode.msg specific flags"""
        content = self.msg_contents.get('eco_mode')
        config = {'enabled': False, 'mode': None, 'saving': None}
        
        # Check if ecoMode is enabled
        enabled_value = self.extract_field_value(content, 'ecoMode_enabled')
        if enabled_value and enabled_value.lower() == 'true':
            config['enabled'] = True
            config['ECOModeON'] = True  # Special flag as requested
            
            # Get the mode in use
            mode_value = self.extract_field_value(content, 'mode_in_use')
            if mode_value:
                config['mode'] = mode_value
                
            # Get the saving value
            saving_value = self.extract_field_value(content, 'ecoMode_saving')
            if saving_value:
                config['saving'] = saving_value
                
        # Extract constants like PRODUCTION, HYBRID, EV
        constants = self.extract_constants(content)
        if constants:
            config['constants'] = constants
            
        return config
    
    def process_eco_cruise(self):
        """Process ecoCruise.msg specific flags"""
        content = self.msg_contents.get('eco_cruise')
        config = {'enabled': False, 'status': None}
        
        # Check for status field
        status_value = self.extract_field_value(content, 'ecoCruise_status')
        if status_value:
            config['status'] = status_value
            # In some cases, a non-zero status might indicate "enabled"
            if status_value != '0' and status_value.lower() != 'false':
                config['enabled'] = True
        
        # Extract constants
        constants = self.extract_constants(content)
        if constants:
            config['constants'] = constants
            
        return config
    
    def process_eco_drive(self):
        """Process ecoDrive.msg specific flags"""
        content = self.msg_contents.get('eco_drive')
        config = {'enabled': False, 'status': None}
        
        # Check for status field
        status_value = self.extract_field_value(content, 'ecoDrive_status')
        if status_value:
            config['status'] = status_value
            # In some cases, a non-zero status might indicate "enabled"
            if status_value != '0' and status_value.lower() != 'false':
                config['enabled'] = True
        
        # Extract constants like OFF, INACTIVE, CRUISING, etc.
        constants = self.extract_constants(content)
        if constants:
            config['constants'] = constants
            
        return config
    
    def process_eco_route(self):
        """Process ecoRoute.msg specific flags"""
        content = self.msg_contents.get('eco_route')
        config = {'enabled': False, 'route': None, 'savings': {}}
        
        # Check if ecoRoute is enabled
        enabled_value = self.extract_field_value(content, 'ecoRoute_enabled')
        if enabled_value and enabled_value.lower() == 'true':
            config['enabled'] = True
            
            # Get optimal route
            route_value = self.extract_field_value(content, 'optimum_route')
            if route_value:
                config['route'] = route_value
                
            # Get savings metrics
            time_saving = self.extract_field_value(content, 'saving_time')
            if time_saving:
                config['savings']['time'] = time_saving
                
            energy_saving = self.extract_field_value(content, 'saving_energy')
            if energy_saving:
                config['savings']['energy'] = energy_saving
                
            percent_saving = self.extract_field_value(content, 'saving_energy_percent')
            if percent_saving:
                config['savings']['percent'] = percent_saving
                
        return config
    
    def process_spat_n_map(self):
        """Process SPaTnMAP.msg specific flags"""
        content = self.msg_contents.get('spat_n_map')
        config = {'intersection_id': None, 'phase': None, 'timing': {}}
        
        # Extract the intersection ID
        intersection_id = self.extract_field_value(content, 'intersection_id')
        if intersection_id:
            config['intersection_id'] = intersection_id
            
        # Extract phase information
        phase_value = self.extract_field_value(content, 'phase')
        if phase_value:
            config['phase'] = phase_value
            
        # Extract signal timing information
        time_to_stop = self.extract_field_value(content, 'time_to_stop')
        if time_to_stop:
            config['timing']['time_to_stop'] = time_to_stop
            
        red_time = self.extract_field_value(content, 'cycle_time_red')
        if red_time:
            config['timing']['red'] = red_time
            
        yellow_time = self.extract_field_value(content, 'cycle_time_yellow')
        if yellow_time:
            config['timing']['yellow'] = yellow_time
            
        green_time = self.extract_field_value(content, 'cycle_time_green')
        if green_time:
            config['timing']['green'] = green_time
            
        return config
    
    def process_vehicle_intel_info(self):
        """Process VehicleIntelInfo.msg to find which modules are included"""
        content = self.msg_contents.get('vehicle_intel_info')
        config = {'modules': []}
        
        if not content:
            return config
            
        # Check which eco modules are included
        if 'ecoMode' in content:
            config['modules'].append('ecoMode')
        if 'ecoRoute' in content:
            config['modules'].append('ecoRoute')
        if 'ecoDrive' in content:
            config['modules'].append('ecoDrive')
        if 'ecoCruise' in content:
            config['modules'].append('ecoCruise')
            
        return config
    
    def process_all_configs(self):
        """Process all message files and generate complete configuration"""
        # Read all message files first
        self.read_all_msg_files()
        
        # Process each message type
        self.processed_config['eco_mode'] = self.process_eco_mode()
        self.processed_config['eco_cruise'] = self.process_eco_cruise()
        self.processed_config['eco_drive'] = self.process_eco_drive()
        self.processed_config['eco_route'] = self.process_eco_route()
        self.processed_config['spat_n_map'] = self.process_spat_n_map()
        self.processed_config['vehicle_intel_info'] = self.process_vehicle_intel_info()
        
        # Create consolidated flags for easy access
        self.processed_config['flags'] = {
            'eco_mode_enabled': self.processed_config['eco_mode']['enabled'],
            'eco_cruise_enabled': self.processed_config['eco_cruise']['enabled'],
            'eco_drive_enabled': self.processed_config['eco_drive']['enabled'], 
            'eco_route_enabled': self.processed_config['eco_route']['enabled'],
            'available_modules': self.processed_config['vehicle_intel_info']['modules']
        }
        
        return self.processed_config
    
    def save_config(self, output_file='nextcar_config.yaml'):
        """Save the processed configuration to a YAML file"""
        with open(output_file, 'w') as f:
            yaml.dump(self.processed_config, f, default_flow_style=False)
            
        print("Configuration saved to %s" % output_file)
        
        # Also save as JSON for easier usage with web tools
        json_file = output_file.replace('.yaml', '.json')
        with open(json_file, 'w') as f:
            json.dump(self.processed_config, f, indent=2)
            
        print("Configuration also saved to %s" % json_file)
        
    def load_config(self, config_file='nextcar_config.yaml'):
        """Load configuration from a YAML file"""
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
            
        return config

# Example usage
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process NextCAR .msg files into a configuration')
    parser.add_argument('--base-dir', type=str, default=os.getcwd(),
                      help='Base directory containing the msg folder structure')
    parser.add_argument('--output', type=str, default='nextcar_config.yaml',
                      help='Output YAML file path')
    
    args = parser.parse_args()
    
    config_reader = NextCARMsgConfig(args.base_dir)
    config_reader.process_all_configs()
    config_reader.save_config(args.output)
    
    print("\nConfiguration processing complete!")
    print("You can now use this configuration file with your RViz visualization tools.")
