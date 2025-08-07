.PHONY: install run test clean lint format dev setup

install:
	pip install -r requirements.txt

setup: install
	python -c "import asyncio; from app.database.session import init_db; asyncio.run(init_db())"

run:
	python run.py

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v

test-coverage:
	pytest tests/ --cov=app --cov-report=html --cov-report=term

lint:
	pylint app/ tests/

format:
	black app/ tests/
	isort app/ tests/

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -f .coverage
	rm -f espressobot.db

docker-build:
	docker build -t espressobot-langgraph .

docker-run:
	docker run -p 8000:8000 --env-file .env espressobot-langgraph