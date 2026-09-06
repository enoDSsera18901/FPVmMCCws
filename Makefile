CC ?= cc
CFLAGS ?= -std=c11 -O2 -g -Wall -Wextra -Wpedantic -Werror
CPPFLAGS ?= -Iinclude
BUILD_DIR := build

.PHONY: all test sanitizers evidence clean

all: $(BUILD_DIR)/pair2_sim $(BUILD_DIR)/test_coordinator

$(BUILD_DIR):
	mkdir -p $@

$(BUILD_DIR)/pair2_sim: src/pair2_sim.c src/coordinator.c include/coordinator.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) src/pair2_sim.c src/coordinator.c -o $@

$(BUILD_DIR)/test_coordinator: tests/test_coordinator.c src/coordinator.c include/coordinator.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) tests/test_coordinator.c src/coordinator.c -o $@

test: $(BUILD_DIR)/test_coordinator
	./$(BUILD_DIR)/test_coordinator

sanitizers: | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) -std=c11 -O1 -g -Wall -Wextra -Wpedantic -Werror \
		-fsanitize=address,undefined -fno-omit-frame-pointer \
		tests/test_coordinator.c src/coordinator.c -o $(BUILD_DIR)/test_coordinator_sanitized
	ASAN_OPTIONS=detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1 ./$(BUILD_DIR)/test_coordinator_sanitized

evidence: all
	./scripts/run_pair2_evidence.sh

clean:
	rm -rf $(BUILD_DIR)
