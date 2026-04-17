# ---------------------------------------------------------
# Numinous Crunch Node Deployment Makefile
# ---------------------------------------------------------

# Optional CLI override:
#   make deploy dev SERVICES="main-worker"
SERVICES ?=

BACKEND_SERVICES = \
    main-worker \
    report-worker \
    scoring-worker \
    gateway-worker \
    public-gateway-worker


IS_ALL := $(filter all,$(MAKECMDGOALS))
IS_DEV := $(filter dev,$(MAKECMDGOALS))
IS_PRODUCTION := $(filter production,$(MAKECMDGOALS))

# Compose files
ifeq ($(IS_PRODUCTION),production)
	COMPOSE_FILES := -f docker-compose.yml -f docker-compose-prod.yml --env-file .production.env
else ifeq ($(IS_DEV),dev)
	COMPOSE_FILES := -f docker-compose.yml -f docker-compose-local.yml --env-file .dev.env
else
	COMPOSE_FILES := -f docker-compose.yml -f docker-compose-local.yml --env-file .local.env
endif

# Decide the list of services
ifeq ($(SERVICES),)
	ifeq ($(IS_ALL),all)
		SERVICES :=
	else ifeq ($(IS_DEV),dev)
		SERVICES_EXCLUDE := $(BACKEND_SERVICES)
		SERVICES := $(filter-out $(SERVICES_EXCLUDE),$(shell docker compose $(COMPOSE_FILES) config --services))
	else ifeq ($(IS_PRODUCTION),production)
		SERVICES := $(BACKEND_SERVICES)
	else
		SERVICES :=
	endif
endif

# ---------------------------------------------------------
# Commands
# ---------------------------------------------------------

## Build + deploy
deploy:
	git submodule update --init --recursive
	docker compose $(COMPOSE_FILES) up -d --build $(SERVICES)

## Restart services
restart:
ifneq ($(SERVICES),)
	docker compose $(COMPOSE_FILES) restart $(SERVICES)
else
	docker compose $(COMPOSE_FILES) restart
endif

## Stop services
stop:
ifneq ($(SERVICES),)
	docker compose $(COMPOSE_FILES) stop $(SERVICES)
else
	docker compose $(COMPOSE_FILES) stop
endif

## Logs (follow)
logs:
ifneq ($(SERVICES),)
	docker compose $(COMPOSE_FILES) logs -f $(SERVICES) --tail 1000
else
	docker compose $(COMPOSE_FILES) logs -f --tail 1000
endif

## Stop & remove
down:
ifneq ($(SERVICES),)
	docker compose $(COMPOSE_FILES) down $(SERVICES)
else
	docker compose $(COMPOSE_FILES) down
endif

## Build images
build:
ifneq ($(SERVICES),)
	docker compose $(COMPOSE_FILES) build $(SERVICES)
else
	docker compose $(COMPOSE_FILES) build
endif

# ---------------------------------------------------------
.PHONY: deploy restart stop logs down build all dev production

all:
	@true

dev:
	@true

production:
	@true
