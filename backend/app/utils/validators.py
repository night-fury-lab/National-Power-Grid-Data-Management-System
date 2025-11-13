from datetime import datetime
import re

class Validator:
    
    @staticmethod
    def validate_plant_id(plant_id):
        """Validate plant ID format"""
        if not plant_id or len(plant_id) > 20:
            return False, "Plant ID must be between 1 and 20 characters"
        
        if not re.match(r'^[A-Z0-9_]+$', plant_id):
            return False, "Plant ID must contain only uppercase letters, numbers, and underscores"
        
        return True, "Valid"
    
    @staticmethod
    def validate_plant_name(plant_name):
        """Validate plant name"""
        if not plant_name or len(plant_name) > 255:
            return False, "Plant name must be between 1 and 255 characters"
        
        return True, "Valid"
    
    @staticmethod
    def validate_efficiency(efficiency):
        """Validate efficiency percentage"""
        try:
            eff_float = float(efficiency)
            if eff_float < 0 or eff_float > 999.99:
                return False, "Efficiency must be between 0 and 999.99"
            return True, "Valid"
        except (ValueError, TypeError):
            return False, "Efficiency must be a valid number"
    
    @staticmethod
    def validate_capacity(capacity):
        """Validate capacity in MW"""
        try:
            cap_float = float(capacity)
            if cap_float < 0:
                return False, "Capacity cannot be negative"
            return True, "Valid"
        except (ValueError, TypeError):
            return False, "Capacity must be a valid number"
    
    @staticmethod
    def validate_date(date_string):
        """Validate date format (YYYY-MM-DD)"""
        try:
            datetime.strptime(date_string, '%Y-%m-%d')
            return True, "Valid"
        except ValueError:
            return False, "Date must be in YYYY-MM-DD format"
    
    @staticmethod
    def validate_state_code(state_code):
        """Validate state code"""
        if not state_code or len(state_code) > 10:
            return False, "State code must be between 1 and 10 characters"
        
        return True, "Valid"
    
    @staticmethod
    def validate_required_fields(data, required_fields):
        """Validate that all required fields are present"""
        missing_fields = [field for field in required_fields if field not in data or not data[field]]
        
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"
        
        return True, "Valid"
    
    @staticmethod
    def validate_plant_data(data):
        """Validate complete plant data"""
        # Check required fields
        required_fields = ['plant_id', 'plant_name', 'state_code', 'sector_id', 'type_id']
        is_valid, message = Validator.validate_required_fields(data, required_fields)
        
        if not is_valid:
            return False, message
        
        # Validate plant ID
        is_valid, message = Validator.validate_plant_id(data['plant_id'])
        if not is_valid:
            return False, message
        
        # Validate plant name
        is_valid, message = Validator.validate_plant_name(data['plant_name'])
        if not is_valid:
            return False, message
        
        # Validate state code
        is_valid, message = Validator.validate_state_code(data['state_code'])
        if not is_valid:
            return False, message
        
        return True, "Valid"
