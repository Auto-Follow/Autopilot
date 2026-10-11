/****************************************************************************
 *
 *   Copyright (c) 2026 Auto-Follow thesis team. All rights reserved.
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

#include "TezAutoFollow.hpp"

#include <string.h>

namespace
{
// Name shown in QGroundControl's flight mode list (register_ext_component_request.name holds 24 characters)
constexpr const char *MODE_NAME = "Tez Auto Follow";
}

TezAutoFollow::TezAutoFollow() :
	ModuleParams(nullptr),
	ScheduledWorkItem(MODULE_NAME, px4::wq_configurations::nav_and_controllers)
{
}

TezAutoFollow::~TezAutoFollow()
{
	perf_free(_loop_perf);
}

bool TezAutoFollow::init()
{
	// Any value that differs from other registrations works; the boot time is unique enough.
	_registration_request_id = hrt_absolute_time();
	ScheduleOnInterval(RUN_INTERVAL);
	return true;
}

void TezAutoFollow::Run()
{
	if (should_exit()) {
		ScheduleClear();
		unregister();
		exit_and_cleanup();
		return;
	}

	perf_begin(_loop_perf);

	if (_mode_id < 0) {
		check_registration_reply();

		if (_mode_id < 0 && !_registration_failed
		    && (_registration_requests == 0 || hrt_elapsed_time(&_last_registration_request) > REGISTRATION_RETRY_INTERVAL)) {
			if (_registration_requests < REGISTRATION_MAX_REQUESTS) {
				send_registration_request();

			} else {
				PX4_ERR("no answer from the commander to %d registration requests, giving up", _registration_requests);
				_registration_failed = true;
			}
		}

		perf_end(_loop_perf);
		return;
	}

	arming_check_request_s arming_check_request;

	if (_arming_check_request_sub.update(&arming_check_request)) {
		reply_to_arming_check(arming_check_request.request_id);
	}

	_vehicle_local_position_sub.update(&_local_position);

	vehicle_status_s vehicle_status;

	if (_vehicle_status_sub.update(&vehicle_status)) {
		const bool active = (vehicle_status.nav_state == _mode_id);

		if (active && !_active) {
			on_mode_entered();
		}

		_active = active;
	}

	if (_active) {
		update_setpoint();
	}

	perf_end(_loop_perf);
}

void TezAutoFollow::send_registration_request()
{
	register_ext_component_request_s request{};
	request.timestamp = hrt_absolute_time();
	request.request_id = _registration_request_id;
	strncpy(request.name, MODE_NAME, sizeof(request.name) - 1);
	request.px4_ros2_api_version = register_ext_component_request_s::LATEST_PX4_ROS2_API_VERSION;
	request.register_arming_check = true; // a mode registration requires an arming check registration
	request.register_mode = true;
	_register_ext_component_request_pub.publish(request);
	_last_registration_request = request.timestamp;
	_registration_requests++;
}

void TezAutoFollow::check_registration_reply()
{
	register_ext_component_reply_s reply;

	while (_register_ext_component_reply_sub.update(&reply)) {
		if (reply.request_id != _registration_request_id) {
			continue;
		}

		if (!reply.success) {
			// A rejection (no free mode slot, ...) does not go away by asking again
			PX4_ERR("mode registration rejected by commander");
			_registration_failed = true;
			continue;
		}

		_arming_check_id = reply.arming_check_id;
		_mode_id = reply.mode_id;
		send_control_mode_config();
		PX4_INFO("registered as '%s' (nav_state %d, arming check %d)", MODE_NAME, _mode_id, _arming_check_id);
	}
}

void TezAutoFollow::send_control_mode_config()
{
	// Same controller chain as the internal Position/Auto modes: the multicopter position controller tracks our
	// trajectory setpoints, attitude and rate controllers below it stay enabled.
	vehicle_control_mode_s config{};
	config.timestamp = hrt_absolute_time();
	config.source_id = _mode_id;
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

void TezAutoFollow::reply_to_arming_check(uint8_t request_id)
{
	arming_check_reply_s reply{};
	reply.timestamp = hrt_absolute_time();
	reply.request_id = request_id;
	reply.registration_id = _arming_check_id;
	reply.health_component_index = arming_check_reply_s::HEALTH_COMPONENT_INDEX_NONE;
	reply.num_events = 0;
	reply.can_arm_and_run = true;
	reply.mode_req_angular_velocity = true;
	reply.mode_req_attitude = true;
	reply.mode_req_local_alt = true;
	reply.mode_req_local_position = true;
	// Like Follow Me in PX4: the vehicle takes off in another mode and is switched to this one in the air.
	reply.mode_req_prevent_arming = true;
	_arming_check_reply_pub.publish(reply);
}

void TezAutoFollow::on_mode_entered()
{
	// The commander only enters the mode while the local position is valid (mode_req_local_position), but this module
	// may still hold an older sample: never hold a position the estimator did not mark valid.
	const bool position_valid = _local_position.timestamp != 0 && _local_position.xy_valid && _local_position.z_valid;
	_hold_position = position_valid ? matrix::Vector3f(_local_position.x, _local_position.y, _local_position.z)
			 : matrix::Vector3f(NAN, NAN, NAN);
	_hold_yaw = _local_position.heading_good_for_control ? _local_position.heading : NAN;

	if (position_valid) {
		PX4_INFO("mode active, holding N %.1f E %.1f D %.1f m", (double)_hold_position(0), (double)_hold_position(1),
			 (double)_hold_position(2));

	} else {
		PX4_WARN("mode active without a valid local position, stopping in place");
	}
}

void TezAutoFollow::update_setpoint()
{
	// Skeleton behaviour: hold the position and heading where the mode was entered. The follow logic replaces this.
	trajectory_setpoint_s setpoint{};
	setpoint.timestamp = hrt_absolute_time();
	_hold_position.copyTo(setpoint.position);
	// Without a position to hold, stop with a zero velocity setpoint instead
	(_hold_position.isAllFinite() ? matrix::Vector3f(NAN, NAN, NAN) : matrix::Vector3f(0.f, 0.f, 0.f)).copyTo(
		setpoint.velocity);
	matrix::Vector3f(NAN, NAN, NAN).copyTo(setpoint.acceleration);
	matrix::Vector3f(NAN, NAN, NAN).copyTo(setpoint.jerk);
	setpoint.yaw = _hold_yaw;
	setpoint.yawspeed = NAN;
	_trajectory_setpoint_pub.publish(setpoint);
}

void TezAutoFollow::unregister()
{
	if (_mode_id < 0) {
		return;
	}

	unregister_ext_component_s request{};
	request.timestamp = hrt_absolute_time();
	strncpy(request.name, MODE_NAME, sizeof(request.name) - 1);
	request.arming_check_id = _arming_check_id;
	request.mode_id = _mode_id;
	request.mode_executor_id = -1;
	_unregister_ext_component_pub.publish(request);
}

int TezAutoFollow::print_status()
{
	PX4_INFO("mode '%s': %s, nav_state %d, %s", MODE_NAME,
		 _mode_id >= 0 ? "registered" : (_registration_failed ? "registration failed" : "not registered"), _mode_id,
		 _active ? "active" : "inactive");
	perf_print_counter(_loop_perf);
	return 0;
}

int TezAutoFollow::task_spawn(int argc, char *argv[])
{
	TezAutoFollow *instance = new TezAutoFollow();

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

int TezAutoFollow::custom_command(int argc, char *argv[])
{
	return print_usage("unknown command");
}

int TezAutoFollow::print_usage(const char *reason)
{
	if (reason) {
		PX4_WARN("%s\n", reason);
	}

	PRINT_MODULE_DESCRIPTION(
		R"DESCR_STR(
### Description
Thesis Auto-Follow flight mode. Registers as an external flight mode ("Tez Auto Follow" in QGroundControl) and,
while selected, sends trajectory setpoints to the multicopter position controller.

The current skeleton holds the position and heading where the mode was entered.
Arming in this mode is refused: take off in another mode, then switch.
)DESCR_STR");

	PRINT_MODULE_USAGE_NAME("tez_auto_follow", "controller");
	PRINT_MODULE_USAGE_COMMAND("start");
	PRINT_MODULE_USAGE_DEFAULT_COMMANDS();

	return 0;
}

extern "C" __EXPORT int tez_auto_follow_main(int argc, char *argv[])
{
	return TezAutoFollow::main(argc, argv);
}
