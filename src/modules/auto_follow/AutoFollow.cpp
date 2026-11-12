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

#include "AutoFollow.hpp"

#include <float.h>
#include <inttypes.h>
#include <mathlib/mathlib.h>
#include <string.h>

using matrix::Vector2f;
using matrix::Vector3f;

// Constant names as in auto_follow_status (console output)
static const char *const STATE_NAMES[] = {"STATE_PASIF", "STATE_TAKIP", "STATE_KAYIP_BEKLE", "STATE_HOLD_ISTENDI"};
static const char *const CHECK_NAMES[] = {"CHECK_OK", "CHECK_NAME", "CHECK_NONFINITE", "CHECK_NORM", "CHECK_SEQ",
					  "CHECK_AGE", "CHECK_NO_TARGET", "CHECK_POSITION", "CHECK_DEPRESSION", "CHECK_RANGE"
					 };
static_assert(sizeof(STATE_NAMES) / sizeof(STATE_NAMES[0]) == auto_follow_status_s::STATE_HOLD_ISTENDI + 1, "state names");
static_assert(sizeof(CHECK_NAMES) / sizeof(CHECK_NAMES[0]) == auto_follow_status_s::CHECK_RANGE + 1, "check names");

AutoFollow::AutoFollow() :
	ModuleParams(nullptr),
	ScheduledWorkItem(MODULE_NAME, px4::wq_configurations::nav_and_controllers)
{
}

AutoFollow::~AutoFollow()
{
	perf_free(_loop_perf);
	perf_free(_loop_interval_perf);
}

bool AutoFollow::init()
{
	parameters_update(true);

	// NaN = not computed yet
	for (int i = 0; i < 3; i++) {
		_status.los_ned[i] = NAN;
	}

	_status.depression = NAN;
	_status.height_diff = NAN;
	_status.range_meas = NAN;
	_status.target_meas_ned[0] = NAN;
	_status.target_meas_ned[1] = NAN;
	_status.latency = NAN;
	clear_guidance_output();

	ScheduleOnInterval(CYCLE_INTERVAL);
	return true;
}

void AutoFollow::parameters_update(bool force)
{
	if (_parameter_update_sub.updated() || force) {
		parameter_update_s param_update;
		_parameter_update_sub.copy(&param_update);
		updateParams();

		// QGC shows angles in degrees, the computation uses radians
		_trk_ang_rad = math::radians(_param_af_trk_ang.get());
		_min_dep_rad = math::radians(_param_af_min_dep.get());
		_yawrate_max_rad = math::radians(_param_af_yawrate_max.get());
	}
}

void AutoFollow::register_mode()
{
	register_ext_component_request_s request{};
	request.timestamp = hrt_absolute_time();
	strncpy(request.name, MODE_NAME, sizeof(request.name) - 1);
	request.request_id = REGISTRATION_REQUEST_ID;
	request.px4_ros2_api_version = register_ext_component_request_s::LATEST_PX4_ROS2_API_VERSION;
	request.register_arming_check = true;
	request.register_mode = true;
	_register_ext_component_request_pub.publish(request);
}

void AutoFollow::check_mode_registration()
{
	register_ext_component_reply_s reply;
	int tries = register_ext_component_reply_s::ORB_QUEUE_LENGTH;

	while (_register_ext_component_reply_sub.update(&reply) && --tries >= 0) {
		if (reply.request_id != REGISTRATION_REQUEST_ID
		    || strncmp(reply.name, MODE_NAME, sizeof(reply.name)) != 0) {
			continue;
		}

		if (reply.success && reply.mode_id >= 0 && reply.arming_check_id >= 0) {
			_mode_id = reply.mode_id;
			_arming_check_id = reply.arming_check_id;
			PX4_INFO("mode '%s' registered: nav_state %d, arming check id %d", MODE_NAME, _mode_id, _arming_check_id);
			configure_control_mode();

		} else {
			// Commander rejects registrations while armed (COM_MODE_ARM_CHK = 0)
			_registration_rejected = true;
			PX4_ERR("mode '%s' registration rejected", MODE_NAME);
		}

		break;
	}
}

