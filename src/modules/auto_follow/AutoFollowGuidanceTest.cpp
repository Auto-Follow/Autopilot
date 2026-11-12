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

/**
 * @file AutoFollowGuidanceTest.cpp
 *
 * Short unit test of the AUTO FOLLOW pure computations with the numerical examples of the spec:
 * geometry, velocity law, velocity limit, acceleration limit, yaw rate limit, corrupt input, the target loss timeouts,
 * the Hold request retries and the resets after AF_DATA_TOUT without input (sequence number memory, filter).
 */

#include <string.h>

#include <gtest/gtest.h>

#include <AlphaBetaFilter.hpp>
#include <AutoFollowGuidance.hpp>
#include <px4_platform_common/defines.h>

using namespace matrix;
using namespace AutoFollowGuidance;

namespace
{

// Spec example: drone 10 m above the takeoff point, AF_TGT_HGT 1.0, AF_GND_OFS 0, default AF_MIN_DEP / AF_MAX_RNG
constexpr float DRONE_Z = -10.f;
constexpr float TGT_HGT = 1.f;
constexpr float GND_OFS = 0.f;
constexpr float MIN_DEPRESSION = 10.f * M_DEG_TO_RAD_F;
constexpr float MAX_RANGE = 40.f;

// Default AF_TRK_ANG, AF_K_DIST, AF_K_FF, AF_VEL_MAX, AF_ACC_MAX, AF_YAW_MIN_D, AF_YAWRATE_MAX, AF_NORM_TOL, AF_DATA_TOUT,
// AF_LOST_T
constexpr float TRACK_ANGLE = 30.f * M_DEG_TO_RAD_F;
constexpr float K_DIST = 0.5f;
constexpr float K_FF = 0.f;
constexpr float VEL_MAX = 2.f;
constexpr float ACC_MAX = 3.f;
constexpr float YAW_MIN_RANGE = 1.f;
constexpr float YAWRATE_MAX = 60.f * M_DEG_TO_RAD_F;
constexpr float NORM_TOL = 0.1f;
constexpr float DATA_TIMEOUT = 0.5f;
constexpr float LOST_TIMEOUT = 1.f;

constexpr uint64_t S = 1000000; // [us] one second

// Level drone with the nose to the north, at the local origin
Geometry level_north_geometry(const Vector3f &los_frd)
{
	Geometry geometry{};
	EXPECT_EQ(compute_geometry(Quatf(), los_frd, Vector2f(0.f, 0.f), DRONE_Z, TGT_HGT, GND_OFS, MIN_DEPRESSION, MAX_RANGE,
				   geometry), auto_follow_status_s::CHECK_OK);
	return geometry;
}

// Velocity law with the measured target as the estimate (filter converged on a standing target)
Guidance guidance_for(const Geometry &geometry)
{
	Guidance guidance{};
	compute_guidance(geometry.target_xy, Vector2f(0.f, 0.f), Vector2f(0.f, 0.f), geometry.height_diff, TRACK_ANGLE, K_DIST,
			 K_FF, YAW_MIN_RANGE, 0.f, guidance);
	return guidance;
}

uint8_t check(const char *name, const float *data, bool has_previous_seq = true, float previous_seq = 4.f)
{
	const uint64_t now = 100 * S;
	const uint64_t arrival = now - 10000; // arrived 10 ms ago
	return check_input(name, data, arrival, now, has_previous_seq, previous_seq, NORM_TOL, DATA_TIMEOUT, true);
}

} // namespace

