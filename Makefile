PYTHON = .venv/bin/python
SETTINGS = config.settings.production

.PHONY: deploy pull migrate static restart logs shell

deploy: pull migrate static restart
	@echo "Déploiement terminé."

pull:
	git pull origin main

migrate:
	$(PYTHON) manage.py migrate --settings=$(SETTINGS)

static:
	$(PYTHON) manage.py collectstatic --noinput --settings=$(SETTINGS)

restart:
	sudo systemctl restart qolloq

logs:
	sudo journalctl -u qolloq -f

shell:
	$(PYTHON) manage.py shell --settings=$(SETTINGS)

createsuperuser:
	$(PYTHON) manage.py createsuperuser --settings=$(SETTINGS)
