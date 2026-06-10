# QolloQ — CLAUDE.md

Outil Django de gestion d'événements scientifiques (colloques, journées d'étude, workshops).
Concurrent direct : SciencesConf. Cible : petits/moyens événements, 50–300 personnes.

## Référence : Edito

Projet Django jumeau déjà en production.
Repo : https://github.com/Hsbtqemy/larevue
Toujours vérifier comment Edito fait les choses avant d'inventer un pattern.

## Stack

Django 6 + Alpine.js + PostgreSQL + Tailwind + WeasyPrint
Hébergement : VPS Infomaniak (Ubuntu 24.04, 2 vCPU, 4 Go RAM, nginx + gunicorn)
Même VPS qu'Edito, base de données séparée.

## Décisions arrêtées

- **Inscription distincte** d'Edito — pas de SSO, pas de base partagée. Seul le modèle
  `User` est structurellement identique. Un hub commun est un projet futur.
- **Vues** : `View` + mixins custom. Pas de CBV génériques Django (LoginView/FormView…
  sont ok, les génériques CRUD non).
- **Modifications inline** : `fetch()` JSON sans rechargement de page.
- **Modales** : Alpine.js avec `x-teleport="body"`.
- **Drag-and-drop** : Sortable.js, pattern `POST [{id, order}]` → `bulk_update`.

## Structure des apps

```
apps/
├── accounts/    — User (AbstractUser, email unique, pas de username)
├── events/      — Événement, Membership (rôles : organisateur / comité / intervenant)
├── submissions/ — Propositions, Évaluations
├── programme/   — Sessions, Communications, Événements annexes
├── logistics/   — Formulaire logistique, Réponses
├── documents/   — Fichiers attachés (réutilisé depuis Edito _documents_panel)
└── emails/      — Campagnes email
```

## Modèle de données (esquisse)

```
User
└── Membership → Événement (rôle : organisateur / comité / intervenant)

Événement
├── Propositions → Évaluations (avis comité)
├── Intervenants (post-acceptation) → Réponse logistique
├── Formulaire logistique (champs configurables)
├── Programme → Sessions → Communications
│                        └── Événements annexes (pauses, repas, plénières)
├── Documents
└── Campagnes email
```

## Infrastructure QolloQ (patterns natifs)

| Besoin | Implémentation |
|---|---|
| Email transactionnel HTML+text | `apps/core/mail.py` → `send_template_email()` |
| Templates email éditables (superadmin) | `apps/emails/models.py` → `EmailTemplate` — sujet + corps FR/EN éditables via `/staff/email-templates/` |
| Nom d'expéditeur par événement | `Event.from_name` — affiché dans la boîte de réception, fallback sur `event.name` |
| Notification organisateur (nouvelle soumission) | `apps/submissions/mail.py` → `send_new_submission_notification()` |

## Points encore ouverts

- **Notifications de décision** (accepté/refusé aux soumettants) — délibérément différé.
  Nécessite : interface de sélection/confirmation, calibration de l'envoi en masse,
  garde-fous contre les envois accidentels avant validation finale.
- **Suivi campagnes email** — envoi simple implémenté ; open rate / click tracking non prévu.
- **Hub commun avec Edito** — SSO ou base utilisateurs partagée, projet futur.

## Patterns à réutiliser depuis Edito

| Besoin | Source dans Edito |
|---|---|
| BaseModel (soft-delete, timestamps) | `apps/core/models.py` |
| CRUD mixins | `apps/core/views.py` |
| Documents attachés | `templates/partials/_documents_panel.html` |
| Drag-and-drop Sortable.js | `templates/issues/detail.html` (lignes 14–89) |
| Export PDF WeasyPrint | `apps/issues/views.py` |
| Auth django-allauth email-based | `apps/accounts/` |