TEST(AutoFollowGuidanceTest, GeometrySpecExample)
{
	// GIVEN: spec section 3 example, LOS (0.8, 0, 0.6) with the nose to the north
	const Geometry geometry = level_north_geometry(Vector3f(0.8f, 0.f, 0.6f));

	// THEN: depression 36.9 deg, h = 9.0 m, d = 12.0 m, target 12 m to the north
	EXPECT_NEAR(geometry.depression, 36.87f * M_DEG_TO_RAD_F, 1e-3f);
	EXPECT_NEAR(geometry.height_diff, 9.f, 1e-4f);
	EXPECT_NEAR(geometry.range, 12.f, 1e-3f);
	EXPECT_NEAR(geometry.target_xy(0), 12.f, 1e-3f);
	EXPECT_NEAR(geometry.target_xy(1), 0.f, 1e-3f);

	// WHEN: the nose points to the east instead, THEN: the same target lies 12 m to the east
	Geometry east{};
	EXPECT_EQ(compute_geometry(Quatf(Eulerf(0.f, 0.f, M_PI_2_F)), Vector3f(0.8f, 0.f, 0.6f), Vector2f(0.f, 0.f), DRONE_Z,
				   TGT_HGT, GND_OFS, MIN_DEPRESSION, MAX_RANGE, east), auto_follow_status_s::CHECK_OK);
	EXPECT_NEAR(east.target_xy(0), 0.f, 1e-3f);
	EXPECT_NEAR(east.target_xy(1), 12.f, 1e-3f);
}

TEST(AutoFollowGuidanceTest, LawSpecExampleMovesAway)
{
	// GIVEN: spec section 5 example, target at 12.0 m, AF_TRK_ANG 30 deg
	const Guidance guidance = guidance_for(level_north_geometry(Vector3f(0.8f, 0.f, 0.6f)));

	// THEN: desired range 15.6 m, law -1.8 m/s (away from the target, to the south), yaw to the target
	EXPECT_NEAR(guidance.range_est, 12.f, 1e-3f);
	EXPECT_NEAR(guidance.range_desired, 15.59f, 0.01f);
	EXPECT_NEAR(guidance.vel_law(0), -1.8f, 0.01f);
	EXPECT_NEAR(guidance.vel_law(1), 0.f, 1e-4f);
	EXPECT_NEAR(guidance.yaw, 0.f, 1e-4f);
	EXPECT_FALSE(guidance.yaw_frozen);

	// AND: below AF_VEL_MAX, so not clipped
	EXPECT_EQ(constrain_length(guidance.vel_law, VEL_MAX), guidance.vel_law);
}

TEST(AutoFollowGuidanceTest, LawClippedToVelMaxS1a)
{
	// GIVEN: S1a geometry, LOS (0.951, 0, 0.309): depression 18 deg, target 27.7 m away
	const Geometry geometry = level_north_geometry(Vector3f(0.951f, 0.f, 0.309f));
	EXPECT_NEAR(geometry.range, 27.7f, 0.05f);

	// WHEN: the law asks for about +6.0 m/s towards the target
	const Guidance guidance = guidance_for(geometry);
	EXPECT_NEAR(guidance.vel_law(0), 6.f, 0.1f);

	// THEN: the output is clipped to AF_VEL_MAX = 2 m/s in the same direction
	const Vector2f vel = constrain_length(guidance.vel_law, VEL_MAX);
	EXPECT_NEAR(vel.norm(), VEL_MAX, 1e-4f);
	EXPECT_NEAR(vel(0), VEL_MAX, 1e-4f);
	EXPECT_NEAR(vel(1), 0.f, 1e-4f);
}

TEST(AutoFollowGuidanceTest, AccelerationLimitPerCycle)
{
	// GIVEN: one 50 Hz cycle, at most AF_ACC_MAX * dt change of the velocity command
	const float max_change = ACC_MAX * 0.02f;

	// WHEN: the command jumps from hover to 2 m/s north, THEN: it moves only max_change towards it
	const Vector2f step = limit_change(Vector2f(0.f, 0.f), Vector2f(VEL_MAX, 0.f), max_change);
	EXPECT_NEAR(step(0), max_change, 1e-6f);
	EXPECT_NEAR(step(1), 0.f, 1e-6f);

	// WHEN: diagonal jump from 1 m/s north, THEN: the length of the change is limited, not each axis
	const Vector2f previous(1.f, 0.f);
	const Vector2f diagonal = limit_change(previous, Vector2f(-1.f, 1.f), max_change);
	EXPECT_NEAR((diagonal - previous).norm(), max_change, 1e-6f);

	// WHEN: the change is small, THEN: the command is reached
	const Vector2f small(1.01f, 0.01f);
	EXPECT_EQ(limit_change(previous, small, max_change), small);
}

