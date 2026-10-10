# No DEPENDS on PX4 libraries here: external modules are configured before PX4's own libraries exist
# (CMakeLists.txt adds EXTERNAL_MODULES_LOCATION first). px4_work_queue is linked into the px4 binary anyway.
px4_add_module(
	MODULE modules__tez_auto_follow
	MAIN tez_auto_follow
	SRCS
		TezAutoFollow.cpp
		TezAutoFollow.hpp
	)
