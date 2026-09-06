#include "coordinator.h"

#include <stdio.h>
#include <string.h>

static unsigned checks_run;
static unsigned failures;

#define CHECK(expr) do { \
    ++checks_run; \
    if (!(expr)) { \
        ++failures; \
        fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #expr); \
    } \
} while (0)

static node_identity_t identity(unsigned controller_id,
                                unsigned mav_sys_id,
                                unsigned px4_instance,
                                const char *ros_namespace) {
    node_identity_t value = {0};
    value.controller_id = controller_id;
    value.mav_sys_id = mav_sys_id;
    value.px4_instance = px4_instance;
    (void)snprintf(value.ros_namespace, sizeof(value.ros_namespace), "%s", ros_namespace);
    return value;
}

static coordinator_t admitted_pair(void) {
    coordinator_t coordinator;
    node_identity_t first = identity(1U, 1U, 0U, "coord_001");
    node_identity_t second = identity(2U, 2U, 1U, "coord_002");
    CHECK(coordinator_init(&coordinator, 500U, 1000U) == COORD_OK);
    CHECK(coordinator_discover(&coordinator, &first, 0U) == COORD_OK);
    CHECK(coordinator_discover(&coordinator, &second, 0U) == COORD_OK);
    CHECK(coordinator_admit(&coordinator, 1U) == COORD_OK);
    CHECK(coordinator_admit(&coordinator, 2U) == COORD_OK);
    return coordinator;
}

static void test_configuration_guards(void) {
    coordinator_t coordinator;
    node_identity_t first = identity(1U, 1U, 0U, "coord_001");
    node_identity_t duplicate_controller = identity(1U, 2U, 1U, "coord_002");
    node_identity_t duplicate_system = identity(2U, 1U, 1U, "coord_002");
    node_identity_t duplicate_instance = identity(2U, 2U, 0U, "coord_002");
    node_identity_t duplicate_namespace = identity(2U, 2U, 1U, "coord_001");
    CHECK(coordinator_init(NULL, 500U, 1000U) == COORD_ERR_ARGUMENT);
    CHECK(coordinator_init(&coordinator, 0U, 1000U) == COORD_ERR_ARGUMENT);
    CHECK(coordinator_init(&coordinator, 1000U, 1000U) == COORD_ERR_ARGUMENT);
    CHECK(coordinator_init(&coordinator, 500U, 1000U) == COORD_OK);
    CHECK(coordinator_discover(&coordinator, &first, 0U) == COORD_OK);
    CHECK(coordinator_discover(&coordinator, &duplicate_controller, 0U) == COORD_ERR_DUPLICATE_IDENTITY);
    CHECK(coordinator_discover(&coordinator, &duplicate_system, 0U) == COORD_ERR_DUPLICATE_IDENTITY);
    CHECK(coordinator_discover(&coordinator, &duplicate_instance, 0U) == COORD_ERR_DUPLICATE_IDENTITY);
    CHECK(coordinator_discover(&coordinator, &duplicate_namespace, 0U) == COORD_ERR_DUPLICATE_IDENTITY);
}

static void test_degradation_suppresses_intent(void) {
    coordinator_t coordinator = admitted_pair();
    CHECK(coordinator_assign(&coordinator, 101U, 1U) == COORD_OK);
    CHECK(coordinator_can_emit_intent(&coordinator, 1U));
    CHECK(coordinator_heartbeat(&coordinator, 2U, 450U) == COORD_OK);
    CHECK(coordinator_tick(&coordinator, 500U) == COORD_OK);
    CHECK(coordinator_find_node(&coordinator, 1U)->state == NODE_DEGRADED);
    CHECK(!coordinator_can_emit_intent(&coordinator, 1U));
    CHECK(coordinator_find_node(&coordinator, 2U)->state == NODE_ACTIVE);
    CHECK(coordinator_heartbeat(&coordinator, 1U, 510U) == COORD_OK);
    CHECK(coordinator_find_node(&coordinator, 1U)->state == NODE_ACTIVE);
}

static void test_loss_reassignment_and_controlled_recovery(void) {
    coordinator_t coordinator = admitted_pair();
    CHECK(coordinator_assign(&coordinator, 101U, 1U) == COORD_OK);
    CHECK(coordinator_assign(&coordinator, 102U, 2U) == COORD_OK);
    CHECK(coordinator_heartbeat(&coordinator, 2U, 900U) == COORD_OK);
    CHECK(coordinator_tick(&coordinator, 1000U) == COORD_OK);
    CHECK(coordinator_find_node(&coordinator, 1U)->state == NODE_LOST);
    CHECK(coordinator_find_task(&coordinator, 101U)->assigned_controller_id == 2U);
    CHECK(!coordinator_can_emit_intent(&coordinator, 1U));
    CHECK(coordinator_heartbeat(&coordinator, 1U, 1100U) == COORD_OK);
    CHECK(coordinator_find_node(&coordinator, 1U)->state == NODE_QUARANTINED);
    CHECK(coordinator_recover(&coordinator, 1U, 1101U) == COORD_ERR_STATE);
    CHECK(coordinator_heartbeat(&coordinator, 1U, 1150U) == COORD_OK);
    CHECK(coordinator_recover(&coordinator, 1U, 1160U) == COORD_OK);
    CHECK(coordinator_find_task(&coordinator, 101U)->assigned_controller_id == 2U);
    CHECK(!coordinator_can_emit_intent(&coordinator, 1U));
    CHECK(coordinator_assign(&coordinator, 101U, 1U) == COORD_OK);
    CHECK(coordinator_find_task(&coordinator, 101U)->assigned_controller_id == 1U);
    CHECK(coordinator_can_emit_intent(&coordinator, 1U));
}

static void test_loss_without_replacement_fails_closed(void) {
    coordinator_t coordinator = admitted_pair();
    CHECK(coordinator_assign(&coordinator, 101U, 1U) == COORD_OK);
    CHECK(coordinator_tick(&coordinator, 1000U) == COORD_ERR_NO_REPLACEMENT);
    CHECK(coordinator_find_task(&coordinator, 101U)->assigned_controller_id == 0U);
    CHECK(!coordinator_can_emit_intent(&coordinator, 1U));
    CHECK(!coordinator_can_emit_intent(&coordinator, 2U));
}

static void test_monotonic_time_and_state_guards(void) {
    coordinator_t coordinator = admitted_pair();
    CHECK(coordinator_heartbeat(&coordinator, 1U, 100U) == COORD_OK);
    CHECK(coordinator_heartbeat(&coordinator, 1U, 99U) == COORD_ERR_TIME_REGRESSION);
    CHECK(coordinator_tick(&coordinator, 50U) == COORD_ERR_TIME_REGRESSION);
    CHECK(coordinator_assign(&coordinator, 0U, 1U) == COORD_ERR_ARGUMENT);
    CHECK(coordinator_assign(&coordinator, 1U, 99U) == COORD_ERR_NOT_FOUND);
    CHECK(coordinator_admit(&coordinator, 1U) == COORD_ERR_STATE);
}

int main(void) {
    test_configuration_guards();
    test_degradation_suppresses_intent();
    test_loss_reassignment_and_controlled_recovery();
    test_loss_without_replacement_fails_closed();
    test_monotonic_time_and_state_guards();
    if (failures != 0U) {
        fprintf(stderr, "%u/%u checks failed\n", failures, checks_run);
        return 1;
    }
    printf("PASS: %u coordinator checks\n", checks_run);
    return 0;
}