void AutoFollow::configure_control_mode()
{
	// Position control stays on: the mode publishes trajectory_setpoint and the PX4 controllers do the rest.
	// Auto is enabled so that moving the RC sticks hands over to Position mode (COM_RC_OVERRIDE).
	vehicle_control_mode_s config{};
	config.timestamp = hrt_absolute_time();
	config.source_id = _mode_id;
	config.flag_multicopter_position_control_enabled = true;
	config.flag_control_manual_enabled = false;
	config.flag_control_auto_enabled = true;
	config.flag_control_offboard_enabled = false;
	config.flag_control_position_enabled = true;
	config.flag_control_velocity_enabled = true;
	config.flag_control_altitude_enabled = true;
	config.flag_control_climb_rate_enabled = true;
	config.flag_control_acceleration_enabled = true;
	config.flag_control_attitude_enabled = true;
	config.flag_control_rates_enabled = true;
	config.flag_control_allocation_enabled = true;
	config.flag_control_termination_enabled = true;
	_config_control_setpoints_pub.publish(config);
}

void AutoFollow::unregister_mode()
{
	unregister_ext_component_s unregister{};
	unregister.timestamp = hrt_absolute_time();
	strncpy(unregister.name, MODE_NAME, sizeof(unregister.name) - 1);
	unregister.arming_check_id = _arming_check_id;
	unregister.mode_id = _mode_id;
	unregister.mode_executor_id = -1; // no executor registered
	_unregister_ext_component_pub.publish(unregister);
}

bool AutoFollow::unregistration_done()
{
	if (!registered()) {
		return true;
	}

	// Commander only reads the unregistration while our publication is advertised. Deleting the module
	// unadvertises it (uORB PublicationBase destructor), so wait until commander has dropped the mode
	// (its bit in can_set_nav_states_mask is only set while registered).
	if (_unregister_time == 0) {
		unregister_mode();
		_unregister_time = hrt_absolute_time();
		return false;
	}

	vehicle_status_s vehicle_status;

	if (_vehicle_status_sub.update(&vehicle_status) && !(vehicle_status.can_set_nav_states_mask & (1u << _mode_id))) {
		return true;
	}

	// Not processed while armed (COM_MODE_ARM_CHK = 0); commander then flags the mode unresponsive.
	return hrt_elapsed_time(&_unregister_time) > UNREGISTER_TIMEOUT;
}

void AutoFollow::reply_to_arming_check(uint8_t request_id)
{
	arming_check_reply_s reply{};
	reply.timestamp = hrt_absolute_time();
	reply.request_id = request_id;
	reply.registration_id = _arming_check_id;
	reply.health_component_index = arming_check_reply_s::HEALTH_COMPONENT_INDEX_NONE;
	reply.num_events = 0;

	// Always true while the mode is active: false would make commander fall back to RTL, not Hold.
	// False only on the ground while not active, so that commander rejects switching into the mode when landed and armed.
	reply.can_arm_and_run = !(_landed && !_mode_active);

	reply.mode_req_angular_velocity = true;
	reply.mode_req_attitude = true;
	reply.mode_req_local_alt = true;
	reply.mode_req_local_position = true;
	reply.mode_req_global_position = false;
	reply.mode_req_home_position = false;
	reply.mode_req_mission = false;
	reply.mode_req_manual_control = false;

	// No takeoff in this mode: arming is refused while it is selected, switching into it while disarmed stays allowed.
	reply.mode_req_prevent_arming = true;

	_arming_check_reply_pub.publish(reply);
}

