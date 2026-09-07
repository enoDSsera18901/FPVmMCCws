#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <limits>
#include <memory>
#include <string>

#include "rclcpp/rclcpp.hpp"
#include "px4_msgs/msg/failsafe_flags.hpp"
#include "px4_msgs/msg/offboard_control_mode.hpp"
#include "px4_msgs/msg/trajectory_setpoint.hpp"
#include "px4_msgs/msg/vehicle_local_position.hpp"
#include "px4_msgs/msg/vehicle_status.hpp"
#include "coordination_msgs/msg/coordination_intent.hpp"
#include "coordination_msgs/msg/supervisor_gate.hpp"
#include "coordination_msgs/msg/vehicle_state.hpp"

using namespace std::chrono_literals;

class CoordinationPx4Bridge : public rclcpp::Node
{
public:
  CoordinationPx4Bridge() : Node("coordination_px4_bridge")
  {
    node_id_ = static_cast<uint8_t>(declare_parameter<int>("node_id", 1));
    px4_namespace_ = declare_parameter<std::string>("px4_namespace", "coord_001");
    publish_rate_hz_ = declare_parameter<double>("publish_rate_hz", 10.0);
    max_intent_age_ms_ = declare_parameter<int>("max_intent_age_ms", 200);
    max_px4_state_age_ms_ = declare_parameter<int>("max_px4_state_age_ms", 250);

    auto px4_qos = rclcpp::QoS(rclcpp::KeepLast(10)).best_effort().durability_volatile();
    const std::string prefix = "/" + px4_namespace_ + "/fmu/";

    local_position_sub_ = create_subscription<px4_msgs::msg::VehicleLocalPosition>(
      prefix + "out/vehicle_local_position", px4_qos,
      [this](px4_msgs::msg::VehicleLocalPosition::UniquePtr msg) { on_local_position(*msg); });
    vehicle_status_sub_ = create_subscription<px4_msgs::msg::VehicleStatus>(
      prefix + "out/vehicle_status", px4_qos,
      [this](px4_msgs::msg::VehicleStatus::UniquePtr msg) { on_vehicle_status(*msg); });
    failsafe_sub_ = create_subscription<px4_msgs::msg::FailsafeFlags>(
      prefix + "out/failsafe_flags", px4_qos,
      [this](px4_msgs::msg::FailsafeFlags::UniquePtr msg) { on_failsafe(*msg); });

    intent_sub_ = create_subscription<coordination_msgs::msg::CoordinationIntent>(
      "coordination_intent", 10,
      [this](coordination_msgs::msg::CoordinationIntent::UniquePtr msg) {
        if (msg->node_id != node_id_) return;
        latest_intent_ = *msg;
        have_intent_ = true;
        last_intent_receive_us_ = now_us();
      });
    gate_sub_ = create_subscription<coordination_msgs::msg::SupervisorGate>(
      "supervisor_gate", 10,
      [this](coordination_msgs::msg::SupervisorGate::UniquePtr msg) {
        if (msg->node_id != node_id_) return;
        latest_gate_ = *msg;
        have_gate_ = true;
        last_gate_receive_us_ = now_us();
      });

    vehicle_state_pub_ = create_publisher<coordination_msgs::msg::VehicleState>("vehicle_state", 10);
    offboard_pub_ = create_publisher<px4_msgs::msg::OffboardControlMode>(prefix + "in/offboard_control_mode", 10);
    trajectory_pub_ = create_publisher<px4_msgs::msg::TrajectorySetpoint>(prefix + "in/trajectory_setpoint", 10);

    const auto period = std::chrono::duration<double>(1.0 / std::max(1.0, publish_rate_hz_));
    timer_ = create_wall_timer(std::chrono::duration_cast<std::chrono::nanoseconds>(period),
      [this]() { on_timer(); });
  }

private:
  uint64_t now_us() const
  {
    return static_cast<uint64_t>(get_clock()->now().nanoseconds() / 1000);
  }

