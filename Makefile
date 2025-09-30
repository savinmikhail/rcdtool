SHELL := bash

# Minimal, simple targets for a long-lived container
IMG      ?= rcdtool
NAME     ?= rcdtoold
DATA_DIR ?= $(CURDIR)/data
UID      := $(shell id -u 2>/dev/null || echo 1000)
GID      := $(shell id -g 2>/dev/null || echo 1000)

.PHONY: build up down ps shell run

build:
	docker build -t $(IMG) .

up: build
	@mkdir -p "$(DATA_DIR)"
	@if [ ! -f "$(DATA_DIR)/config.ini" ]; then cp -n config.ini.sample "$(DATA_DIR)/config.ini"; fi
	@if docker ps -a --format '{{.Names}}' | grep -qx "$(NAME)"; then \
		docker start "$(NAME)" >/dev/null; \
	else \
		docker run -d --restart unless-stopped --name "$(NAME)" \
		  -v "$(DATA_DIR):/work" \
		  --user $(UID):$(GID) \
		  --entrypoint sh "$(IMG)" -c 'sleep infinity' >/dev/null; \
	fi
	@docker ps --filter name="^$(NAME)$$" --format 'Running: {{.Names}} ({{.Status}})'

down:
	@docker rm -f "$(NAME)" >/dev/null 2>&1 || true; echo "+ Removed: $(NAME)"

shell: up
	docker exec -it -w /work "$(NAME)" bash
