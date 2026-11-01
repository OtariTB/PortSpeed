import test from 'node:test';
import assert from 'node:assert/strict';
import { ClientVehicleSim, SIM_TIME_STEP } from '../src/sim.js';

test('ClientVehicleSim accelerates forward and shifts gears under full throttle', () => {
  const car = new ClientVehicleSim();
  car.throttle = 1.0;

  for (let i = 0; i < 240; i++) {
    car.step(SIM_TIME_STEP);
  }

  assert.ok(car.speedKmh > 80.0, `Expected speed > 80, got ${car.speedKmh}`);
  assert.ok(car.x > 30.0, `Expected x > 30, got ${car.x}`);
  assert.ok(car.gear >= 2, `Expected gear >= 2, got ${car.gear}`);
  assert.ok(car.rpm >= car.idleRpm);
  assert.ok(car.rpm <= car.maxRpm);
});

test('ClientVehicleSim decelerates smoothly to complete stop under braking', () => {
  const car = new ClientVehicleSim();
  car.throttle = 1.0;
  for (let i = 0; i < 180; i++) car.step(SIM_TIME_STEP);
  assert.ok(car.speedKmh > 70.0);

  // Apply brakes
  car.throttle = 0;
  car.brake = 1.0;

  for (let i = 0; i < 240; i++) {
    car.step(SIM_TIME_STEP);
  }

  assert.equal(car.speedKmh, 0.0);
  assert.equal(car.vx, 0.0);
});

test('ClientVehicleSim turns and changes yaw under steering input', () => {
  const car = new ClientVehicleSim();
  car.throttle = 0.8;
  car.steering = 0.5; // Turn right

  for (let i = 0; i < 120; i++) {
    car.step(SIM_TIME_STEP);
  }

  assert.ok(car.yaw > 0.1, `Expected yaw > 0.1, got ${car.yaw}`);
  assert.ok(car.y > 1.0, `Expected y > 1.0, got ${car.y}`);
});

test('ClientVehicleSim resolves collision impulse and inflicts damage', () => {
  const car = new ClientVehicleSim();
  car.vx = 25.0; // ~90 km/h
  car.vy = 0;

  car.applyCollision(-1.0, 0.0, 25.0);

  // Velocity reflected
  assert.ok(car.vx < 0.0, `Expected vx < 0, got ${car.vx}`);
  // Sustained damage
  assert.ok(car.damagePercent > 10.0, `Expected damage > 10%, got ${car.damagePercent}`);
  assert.ok(car.engineHealth < 100.0, `Expected engine health < 100%, got ${car.engineHealth}`);
});

test('ClientVehicleSim exports complete telemetry snapshot', () => {
  const car = new ClientVehicleSim();
  car.throttle = 0.75;
  car.steering = -0.25;
  car.step(SIM_TIME_STEP);

  const t = car.getTelemetry();
  assert.equal(t.throttle, 0.75);
  assert.equal(t.steering, -0.25);
  assert.equal(t.lap, 1);
  assert.ok(t.lapTime > 0);
  assert.equal(t.isTotaled, false);
});

