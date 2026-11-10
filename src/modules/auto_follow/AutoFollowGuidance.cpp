/****************************************************************************
 *
 *   Copyright (c) 2026 PX4 Development Team. All rights reserved.
 *   Copyright (c) 2026 Pamukkale Elektrik-Elektronik Mühendisliği tez ekibi.
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

#include "AutoFollowGuidance.hpp"

#include <float.h>
#include <math.h>
#include <string.h>

#include <mathlib/mathlib.h>
#include <px4_platform_common/defines.h>

using matrix::Vector2f;
using matrix::Vector3f;

namespace AutoFollowGuidance
{

uint8_t check_input(const char *name, const float *data, uint64_t arrival, uint64_t now, bool has_previous_seq,
		    float previous_seq, float norm_tol, float data_timeout, bool position_valid)
{
	// Conditions are written as !(pass) so that NaN never passes.

	// 1. debug_array is shared with other senders (comparison includes the terminating NUL)
	if (strncmp(name, INPUT_NAME, sizeof(INPUT_NAME)) != 0) {
		return auto_follow_status_s::CHECK_NAME;
	}

	// 2.
	for (int i = 0; i < INPUT_SIZE; i++) {
		if (!PX4_ISFINITE(data[i])) {
			return auto_follow_status_s::CHECK_NONFINITE;
		}
	}

	// 3. LOS must be a unit vector
	const Vector3f los(data[INPUT_LOS_X], data[INPUT_LOS_Y], data[INPUT_LOS_Z]);

	if (!(fabsf(los.norm() - 1.f) <= norm_tol)) {
		return auto_follow_status_s::CHECK_NORM;
	}

	// 4. repeated or older message (float carries integers exactly up to 2^24)
	if (has_previous_seq && !(data[INPUT_SEQ] > previous_seq)) {
		return auto_follow_status_s::CHECK_SEQ;
	}

	// 5. real age = time since arrival on the FC + age at sending
	const float since_arrival = (now > arrival) ? (now - arrival) * 1e-6f : 0.f; // [s]
	const float age = since_arrival + data[INPUT_AGE] * 1e-3f; // [s]

	if (!(age < data_timeout)) {
		return auto_follow_status_s::CHECK_AGE;
	}

	// 6. not corrupt data, starts KAYIP_BEKLE
	if (fabsf(data[INPUT_TARGET] - 1.f) > FLT_EPSILON) {
		return auto_follow_status_s::CHECK_NO_TARGET;
	}

	// 7.
	if (!position_valid) {
		return auto_follow_status_s::CHECK_POSITION;
	}

	return auto_follow_status_s::CHECK_OK;
}

uint8_t compute_geometry(const matrix::Quatf &q, const Vector3f &los_frd, const Vector2f &drone_xy,
			 float drone_z, float tgt_hgt, float gnd_ofs, float min_depression, float max_range, Geometry &out)
{
	out.height_diff = NAN;
	out.range = NAN;
	out.target_xy = Vector2f(NAN, NAN);

	// Normalized so that asin() gives the angle (length within AF_NORM_TOL of 1)
	out.los_ned = q.rotateVector(los_frd.normalized());
	out.depression = asinf(math::constrain(out.los_ned(2), -1.f, 1.f));

	// 8. shallow look angles amplify angle errors into large range errors
	if (!(out.depression >= min_depression)) {
		return auto_follow_status_s::CHECK_DEPRESSION;
	}

	// Flat ground at the takeoff level (EKF origin), looked-at point AF_TGT_HGT above it
	out.height_diff = -drone_z - gnd_ofs - tgt_hgt;

	// d = h / tan(depression) = h * |LOS_NED_xy| / LOS_NED_z, LOS_NED_z > 0 after check 8
	const Vector2f los_ned_xy(out.los_ned(0), out.los_ned(1));
	const float horizontal = los_ned_xy.norm();
	out.range = out.height_diff * horizontal / out.los_ned(2);

	// 9. range > 0 also guarantees a horizontal LOS direction
	if (!(out.height_diff > 0.f && out.range > 0.f && out.range <= max_range)) {
		return auto_follow_status_s::CHECK_RANGE;
	}

	out.target_xy = drone_xy + los_ned_xy * (out.range / horizontal);
	return auto_follow_status_s::CHECK_OK;
}

void compute_guidance(const Vector2f &target_est, const Vector2f &target_vel, const Vector2f &drone_xy,
		      float height_diff, float track_angle, float k_dist, float k_ff, float yaw_min_range, float last_yaw, Guidance &out)
{
	const Vector2f to_target = target_est - drone_xy;
	out.range_est = to_target.norm();
	out.range_desired = height_diff / tanf(track_angle);

	// Positive range error moves towards the target, negative away from it
	out.vel_law = target_vel * k_ff + to_target.unit_or_zero() * (k_dist * (out.range_est - out.range_desired));

	// The direction is undefined when the target is (almost) below the drone
	out.yaw_frozen = !(out.range_est >= yaw_min_range);
	out.yaw = out.yaw_frozen ? last_yaw : atan2f(to_target(1), to_target(0));
}

Vector2f constrain_length(const Vector2f &v, float max_length)
{
	const float length = v.norm();

	if (length > max_length) {
		return v * (max_length / length);
	}

	return v;
}

Vector2f limit_change(const Vector2f &previous, const Vector2f &desired, float max_change)
{
	const Vector2f change = desired - previous;
	const float length = change.norm();

	if (length > max_change) {
		return previous + change * (max_change / length);
	}

	return desired;
}

bool update_state(StateMachine &sm, bool mode_active, uint64_t now, uint64_t last_valid, uint64_t last_no_target,
		  float data_timeout, float lost_timeout)
{
	if (!mode_active) {
		sm.state = auto_follow_status_s::STATE_PASIF;
		return false;
	}

	const uint64_t data_timeout_us = static_cast<uint64_t>(data_timeout * 1e6f);
	const uint64_t lost_timeout_us = static_cast<uint64_t>(lost_timeout * 1e6f);
	const bool entered = (sm.state == auto_follow_status_s::STATE_PASIF);

	if (entered) {
		sm.entry_time = now;
	}

	// Without a target at entry the timeout is counted from the entry (Hold at entry + data_timeout + lost_timeout)
	const uint64_t reference = math::max(last_valid, sm.entry_time);
	const bool target_valid = (last_valid > last_no_target) && (now < last_valid + data_timeout_us);

	switch (sm.state) {
	case auto_follow_status_s::STATE_PASIF:
		if (target_valid) {
			sm.state = auto_follow_status_s::STATE_TAKIP;

		} else {
			sm.state = auto_follow_status_s::STATE_KAYIP_BEKLE;
			sm.lost_start = reference + data_timeout_us;
		}

		break;

	case auto_follow_status_s::STATE_TAKIP:
		if (last_no_target > last_valid) {
			// companion computer reports no target: no need to wait for the timeout
			sm.state = auto_follow_status_s::STATE_KAYIP_BEKLE;
			sm.lost_start = last_no_target;

		} else if (now >= reference + data_timeout_us) {
			sm.state = auto_follow_status_s::STATE_KAYIP_BEKLE;
			sm.lost_start = reference + data_timeout_us;
		}

		break;

	case auto_follow_status_s::STATE_KAYIP_BEKLE:
		if (target_valid) {
			sm.state = auto_follow_status_s::STATE_TAKIP;

		} else if (now >= sm.lost_start + lost_timeout_us) {
			sm.state = auto_follow_status_s::STATE_HOLD_ISTENDI;
		}

		break;

	default:
		// HOLD_ISTENDI: no automatic return to tracking
		break;
	}

	return entered;
}

float time_since_valid(const StateMachine &sm, uint64_t now, uint64_t last_valid)
{
	uint64_t reference = last_valid;

	if (sm.state != auto_follow_status_s::STATE_PASIF) {
		reference = math::max(last_valid, sm.entry_time);

	} else if (last_valid == 0) {
		return NAN;
	}

	return (now > reference) ? (now - reference) * 1e-6f : 0.f;
}

float lost_time(const StateMachine &sm, uint64_t now)
{
	if ((sm.state == auto_follow_status_s::STATE_KAYIP_BEKLE || sm.state == auto_follow_status_s::STATE_HOLD_ISTENDI)
	    && now > sm.lost_start) {
		return (now - sm.lost_start) * 1e-6f;
	}

	return 0.f;
}

} // namespace AutoFollowGuidance