void AutoFollow::update_vehicle_state()
{
	if (_vehicle_local_position_sub.update(&_local_position)) {
		// An EKF position reset shifts local NED by delta_xy / delta_z. The held point is shifted with it, so the vehicle
		// stays in place (as FlightTaskManualAcceleration.cpp:106-109, MulticopterPositionControl.cpp:700-707).
		// The filter state is not valid across the reset; the next accepted measurement initializes it again.
		if (_local_position.xy_reset_counter != _xy_reset_counter) {
			_xy_reset_counter = _local_position.xy_reset_counter;
			_hold_xy += Vector2f(_local_position.delta_xy);
			_filter.reset();
		}

		if (_local_position.z_reset_counter != _z_reset_counter) {
			_z_reset_counter = _local_position.z_reset_counter;
			_status.alt_hold_z += _local_position.delta_z;
			_filter.reset();
		}

		// The held / commanded yaw is shifted with an EKF heading reset (as MulticopterPositionControl.cpp:709-711).
		// The measured target position rotates with the heading, so the filter is reset as for a position reset.
		if (_local_position.heading_reset_counter != _heading_reset_counter) {
			_heading_reset_counter = _local_position.heading_reset_counter;
			_yaw_cmd = matrix::wrap_pi(_yaw_cmd + _local_position.delta_heading);
			_filter.reset();
		}
	}

	vehicle_attitude_s attitude;

	if (_vehicle_attitude_sub.update(&attitude)) {
		_attitude = matrix::Quatf(attitude.q);
	}
}

void AutoFollow::process_input(hrt_abstime now)
{
	using namespace AutoFollowGuidance;

	debug_array_s input;

	if (!_debug_array_sub.update(&input)) {
		return;
	}

	const float *data = input.data;
	_has_previous_seq = keep_previous_seq(_has_previous_seq, _last_name_pass, now, _param_af_data_tout.get());
	uint8_t result = check_input(input.name, data, input.timestamp, now, _has_previous_seq, _previous_seq,
				     _param_af_norm_tol.get(), _param_af_data_tout.get(), _local_position.xy_valid && _local_position.z_valid);

	// Raw AF_LOS values are logged before validation; samples of other debug_array senders are only counted
	if (result != auto_follow_status_s::CHECK_NAME) {
		_last_name_pass = now;
		_status.los_timestamp = input.timestamp;
		_status.los_frd[0] = data[INPUT_LOS_X];
		_status.los_frd[1] = data[INPUT_LOS_Y];
		_status.los_frd[2] = data[INPUT_LOS_Z];
		_status.los_age = data[INPUT_AGE];
		_status.los_seq = (data[INPUT_SEQ] >= 0.f && data[INPUT_SEQ] < 4294967296.f) ? static_cast<uint32_t>(data[INPUT_SEQ]) : 0;
		_status.los_target = fabsf(data[INPUT_TARGET] - 1.f) <= FLT_EPSILON;
	}

	if (sequence_passed(result)) {
		_has_previous_seq = true;
		_previous_seq = data[INPUT_SEQ];
	}

	if (result == auto_follow_status_s::CHECK_OK) {
		// Checks 8 and 9 (attitude of the latest vehicle_attitude, no latency compensation)
		Geometry geometry;
		result = compute_geometry(_attitude, Vector3f(data[INPUT_LOS_X], data[INPUT_LOS_Y], data[INPUT_LOS_Z]),
					  Vector2f(_local_position.x, _local_position.y), _local_position.z, _param_af_tgt_hgt.get(),
					  _param_af_gnd_ofs.get(), _min_dep_rad, _param_af_max_rng.get(), geometry);

		geometry.los_ned.copyTo(_status.los_ned);
		_status.depression = geometry.depression;
		_status.height_diff = geometry.height_diff;
		_status.range_meas = geometry.range;
		geometry.target_xy.copyTo(_status.target_meas_ned);

		if (result == auto_follow_status_s::CHECK_OK) {
			// Time between the estimated capture times (arrival - age) of this and the previous accepted sample
			const float dt_measurement = (input.timestamp - _last_accepted_arrival) * 1e-6f
						     - (data[INPUT_AGE] - _last_accepted_age) * 1e-3f;
			_filter.correct(geometry.target_xy, dt_measurement, _param_af_alpha.get(), _param_af_beta.get());
			_status.filter_updated = true;

			_last_accepted_arrival = input.timestamp;
			_last_accepted_age = data[INPUT_AGE];
			_last_valid = input.timestamp;
			_last_height_diff = geometry.height_diff;
			_status.latency = (now - input.timestamp) * 1e-3f + data[INPUT_AGE];
		}
	}

	if (result == auto_follow_status_s::CHECK_NO_TARGET) {
		_last_no_target = input.timestamp;
	}

	_status.check_result = result;
	count_check_result(result, now);
}

