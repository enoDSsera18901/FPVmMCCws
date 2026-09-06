#ifndef COORDINATOR_H
#define COORDINATOR_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define COORD_MAX_NODES 8U
#define COORD_MAX_TASKS 16U
#define COORD_NAMESPACE_LEN 32U

typedef enum {
    NODE_EMPTY = 0,
    NODE_DISCOVERED,
    NODE_ACTIVE,
    NODE_DEGRADED,
    NODE_LOST,
    NODE_QUARANTINED
} node_state_t;

typedef struct {
    unsigned controller_id;
    unsigned mav_sys_id;
    unsigned px4_instance;
    char ros_namespace[COORD_NAMESPACE_LEN];
} node_identity_t;

typedef struct {
    node_identity_t identity;
    node_state_t state;
    uint64_t last_heartbeat_ms;
    unsigned recovery_heartbeats;
} node_t;

typedef struct {
    unsigned task_id;
    unsigned assigned_controller_id;
} mission_task_t;

typedef struct {
    node_t nodes[COORD_MAX_NODES];
    size_t node_count;
    mission_task_t tasks[COORD_MAX_TASKS];
    size_t task_count;
    uint64_t degrade_after_ms;
    uint64_t lost_after_ms;
} coordinator_t;

typedef enum {
    COORD_OK = 0,
    COORD_ERR_ARGUMENT,
    COORD_ERR_CAPACITY,
    COORD_ERR_DUPLICATE_IDENTITY,
    COORD_ERR_NOT_FOUND,
    COORD_ERR_STATE,
    COORD_ERR_TIME_REGRESSION,
    COORD_ERR_NO_REPLACEMENT
} coord_result_t;

coord_result_t coordinator_init(coordinator_t *coordinator,
                                uint64_t degrade_after_ms,
                                uint64_t lost_after_ms);
coord_result_t coordinator_discover(coordinator_t *coordinator,
                                    const node_identity_t *identity,
                                    uint64_t now_ms);
coord_result_t coordinator_admit(coordinator_t *coordinator,
                                 unsigned controller_id);
coord_result_t coordinator_heartbeat(coordinator_t *coordinator,
                                     unsigned controller_id,
                                     uint64_t now_ms);
coord_result_t coordinator_tick(coordinator_t *coordinator, uint64_t now_ms);
coord_result_t coordinator_assign(coordinator_t *coordinator,
                                  unsigned task_id,
                                  unsigned controller_id);
coord_result_t coordinator_recover(coordinator_t *coordinator,
                                   unsigned controller_id,
                                   uint64_t now_ms);
const node_t *coordinator_find_node(const coordinator_t *coordinator,
                                    unsigned controller_id);
const mission_task_t *coordinator_find_task(const coordinator_t *coordinator,
                                            unsigned task_id);
bool coordinator_can_emit_intent(const coordinator_t *coordinator,
                                 unsigned controller_id);
const char *coordinator_state_name(node_state_t state);
const char *coordinator_result_name(coord_result_t result);

#endif

