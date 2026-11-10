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

#include "AutoFollow.hpp"

#include <mathlib/mathlib.h>
#include <string.h>

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

	PX4_INFO("mode active: %s, landed: %s", _mode_active ? "yes" : "no", _landed ? "yes" : "no");
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

Arming in this mode is refused; take off in another mode and switch to AUTO FOLLOW in the air.
)DESCR_STR");

	PRINT_MODULE_USAGE_NAME("auto_follow", "controller");
	PRINT_MODULE_USAGE_COMMAND_DESCR("start", "Start the module and register the AUTO FOLLOW mode");
	PRINT_MODULE_USAGE_COMMAND_DESCR("stop", "Unregister the mode and stop the module");
	PRINT_MODULE_USAGE_COMMAND_DESCR("status", "Print registration state, assigned nav_state and cycle timing");

	return 0;
}

extern "C" __EXPORT int auto_follow_main(int argc, char *argv[])
{
	return AutoFollow::main(argc, argv);
}