void AutoFollow::count_check_result(uint8_t check_result, hrt_abstime now)
{
	switch (check_result) {
	case auto_follow_status_s::CHECK_OK:
		_status.accept_count++;
		return;

	case auto_follow_status_s::CHECK_NO_TARGET:
		// Not corrupt data: counted, not reported as a rejection
		_status.no_target_count++;
		return;

	case auto_follow_status_s::CHECK_NAME:
		_status.reject_name_count++;
		break;

	case auto_follow_status_s::CHECK_NONFINITE:
		_status.reject_nonfinite_count++;
		break;

	case auto_follow_status_s::CHECK_NORM:
		_status.reject_norm_count++;
		break;

	case auto_follow_status_s::CHECK_SEQ:
		_status.reject_seq_count++;
		break;

	case auto_follow_status_s::CHECK_AGE:
		_status.reject_age_count++;
		break;

	case auto_follow_status_s::CHECK_POSITION:
		_status.reject_position_count++;
		break;

	case auto_follow_status_s::CHECK_DEPRESSION:
		_status.reject_depression_count++;
		break;

	case auto_follow_status_s::CHECK_RANGE:
		_status.reject_range_count++;
		break;

	default:
		return;
	}

	// Rate limited: rejected samples can arrive at the full input rate
	if (_last_reject_warn == 0 || now >= _last_reject_warn + REJECT_WARN_INTERVAL) {
		_last_reject_warn = now;
		PX4_WARN("input sample rejected: %s", CHECK_NAMES[check_result]);
	}
}

void AutoFollow::enter_mode()
{
	// The altitude at entry is held while the mode is active
	_status.alt_hold_z = _local_position.z_valid ? _local_position.z : NAN;

	// The acceleration limit starts from the current horizontal velocity, so the velocity setpoint does not jump
	_vel_cmd = _local_position.v_xy_valid ? Vector2f(_local_position.vx, _local_position.vy) : Vector2f(0.f, 0.f);

	// Kept until the guidance has a direction (NaN: mc_pos_control keeps the current yaw)
	_yaw_cmd = _local_position.heading;
	_hold_xy = Vector2f(NAN, NAN);
}

void AutoFollow::publish_setpoint(hrt_abstime now, float dt, bool lost_state_entered)
{
	using namespace AutoFollowGuidance;

	const bool xy_valid = _local_position.xy_valid;
	const Vector2f drone_xy(_local_position.x, _local_position.y);

	// NaN = not controlled. Every axis keeps one finite value, x and y of the same kind (PositionControl::_inputValid).
	trajectory_setpoint_s setpoint{};
	setpoint.timestamp = now;

	for (int i = 0; i < 3; i++) {
		setpoint.position[i] = NAN;
		setpoint.velocity[i] = NAN;
		setpoint.acceleration[i] = NAN;
		setpoint.jerk[i] = NAN;
	}

	setpoint.yawspeed = NAN;

	if (lost_state_entered) {
		// Held position = position at the moment of the loss, taken below
		_hold_xy = Vector2f(NAN, NAN);
	}

	if (_state_machine.state == auto_follow_status_s::STATE_TAKIP && xy_valid && _filter.initialized()) {
		Guidance guidance;
		compute_guidance(_filter.position(), _filter.velocity(), drone_xy, _last_height_diff, _trk_ang_rad,
				 _param_af_k_dist.get(), _param_af_k_ff.get(), _param_af_yaw_min_d.get(), _yaw_cmd, guidance);

		// law -> AF_VEL_MAX -> AF_ACC_MAX
		_vel_cmd = limit_change(_vel_cmd, constrain_length(guidance.vel_law, _param_af_vel_max.get()),
					_param_af_acc_max.get() * dt);
		_yaw_cmd = limit_yaw_change(_yaw_cmd, guidance.yaw, _yawrate_max_rad * dt);

		guidance.vel_law.copyTo(_status.vel_cmd_law);
		_status.range_est = guidance.range_est;
		_status.range_desired = guidance.range_desired;
		_status.yaw_frozen = guidance.yaw_frozen;

	} else {
		// Hover: KAYIP_BEKLE / HOLD_ISTENDI, or no valid local position or estimate.
		// Without a valid local position the held position is meaningless: velocity 0 only, commander handles the rest.
		_vel_cmd.zero();
		_status.vel_cmd_law[0] = NAN;
		_status.vel_cmd_law[1] = NAN;
		_status.range_est = NAN;
		_status.range_desired = NAN;
		_status.yaw_frozen = false;

		if (_state_machine.state != auto_follow_status_s::STATE_TAKIP && xy_valid) {
			if (!PX4_ISFINITE(_hold_xy(0))) {
				_hold_xy = drone_xy;
			}

			setpoint.position[0] = _hold_xy(0);
			setpoint.position[1] = _hold_xy(1);
		}
	}

	setpoint.velocity[0] = _vel_cmd(0);
	setpoint.velocity[1] = _vel_cmd(1);
	setpoint.position[2] = _status.alt_hold_z;

	if (!PX4_ISFINITE(_status.alt_hold_z)) {
		// No valid altitude at entry: keep the z axis controlled
		setpoint.velocity[2] = 0.f;
	}

	setpoint.yaw = _yaw_cmd;
	_trajectory_setpoint_pub.publish(setpoint);

	_vel_cmd.copyTo(_status.vel_cmd);
	_status.yaw_cmd = _yaw_cmd;
}

