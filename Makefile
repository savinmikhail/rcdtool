SHELL := bash

# docker compose driven workflow
COMPOSE  ?= docker compose
SERVICE  ?= rcdtoold
IMG      ?= rcdtool
NAME     ?= rcdtoold
DATA_DIR ?= $(CURDIR)/data
UID      := $(shell id -u 2>/dev/null || echo 1000)
GID      := $(shell id -g 2>/dev/null || echo 1000)

.PHONY: build up up-nc down ps bash logs restart

build:
	UID=$(UID) GID=$(GID) $(COMPOSE) build

up: ## Start long‑lived dev container with volumes
	@mkdir -p "$(DATA_DIR)"
	@if [ ! -f "$(DATA_DIR)/config.ini" ]; then cp -n config.ini.sample "$(DATA_DIR)/config.ini"; fi
	UID=$(UID) GID=$(GID) $(COMPOSE) up -d
	@$(COMPOSE) ps

down:
	$(COMPOSE) down

bash:
	$(COMPOSE) exec -w /work $(SERVICE) bash

restart:
	$(COMPOSE) restart $(SERVICE)
