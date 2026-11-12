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
 * @file AutoFollow.hpp
 *
 * AUTO FOLLOW external flight mode: registers itself with commander, answers the arming checks,
 * validates the companion computer line of sight (debug_array "AF_LOS"), estimates the target position
 * and publishes trajectory_setpoint while the mode is active. On target loss it holds position and then requests Hold
 * from commander. auto_follow_status is published every cycle.
 */

#pragma once

#include <drivers/drv_hrt.h>
#include <lib/perf/perf_counter.h>
#include <px4_platform_common/defines.h>
#include <px4_platform_common/module.h>
#include <px4_platform_common/module_params.h>
#include <px4_platform_common/px4_work_queue/ScheduledWorkItem.hpp>
#include <systemlib/mavlink_log.h>

#include "AlphaBetaFilter.hpp"
#include "AutoFollowGuidance.hpp"

#include <uORB/Publication.hpp>
#include <uORB/Subscription.hpp>
#include <uORB/SubscriptionInterval.hpp>
#include <uORB/topics/arming_check_reply.h>
#include <uORB/topics/arming_check_request.h>
#include <uORB/topics/auto_follow_status.h>
#include <uORB/topics/debug_array.h>
#include <uORB/topics/parameter_update.h>
#include <uORB/topics/register_ext_component_reply.h>
#include <uORB/topics/register_ext_component_request.h>
#include <uORB/topics/trajectory_setpoint.h>
#include <uORB/topics/unregister_ext_component.h>
#include <uORB/topics/vehicle_attitude.h>
#include <uORB/topics/vehicle_command.h>
#include <uORB/topics/vehicle_command_ack.h>
#include <uORB/topics/vehicle_control_mode.h>
#include <uORB/topics/vehicle_land_detected.h>
#include <uORB/topics/vehicle_local_position.h>
#include <uORB/topics/vehicle_status.h>

using namespace time_literals;

class AutoFollow : public ModuleBase<AutoFollow>, public ModuleParams, public px4::ScheduledWorkItem
{
public:
	AutoFollow();
	~AutoFollow() override;

	/** @see ModuleBase */
	static int task_spawn(int argc, char *argv[]);

	/** @see ModuleBase */
	static int custom_command(int argc, char *argv[]);

	/** @see ModuleBase */
	static int print_usage(const char *reason = nullptr);

	/** @see ModuleBase::print_status() */
	int print_status() override;

	bool init();

private:
	void Run() override;

	void parameters_update(bool force);

	void register_mode();
	void check_mode_registration();
	void configure_control_mode();
	void unregister_mode();
	bool unregistration_done();
	void reply_to_arming_check(uint8_t request_id);

	void update_vehicle_state();
	void process_input(hrt_abstime now);
	void count_check_result(uint8_t check_result, hrt_abstime now);
	void enter_mode();
	void publish_setpoint(hrt_abstime now, float dt, bool lost_state_entered);
	void update_hold_request(hrt_abstime now, bool hold_state_entered);
	void publish_hold_request(hrt_abstime now);
	void clear_guidance_output();
	void publish_status(hrt_abstime now);

	bool registered() const { return _mode_id >= 0 && _arming_check_id >= 0; }

	// Mode name shown in QGC / RC. Must stay fixed: commander keeps the slot by its hash (COM_MODEx_HASH).
	static constexpr const char *MODE_NAME = "AUTO FOLLOW";

	// Arbitrary id to match the registration reply with our request.
	static constexpr uint64_t REGISTRATION_REQUEST_ID = 0xAF15;

	// Fixed 50 Hz cycle, so that data loss is noticed even when no input arrives.
	static constexpr hrt_abstime CYCLE_INTERVAL = 20_ms;

	// Longest wait on stop for commander to drop the mode (vehicle_status is published at least at 2 Hz).
	static constexpr hrt_abstime UNREGISTER_TIMEOUT = 1_s;

	// Shortest interval between two console warnings about rejected input samples.
	static constexpr hrt_abstime REJECT_WARN_INTERVAL = 1_s;

	// Hold request in HOLD_ISTENDI: repeated after this time if rejected (or not answered), at most HOLD_REQUEST_MAX requests.
	static constexpr hrt_abstime HOLD_RETRY_INTERVAL = 1_s;
	static constexpr uint8_t HOLD_REQUEST_MAX = 3;

	// Subscriptions
	uORB::SubscriptionInterval _parameter_update_sub{ORB_ID(parameter_update), 1_s};
	uORB::Subscription _register_ext_component_reply_sub{ORB_ID(register_ext_component_reply)};
	uORB::Subscription _arming_check_request_sub{ORB_ID(arming_check_request)};
	uORB::Subscription _vehicle_status_sub{ORB_ID(vehicle_status)};
	uORB::Subscription _vehicle_land_detected_sub{ORB_ID(vehicle_land_detected)};
	uORB::Subscription _vehicle_local_position_sub{ORB_ID(vehicle_local_position)};
	uORB::Subscription _vehicle_attitude_sub{ORB_ID(vehicle_attitude)};
	uORB::Subscription _debug_array_sub{ORB_ID(debug_array)};
	uORB::Subscription _vehicle_command_ack_sub{ORB_ID(vehicle_command_ack)};

	// Publications
	uORB::Publication<register_ext_component_request_s> _register_ext_component_request_pub{ORB_ID(register_ext_component_request)};
	uORB::Publication<unregister_ext_component_s> _unregister_ext_component_pub{ORB_ID(unregister_ext_component)};
	uORB::Publication<vehicle_control_mode_s> _config_control_setpoints_pub{ORB_ID(config_control_setpoints)};
	uORB::Publication<arming_check_reply_s> _arming_check_reply_pub{ORB_ID(arming_check_reply)};
	uORB::Publication<trajectory_setpoint_s> _trajectory_setpoint_pub{ORB_ID(trajectory_setpoint)};
	uORB::Publication<auto_follow_status_s> _auto_follow_status_pub{ORB_ID(auto_follow_status)};
	uORB::Publication<vehicle_command_s> _vehicle_command_pub{ORB_ID(vehicle_command)};
	orb_advert_t _mavlink_log_pub{nullptr};

