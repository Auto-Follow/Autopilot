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

/**
 * @file TezAutoFollow.hpp
 *
 * Thesis Auto-Follow flight mode (example skeleton).
 *
 * Registers itself with the commander as an external flight mode (same mechanism as mc_nn_control), so it shows up
 * in QGroundControl without changing PX4 sources. While active it publishes trajectory setpoints for the PX4
 * multicopter position controller. The skeleton only holds the position where the mode was selected; the control
 * team replaces update_setpoint() with the follow logic.
 */

#pragma once

#include <drivers/drv_hrt.h>
#include <lib/matrix/matrix/math.hpp>
#include <lib/perf/perf_counter.h>
#include <px4_platform_common/defines.h>
#include <px4_platform_common/module.h>
#include <px4_platform_common/module_params.h>
#include <px4_platform_common/px4_work_queue/ScheduledWorkItem.hpp>

#include <uORB/Publication.hpp>
#include <uORB/Subscription.hpp>
#include <uORB/topics/arming_check_reply.h>
#include <uORB/topics/arming_check_request.h>
#include <uORB/topics/register_ext_component_reply.h>
#include <uORB/topics/register_ext_component_request.h>
#include <uORB/topics/trajectory_setpoint.h>
#include <uORB/topics/unregister_ext_component.h>
#include <uORB/topics/vehicle_control_mode.h>
#include <uORB/topics/vehicle_local_position.h>
#include <uORB/topics/vehicle_status.h>

using namespace time_literals;

class TezAutoFollow : public ModuleBase<TezAutoFollow>, public ModuleParams, public px4::ScheduledWorkItem
{
public:
	TezAutoFollow();
	~TezAutoFollow() override;

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

	void send_registration_request();
	void check_registration_reply();
	void send_control_mode_config();
	void reply_to_arming_check(uint8_t request_id);
	void on_mode_entered();
	void update_setpoint();
	void unregister();

	// The commander declares an external mode unresponsive if an arming check request is not answered within
	// 50 ms (externalChecks.hpp REQUEST_TIMEOUT), so the loop runs well below that.
	static constexpr hrt_abstime RUN_INTERVAL = 10_ms;
	// The commander answers a registration within one of its cycles. A repeated request would register the mode a
	// second time (ModeManagement only warns about the duplicate name), so repeat rarely and give up after a while.
	static constexpr hrt_abstime REGISTRATION_RETRY_INTERVAL = 5_s;
	static constexpr int REGISTRATION_MAX_REQUESTS = 3;

	uORB::Subscription _arming_check_request_sub{ORB_ID(arming_check_request)};
	uORB::Subscription _register_ext_component_reply_sub{ORB_ID(register_ext_component_reply)};
	uORB::Subscription _vehicle_local_position_sub{ORB_ID(vehicle_local_position)};
	uORB::Subscription _vehicle_status_sub{ORB_ID(vehicle_status)};

	uORB::Publication<arming_check_reply_s> _arming_check_reply_pub{ORB_ID(arming_check_reply)};
	uORB::Publication<vehicle_control_mode_s> _config_control_setpoints_pub{ORB_ID(config_control_setpoints)};
	uORB::Publication<register_ext_component_request_s> _register_ext_component_request_pub{ORB_ID(register_ext_component_request)};
	uORB::Publication<trajectory_setpoint_s> _trajectory_setpoint_pub{ORB_ID(trajectory_setpoint)};
	uORB::Publication<unregister_ext_component_s> _unregister_ext_component_pub{ORB_ID(unregister_ext_component)};

	perf_counter_t _loop_perf{perf_alloc(PC_ELAPSED, MODULE_NAME": cycle")};

	vehicle_local_position_s _local_position{};

	uint64_t _registration_request_id{0};
	hrt_abstime _last_registration_request{0};
	int _registration_requests{0};
	bool _registration_failed{false};
	int8_t _arming_check_id{-1};
	int8_t _mode_id{-1};

	bool _active{false};
	matrix::Vector3f _hold_position{}; // [m] NED, local frame; NAN when the estimate was not valid on entry
	float _hold_yaw{NAN};              // [rad]
};