TEST(AutoFollowGuidanceTest, CorruptInputRejected)
{
	// GIVEN: a valid AF_LOS sample: LOS (0.8, 0, 0.6), age 50 ms, sequence 5 after 4, target visible
	const float valid[INPUT_SIZE] {0.8f, 0.f, 0.6f, 50.f, 5.f, 1.f};
	EXPECT_EQ(check("AF_LOS", valid), auto_follow_status_s::CHECK_OK);

	// NaN / Inf in any value
	float data[INPUT_SIZE];
	memcpy(data, valid, sizeof(data));
	data[INPUT_LOS_X] = NAN;
	EXPECT_EQ(check("AF_LOS", data), auto_follow_status_s::CHECK_NONFINITE);
	memcpy(data, valid, sizeof(data));
	data[INPUT_AGE] = INFINITY;
	EXPECT_EQ(check("AF_LOS", data), auto_follow_status_s::CHECK_NONFINITE);

	// LOS length 0.71, outside AF_NORM_TOL
	memcpy(data, valid, sizeof(data));
	data[INPUT_LOS_X] = 0.5f;
	data[INPUT_LOS_Z] = 0.5f;
	EXPECT_EQ(check("AF_LOS", data), auto_follow_status_s::CHECK_NORM);

	// repeated and older sequence number
	memcpy(data, valid, sizeof(data));
	data[INPUT_SEQ] = 4.f;
	EXPECT_EQ(check("AF_LOS", data), auto_follow_status_s::CHECK_SEQ);
	data[INPUT_SEQ] = 3.f;
	EXPECT_EQ(check("AF_LOS", data), auto_follow_status_s::CHECK_SEQ);

	// other debug_array sender (also a longer name with the same start)
	EXPECT_EQ(check("OTHER", valid), auto_follow_status_s::CHECK_NAME);
	EXPECT_EQ(check("AF_LOS2", valid), auto_follow_status_s::CHECK_NAME);
}

TEST(AutoFollowGuidanceTest, DataTimeoutThenHold)
{
	// GIVEN: tracking, the last valid sample arrived at t1 (after the mode entry at t0)
	StateMachine sm{};
	const uint64_t t0 = 10 * S;
	const uint64_t t1 = t0 + S;
	update_state(sm, true, t0, t0, 0, DATA_TIMEOUT, LOST_TIMEOUT);
	update_state(sm, true, t1, t1, 0, DATA_TIMEOUT, LOST_TIMEOUT);
	EXPECT_EQ(sm.state, auto_follow_status_s::STATE_TAKIP);

	// WHEN: no more valid samples
	// THEN: still tracking just before AF_DATA_TOUT (0.5 s), KAYIP_BEKLE at 0.5 s
	update_state(sm, true, t1 + S / 2 - 20000, t1, 0, DATA_TIMEOUT, LOST_TIMEOUT);
	EXPECT_EQ(sm.state, auto_follow_status_s::STATE_TAKIP);
	update_state(sm, true, t1 + S / 2, t1, 0, DATA_TIMEOUT, LOST_TIMEOUT);
	EXPECT_EQ(sm.state, auto_follow_status_s::STATE_KAYIP_BEKLE);
	EXPECT_NEAR(time_since_valid(sm, t1 + S / 2, t1), 0.5f, 1e-6f);

	// THEN: still waiting just before AF_LOST_T (+1.0 s), HOLD_ISTENDI at +1.0 s (1.5 s after the last valid sample)
	update_state(sm, true, t1 + 3 * S / 2 - 20000, t1, 0, DATA_TIMEOUT, LOST_TIMEOUT);
	EXPECT_EQ(sm.state, auto_follow_status_s::STATE_KAYIP_BEKLE);
	update_state(sm, true, t1 + 3 * S / 2, t1, 0, DATA_TIMEOUT, LOST_TIMEOUT);
	EXPECT_EQ(sm.state, auto_follow_status_s::STATE_HOLD_ISTENDI);
	EXPECT_NEAR(lost_time(sm, t1 + 3 * S / 2), 1.f, 1e-6f);
}

