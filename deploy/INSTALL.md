# Installation sur le VPS

Ubuntu 24.04, même serveur qu'Edito. Base de données séparée.

## 1. Cloner le dépôt

```bash
sudo mkdir -p /var/www/qolloq
sudo chown ubuntu:ubuntu /var/www/qolloq
git clone https://github.com/Hsbtqemy/QolloQ.git /var/www/qolloq
cd /var/www/qolloq
```

## 2. Environnement Python

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements/production.txt
```

## 3. Variables d'environnement

```bash
cp .env.example .env
nano .env   # remplir SECRET_KEY, DB_PASSWORD, ALLOWED_HOSTS (IP du serveur)
```

Générer une SECRET_KEY :
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

## 4. Base de données

```bash
sudo -u postgres createdb qolloq
sudo -u postgres createuser qolloq_user
sudo -u postgres psql -c "ALTER USER qolloq_user PASSWORD 'mot_de_passe';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE qolloq TO qolloq_user;"
# PostgreSQL 15+ : droit sur le schéma public
sudo -u postgres psql -d qolloq -c "GRANT ALL ON SCHEMA public TO qolloq_user;"
```

## 5. Migrations + static

```bash
make migrate
make static
```

## 6. Superutilisateur

```bash
make createsuperuser
```

## 7. Service systemd

```bash
sudo cp deploy/qolloq.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable qolloq
sudo systemctl start qolloq
sudo systemctl status qolloq
```

## 8. Nginx

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/qolloq
sudo ln -s /etc/nginx/sites-available/qolloq /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 9. Déploiements suivants

```bash
cd /var/www/qolloq
make deploy
```

## Ajouter SSL (une fois le domaine pointé)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d qolloq.exemple.fr
```

Puis dans `.env` :
```
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```
Et décommenter `SECURE_SSL_REDIRECT` dans `config/settings/production.py`.
