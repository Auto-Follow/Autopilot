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
 * @file AlphaBetaFilter.hpp
 *
 * Horizontal (x, y) alpha-beta filter for the target position on the ground.
 * Prediction runs every cycle, correction only with an accepted measurement.
 */

#pragma once

#include <matrix/math.hpp>

class AlphaBetaFilter
{
public:
	/** Forget the state; the next measurement initializes it (e.g. after an EKF position reset). */
	void reset() { _initialized = false; }

	/**
	 * Propagate the position with the estimated velocity.
	 * @param dt time since the last prediction [s]
	 */
	void predict(float dt)
	{
		if (_initialized) {
			_position += _velocity * dt;
		}
	}

	/**
	 * Correct with a measurement. The first measurement sets the position and zeroes the velocity.
	 * @param measurement measured target position, NED x, y [m]
	 * @param dt_measurement time between the capture times of this and the previous measurement [s]
	 * @param alpha position gain [-]
	 * @param beta velocity gain [-]
	 */
	void correct(const matrix::Vector2f &measurement, float dt_measurement, float alpha, float beta)
	{
		if (!_initialized) {
			_position = measurement;
			_velocity.zero();
			_initialized = true;
			return;
		}

		const matrix::Vector2f residual = measurement - _position;
		_position += residual * alpha;

		// beta / dt is undefined for non-increasing capture times: keep the velocity then
		if (dt_measurement > 0.f) {
			_velocity += residual * (beta / dt_measurement);
		}
	}

	bool initialized() const { return _initialized; }
	const matrix::Vector2f &position() const { return _position; } // [m] NED x, y
	const matrix::Vector2f &velocity() const { return _velocity; } // [m/s] NED x, y

private:
	matrix::Vector2f _position{};
	matrix::Vector2f _velocity{};
	bool _initialized{false};
};
