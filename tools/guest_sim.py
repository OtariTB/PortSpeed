"""Need for Speed ProStreet - Vehicle Dynamics, Physics & AI Race Simulation Model.

Implements the vehicle physics engine, rigid body integration, suspension/drivetrain,
tire slip curves, collision impulse resolution, and AI raceline navigation,
mirroring authentic ProStreet classes:
- ChassisSimple, Engine, DamagePhysics, DamageVehicle
- AIVehicleControlSteeringPid, AIVehicleControlThrottlePid, AIGoalRacer, AIRaceTactic
"""

import math
import struct
from typing import List, Tuple, Dict, Any, Optional

# Protocol Memory Base in 640 MB Linear Guest Space
SIM_GUEST_BASE          = 0x02040000
SIM_GUEST_VEHICLE_ARRAY = 0x02041000
SIM_VEHICLE_RECORD_SIZE = 256
SIM_MAX_VEHICLES        = 8

# Physical Constants
GRAVITY                 = 9.80665   # m/s^2
AIR_DENSITY             = 1.225     # kg/m^3
TIME_STEP               = 1.0 / 60.0 # 60 Hz physics update (16.67 ms)

# Gear ratios for 6-speed transmission (e.g. Nissan 240SX / Silvia S15)
GEAR_RATIOS = [0.0, 3.42, 2.14, 1.48, 1.12, 0.89, 0.72] # 0 = Neutral, 1..6
FINAL_DRIVE = 3.91
WHEEL_RADIUS = 0.32 # meters (~18-inch wheels)
TIRE_MU_PEAK = 1.15 # peak friction coefficient on tarmac