TEST(AutoFollowGuidanceTest, NoTargetImmediatelyLost)
{
	// GIVEN: a sample with target flag 0 is not corrupt data but CHECK_NO_TARGET
	const float no_target[INPUT_SIZE] {0.8f, 0.f, 0.6f, 50.f, 5.f, 0.f};
	EXPECT_EQ(check("AF_LOS", no_target), auto_follow_status_s::CHECK_NO_TARGET);

	// GIVEN: tracking with the last valid sample at t0
	StateMachine sm{};
	const uint64_t t0 = 10 * S;
	update_state(sm, true, t0, t0, 0, DATA_TIMEOUT, LOST_TIMEOUT);
	EXPECT_EQ(sm.state, auto_follow_status_s::STATE_TAKIP);

	// WHEN: the "no target" sample arrives 0.1 s later, THEN: KAYIP_BEKLE in the next cycle, without waiting 0.5 s
	const uint64_t t_no_target = t0 + S / 10;
	update_state(sm, true, t_no_target + 20000, t0, t_no_target, DATA_TIMEOUT, LOST_TIMEOUT);
	EXPECT_EQ(sm.state, auto_follow_status_s::STATE_KAYIP_BEKLE);

	// AND: Hold is requested AF_LOST_T (1.0 s) after the "no target" sample
	update_state(sm, true, t_no_target + S - 20000, t0, t_no_target, DATA_TIMEOUT, LOST_TIMEOUT);
	EXPECT_EQ(sm.state, auto_follow_status_s::STATE_KAYIP_BEKLE);
	update_state(sm, true, t_no_target + S, t0, t_no_target, DATA_TIMEOUT, LOST_TIMEOUT);
	EXPECT_EQ(sm.state, auto_follow_status_s::STATE_HOLD_ISTENDI);
}

TEST(AutoFollowGuidanceTest, DisarmedStaysInLostWait)
{
	// GIVEN: the mode active while disarmed (bench test), tracking with the last valid sample at t0
	StateMachine sm{};
	const uint64_t t0 = 10 * S;
	update_state(sm, true, t0, t0, 0, DATA_TIMEOUT, LOST_TIMEOUT, false);
	EXPECT_EQ(sm.state, auto_follow_status_s::STATE_TAKIP);

	// WHEN: no data for much longer than AF_DATA_TOUT + AF_LOST_T, THEN: KAYIP_BEKLE, no HOLD_ISTENDI
	update_state(sm, true, t0 + S / 2, t0, 0, DATA_TIMEOUT, LOST_TIMEOUT, false);
	EXPECT_EQ(sm.state, auto_follow_status_s::STATE_KAYIP_BEKLE);
	update_state(sm, true, t0 + 10 * S, t0, 0, DATA_TIMEOUT, LOST_TIMEOUT, false);
	EXPECT_EQ(sm.state, auto_follow_status_s::STATE_KAYIP_BEKLE);

	// WHEN: a valid sample arrives again, THEN: back to TAKIP
	const uint64_t t1 = t0 + 10 * S + S / 10;
	update_state(sm, true, t1, t1, 0, DATA_TIMEOUT, LOST_TIMEOUT, false);
	EXPECT_EQ(sm.state, auto_follow_status_s::STATE_TAKIP);
}

TEST(AutoFollowGuidanceTest, RestartedSenderAcceptedAfterTimeout)
{
	// GIVEN: sequence 1000 arrived at t0 (last AF_LOS sample), then the companion computer restarts and counts from 1
	const uint64_t t0 = 10 * S;
	const float restarted[INPUT_SIZE] {0.8f, 0.f, 0.6f, 50.f, 1.f, 1.f};

	// WHEN: sequence 1 arrives just before AF_DATA_TOUT (0.5 s), THEN: still compared with 1000 and rejected
	uint64_t now = t0 + S / 2 - 20000;
	bool has_previous_seq = keep_previous_seq(true, t0, now, DATA_TIMEOUT);
	EXPECT_EQ(check_input("AF_LOS", restarted, now, now, has_previous_seq, 1000.f, NORM_TOL, DATA_TIMEOUT, true),
		  auto_follow_status_s::CHECK_SEQ);

	// WHEN: AF_DATA_TOUT without any AF_LOS sample, THEN: 1000 is forgotten and sequence 1 is accepted
	now = t0 + S / 2;
	has_previous_seq = keep_previous_seq(true, t0, now, DATA_TIMEOUT);
	EXPECT_FALSE(has_previous_seq);
	EXPECT_EQ(check_input("AF_LOS", restarted, now, now, has_previous_seq, 1000.f, NORM_TOL, DATA_TIMEOUT, true),
		  auto_follow_status_s::CHECK_OK);
}

