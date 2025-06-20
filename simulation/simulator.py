import numpy as np
from scipy.integrate import solve_ivp
from models.dynamics import rocket_ode
from config import INITIAL_CONDITIONS, TOTAL_TIME, TIME_STEP, PID_GAINS
from control.pid import PID
import matplotlib.pyplot as plt
import os

def guidance_law(t):
    """
    Define target [roll, pitch, yaw] over time.
    For example: pitch over from 0 to 10 degrees in first 5 seconds, then hold.
    """
    pitch_target = np.deg2rad(10) if t > 5 else np.deg2rad(0)
    return np.array([0.0, pitch_target, 0.0])  # [roll, pitch, yaw]

# gains: dict with keys 'roll','pitch','yaw' mapping to dicts of kp,ki,kd overrides
# thrust: float to override THRUST_PROFILE.thrust
# drag: float to override ROCKET.drag_coefficient

def simulate_closed_loop(initial_state=None, gains=None, thrust=None, drag=None):
    # Initial state vector: [x, y, z, vx, vy, vz, phi, theta, psi, wx, wy, wz]
    if initial_state is not None:
        state0 = np.array(initial_state, dtype=float)
    else:
        state0 = np.array(
            INITIAL_CONDITIONS.position +
            INITIAL_CONDITIONS.velocity +
            INITIAL_CONDITIONS.orientation +
            INITIAL_CONDITIONS.angular_velocity,
            dtype=float
        )

    # PID controllers
    gains = gains or PID_GAINS
    pid_roll = PID(**gains['roll'])
    pid_pitch = PID(**gains['pitch'])
    pid_yaw = PID(**gains['yaw'])

    torques_history = []

    def closed_loop_dynamics(t, state):
        # --- Guidance target ---
        target_angles = guidance_law(t)
        current_angles = state[6:9]  # phi, theta, psi

        # --- PID control ---
        pid_roll.setpoint = target_angles[0]
        pid_pitch.setpoint = target_angles[1]
        pid_yaw.setpoint = target_angles[2]
        torque = np.array([
            pid_roll.update(current_angles[0], TIME_STEP),
            pid_pitch.update(current_angles[1], TIME_STEP),
            pid_yaw.update(current_angles[2], TIME_STEP)
        ])

        # --- Record torque for plotting ---
        torques_history.append((t, *torque))

        return rocket_ode(t, state, torque, thrust=thrust, drag_coeff=drag)

    # Solve using solve_ivp
    sol = solve_ivp(
        fun=closed_loop_dynamics,
        t_span=(0, TOTAL_TIME),
        y0=state0,
        method='RK45',
        dense_output=True,
        max_step=0.05  # Optional: controls resolution
    )

    # Convert torques_history to array for easy plotting
    torques_history = np.array(torques_history)
    return sol, torques_history


