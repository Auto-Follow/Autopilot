# Thesis PX4 modules, built out of tree so the locked PX4 source stays untouched:
#   cmake -S . -B build/px4_sitl_tez -G Ninja -DCONFIG=px4_sitl_default -DEXTERNAL_MODULES_LOCATION=<repo>/tez/px4
# (tez/sim/derle.sh does this). Every module listed here is linked into the px4 binary.
set(config_module_list_external
	modules/tez_auto_follow
	PARENT_SCOPE
	)