TEST(AutoFollowGuidanceTest, FilterRestartsAfterLongGap)
{
	// GIVEN: the filter estimates a target moving 1 m/s north, last valid sample at t0 (mode not active)
	AlphaBetaFilter filter;
	filter.correct(Vector2f(0.f, 0.f), 0.f, 0.5f, 0.17f);
	filter.correct(Vector2f(0.1f, 0.f), 0.1f, 0.5f, 0.17f);
	EXPECT_GT(filter.velocity()(0), 0.f);
	StateMachine sm{};
	const uint64_t t0 = 10 * S;

	// THEN: the estimate is still used just before AF_DATA_TOUT, it is stale from AF_DATA_TOUT on (module resets the filter)
	EXPECT_LT(time_since_valid(sm, t0 + S / 2 - 20000, t0), DATA_TIMEOUT);
	EXPECT_FALSE(time_since_valid(sm, t0 + S / 2, t0) < DATA_TIMEOUT);
	filter.reset();

	// WHEN: the next accepted measurement arrives, THEN: position = measurement, velocity 0 (no old velocity carried over)
	filter.predict(10.f);
	filter.correct(Vector2f(5.f, 3.f), 10.f, 0.5f, 0.17f);
	EXPECT_EQ(filter.position(), Vector2f(5.f, 3.f));
	EXPECT_EQ(filter.velocity(), Vector2f(0.f, 0.f));
}

TEST(AutoFollowGuidanceTest, FrozenSenderNeverAccepted)
{
	// GIVEN: a frozen companion computer repeats its last sample (sequence 5) at 20 Hz for 3 s
	// (bookkeeping as in AutoFollow::process_input: the AF_LOS name refreshes the memory, the sequence check sets it)
	const float frozen[INPUT_SIZE] {0.8f, 0.f, 0.6f, 50.f, 5.f, 1.f};
	const uint64_t t0 = 10 * S;
	bool has_previous_seq = false;
	float previous_seq = 0.f;
	uint64_t last_name_pass = 0;
	int accepted = 0;
	uint64_t now = t0;

	for (; now < t0 + 3 * S; now += S / 20) {
		has_previous_seq = keep_previous_seq(has_previous_seq, last_name_pass, now, DATA_TIMEOUT);
		const uint8_t result = check_input("AF_LOS", frozen, now, now, has_previous_seq, previous_seq, NORM_TOL, DATA_TIMEOUT,
						   true);

		if (result != auto_follow_status_s::CHECK_NAME) {
			last_name_pass = now;
		}

		if (sequence_passed(result)) {
			has_previous_seq = true;
			previous_seq = frozen[INPUT_SEQ];
		}

		accepted += (result == auto_follow_status_s::CHECK_OK) ? 1 : 0;
	}

	// THEN: only the first sample is accepted, every repetition is CHECK_SEQ (no valid data: KAYIP_BEKLE, then Hold)
	EXPECT_EQ(accepted, 1);
	EXPECT_TRUE(keep_previous_seq(has_previous_seq, last_name_pass, now, DATA_TIMEOUT));

	// WHEN: the sender is silent for AF_DATA_TOUT (0.5 s) and restarts with sequence 1, THEN: sequence 1 is accepted
	const float restarted[INPUT_SIZE] {0.8f, 0.f, 0.6f, 50.f, 1.f, 1.f};
	now = last_name_pass + S / 2;
	has_previous_seq = keep_previous_seq(has_previous_seq, last_name_pass, now, DATA_TIMEOUT);
	EXPECT_FALSE(has_previous_seq);
	EXPECT_EQ(check_input("AF_LOS", restarted, now, now, has_previous_seq, previous_seq, NORM_TOL, DATA_TIMEOUT, true),
		  auto_follow_status_s::CHECK_OK);
}

