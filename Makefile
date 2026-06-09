PYTHON = venv/bin/python
PIP    = venv/bin/pip
SETTINGS = config.settings.production

.PHONY: deploy pull deps migrate static restart logs shell createsuperuser

deploy: pull deps migrate static restart
	@echo "Déploiement terminé."

pull:
	sudo -u qolloq git pull

deps:
	sudo -u qolloq $(PIP) install -q -r requirements/production.txt

migrate:
	sudo -u qolloq $(PYTHON) manage.py migrate --settings=$(SETTINGS)

static:
	sudo -u qolloq $(PYTHON) manage.py collectstatic --noinput --settings=$(SETTINGS)

restart:
	sudo systemctl restart qolloq

logs:
	sudo journalctl -u qolloq -f

shell:
	sudo -u qolloq $(PYTHON) manage.py shell --settings=$(SETTINGS)

createsuperuser:
	sudo -u qolloq $(PYTHON) manage.py createsuperuser --settings=$(SETTINGS)
