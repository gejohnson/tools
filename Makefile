.PHONY: dev run build docker-build docker-run

dev:
	APP_PASSWORD=changeme BASE_URL=http://localhost:8000 uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run:
	APP_PASSWORD=changeme BASE_URL=http://localhost:8000 uvicorn app.main:app --host 0.0.0.0 --port 8000

build:
	python -m py_compile app/main.py

docker-build:
	docker build -t yt-podcast-tool .

docker-run:
	docker run --rm -p 8000:8000 -e APP_PASSWORD=changeme -e BASE_URL=http://localhost:8000 -v $$(pwd)/data:/app/data yt-podcast-tool
