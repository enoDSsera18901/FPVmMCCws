#include "coordinator.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void require_ok(coord_result_t result, const char *operation) {
    if (result != COORD_OK) {
        fprintf(stderr, "%s failed: %s\n", operation, coordinator_result_name(result));
        exit(EXIT_FAILURE);
    }
}

static void event(FILE *stream,
                  uint64_t time_ms,
                  const char *event_name,
                  const coordinator_t *coordinator,
                  unsigned task_id) {
    const node_t *n1 = coordinator_find_node(coordinator, 1U);
    const node_t *n2 = coordinator_find_node(coordinator, 2U);
    const mission_task_t *task = coordinator_find_task(coordinator, task_id);
    fprintf(stream, "%llu,%s,%s,%s,%u,%s,%s\n",
            (unsigned long long)time_ms,
            event_name,
            n1 == NULL ? "missing" : coordinator_state_name(n1->state),
            n2 == NULL ? "missing" : coordinator_state_name(n2->state),
            task == NULL ? 0U : task->assigned_controller_id,
            coordinator_can_emit_intent(coordinator, 1U) ? "enabled" : "suppressed",
            coordinator_can_emit_intent(coordinator, 2U) ? "enabled" : "suppressed");
}

int main(int argc, char **argv) {
    coordinator_t coordinator;
    node_identity_t node1 = {1U, 1U, 0U, "coord_001"};
    node_identity_t node2 = {2U, 2U, 1U, "coord_002"};
    FILE *stream = stdout;
    const unsigned reassigned_task = 101U;

    if (argc > 2) {
        fprintf(stderr, "usage: %s [events.csv]\n", argv[0]);
        return EXIT_FAILURE;
    }
    if (argc == 2) {
        stream = fopen(argv[1], "w");
        if (stream == NULL) {
            perror("open evidence output");
            return EXIT_FAILURE;
        }
    }

    fprintf(stream, "time_ms,event,node_1_state,node_2_state,task_101_owner,node_1_intent,node_2_intent\n");
    require_ok(coordinator_init(&coordinator, 500U, 1000U), "init");
    require_ok(coordinator_discover(&coordinator, &node1, 0U), "discover node 1");
    require_ok(coordinator_discover(&coordinator, &node2, 0U), "discover node 2");
    require_ok(coordinator_admit(&coordinator, 1U), "admit node 1");
    require_ok(coordinator_admit(&coordinator, 2U), "admit node 2");
    require_ok(coordinator_assign(&coordinator, reassigned_task, 1U), "assign task 101");
    require_ok(coordinator_assign(&coordinator, 102U, 2U), "assign task 102");
    event(stream, 0U, "pair_admitted_and_mission_assigned", &coordinator, reassigned_task);

    require_ok(coordinator_heartbeat(&coordinator, 1U, 100U), "heartbeat node 1");
    require_ok(coordinator_heartbeat(&coordinator, 2U, 100U), "heartbeat node 2");
    require_ok(coordinator_heartbeat(&coordinator, 2U, 650U), "heartbeat node 2");
    require_ok(coordinator_tick(&coordinator, 700U), "degradation tick");
    event(stream, 700U, "node_1_link_degraded", &coordinator, reassigned_task);

    require_ok(coordinator_heartbeat(&coordinator, 2U, 1050U), "heartbeat node 2");
    require_ok(coordinator_tick(&coordinator, 1100U), "loss tick");
    event(stream, 1100U, "node_1_lost_task_reassigned", &coordinator, reassigned_task);

    require_ok(coordinator_heartbeat(&coordinator, 1U, 1200U), "recovery heartbeat 1");
    event(stream, 1200U, "node_1_quarantined", &coordinator, reassigned_task);
    require_ok(coordinator_heartbeat(&coordinator, 1U, 1250U), "recovery heartbeat 2");
    require_ok(coordinator_recover(&coordinator, 1U, 1260U), "controlled recovery");
    event(stream, 1260U, "node_1_recovered_unassigned", &coordinator, reassigned_task);

    require_ok(coordinator_assign(&coordinator, reassigned_task, 1U), "controlled reconfiguration");
    event(stream, 1270U, "task_101_reconfigured_to_node_1", &coordinator, reassigned_task);

    if (stream != stdout && fclose(stream) != 0) {
        perror("close evidence output");
        return EXIT_FAILURE;
    }
    return EXIT_SUCCESS;
}