  bool fresh(uint64_t received_us, int max_age_ms) const
  {
    const uint64_t now = now_us();
    return received_us > 0u && now >= received_us &&
      (now - received_us) <= static_cast<uint64_t>(max_age_ms) * 1000u;
  }

  void on_vehicle_status(const px4_msgs::msg::VehicleStatus & msg)
  {
    latest_status_ = msg;
    have_status_ = true;
    last_status_receive_us_ = now_us();
  }

  void on_failsafe(const px4_msgs::msg::FailsafeFlags & msg)
  {
    latest_failsafe_ = msg;
    have_failsafe_ = true;
    last_failsafe_receive_us_ = now_us();
  }

  void on_local_position(const px4_msgs::msg::VehicleLocalPosition & msg)
  {
    latest_local_position_ = msg;
    have_local_position_ = true;
    last_local_position_receive_us_ = now_us();
    publish_vehicle_state();
  }

  bool px4_state_fresh() const
  {
    return have_local_position_ && have_status_ && have_failsafe_ &&
      fresh(last_local_position_receive_us_, max_px4_state_age_ms_) &&
      fresh(last_status_receive_us_, max_px4_state_age_ms_) &&
      fresh(last_failsafe_receive_us_, max_px4_state_age_ms_);
  }

  bool accepts_offboard_setpoints() const
  {
    return have_status_ &&
      latest_status_.nav_state == px4_msgs::msg::VehicleStatus::NAVIGATION_STATE_OFFBOARD;
  }

  bool local_nav_healthy() const
  {
    if (!px4_state_fresh()) return false;
    const bool estimator_ok = latest_local_position_.xy_valid && latest_local_position_.z_valid &&
      latest_local_position_.v_xy_valid && latest_local_position_.v_z_valid &&
      latest_local_position_.heading_good_for_control;
    const bool failsafe_ok = !latest_status_.failsafe &&
      !latest_failsafe_.fd_critical_failure &&
      !latest_failsafe_.navigator_failure &&
      !latest_failsafe_.position_accuracy_low;
    return estimator_ok && failsafe_ok;
  }

  void publish_vehicle_state()
  {
    if (!have_local_position_) return;
    coordination_msgs::msg::VehicleState out{};
    out.node_id = node_id_;
    out.local_receive_timestamp_us = now_us();
    out.px4_timestamp_us = latest_local_position_.timestamp;
    out.position_valid = latest_local_position_.xy_valid && latest_local_position_.z_valid;
    out.velocity_valid = latest_local_position_.v_xy_valid && latest_local_position_.v_z_valid;
    out.heading_valid = latest_local_position_.heading_good_for_control;
    out.local_nav_healthy = local_nav_healthy();
    out.north_m = latest_local_position_.x;
    out.east_m = latest_local_position_.y;
    out.down_m = latest_local_position_.z;
    out.vn_mps = latest_local_position_.vx;
    out.ve_mps = latest_local_position_.vy;
    out.vd_mps = latest_local_position_.vz;
    out.yaw_rad = latest_local_position_.heading;
    if (have_status_) {
      out.nav_state = latest_status_.nav_state;
      out.arming_state = latest_status_.arming_state;
      out.accepts_offboard_setpoints = accepts_offboard_setpoints();
      out.failsafe = latest_status_.failsafe;
    }
    if (have_failsafe_) {
      out.offboard_control_signal_lost = latest_failsafe_.offboard_control_signal_lost;
      out.critical_failure = latest_failsafe_.fd_critical_failure;
      out.global_position_invalid = latest_failsafe_.global_position_invalid;
    }
    vehicle_state_pub_->publish(out);
  }

  void publish_offboard_mode()
  {
    px4_msgs::msg::OffboardControlMode mode{};
    mode.timestamp = now_us();
    const bool use_position = have_intent_ && latest_intent_.position_valid;
    const bool use_velocity = have_intent_ && !use_position && latest_intent_.velocity_valid;
    mode.position = use_position;
    mode.velocity = use_velocity;
    mode.acceleration = false;
    mode.attitude = false;
    mode.body_rate = false;
    mode.thrust_and_torque = false;
    mode.direct_actuator = false;
    offboard_pub_->publish(mode);
  }