void AutoFollow::update_hold_request(hrt_abstime now, bool hold_state_entered)
{
	// Answers of commander to our request (target = source of the request, Commander.cpp answer_command)
	vehicle_command_ack_s ack;
	int tries = vehicle_command_ack_s::ORB_QUEUE_LENGTH;

	while (_vehicle_command_ack_sub.update(&ack) && --tries >= 0) {
		if (ack.command == vehicle_command_s::VEHICLE_CMD_SET_NAV_STATE && ack.target_system == _system_id
		    && ack.target_component == _component_id && _hold_request_time != 0 && ack.timestamp >= _hold_request_time) {
			_hold_answered = true;
			_hold_accepted = (ack.result == vehicle_command_ack_s::VEHICLE_CMD_RESULT_ACCEPTED);
		}
	}

	if (hold_state_entered) {
		_status.hold_request_count = 0;
		_hold_answered = false;
		_hold_accepted = false;
		_hold_failure_reported = false;
	}

	if (!_mode_active || _state_machine.state != auto_follow_status_s::STATE_HOLD_ISTENDI) {
		return;
	}

	switch (AutoFollowGuidance::hold_action(_status.hold_request_count, _hold_answered, _hold_accepted, _hold_failure_reported,
						now, _hold_request_time, HOLD_RETRY_INTERVAL, HOLD_REQUEST_MAX)) {
	case AutoFollowGuidance::HoldAction::REQUEST:
		publish_hold_request(now);
		break;

	case AutoFollowGuidance::HoldAction::REPORT_FAILURE:
		// The vehicle keeps holding position in this mode; no other mode is requested, the pilot takes over
		mavlink_log_critical(&_mavlink_log_pub, "AUTO FOLLOW: Hold rejected, holding position");
		_hold_failure_reported = true;
		break;

	default:
		break;
	}
}

void AutoFollow::publish_hold_request(hrt_abstime now)
{
	// Same as a mode change by the user: source component < COMPONENT_MODE_EXECUTOR_START (Commander.cpp:1559-1562)
	vehicle_command_s command{};
	command.command = vehicle_command_s::VEHICLE_CMD_SET_NAV_STATE;
	command.param1 = vehicle_status_s::NAVIGATION_STATE_AUTO_LOITER;
	command.target_system = _system_id;
	command.target_component = _component_id;
	command.source_system = _system_id;
	command.source_component = _component_id;
	command.from_external = false;
	command.timestamp = now;
	_vehicle_command_pub.publish(command);

	_hold_request_time = now;
	_hold_answered = false;
	_hold_accepted = false;
	_status.hold_request_count++;
}

void AutoFollow::clear_guidance_output()
{
	// Guidance only runs while the mode is active
	for (int i = 0; i < 2; i++) {
		_status.vel_cmd_law[i] = NAN;
		_status.vel_cmd[i] = NAN;
	}

	_status.range_est = NAN;
	_status.range_desired = NAN;
	_status.yaw_cmd = NAN;
	_status.yaw_frozen = false;
	_status.alt_hold_z = NAN;
}

