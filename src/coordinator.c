#include "coordinator.h"

#include <string.h>

static node_t *find_node_mut(coordinator_t *coordinator, unsigned controller_id) {
    size_t i;
    for (i = 0; i < coordinator->node_count; ++i) {
        if (coordinator->nodes[i].identity.controller_id == controller_id) {
            return &coordinator->nodes[i];
        }
    }
    return NULL;
}

static mission_task_t *find_task_mut(coordinator_t *coordinator, unsigned task_id) {
    size_t i;
    for (i = 0; i < coordinator->task_count; ++i) {
        if (coordinator->tasks[i].task_id == task_id) {
            return &coordinator->tasks[i];
        }
    }
    return NULL;
}

static bool identity_conflicts(const node_t *node, const node_identity_t *identity) {
    return node->identity.controller_id == identity->controller_id ||
           node->identity.mav_sys_id == identity->mav_sys_id ||
           node->identity.px4_instance == identity->px4_instance ||
           strcmp(node->identity.ros_namespace, identity->ros_namespace) == 0;
}

static node_t *first_active_replacement(coordinator_t *coordinator,
                                        unsigned excluded_controller_id) {
    size_t i;
    for (i = 0; i < coordinator->node_count; ++i) {
        node_t *node = &coordinator->nodes[i];
        if (node->identity.controller_id != excluded_controller_id &&
            node->state == NODE_ACTIVE) {
            return node;
        }
    }
    return NULL;
}

coord_result_t coordinator_init(coordinator_t *coordinator,
                                uint64_t degrade_after_ms,
                                uint64_t lost_after_ms) {
    if (coordinator == NULL || degrade_after_ms == 0U ||
        lost_after_ms <= degrade_after_ms) {
        return COORD_ERR_ARGUMENT;
    }
    memset(coordinator, 0, sizeof(*coordinator));
    coordinator->degrade_after_ms = degrade_after_ms;
    coordinator->lost_after_ms = lost_after_ms;
    return COORD_OK;
}

coord_result_t coordinator_discover(coordinator_t *coordinator,
                                    const node_identity_t *identity,
                                    uint64_t now_ms) {
    size_t i;
    node_t *node;
    if (coordinator == NULL || identity == NULL ||
        identity->controller_id == 0U || identity->mav_sys_id == 0U ||
        identity->ros_namespace[0] == '\0') {
        return COORD_ERR_ARGUMENT;
    }
    if (coordinator->node_count >= COORD_MAX_NODES) {
        return COORD_ERR_CAPACITY;
    }
    for (i = 0; i < coordinator->node_count; ++i) {
        if (identity_conflicts(&coordinator->nodes[i], identity)) {
            return COORD_ERR_DUPLICATE_IDENTITY;
        }
    }
    node = &coordinator->nodes[coordinator->node_count++];
    memset(node, 0, sizeof(*node));
    node->identity = *identity;
    node->state = NODE_DISCOVERED;
    node->last_heartbeat_ms = now_ms;
    return COORD_OK;
}

coord_result_t coordinator_admit(coordinator_t *coordinator,
                                 unsigned controller_id) {
    node_t *node;
    if (coordinator == NULL) {
        return COORD_ERR_ARGUMENT;
    }
    node = find_node_mut(coordinator, controller_id);
    if (node == NULL) {
        return COORD_ERR_NOT_FOUND;
    }
    if (node->state != NODE_DISCOVERED) {
        return COORD_ERR_STATE;
    }
    node->state = NODE_ACTIVE;
    return COORD_OK;
}

coord_result_t coordinator_heartbeat(coordinator_t *coordinator,
                                     unsigned controller_id,
                                     uint64_t now_ms) {
    node_t *node;
    if (coordinator == NULL) {
        return COORD_ERR_ARGUMENT;
    }
    node = find_node_mut(coordinator, controller_id);
    if (node == NULL) {
        return COORD_ERR_NOT_FOUND;
    }
    if (now_ms < node->last_heartbeat_ms) {
        return COORD_ERR_TIME_REGRESSION;
    }
    node->last_heartbeat_ms = now_ms;
    if (node->state == NODE_DEGRADED) {
        node->state = NODE_ACTIVE;
    } else if (node->state == NODE_LOST) {
        node->state = NODE_QUARANTINED;
        node->recovery_heartbeats = 1U;
    } else if (node->state == NODE_QUARANTINED &&
               node->recovery_heartbeats < 2U) {
        node->recovery_heartbeats++;
    }
    return COORD_OK;
}