	// Performance counters
	perf_counter_t _loop_perf{perf_alloc(PC_ELAPSED, MODULE_NAME": cycle")};
	perf_counter_t _loop_interval_perf{perf_alloc(PC_INTERVAL, MODULE_NAME": interval")};

	// Registration state
	bool _registration_sent{false};
	bool _registration_rejected{false};
	int8_t _mode_id{-1};          // assigned nav_state (23..30), -1 if not registered
	int8_t _arming_check_id{-1};  // arming check registration id, -1 if not registered
	hrt_abstime _unregister_time{0}; // time the unregistration was published, 0 if not yet

	// Vehicle state
	bool _mode_active{false};     // vehicle_status.nav_state == _mode_id
	bool _landed{false};          // vehicle_land_detected.landed
	bool _armed{false};           // vehicle_status.arming_state; disarmed: no Hold request (bench tests)
	uint8_t _system_id{0};        // vehicle_status.system_id, target and source of the Hold request
	uint8_t _component_id{0};     // vehicle_status.component_id (< COMPONENT_MODE_EXECUTOR_START: source "User")
	vehicle_local_position_s _local_position{};
	matrix::Quatf _attitude{0.f, 0.f, 0.f, 0.f}; // FRD to NED; zero until received, rotates to NaN (rejected)
	uint8_t _xy_reset_counter{0};
	uint8_t _z_reset_counter{0};
	uint8_t _heading_reset_counter{0};

	// Status message, also holds the raw input, counters and geometry of the last sample between cycles
	auto_follow_status_s _status{};

	// Input history
	bool _has_previous_seq{false};
	float _previous_seq{0.f};               // sequence number of the last sample that passed the sequence check
	hrt_abstime _last_name_pass{0};         // [us] time the last sample passed the name check (AF_LOS)
	hrt_abstime _last_valid{0};             // [us] arrival of the last sample that passed all checks
	hrt_abstime _last_no_target{0};         // [us] arrival of the last CHECK_NO_TARGET sample
	hrt_abstime _last_accepted_arrival{0};  // [us] arrival of the last accepted sample
	float _last_accepted_age{0.f};          // [ms] age of the last accepted sample (capture time = arrival - age)
	float _last_height_diff{NAN};           // [m] h of the last accepted sample
	hrt_abstime _last_reject_warn{0};

	// Estimation and guidance
	AlphaBetaFilter _filter;
	AutoFollowGuidance::StateMachine _state_machine;
	hrt_abstime _last_cycle{0};
	matrix::Vector2f _vel_cmd{};            // [m/s] NED x, y, state of the acceleration limit
	float _yaw_cmd{NAN};                    // [rad] last yaw setpoint
	matrix::Vector2f _hold_xy{NAN, NAN};    // [m] NED x, y held in KAYIP_BEKLE / HOLD_ISTENDI

	// Hold request (VEHICLE_CMD_SET_NAV_STATE), count in _status.hold_request_count
	hrt_abstime _hold_request_time{0};      // [us] time of the last request
	bool _hold_answered{false};             // commander answered the last request
	bool _hold_accepted{false};             // the answer was ACCEPTED
	bool _hold_failure_reported{false};     // QGC warning after the last rejected request sent

	// Angle parameters converted from [deg] to [rad]
	float _trk_ang_rad{0.f};
	float _min_dep_rad{0.f};
	float _yawrate_max_rad{0.f};            // [rad/s]

	// AF_ENABLE is only read by the boot script (rc.mc_apps), not by the module.
	DEFINE_PARAMETERS(
		(ParamFloat<px4::params::AF_TRK_ANG>) _param_af_trk_ang,      // [deg]
		(ParamFloat<px4::params::AF_K_DIST>) _param_af_k_dist,        // [1/s]
		(ParamFloat<px4::params::AF_K_FF>) _param_af_k_ff,            // [-]
		(ParamFloat<px4::params::AF_VEL_MAX>) _param_af_vel_max,      // [m/s]
		(ParamFloat<px4::params::AF_ACC_MAX>) _param_af_acc_max,      // [m/s^2]
		(ParamFloat<px4::params::AF_ALPHA>) _param_af_alpha,          // [-]
		(ParamFloat<px4::params::AF_BETA>) _param_af_beta,            // [-]
		(ParamFloat<px4::params::AF_DATA_TOUT>) _param_af_data_tout,  // [s]
		(ParamFloat<px4::params::AF_LOST_T>) _param_af_lost_t,        // [s]
		(ParamFloat<px4::params::AF_YAW_MIN_D>) _param_af_yaw_min_d,  // [m]
		(ParamFloat<px4::params::AF_YAWRATE_MAX>) _param_af_yawrate_max, // [deg/s]
		(ParamFloat<px4::params::AF_TGT_HGT>) _param_af_tgt_hgt,      // [m]
		(ParamFloat<px4::params::AF_GND_OFS>) _param_af_gnd_ofs,      // [m]
		(ParamFloat<px4::params::AF_NORM_TOL>) _param_af_norm_tol,    // [-]
		(ParamFloat<px4::params::AF_MIN_DEP>) _param_af_min_dep,      // [deg]
		(ParamFloat<px4::params::AF_MAX_RNG>) _param_af_max_rng       // [m]
	)
};
