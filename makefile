deploy:
	aws ecr get-login-password --region us-east-2 --profile wise | docker login --username AWS --password-stdin 935364008466.dkr.ecr.us-east-2.amazonaws.com/wisematic/erp-core
	AWS_PROFILE=wise skaffold run

clear_migrate:
	cd api && rm db.sqlite3
	cd api && find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
	cd api && find . -path "*/migrations/*.pyc" -delete

migrate:
	cd api && python manage.py makemigrations
	cd api && python manage.py migrate

clean_migrate:
	make clear_migrate
	make migrate
