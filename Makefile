.PHONY: install seed backend frontend deploy-ec2 deploy-ecs

install:
	pip install -r backend/requirements.txt
	cd frontend && npm install

seed:
	python -m backend.rag.indexer

backend:
	uvicorn backend.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

# Deploy to AWS (fill in deploy/cloudformation/parameters/ first)
deploy-ec2:
	bash deploy/cloudformation/deploy-ec2.sh

deploy-ecs:
	bash deploy/cloudformation/deploy-ecs.sh

# Simulate ECS locally (Docker + Postgres + Redis)
ecs-local:
	docker compose -f deploy/ecs/docker-compose.local.yml up --build
