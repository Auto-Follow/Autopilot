############################################################################
#
#   Copyright (c) 2026 PX4 Development Team. All rights reserved.
#   Copyright (c) 2026 Pamukkale Elektrik-Elektronik Mühendisliği tez ekibi.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in
#    the documentation and/or other materials provided with the
#    distribution.
# 3. Neither the name PX4 nor the names of its contributors may be
#    used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
# OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
############################################################################

# Pure computations (validation, geometry, guidance, state machine), unit testable without uORB
px4_add_library(AutoFollowGuidance
	AutoFollowGuidance.cpp
	AutoFollowGuidance.hpp
)
target_include_directories(AutoFollowGuidance PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

px4_add_module(
	MODULE modules__auto_follow
	MAIN auto_follow
	SRCS
		AlphaBetaFilter.hpp
		AutoFollow.cpp
		AutoFollow.hpp
	MODULE_CONFIG
		module.yaml
	DEPENDS
		AutoFollowGuidance
		px4_work_queue
)

px4_add_unit_gtest(SRC AutoFollowGuidanceTest.cpp LINKLIBS AutoFollowGuidance)