class VehiclePhysics:
    """Rigid body vehicle dynamics model matching ChassisSimple and Engine."""

    def __init__(self, vehicle_id: int, is_ai: bool = False):
        self.id = vehicle_id
        self.is_ai = is_ai

        # Spatial state
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.vz = 0.0
        self.yaw = 0.0     # Heading angle in radians (0 = along +X axis)
        self.pitch = 0.0
        self.roll = 0.0
        self.yaw_rate = 0.0 # rad/s

        # Mass & Aerodynamics
        self.mass = 1350.0  # kg
        self.cd = 0.31      # Drag coefficient
        self.frontal_area = 2.05 # m^2
        self.cl_downforce = 0.28 # Downforce coefficient

        # Engine & Transmission
        self.gear = 1
        self.rpm = 1000.0   # Idle RPM
        self.idle_rpm = 900.0
        self.max_rpm = 7800.0
        self.peak_torque = 380.0 # Nm
        self.clutch_engaged = 1.0

        # Controls input
        self.throttle = 0.0 # 0.0 .. 1.0
        self.brake = 0.0    # 0.0 .. 1.0
        self.steering = 0.0 # -1.0 (left) .. +1.0 (right)
        self.handbrake = 0.0 # 0.0 .. 1.0
        self.nitrous = 0.0  # 0.0 .. 1.0
        self.nitrous_left = 100.0 # %

        # Damage & Health
        self.damage_percent = 0.0 # 0.0 .. 100.0%
        self.engine_health = 100.0 # 100% -> 0%
        self.is_totaled = False

        # Race tracking
        self.lap = 1
        self.lap_time = 0.0
        self.track_distance = 0.0

        # AI navigation target
        self.ai_target_speed = 45.0 # m/s (~162 km/h)
        self.ai_target_x = 0.0
        self.ai_target_y = 0.0

    @property
    def speed_ms(self) -> float:
        """Forward vehicle velocity in m/s."""
        return math.sqrt(self.vx * self.vx + self.vy * self.vy)

    @property
    def speed_kmh(self) -> float:
        """Vehicle speed in km/h."""
        return self.speed_ms * 3.6

    def compute_engine_torque(self) -> float:
        """Computes engine torque output based on current RPM and throttle."""
        if self.engine_health <= 0.0 or self.is_totaled:
            return 0.0

        # Torque curve model: parabolic drop-off below 3500 and above 6500 RPM
        rpm_ratio = self.rpm / 4800.0
        torque_factor = max(0.2, min(1.0, 1.0 - 0.5 * (rpm_ratio - 1.0) ** 2))
        torque = self.peak_torque * torque_factor * self.throttle

        # Nitrous boost adds 35% torque
        if self.nitrous > 0.0 and self.nitrous_left > 0.0:
            torque *= 1.35
            self.nitrous_left = max(0.0, self.nitrous_left - 0.2)

        # Health penalty
        torque *= (self.engine_health / 100.0)
        return torque

    def update(self, dt: float = TIME_STEP) -> None:
        """Executes one simulation step of vehicle physics and powertrain integration."""
        if self.is_totaled:
            return

        speed = self.speed_ms
        cos_yaw = math.cos(self.yaw)
        sin_yaw = math.sin(self.yaw)

        # 1. Aerodynamic drag & downforce
        drag_force = 0.5 * AIR_DENSITY * self.cd * self.frontal_area * (speed * speed)
        downforce = 0.5 * AIR_DENSITY * self.cl_downforce * self.frontal_area * (speed * speed)
        normal_load = self.mass * GRAVITY + downforce

        # 2. Powertrain & Drive Force
        torque = self.compute_engine_torque()
        gear_ratio = GEAR_RATIOS[self.gear]
        drive_force = 0.0
        if gear_ratio > 0.0:
            drive_force = (torque * gear_ratio * FINAL_DRIVE) / WHEEL_RADIUS

        # 3. Braking Force
        max_brake_force = normal_load * TIRE_MU_PEAK * 0.95
        brake_force = self.brake * max_brake_force
        if self.handbrake > 0.0:
            brake_force += self.handbrake * max_brake_force * 0.5

        # 4. Net longitudinal force along vehicle heading
        if self.brake > 0.0 and speed < 0.2:
            new_speed = 0.0
            self.vx = 0.0
            self.vy = 0.0
            self.yaw_rate = 0.0
            return

        net_fwd_force = drive_force - drag_force - (brake_force if speed > 0.1 else 0.0)
        accel_fwd = net_fwd_force / self.mass

        # 5. Steering & Lateral Dynamics (Bicycle Model)
        wheelbase = 2.55 # meters
        max_steer_angle = math.radians(34.0)
        steer_angle = self.steering * max_steer_angle

        # High-speed steering stability decay
        speed_stability_factor = 1.0 / (1.0 + speed * 0.02)
        effective_steer = steer_angle * speed_stability_factor

        if speed > 0.5:
            # Yaw rate from Ackermann kinematics with tire slip angle saturation
            self.yaw_rate = (speed / wheelbase) * math.tan(effective_steer)
            # Lateral acceleration cap
            max_yaw_rate = (TIRE_MU_PEAK * GRAVITY) / speed
            self.yaw_rate = max(-max_yaw_rate, min(max_yaw_rate, self.yaw_rate))
        else:
            self.yaw_rate = 0.0

        self.yaw += self.yaw_rate * dt

        # 6. Velocity update in world coordinates
        new_speed = max(0.0, speed + accel_fwd * dt)
        self.vx = new_speed * math.cos(self.yaw)
        self.vy = new_speed * math.sin(self.yaw)

        # 7. Position update
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.track_distance += new_speed * dt
        self.lap_time += dt

        # 8. Powertrain RPM update & Automatic transmission shifts
        if gear_ratio > 0.0:
            wheel_rpm = (new_speed / (2.0 * math.pi * WHEEL_RADIUS)) * 60.0
            expected_rpm = wheel_rpm * gear_ratio * FINAL_DRIVE
            self.rpm = max(self.idle_rpm, min(self.max_rpm, expected_rpm))
        else:
            self.rpm = self.idle_rpm + self.throttle * 4000.0

        # Auto upshift
        if self.rpm > 6800.0 and self.gear < 6:
            self.gear += 1
            self.rpm = max(self.idle_rpm, self.rpm * 0.72)
        # Auto downshift
        elif self.rpm < 2400.0 and self.gear > 1:
            self.gear -= 1
            self.rpm = min(self.max_rpm, self.rpm * 1.38)

    def apply_collision(self, normal_x: float, normal_y: float, impulse_speed: float) -> None:
        """Resolves collision impact with track barrier or other vehicle (DamagePhysics)."""
        restitution = 0.35
        # Reflect velocity along collision normal
        dot = self.vx * normal_x + self.vy * normal_y
        if dot < 0.0:
            self.vx -= (1.0 + restitution) * dot * normal_x
            self.vy -= (1.0 + restitution) * dot * normal_y

        # Impact energy damage calculation
        impact_kmh = impulse_speed * 3.6
        if impact_kmh > 15.0:
            damage_increment = (impact_kmh - 15.0) * 0.45
            self.damage_percent = min(100.0, self.damage_percent + damage_increment)
            if self.damage_percent >= 25.0:
                self.engine_health = max(0.0, self.engine_health - damage_increment * 0.5)
            if self.damage_percent >= 100.0:
                self.is_totaled = True

    def pack(self) -> bytes:
        """Packs vehicle state into 256 bytes binary representation."""
        buf = bytearray(SIM_VEHICLE_RECORD_SIZE)
        struct.pack_into(
            '<12f', buf, 0,
            self.x, self.y, self.z,
            self.vx, self.vy, self.z,
            self.yaw, self.pitch, self.roll,
            self.yaw_rate, self.rpm, self.speed_kmh
        )
        struct.pack_into(
            '<5f', buf, 48,
            self.throttle, self.brake, self.steering, self.handbrake, self.nitrous
        )
        struct.pack_into(
            '<3f', buf, 68,
            self.damage_percent, self.engine_health, self.nitrous_left
        )
        struct.pack_into(
            '<4i', buf, 80,
            self.gear, 1 if self.is_ai else 0, 1 if self.is_totaled else 0, self.lap
        )
        struct.pack_into(
            '<2f', buf, 96,
            self.lap_time, self.track_distance
        )
        return bytes(buf)

    def unpack(self, data: bytes) -> None:
        """Unpacks vehicle state from binary representation."""
        vals = struct.unpack_from('<12f', data, 0)
        self.x, self.y, self.z = vals[0], vals[1], vals[2]
        self.vx, self.vy = vals[3], vals[4]
        self.yaw, self.pitch, self.roll = vals[6], vals[7], vals[8]
        self.yaw_rate, self.rpm = vals[9], vals[10]

        inputs = struct.unpack_from('<5f', data, 48)
        self.throttle, self.brake, self.steering, self.handbrake, self.nitrous = inputs

        damage = struct.unpack_from('<3f', data, 68)
        self.damage_percent, self.engine_health, self.nitrous_left = damage

        ints = struct.unpack_from('<4i', data, 80)
        self.gear = ints[0]
        self.is_ai = bool(ints[1])
        self.is_totaled = bool(ints[2])
        self.lap = ints[3]

        timing = struct.unpack_from('<2f', data, 96)
        self.lap_time, self.track_distance = timing


