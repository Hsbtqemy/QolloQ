# Installation sur le VPS

Ubuntu 24.04, même serveur qu'Edito. Base de données séparée.

## 1. Cloner le dépôt

Le dépôt est privé — utiliser une clé SSH.

```bash
# Créer le user dédié
sudo useradd -m -s /bin/bash qolloq

# Générer une clé SSH pour le user qolloq
sudo -u qolloq ssh-keygen -t ed25519 -C "vps-qolloq" -f /home/qolloq/.ssh/id_ed25519 -N ""
sudo cat /home/qolloq/.ssh/id_ed25519.pub
# → Ajouter la clé dans GitHub : repo QolloQ → Settings → Deploy keys
```

```bash
sudo -u qolloq git clone git@github.com:Hsbtqemy/QolloQ.git /home/qolloq/qolloq
```

## 2. Environnement Python

```bash
sudo -u qolloq python3 -m venv /home/qolloq/qolloq/venv
sudo -u qolloq /home/qolloq/qolloq/venv/bin/pip install -r /home/qolloq/qolloq/requirements/production.txt
```

## 3. Variables d'environnement

```bash
sudo -u qolloq cp /home/qolloq/qolloq/.env.example /home/qolloq/qolloq/.env
sudo -u qolloq nano /home/qolloq/qolloq/.env
```

Générer une SECRET_KEY :
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

À remplir au minimum :
- `SECRET_KEY`
- `ALLOWED_HOSTS` → IP publique du serveur
- `DB_USER` et `DB_PASSWORD`
- `SITE_URL=http://<IP>`
- Laisser `SESSION_COOKIE_SECURE=False` et `CSRF_COOKIE_SECURE=False` tant que le site tourne sans HTTPS

## 4. Base de données

```bash
sudo -u postgres createuser qolloq_user
sudo -u postgres psql -c "ALTER USER qolloq_user PASSWORD 'mot_de_passe';"
sudo -u postgres createdb qolloq --owner=qolloq_user
sudo -u postgres psql -d qolloq -c "GRANT ALL ON SCHEMA public TO qolloq_user;"
```

## 5. Migrations + static

```bash
sudo -u qolloq /home/qolloq/qolloq/venv/bin/python /home/qolloq/qolloq/manage.py migrate --settings=config.settings.production
sudo -u qolloq /home/qolloq/qolloq/venv/bin/python /home/qolloq/qolloq/manage.py collectstatic --noinput --settings=config.settings.production
```

## 6. Superutilisateur

```bash
sudo -u qolloq /home/qolloq/qolloq/venv/bin/python /home/qolloq/qolloq/manage.py createsuperuser --settings=config.settings.production
```

## 7. Logs + service systemd

```bash
sudo mkdir -p /var/log/qolloq
sudo chown qolloq:www-data /var/log/qolloq

sudo cp /home/qolloq/qolloq/deploy/qolloq.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable qolloq
sudo systemctl start qolloq
sudo systemctl status qolloq
```

## 8. Nginx

```bash
# Rendre le home traversable par www-data (nginx)
sudo chmod o+x /home/qolloq

sudo cp /home/qolloq/qolloq/deploy/nginx.conf /etc/nginx/sites-available/qolloq
# Éditer server_name avec l'IP réelle
sudo nano /etc/nginx/sites-available/qolloq

sudo ln -s /etc/nginx/sites-available/qolloq /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 9. Déploiements suivants

```bash
cd /home/qolloq/qolloq
sudo -u qolloq git pull
sudo -u qolloq venv/bin/python manage.py migrate --settings=config.settings.production
sudo -u qolloq venv/bin/python manage.py collectstatic --noinput --settings=config.settings.production
sudo systemctl restart qolloq
```

## Ajouter SSL (une fois le domaine pointé)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d qolloq.exemple.fr
```

Puis dans `/home/qolloq/qolloq/.env` :
```
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```
Et décommenter `SECURE_SSL_REDIRECT` dans `config/settings/production.py`.