  void publish_trajectory()
  {
    const float nan = std::numeric_limits<float>::quiet_NaN();
    px4_msgs::msg::TrajectorySetpoint sp{};
    sp.timestamp = now_us();
    sp.position = {nan, nan, nan};
    sp.velocity = {nan, nan, nan};
    sp.acceleration = {nan, nan, nan};
    sp.jerk = {nan, nan, nan};
    sp.yaw = nan;
    sp.yawspeed = nan;
    if (latest_intent_.position_valid) {
      sp.position = {latest_intent_.north_m, latest_intent_.east_m, latest_intent_.down_m};
      if (latest_intent_.velocity_valid) {
        sp.velocity = {latest_intent_.vn_mps, latest_intent_.ve_mps, latest_intent_.vd_mps};
      }
    } else if (latest_intent_.velocity_valid) {
      sp.velocity = {latest_intent_.vn_mps, latest_intent_.ve_mps, latest_intent_.vd_mps};
    }
    if (latest_intent_.yaw_valid) sp.yaw = latest_intent_.yaw_rad;
    trajectory_pub_->publish(sp);
  }

  void on_timer()
  {
    if (!have_gate_ || !fresh(last_gate_receive_us_, max_intent_age_ms_)) return;
    if (latest_gate_.operator_override || !latest_gate_.external_control_requested) return;

    /* Heartbeat is intentionally allowed before PX4 enters Offboard so the operator can select it. */
    publish_offboard_mode();

    if (!latest_gate_.permit_intent || !have_intent_ || !fresh(last_intent_receive_us_, max_intent_age_ms_)) return;
    if (!px4_state_fresh() || !local_nav_healthy()) return;
    if (!accepts_offboard_setpoints()) return;
    if (!latest_intent_.position_valid && !latest_intent_.velocity_valid) return;
    publish_trajectory();
  }

  uint8_t node_id_{1u};
  std::string px4_namespace_;
  double publish_rate_hz_{10.0};
  int max_intent_age_ms_{200};
  int max_px4_state_age_ms_{250};

  bool have_intent_{false};
  bool have_gate_{false};
  bool have_local_position_{false};
  bool have_status_{false};
  bool have_failsafe_{false};
  uint64_t last_intent_receive_us_{0u};
  uint64_t last_gate_receive_us_{0u};
  uint64_t last_local_position_receive_us_{0u};
  uint64_t last_status_receive_us_{0u};
  uint64_t last_failsafe_receive_us_{0u};

  coordination_msgs::msg::CoordinationIntent latest_intent_{};
  coordination_msgs::msg::SupervisorGate latest_gate_{};
  px4_msgs::msg::VehicleLocalPosition latest_local_position_{};
  px4_msgs::msg::VehicleStatus latest_status_{};
  px4_msgs::msg::FailsafeFlags latest_failsafe_{};

  rclcpp::Subscription<coordination_msgs::msg::CoordinationIntent>::SharedPtr intent_sub_;
  rclcpp::Subscription<coordination_msgs::msg::SupervisorGate>::SharedPtr gate_sub_;
  rclcpp::Subscription<px4_msgs::msg::VehicleLocalPosition>::SharedPtr local_position_sub_;
  rclcpp::Subscription<px4_msgs::msg::VehicleStatus>::SharedPtr vehicle_status_sub_;
  rclcpp::Subscription<px4_msgs::msg::FailsafeFlags>::SharedPtr failsafe_sub_;
  rclcpp::Publisher<coordination_msgs::msg::VehicleState>::SharedPtr vehicle_state_pub_;
  rclcpp::Publisher<px4_msgs::msg::OffboardControlMode>::SharedPtr offboard_pub_;
  rclcpp::Publisher<px4_msgs::msg::TrajectorySetpoint>::SharedPtr trajectory_pub_;
  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<CoordinationPx4Bridge>());
  rclcpp::shutdown();
  return 0;
}