class AIRacerController:
    """Authentic AI driver controller implementing AIVehicleControlSteeringPid and AIVehicleControlThrottlePid."""

    def __init__(self, vehicle: VehiclePhysics):
        self.vehicle = vehicle
        # PID gains for steering
        self.kp_steer = 1.6
        self.kd_steer = 0.4
        self.prev_steer_error = 0.0

        # PID gains for throttle / speed
        self.kp_throttle = 0.15

        # Tactical state
        self.is_drafting = False
        self.overtake_bias = 0.0 # lateral offset

    def update_ai(self, target_x: float, target_y: float, target_speed: float, ahead_vehicle: Optional[VehiclePhysics] = None) -> None:
        """Updates AI throttle, braking, and steering outputs to follow racing line."""
        v = self.vehicle

        # 1. Target vector
        dx = target_x - v.x
        dy = target_y - v.y
        dist_to_target = math.sqrt(dx * dx + dy * dy)
        target_heading = math.atan2(dy, dx)

        # 2. Heading error normalized to [-pi, pi]
        heading_error = target_heading - v.yaw
        while heading_error > math.pi: heading_error -= 2.0 * math.pi
        while heading_error < -math.pi: heading_error += 2.0 * math.pi

        # 3. Steering PID calculation
        d_error = (heading_error - self.prev_steer_error) / TIME_STEP
        steer_cmd = self.kp_steer * heading_error + self.kd_steer * d_error
        v.steering = max(-1.0, min(1.0, steer_cmd))
        self.prev_steer_error = heading_error

        # 4. Drafting & Overtake Tactics (AIDraftTactic, AIPassTactic)
        effective_target_speed = target_speed
        if ahead_vehicle and not ahead_vehicle.is_totaled:
            dist_to_ahead = math.sqrt((ahead_vehicle.x - v.x) ** 2 + (ahead_vehicle.y - v.y) ** 2)
            if dist_to_ahead < 25.0 and dist_to_ahead > 6.0:
                self.is_drafting = True
                # Slipstream enables slightly higher chase speed
                effective_target_speed = ahead_vehicle.speed_ms + 4.0
                # Overtake shift
                if dist_to_ahead < 14.0 and v.speed_ms > ahead_vehicle.speed_ms:
                    v.steering += 0.25 # pull out to pass
            else:
                self.is_drafting = False

        # 5. Throttle / Brake PID calculation
        current_speed = v.speed_ms
        speed_error = effective_target_speed - current_speed

        if speed_error > 0.0:
            v.throttle = min(1.0, speed_error * self.kp_throttle)
            v.brake = 0.0
        else:
            v.throttle = 0.0
            v.brake = min(1.0, -speed_error * 0.3)