coord_result_t coordinator_tick(coordinator_t *coordinator, uint64_t now_ms) {
    size_t i;
    coord_result_t result = COORD_OK;
    if (coordinator == NULL) {
        return COORD_ERR_ARGUMENT;
    }
    for (i = 0; i < coordinator->node_count; ++i) {
        node_t *node = &coordinator->nodes[i];
        uint64_t age;
        size_t task_index;
        if (now_ms < node->last_heartbeat_ms) {
            return COORD_ERR_TIME_REGRESSION;
        }
        if (node->state != NODE_ACTIVE && node->state != NODE_DEGRADED) {
            continue;
        }
        age = now_ms - node->last_heartbeat_ms;
        if (age >= coordinator->lost_after_ms) {
            node_t *replacement;
            node->state = NODE_LOST;
            replacement = first_active_replacement(coordinator,
                                                   node->identity.controller_id);
            for (task_index = 0; task_index < coordinator->task_count; ++task_index) {
                mission_task_t *task = &coordinator->tasks[task_index];
                if (task->assigned_controller_id != node->identity.controller_id) {
                    continue;
                }
                if (replacement == NULL) {
                    task->assigned_controller_id = 0U;
                    result = COORD_ERR_NO_REPLACEMENT;
                } else {
                    task->assigned_controller_id = replacement->identity.controller_id;
                }
            }
        } else if (age >= coordinator->degrade_after_ms) {
            node->state = NODE_DEGRADED;
        }
    }
    return result;
}

coord_result_t coordinator_assign(coordinator_t *coordinator,
                                  unsigned task_id,
                                  unsigned controller_id) {
    node_t *node;
    mission_task_t *task;
    if (coordinator == NULL || task_id == 0U) {
        return COORD_ERR_ARGUMENT;
    }
    node = find_node_mut(coordinator, controller_id);
    if (node == NULL) {
        return COORD_ERR_NOT_FOUND;
    }
    if (node->state != NODE_ACTIVE) {
        return COORD_ERR_STATE;
    }
    task = find_task_mut(coordinator, task_id);
    if (task == NULL) {
        if (coordinator->task_count >= COORD_MAX_TASKS) {
            return COORD_ERR_CAPACITY;
        }
        task = &coordinator->tasks[coordinator->task_count++];
        task->task_id = task_id;
    }
    task->assigned_controller_id = controller_id;
    return COORD_OK;
}

coord_result_t coordinator_recover(coordinator_t *coordinator,
                                   unsigned controller_id,
                                   uint64_t now_ms) {
    node_t *node;
    if (coordinator == NULL) {
        return COORD_ERR_ARGUMENT;
    }
    node = find_node_mut(coordinator, controller_id);
    if (node == NULL) {
        return COORD_ERR_NOT_FOUND;
    }
    if (node->state != NODE_QUARANTINED || node->recovery_heartbeats < 2U ||
        now_ms < node->last_heartbeat_ms ||
        now_ms - node->last_heartbeat_ms >= coordinator->degrade_after_ms) {
        return COORD_ERR_STATE;
    }
    node->state = NODE_ACTIVE;
    node->recovery_heartbeats = 0U;
    return COORD_OK;
}

const node_t *coordinator_find_node(const coordinator_t *coordinator,
                                    unsigned controller_id) {
    size_t i;
    if (coordinator == NULL) {
        return NULL;
    }
    for (i = 0; i < coordinator->node_count; ++i) {
        if (coordinator->nodes[i].identity.controller_id == controller_id) {
            return &coordinator->nodes[i];
        }
    }
    return NULL;
}

const mission_task_t *coordinator_find_task(const coordinator_t *coordinator,
                                            unsigned task_id) {
    size_t i;
    if (coordinator == NULL) {
        return NULL;
    }
    for (i = 0; i < coordinator->task_count; ++i) {
        if (coordinator->tasks[i].task_id == task_id) {
            return &coordinator->tasks[i];
        }
    }
    return NULL;
}

bool coordinator_can_emit_intent(const coordinator_t *coordinator,
                                 unsigned controller_id) {
    const node_t *node = coordinator_find_node(coordinator, controller_id);
    size_t i;
    if (node == NULL || node->state != NODE_ACTIVE) {
        return false;
    }
    for (i = 0; i < coordinator->task_count; ++i) {
        if (coordinator->tasks[i].assigned_controller_id == controller_id) {
            return true;
        }
    }
    return false;
}

const char *coordinator_state_name(node_state_t state) {
    switch (state) {
        case NODE_EMPTY: return "empty";
        case NODE_DISCOVERED: return "discovered";
        case NODE_ACTIVE: return "active";
        case NODE_DEGRADED: return "degraded";
        case NODE_LOST: return "lost";
        case NODE_QUARANTINED: return "quarantined";
        default: return "unknown";
    }
}

const char *coordinator_result_name(coord_result_t result) {
    switch (result) {
        case COORD_OK: return "ok";
        case COORD_ERR_ARGUMENT: return "invalid_argument";
        case COORD_ERR_CAPACITY: return "capacity";
        case COORD_ERR_DUPLICATE_IDENTITY: return "duplicate_identity";
        case COORD_ERR_NOT_FOUND: return "not_found";
        case COORD_ERR_STATE: return "invalid_state";
        case COORD_ERR_TIME_REGRESSION: return "time_regression";
        case COORD_ERR_NO_REPLACEMENT: return "no_replacement";
        default: return "unknown";
    }
}
