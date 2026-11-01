/**
 * Need for Speed ProStreet - Client-Side Vehicle Dynamics & Race Simulation.
 *
 * Implements rigid body dynamics, powertrain integration, automatic gear shifts,
 * tire friction/slip, collision impulse response, and AI waypoint tracking.
 */

export const SIM_TIME_STEP = 1.0 / 60.0; // 60 Hz physics update (16.67 ms)
export const GEAR_RATIOS = [0.0, 3.42, 2.14, 1.48, 1.12, 0.89, 0.72];
export const FINAL_DRIVE = 3.91;
export const WHEEL_RADIUS = 0.32; // meters

export interface VehicleTelemetry {
  x: number;
  y: number;
  z: number;
  speedKmh: number;
  rpm: number;
  gear: number;
  yaw: number;
  throttle: number;
  brake: number;
  steering: number;
  damagePercent: number;
  engineHealth: number;
  isTotaled: boolean;
  lap: number;
  lapTime: number;
}

export class ClientVehicleSim {
  public x: number = 0;
  public y: number = 0;
  public z: number = 0;
  public vx: number = 0;
  public vy: number = 0;
  public yaw: number = 0; // heading angle in radians
  public yawRate: number = 0;

  public mass: number = 1350; // kg
  public cd: number = 0.31;
  public frontalArea: number = 2.05;

  public gear: number = 1;
  public rpm: number = 1000;
  public idleRpm: number = 900;
  public maxRpm: number = 7800;
  public peakTorque: number = 380; // Nm

  public throttle: number = 0;
  public brake: number = 0;
  public steering: number = 0;
  public handbrake: number = 0;
  public nitrous: number = 0;
  public nitrousLeft: number = 100;

  public damagePercent: number = 0;
  public engineHealth: number = 100;
  public isTotaled: boolean = false;

  public lap: number = 1;
  public lapTime: number = 0;
  public trackDistance: number = 0;
  public isAi: boolean = false;

  constructor(isAi: boolean = false) {
    this.isAi = isAi;
  }

  public get speedMs(): number {
    return Math.sqrt(this.vx * this.vx + this.vy * this.vy);
  }

  public get speedKmh(): number {
    return this.speedMs * 3.6;
  }

  public computeTorque(): number {
    if (this.engineHealth <= 0 || this.isTotaled) return 0;
    const rpmRatio = this.rpm / 4800.0;
    const torqueFactor = Math.max(0.2, Math.min(1.0, 1.0 - 0.5 * (rpmRatio - 1.0) ** 2));
    let torque = this.peakTorque * torqueFactor * this.throttle;
    if (this.nitrous > 0 && this.nitrousLeft > 0) {
      torque *= 1.35;
      this.nitrousLeft = Math.max(0, this.nitrousLeft - 0.2);
    }
    return torque * (this.engineHealth / 100.0);
  }

  public step(dt: number = SIM_TIME_STEP): void {
    if (this.isTotaled) return;

    const speed = this.speedMs;

    // Stop detection
    if (this.brake > 0 && speed < 0.2) {
      this.vx = 0;
      this.vy = 0;
      this.yawRate = 0;
      return;
    }

    // Aerodynamics
    const drag = 0.5 * 1.225 * this.cd * this.frontalArea * (speed * speed);
    const downforce = 0.5 * 1.225 * 0.28 * this.frontalArea * (speed * speed);
    const normalLoad = this.mass * 9.80665 + downforce;

    // Powertrain drive force
    const torque = this.computeTorque();
    const gRatio = GEAR_RATIOS[this.gear] || 0;
    let driveForce = 0;
    if (gRatio > 0) {
      driveForce = (torque * gRatio * FINAL_DRIVE) / WHEEL_RADIUS;
    }

    // Braking force
    const maxBrake = normalLoad * 1.15 * 0.95;
    const brakeForce = this.brake * maxBrake + this.handbrake * maxBrake * 0.5;

    const netFwdForce = driveForce - drag - (speed > 0.1 ? brakeForce : 0);
    const accelFwd = netFwdForce / this.mass;

    // Steering kinematics
    const maxSteerAngle = (34.0 * Math.PI) / 180.0;
    const effectiveSteer = (this.steering * maxSteerAngle) / (1.0 + speed * 0.02);
    if (speed > 0.5) {
      this.yawRate = (speed / 2.55) * Math.tan(effectiveSteer);
      const maxYaw = (1.15 * 9.80665) / speed;
      this.yawRate = Math.max(-maxYaw, Math.min(maxYaw, this.yawRate));
    } else {
      this.yawRate = 0;
    }

    this.yaw += this.yawRate * dt;

    const newSpeed = Math.max(0, speed + accelFwd * dt);
    this.vx = newSpeed * Math.cos(this.yaw);
    this.vy = newSpeed * Math.sin(this.yaw);

    this.x += this.vx * dt;
    this.y += this.vy * dt;
    this.trackDistance += newSpeed * dt;
    this.lapTime += dt;

    // Transmission & RPM
    if (gRatio > 0) {
      const wheelRpm = (newSpeed / (2.0 * Math.PI * WHEEL_RADIUS)) * 60.0;
      const expectedRpm = wheelRpm * gRatio * FINAL_DRIVE;
      this.rpm = Math.max(this.idleRpm, Math.min(this.maxRpm, expectedRpm));
    } else {
      this.rpm = this.idleRpm + this.throttle * 4000.0;
    }

    // Auto transmission
    if (this.rpm > 6800 && this.gear < 6) {
      this.gear += 1;
      this.rpm = Math.max(this.idleRpm, this.rpm * 0.72);
    } else if (this.rpm < 2400 && this.gear > 1) {
      this.gear -= 1;
      this.rpm = Math.min(this.maxRpm, this.rpm * 1.38);
    }
  }

  public applyCollision(nx: number, ny: number, impulseSpeed: number): void {
    const restitution = 0.35;
    const dot = this.vx * nx + this.vy * ny;
    if (dot < 0) {
      this.vx -= (1.0 + restitution) * dot * nx;
      this.vy -= (1.0 + restitution) * dot * ny;
    }

    const impactKmh = impulseSpeed * 3.6;
    if (impactKmh > 15.0) {
      const inc = (impactKmh - 15.0) * 0.45;
      this.damagePercent = Math.min(100.0, this.damagePercent + inc);
      if (this.damagePercent >= 25.0) {
        this.engineHealth = Math.max(0.0, this.engineHealth - inc * 0.5);
      }
      if (this.damagePercent >= 100.0) {
        this.isTotaled = true;
      }
    }
  }

  public getTelemetry(): VehicleTelemetry {
    return {
      x: this.x,
      y: this.y,
      z: this.z,
      speedKmh: this.speedKmh,
      rpm: this.rpm,
      gear: this.gear,
      yaw: this.yaw,
      throttle: this.throttle,
      brake: this.brake,
      steering: this.steering,
      damagePercent: this.damagePercent,
      engineHealth: this.engineHealth,
      isTotaled: this.isTotaled,
      lap: this.lap,
      lapTime: this.lapTime,
    };
  }
}