class RaceSimulationWorld:
    """Manages the full multi-vehicle race simulation world in linear guest memory."""

    def __init__(self, memory: bytearray):
        self.mem = memory
        self.vehicles: List[VehiclePhysics] = []
        self.ai_controllers: List[AIRacerController] = []
        self.track_length = 3200.0 # 3.2 km track circuit
        self.init_vehicles()

    def init_vehicles(self, num_racers: int = 4) -> None:
        """Initializes player car and AI field."""
        self.vehicles.clear()
        self.ai_controllers.clear()

        # Vehicle 0: Player
        player = VehiclePhysics(0, is_ai=False)
        player.x = 0.0
        player.y = 0.0
        self.vehicles.append(player)

        # Vehicles 1..N: AI Competitors
        for i in range(1, num_racers):
            ai_car = VehiclePhysics(i, is_ai=True)
            ai_car.x = -i * 12.0 # Grid start staggering
            ai_car.y = (i % 2) * 3.5 - 1.75
            self.vehicles.append(ai_car)
            self.ai_controllers.append(AIRacerController(ai_car))

        self.sync_to_guest_memory()

    def step(self, dt: float = TIME_STEP) -> None:
        """Performs one full frame update of all vehicles, collision checks, and AI."""
        # 1. Update AI drivers
        for controller in self.ai_controllers:
            car = controller.vehicle
            # Circular oval track waypoint synthesis: R = 400m
            theta = (car.track_distance / self.track_length) * 2.0 * math.pi
            lookahead = 0.05
            target_x = 400.0 * math.cos(theta + lookahead)
            target_y = 200.0 * math.sin(theta + lookahead)
            controller.update_ai(target_x, target_y, target_speed=48.0)

        # 2. Update physics integration for all vehicles
        for car in self.vehicles:
            car.update(dt)

        # 3. Inter-vehicle collision detection & impulse resolution
        n = len(self.vehicles)
        collision_radius = 2.4 # meters
        for i in range(n):
            for j in range(i + 1, n):
                c1 = self.vehicles[i]
                c2 = self.vehicles[j]
                dx = c2.x - c1.x
                dy = c2.y - c1.y
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < collision_radius and dist > 0.01:
                    nx = dx / dist
                    ny = dy / dist
                    rel_speed = math.sqrt((c1.vx - c2.vx) ** 2 + (c1.vy - c2.vy) ** 2)
                    c1.apply_collision(-nx, -ny, rel_speed * 0.5)
                    c2.apply_collision(nx, ny, rel_speed * 0.5)

        # 4. Sync updated state to guest memory
        self.sync_to_guest_memory()

    def sync_to_guest_memory(self) -> None:
        """Writes all vehicle records into linear guest memory array at 0x02041000."""
        for i, car in enumerate(self.vehicles):
            offset = SIM_GUEST_VEHICLE_ARRAY + i * SIM_VEHICLE_RECORD_SIZE
            packed = car.pack()
            self.mem[offset : offset + len(packed)] = packed
