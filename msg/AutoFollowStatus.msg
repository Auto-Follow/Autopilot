# AUTO FOLLOW external flight mode (auto_follow module) status.
# Published every 50 Hz cycle while the module runs, also when the mode is not active (STATE_PASIF).
# NED = local position frame (x north, y east, z down); FRD = body frame (x forward, y right, z down).

uint64 timestamp                 # time since system start (microseconds)

uint8 STATE_PASIF = 0            # mode not active, no trajectory_setpoint published
uint8 STATE_TAKIP = 1            # valid target data, guidance running
uint8 STATE_KAYIP_BEKLE = 2      # target lost, holding position (hover)
uint8 STATE_HOLD_ISTENDI = 3     # AF_LOST_T elapsed, Hold requested

uint8 CHECK_OK = 0               # sample accepted
uint8 CHECK_NAME = 1             # name is not AF_LOS
uint8 CHECK_NONFINITE = 2        # NaN or Inf in data[0..5]
uint8 CHECK_NORM = 3             # LOS length differs from 1 by more than AF_NORM_TOL
uint8 CHECK_SEQ = 4              # sequence number not greater than the previous one
uint8 CHECK_AGE = 5              # real age not below AF_DATA_TOUT
uint8 CHECK_NO_TARGET = 6        # target flag is not 1 (not corrupt data, starts KAYIP_BEKLE)
uint8 CHECK_POSITION = 7         # local position not valid (xy_valid, z_valid)
uint8 CHECK_DEPRESSION = 8       # depression angle below AF_MIN_DEP
uint8 CHECK_RANGE = 9            # height difference or horizontal range out of (0, AF_MAX_RNG]

uint8 mode_nav_state             # nav_state assigned to AUTO FOLLOW (23..30), 0 if not registered
bool mode_active                 # vehicle_status.nav_state == mode_nav_state
uint8 state                      # STATE_*

# Raw input: last AF_LOS sample (debug_array), copied before validation
uint64 los_timestamp             # [us] arrival time of the last AF_LOS sample on the FC, 0 if none
float32[3] los_frd               # raw LOS x, y, z, body FRD (data[0..2])
float32 los_age                  # [ms] age reported by the companion computer (data[3])
uint32 los_seq                   # sequence number (data[4])
bool los_target                  # target flag (data[5] == 1)

# Validation
uint8 check_result               # CHECK_* of the last debug_array sample
uint32 accept_count              # accepted samples
uint32 reject_name_count         # CHECK_NAME
uint32 reject_nonfinite_count    # CHECK_NONFINITE
uint32 reject_norm_count         # CHECK_NORM
uint32 reject_seq_count          # CHECK_SEQ
uint32 reject_age_count          # CHECK_AGE
uint32 reject_position_count     # CHECK_POSITION
uint32 reject_depression_count   # CHECK_DEPRESSION
uint32 reject_range_count        # CHECK_RANGE
uint32 no_target_count           # CHECK_NO_TARGET
float32 latency                  # [ms] total delay of the last accepted sample = (processing time - arrival) + age

# Geometry of the last sample that reached the geometry step
float32[3] los_ned               # LOS rotated to NED
float32 depression               # [rad] depression angle
float32 height_diff              # [m] height difference h
float32 range_meas               # [m] horizontal range from this measurement
float32[2] target_meas_ned       # [m] filter input: measured target NED x, y

# Alpha-beta filter output
float32[2] target_est_ned        # [m] estimated target NED x, y
float32[2] target_vel_ned        # [m/s] estimated target NED velocity x, y
bool filter_updated              # correction with a new measurement in this cycle

# Guidance
float32 range_est                # [m] horizontal range to the estimated target
float32 range_desired            # [m] desired horizontal range
float32[2] vel_cmd_law           # [m/s] law output before limits, NED x, y
float32[2] vel_cmd               # [m/s] after AF_VEL_MAX and AF_ACC_MAX, sent in trajectory_setpoint, NED x, y
float32 yaw_cmd                  # [rad] yaw setpoint
bool yaw_frozen                  # yaw held because range_est < AF_YAW_MIN_D
float32 alt_hold_z               # [m] held altitude, NED z

# Timing
float32 time_since_valid         # [s] time since the last valid sample
float32 lost_time                # [s] time counted towards AF_LOST_T
uint8 hold_request_count         # Hold requests sent
