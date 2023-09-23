import thorlabs_apt
import time

class thorlabs_motor:
    ## =============================================================================
    def __init__(self):
        (self.hw_type,self.serial_number) = thorlabs_apt.list_available_devices()[0]

        try:
            self.motor = thorlabs_apt.Motor(self.serial_number)
        except:
            raise ImportError('Failed to initialize the motor.')
            
        try:
            self.locate_home_position()
        except:
            raise ValueError('Failed to locate the motor\'s home position')
        return

    ## =============================================================================
    def locate_home_position(self):
        #print('has_homing_been_completed=', motor.has_homing_been_completed)
        #homepar = motor.get_move_home_parameters()
        #print(f'homing_parameters: direction={hpar[0]}, lim_switch={hpar[1]}, velocity={hpar[2]:.6f}, zero_offset={hpar[3]:.6f}')
        self.motor.set_move_home_parameters(2, 1, 10.0, 4.0)
        self.motor.move_home(True)
        if not self.motor.has_homing_been_completed:
            raise ValueError('Motor failed to find home position')
        return
    
    ## =============================================================================
    def live_motion_monitor(self, target_angle_deg):
        self.motor.move_to(target_angle_deg, blocking=True)      ## Move to absolute position. Units are "deg".

        while self.motor.is_in_motion:
            pos_error = self.motor.position - target_angle_deg
            #position_achieved = abs(pos_error) < 0.001
            print(f'{i}: is_in_motion={self.motor.is_in_motion}, is_settled={self.motor.is_settled}, is_tracking={self.motor.is_tracking}, pos_error={self.pos_error:.6f}')
            time.sleep(0.1)
            
        return

    ## =============================================================================
    def move_to(self, angle_deg):
        self.motor.move_to(target_pos, blocking=True)      ## Move to absolute position. Units are "deg".