TEST(AutoFollowGuidanceTest, YawRateLimitPerCycle)
{
	// GIVEN: one 50 Hz cycle, at most AF_YAWRATE_MAX (60 deg/s) * dt = 1.2 deg change of the yaw setpoint
	const float max_change = YAWRATE_MAX * 0.02f;

	// WHEN: the target is 90 deg to the right, THEN: the yaw setpoint turns right by 1.2 deg only
	EXPECT_NEAR(limit_yaw_change(0.f, M_PI_2_F, max_change), max_change, 1e-6f);

	// WHEN: the target is to the left, THEN: it turns left
	EXPECT_NEAR(limit_yaw_change(0.f, -M_PI_2_F, max_change), -max_change, 1e-6f);

	// WHEN: from 179.5 deg to -179 deg, THEN: the shorter way across +-180 deg, wrapped (-179.3 deg)
	const float across = limit_yaw_change(179.5f * M_DEG_TO_RAD_F, -179.f * M_DEG_TO_RAD_F, max_change);
	EXPECT_NEAR(across, -179.3f * M_DEG_TO_RAD_F, 1e-4f);

	// WHEN: the change is small, THEN: the yaw towards the target is reached
	EXPECT_NEAR(limit_yaw_change(0.f, 0.01f, max_change), 0.01f, 1e-6f);

	// WHEN: 1 s of 50 Hz cycles, THEN: 60 deg
	float yaw = 0.f;

	for (int i = 0; i < 50; i++) {
		yaw = limit_yaw_change(yaw, 170.f * M_DEG_TO_RAD_F, max_change);
	}

	EXPECT_NEAR(yaw, 60.f * M_DEG_TO_RAD_F, 1e-4f);

	// WHEN: no previous yaw setpoint, THEN: no reference to limit from, the yaw towards the target is used
	EXPECT_NEAR(limit_yaw_change(NAN, 1.f, max_change), 1.f, 1e-6f);
}

TEST(AutoFollowGuidanceTest, HoldRequestRetries)
{
	// GIVEN: HOLD_ISTENDI is entered at t0, retries 1 s apart, at most 3 requests (tasks 5.2)
	const uint64_t t0 = 10 * S;
	const uint8_t max_requests = 3;

	// THEN: the first request is sent at once
	EXPECT_EQ(hold_action(0, false, false, false, t0, 0, S, max_requests), HoldAction::REQUEST);

	// WHEN: commander rejects it, THEN: no new request before 1 s, a new one at 1 s
	EXPECT_EQ(hold_action(1, true, false, false, t0 + S - 20000, t0, S, max_requests), HoldAction::NONE);
	EXPECT_EQ(hold_action(1, true, false, false, t0 + S, t0, S, max_requests), HoldAction::REQUEST);

	// WHEN: the second request is not answered at all, THEN: it is repeated at 1 s as well
	EXPECT_EQ(hold_action(2, false, false, false, t0 + 2 * S, t0 + S, S, max_requests), HoldAction::REQUEST);

	// WHEN: the third request is rejected, THEN: no fourth request, the failure is reported once
	EXPECT_EQ(hold_action(3, true, false, false, t0 + 2 * S + 20000, t0 + 2 * S, S, max_requests), HoldAction::REPORT_FAILURE);
	EXPECT_EQ(hold_action(3, true, false, true, t0 + 10 * S, t0 + 2 * S, S, max_requests), HoldAction::NONE);

	// WHEN: a request is accepted, THEN: nothing more (commander switches to Hold, the mode becomes PASIF)
	EXPECT_EQ(hold_action(1, true, true, false, t0 + 5 * S, t0, S, max_requests), HoldAction::NONE);
}