void AutoFollow::publish_status(hrt_abstime now)
{
	_status.timestamp = now;
	_status.mode_nav_state = registered() ? static_cast<uint8_t>(_mode_id) : 0;
	_status.mode_active = _mode_active;
	_status.state = _state_machine.state;

	if (_filter.initialized()) {
		_filter.position().copyTo(_status.target_est_ned);
		_filter.velocity().copyTo(_status.target_vel_ned);

	} else {
		for (int i = 0; i < 2; i++) {
			_status.target_est_ned[i] = NAN;
			_status.target_vel_ned[i] = NAN;
		}
	}

	_status.time_since_valid = AutoFollowGuidance::time_since_valid(_state_machine, now, _last_valid);
	_status.lost_time = AutoFollowGuidance::lost_time(_state_machine, now);

	_auto_follow_status_pub.publish(_status);
}

void AutoFollow::Run()
{
	if (should_exit()) {
		if (unregistration_done()) {
			ScheduleClear();
			exit_and_cleanup();
		}

		return;
	}

	perf_begin(_loop_perf);
	perf_count(_loop_interval_perf);

	parameters_update(false);

	// Registration is only accepted while disarmed, therefore the module is started on boot.
	if (!_registration_sent) {
		register_mode();
		_registration_sent = true;

	} else if (!registered() && !_registration_rejected) {
		check_mode_registration();
	}

	vehicle_status_s vehicle_status;

	if (_vehicle_status_sub.update(&vehicle_status)) {
		_mode_active = registered() && (vehicle_status.nav_state == static_cast<uint8_t>(_mode_id));
		_armed = (vehicle_status.arming_state == vehicle_status_s::ARMING_STATE_ARMED);
		_system_id = vehicle_status.system_id;
		_component_id = vehicle_status.component_id;
	}

	vehicle_land_detected_s vehicle_land_detected;

	if (_vehicle_land_detected_sub.update(&vehicle_land_detected)) {
		_landed = vehicle_land_detected.landed;
	}

	// Commander requests every 300 ms and expects the reply within 50 ms; the 20 ms cycle is fast enough.
	arming_check_request_s arming_check_request;

	if (registered() && _arming_check_request_sub.update(&arming_check_request)) {
		reply_to_arming_check(arming_check_request.request_id);
	}

	const hrt_abstime now = hrt_absolute_time();
	const float dt = (_last_cycle != 0) ? (now - _last_cycle) * 1e-6f : 0.f; // [s]
	_last_cycle = now;

	update_vehicle_state();

	// Validation, geometry and filter also run while the mode is not active, so the data is visible in the log
	_filter.predict(dt);
	_status.filter_updated = false;
	process_input(now);

	const uint8_t previous_state = _state_machine.state;
	const bool entered = AutoFollowGuidance::update_state(_state_machine, _mode_active, now, _last_valid, _last_no_target,
			     _param_af_data_tout.get(), _param_af_lost_t.get(), _armed);

	// No valid sample for AF_DATA_TOUT (same reference as the state machine): the estimate is stale and is not used again,
	// the next accepted measurement initializes the filter (position = measurement, velocity 0)
	if (!(AutoFollowGuidance::time_since_valid(_state_machine, now, _last_valid) < _param_af_data_tout.get())) {
		_filter.reset();
	}

	if (_mode_active) {
		if (entered) {
			enter_mode();
		}

		// Published in every active cycle, also in the first one (otherwise mc_pos_control keeps the previous setpoint)
		const bool lost_state_entered = _state_machine.state == auto_follow_status_s::STATE_KAYIP_BEKLE
						&& previous_state != auto_follow_status_s::STATE_KAYIP_BEKLE;
		publish_setpoint(now, dt, lost_state_entered);

	} else {
		clear_guidance_output();
	}

	// KAYIP_BEKLE -> HOLD_ISTENDI: Hold is requested from commander, repeated if rejected
	update_hold_request(now, _state_machine.state == auto_follow_status_s::STATE_HOLD_ISTENDI
			    && previous_state != auto_follow_status_s::STATE_HOLD_ISTENDI);

	publish_status(now);

	perf_end(_loop_perf);
}

