APP_NAME ?= akwaya
IMAGE_TAG ?= latest
CONTAINER_NAME ?= $(APP_NAME)-container


ENV_FILE ?= .env

build:
	docker build -t $(APP_NAME):$(IMAGE_TAG) .

run:
	docker run --rm -it \
		--name $(CONTAINER_NAME) \
		--env-file $(ENV_FILE) \
		-p 8000:8000 \
		$(APP_NAME):$(IMAGE_TAG)

stop:
	docker stop $(CONTAINER_NAME) || true

clean:
	docker rm -f $(CONTAINER_NAME) || true


fresh_run: clean build run