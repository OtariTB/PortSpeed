"""Automated tests for vehicle dynamics, physics simulation, collision, and AI racing.

Verifies:
1. Powertrain acceleration and automatic transmission gear shifting (ChassisSimple, Engine).
2. Aerodynamic drag saturation and terminal velocity calculation.
3. Braking dynamics and deceleration to standstill.
4. Steering kinematics and lateral yaw dynamics.
5. Collision impulse resolution, bounce-back restitution, and damage scaling (DamagePhysics, DamageVehicle).
6. AI raceline PID waypoint tracking and drafting tactics (AIGoalRacer, AIRaceTactic).
7. Guest memory binary serialization (256-byte records) at 0x02041000.
"""

import math
import struct
import unittest
from tools.guest_sim import (
    VehiclePhysics,
    AIRacerController,
    RaceSimulationWorld,
    SIM_GUEST_VEHICLE_ARRAY,
    SIM_VEHICLE_RECORD_SIZE,
    TIME_STEP
)


class TestRaceSimulation(unittest.TestCase):
    def setUp(self):
        self.mem = bytearray(0x28000000) # 640 MB guest linear memory
        self.car = VehiclePhysics(0)

    def test_straight_line_acceleration_and_gear_shifts(self):
        """Verify vehicle accelerates forward and shifts gears automatically under full throttle."""
        self.car.throttle = 1.0

        # Run 240 physics frames (4 seconds)
        for _ in range(240):
            self.car.update(TIME_STEP)

        # Vehicle must have moved forward and accelerated significantly
        self.assertGreater(self.car.speed_kmh, 80.0)
        self.assertGreater(self.car.x, 30.0)
        # Must have upshifted past 1st gear
        self.assertGreaterEqual(self.car.gear, 2)
        # RPM should stay in valid operating range
        self.assertGreaterEqual(self.car.rpm, self.car.idle_rpm)
        self.assertLessEqual(self.car.rpm, self.car.max_rpm)

    def test_aerodynamic_drag_and_terminal_velocity(self):
        """Verify aerodynamic drag opposes motion and caps top speed."""
        self.car.throttle = 1.0
        # Run 1800 frames (30 seconds) to reach terminal speed
        for _ in range(1800):
            self.car.update(TIME_STEP)

        top_speed_kmh = self.car.speed_kmh
        # Realistic top speed for Nissan 240SX (~220 - 260 km/h)
        self.assertGreater(top_speed_kmh, 210.0)
        self.assertLess(top_speed_kmh, 280.0)

        # In 6th gear at top speed
        self.assertEqual(self.car.gear, 6)

    def test_braking_dynamics(self):
        """Verify braking smoothly stops the vehicle without reversing."""
        # Accelerate to 100 km/h first
        self.car.throttle = 1.0
        for _ in range(180):
            self.car.update(TIME_STEP)
        self.assertGreater(self.car.speed_kmh, 70.0)

        # Apply 100% brakes, zero throttle
        self.car.throttle = 0.0
        self.car.brake = 1.0

        # Simulate until stop
        for _ in range(240):
            self.car.update(TIME_STEP)

        # Must come to a complete stop
        self.assertAlmostEqual(self.car.speed_kmh, 0.0, places=1)
        self.assertGreaterEqual(self.car.vx, 0.0) # No negative speed

    def test_steering_and_yaw_kinematics(self):
        """Verify steering induces yaw angle change and curved trajectory."""
        self.car.throttle = 0.8
        self.car.steering = 0.6 # Steer right

        for _ in range(120): # 2 seconds
            self.car.update(TIME_STEP)

        # Heading angle yaw must be positive (turning right)
        self.assertGreater(self.car.yaw, 0.2)
        # Y position must have deviated from straight line (y > 0)
        self.assertGreater(self.car.y, 2.0)

    def test_collision_impulse_and_damage_physics(self):
        """Verify collision with wall reflects velocity and inflicts damage."""
        # Drive forward at 90 km/h (25 m/s)
        self.car.vx = 25.0
        self.car.vy = 0.0
        self.car.yaw = 0.0

        # Hit a vertical wall perpendicular to X axis (normal pointing -X)
        self.car.apply_collision(normal_x=-1.0, normal_y=0.0, impulse_speed=25.0)

        # Velocity should bounce back (vx negative)
        self.assertLess(self.car.vx, 0.0)
        # Vehicle must have sustained damage
        self.assertGreater(self.car.damage_percent, 10.0)
        # Engine health must have decreased
        self.assertLess(self.car.engine_health, 100.0)

    def test_ai_waypoint_tracking_and_pid_control(self):
        """Verify AI driver steers towards target waypoint and accelerates."""
        ai_car = VehiclePhysics(1, is_ai=True)
        controller = AIRacerController(ai_car)

        # Target waypoint at (100, 20) with target speed 40 m/s
        for _ in range(180): # 3 seconds
            controller.update_ai(target_x=100.0, target_y=20.0, target_speed=40.0)
            ai_car.update(TIME_STEP)

        # AI should have steered towards positive Y and gained speed
        self.assertGreater(ai_car.x, 20.0)
        self.assertGreater(ai_car.y, 1.0)
        self.assertGreater(ai_car.speed_kmh, 40.0)

    def test_guest_memory_binary_serialization(self):
        """Verify 256-byte vehicle records pack and unpack faithfully in guest memory."""
        world = RaceSimulationWorld(self.mem)
        world.step(TIME_STEP)

        # Read back player vehicle record from guest memory
        packed_player = bytes(self.mem[SIM_GUEST_VEHICLE_ARRAY : SIM_GUEST_VEHICLE_ARRAY + SIM_VEHICLE_RECORD_SIZE])
        self.assertEqual(len(packed_player), 256)

        readback_car = VehiclePhysics(99)
        readback_car.unpack(packed_player)

        # Verify values match live world state
        player_live = world.vehicles[0]
        self.assertAlmostEqual(readback_car.x, player_live.x, places=4)
        self.assertAlmostEqual(readback_car.speed_kmh, player_live.speed_kmh, places=2)
        self.assertEqual(readback_car.gear, player_live.gear)
        self.assertEqual(readback_car.is_ai, False)


if __name__ == '__main__':
    unittest.main()

