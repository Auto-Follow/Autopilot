/****************************************************************************
 *
 *   Copyright (c) 2026 PX4 Development Team. All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 *
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in
 *    the documentation and/or other materials provided with the
 *    distribution.
 * 3. Neither the name PX4 nor the names of its contributors may be
 *    used to endorse or promote products derived from this software
 *    without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
 * FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
 * COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
 * INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
 * BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
 * OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
 * AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
 * LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
 * ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 *
 ****************************************************************************/

/**
 * @file AutoFollowGuidance.hpp
 *
 * Pure computations of the AUTO FOLLOW mode: input validation, geometry (LOS to target position on flat ground),
 * velocity guidance law with limits and the target loss state machine.
 * No uORB access and no parameters: every value and every time is an argument, so that it can be unit tested.
 * Result and state codes are the CHECK_* / STATE_* constants of auto_follow_status.
 */

#pragma once

#include <stdint.h>

#include <matrix/math.hpp>
#include <uORB/topics/auto_follow_status.h>

namespace AutoFollowGuidance
{

// Name of the companion computer input in debug_array (at most 9 characters)
static constexpr char INPUT_NAME[] = "AF_LOS";

// Layout of the input in debug_array.data
enum InputIndex : uint8_t {
	INPUT_LOS_X = 0,  // LOS x, body FRD
	INPUT_LOS_Y = 1,  // LOS y, body FRD
	INPUT_LOS_Z = 2,  // LOS z, body FRD
	INPUT_AGE = 3,    // [ms] age reported by the companion computer
	INPUT_SEQ = 4,    // sequence number
	INPUT_TARGET = 5, // target flag, 1 = target visible
	INPUT_SIZE = 6
};

/**
 * Input checks 1..7 in the specified order, the first failing check is the result.
 * Checks 8 (depression) and 9 (range) are done in compute_geometry().
 * @param name debug_array.name, NUL terminated
 * @param data debug_array.data, at least INPUT_SIZE values
 * @param arrival debug_array.timestamp, arrival time on the FC [us]
 * @param now current time [us]
 * @param has_previous_seq false until a sample passed the sequence check
 * @param previous_seq sequence number of the last sample that passed the sequence check
 * @param norm_tol AF_NORM_TOL [-]
 * @param data_timeout AF_DATA_TOUT [s]
 * @param position_valid vehicle_local_position xy_valid && z_valid
 * @return CHECK_OK if checks 1..7 passed, otherwise the CHECK_* of the first failing check
 */
uint8_t check_input(const char *name, const float *data, uint64_t arrival, uint64_t now, bool has_previous_seq,
		    float previous_seq, float norm_tol, float data_timeout, bool position_valid);

/** True if a sample with this result passed the sequence check (its sequence number becomes the previous one). */
inline bool sequence_passed(uint8_t check_result)
{
	return check_result == auto_follow_status_s::CHECK_OK || check_result > auto_follow_status_s::CHECK_SEQ;
}

struct Geometry {
	matrix::Vector3f los_ned;       // LOS in NED (unit length)
	float depression;               // [rad] depression angle
	float height_diff;              // [m] height difference h
	float range;                    // [m] horizontal range d
	matrix::Vector2f target_xy;     // [m] measured target position, NED x, y
};

/**
 * Checks 8 and 9 with the flat ground geometry:
 * LOS_NED = R(q) LOS_FRD, depression = asin(LOS_NED.z), h = -z - gnd_ofs - tgt_hgt, d = h / tan(depression),
 * target = drone + d * LOS_NED_xy / |LOS_NED_xy|.
 * Values not reached by a failing check are NaN.
 * @param q vehicle_attitude.q (FRD to NED)
 * @param los_frd LOS, body FRD (length checked by check_input)
 * @param drone_xy vehicle_local_position x, y [m]
 * @param drone_z vehicle_local_position z [m], NED (down positive)
 * @param tgt_hgt AF_TGT_HGT [m]
 * @param gnd_ofs AF_GND_OFS [m]
 * @param min_depression AF_MIN_DEP [rad]
 * @param max_range AF_MAX_RNG [m]
 * @return CHECK_OK, CHECK_DEPRESSION or CHECK_RANGE
 */
uint8_t compute_geometry(const matrix::Quatf &q, const matrix::Vector3f &los_frd, const matrix::Vector2f &drone_xy,
			 float drone_z, float tgt_hgt, float gnd_ofs, float min_depression, float max_range, Geometry &out);

struct Guidance {
	matrix::Vector2f vel_law;       // [m/s] law output before limits, NED x, y
	float range_est;                // [m] horizontal range to the estimated target
	float range_desired;            // [m] desired horizontal range
	float yaw;                      // [rad] yaw setpoint
	bool yaw_frozen;                // yaw kept because the target is closer than yaw_min_range
};

/**
 * Velocity law v = k_ff * v_target + k_dist * (d_est - d_desired) * u, d_desired = h / tan(track_angle),
 * u = horizontal unit vector from the drone to the estimated target; yaw = atan2(dy, dx) towards the target.
 * @param target_est estimated target position, NED x, y [m]
 * @param target_vel estimated target velocity, NED x, y [m/s]
 * @param drone_xy vehicle_local_position x, y [m]
 * @param height_diff h of the last accepted measurement [m]
 * @param track_angle AF_TRK_ANG [rad]
 * @param k_dist AF_K_DIST [1/s]
 * @param k_ff AF_K_FF [-]
 * @param yaw_min_range AF_YAW_MIN_D [m]
 * @param last_yaw yaw kept when the target is closer than yaw_min_range [rad]
 */
void compute_guidance(const matrix::Vector2f &target_est, const matrix::Vector2f &target_vel, const matrix::Vector2f &drone_xy,
		      float height_diff, float track_angle, float k_dist, float k_ff, float yaw_min_range, float last_yaw, Guidance &out);

/** Scale v down to the length max_length (AF_VEL_MAX) if it is longer. */
matrix::Vector2f constrain_length(const matrix::Vector2f &v, float max_length);

/**
 * Move from previous towards desired by at most max_change (length of the change vector, AF_ACC_MAX * dt),
 * so the limit does not depend on the direction.
 */
matrix::Vector2f limit_change(const matrix::Vector2f &previous, const matrix::Vector2f &desired, float max_change);

struct StateMachine {
	uint8_t state{auto_follow_status_s::STATE_PASIF};
	uint64_t entry_time{0};         // [us] time the mode became active
	uint64_t lost_start{0};         // [us] start of the AF_LOST_T countdown
};

/**
 * Target loss state machine (PASIF / TAKIP / KAYIP_BEKLE / HOLD_ISTENDI).
 * - not active -> PASIF
 * - entry: TAKIP if a valid sample is younger than data_timeout and no "no target" sample came after it,
 *   otherwise KAYIP_BEKLE with Hold at max(last valid, entry) + data_timeout + lost_timeout
 * - TAKIP -> KAYIP_BEKLE: "no target" sample after the last valid one (countdown starts at its arrival),
 *   or data_timeout without a valid sample since max(last valid, entry)
 * - KAYIP_BEKLE -> TAKIP: new valid sample; KAYIP_BEKLE -> HOLD_ISTENDI: lost_timeout elapsed
 * - HOLD_ISTENDI is only left when the mode is no longer active
 * @param mode_active vehicle_status.nav_state is the AUTO FOLLOW nav_state
 * @param now current time [us]
 * @param last_valid arrival time of the last sample that passed all 9 checks, 0 if none [us]
 * @param last_no_target arrival time of the last CHECK_NO_TARGET sample, 0 if none [us]
 * @param data_timeout AF_DATA_TOUT [s]
 * @param lost_timeout AF_LOST_T [s]
 * @return true in the cycle the mode became active
 */
bool update_state(StateMachine &sm, bool mode_active, uint64_t now, uint64_t last_valid, uint64_t last_no_target,
		  float data_timeout, float lost_timeout);

/** Seconds since the last valid sample, counted from the entry time if that is later; NaN in PASIF without any valid sample. */
float time_since_valid(const StateMachine &sm, uint64_t now, uint64_t last_valid);

/** Seconds counted towards AF_LOST_T (0 in PASIF and TAKIP, and before the countdown starts). */
float lost_time(const StateMachine &sm, uint64_t now);

} // namespace AutoFollowGuidance