int AutoFollow::task_spawn(int argc, char *argv[])
{
	AutoFollow *instance = new AutoFollow();

	if (instance) {
		_object.store(instance);
		_task_id = task_id_is_work_queue;

		if (instance->init()) {
			return PX4_OK;
		}

	} else {
		PX4_ERR("alloc failed");
	}

	delete instance;
	_object.store(nullptr);
	_task_id = -1;

	return PX4_ERROR;
}

int AutoFollow::print_status()
{
	if (!_registration_sent) {
		PX4_INFO("mode '%s': registration not sent yet", MODE_NAME);

	} else if (_registration_rejected) {
		PX4_INFO("mode '%s': registration rejected", MODE_NAME);

	} else if (!registered()) {
		PX4_INFO("mode '%s': waiting for registration reply", MODE_NAME);

	} else {
		PX4_INFO("mode '%s': registered, nav_state %d, arming check id %d", MODE_NAME, _mode_id, _arming_check_id);
	}

	PX4_INFO("mode active: %s, landed: %s, armed: %s", _mode_active ? "yes" : "no", _landed ? "yes" : "no", _armed ? "yes" : "no");
	PX4_INFO("state: %s, check_result: %s", STATE_NAMES[_state_machine.state], CHECK_NAMES[_status.check_result]);
	PX4_INFO("accept_count: %" PRIu32 ", no_target_count: %" PRIu32 ", hold_request_count: %" PRIu8,
		 _status.accept_count, _status.no_target_count, _status.hold_request_count);
	PX4_INFO("reject counts: name %" PRIu32 ", nonfinite %" PRIu32 ", norm %" PRIu32 ", seq %" PRIu32 ", age %" PRIu32
		 ", position %" PRIu32 ", depression %" PRIu32 ", range %" PRIu32,
		 _status.reject_name_count, _status.reject_nonfinite_count, _status.reject_norm_count, _status.reject_seq_count,
		 _status.reject_age_count, _status.reject_position_count, _status.reject_depression_count, _status.reject_range_count);
	perf_print_counter(_loop_perf);
	perf_print_counter(_loop_interval_perf);
	return 0;
}

int AutoFollow::custom_command(int argc, char *argv[])
{
	return print_usage("unknown command");
}

int AutoFollow::print_usage(const char *reason)
{
	if (reason) {
		PX4_WARN("%s\n", reason);
	}

	PRINT_MODULE_DESCRIPTION(
		R"DESCR_STR(
### Description
AUTO FOLLOW external flight mode for multicopters.

The module registers the flight mode "AUTO FOLLOW" with commander (it gets a nav_state
in the external range 23..30) and answers the arming checks. It runs at a fixed 50 Hz.
Registration is only accepted while disarmed, so the module is started on boot
from rc.mc_apps when AF_ENABLE is 1.

Input is the line of sight to the target in body FRD from the companion computer
(MAVLink DEBUG_FLOAT_ARRAY named AF_LOS, uORB debug_array). Every sample is validated;
the target position on flat ground is estimated with an alpha-beta filter.
While the mode is active, trajectory_setpoint (horizontal velocity, altitude held at entry,
yaw towards the target, rate limited by AF_YAWRATE_MAX) is published every cycle. On target loss
the vehicle holds position; after AF_LOST_T Hold is requested from commander (repeated at most
3 times at 1 s if rejected). The mode does not resume tracking by itself after Hold.
auto_follow_status is published every cycle and always logged.

Arming in this mode is refused; take off in another mode and switch to AUTO FOLLOW in the air.
)DESCR_STR");

	PRINT_MODULE_USAGE_NAME("auto_follow", "controller");
	PRINT_MODULE_USAGE_COMMAND_DESCR("start", "Start the module and register the AUTO FOLLOW mode");
	PRINT_MODULE_USAGE_COMMAND_DESCR("stop", "Unregister the mode and stop the module");
	PRINT_MODULE_USAGE_COMMAND_DESCR("status", "Print registration, nav_state, state, last check result, counters and timing");

	return 0;
}

extern "C" __EXPORT int auto_follow_main(int argc, char *argv[])
{
	return AutoFollow::main(argc, argv);
}
