# QolloQ — Notes de conception

Outil de gestion d'événements scientifiques (colloques, journées d'étude, workshops).
Pensé en parallèle d'Edito, sur le même modèle : compte flottant, rattaché à plusieurs événements.

---

## Contexte : Edito

QolloQ est conçu comme le compagnon d'**Edito**, un outil de gestion éditoriale pour
revues académiques (déjà en production). Comprendre Edito aide à comprendre QolloQ.

**Ce qu'est Edito :**
- Gestion du cycle de vie d'un numéro de revue : soumission d'articles → relectures
  → révisions → publication.
- Multi-revues : un compte utilisateur peut être membre de plusieurs revues.
- Stack : Django 6 + Alpine.js + PostgreSQL + Tailwind + WeasyPrint (PDF).
- Hébergé sur VPS Infomaniak (Ubuntu 24.04, 2 vCPU, 4 Go RAM, nginx + gunicorn).
- Repo : https://github.com/Hsbtqemy/larevue

**Patterns établis dans Edito, réutilisables dans QolloQ :**
- Vues basées sur `View` (pas de CBV génériques Django) avec mixins custom
  (`JournalMemberRequiredMixin`, `SuperuserRequiredMixin`).
- Modifications inline via `fetch()` JSON (pas de rechargement de page).
- Modales Alpine.js avec `x-teleport="body"`.
- Drag-and-drop via Sortable.js : `POST [{id, order}]` → `bulk_update`.
- Export PDF via WeasyPrint.
- Module documents attachés (`_documents_panel`) : réutilisable directement.
- Système de rôles : superuser (admin global) / membre (accès à une entité).

**Ce qui est partagé entre Edito et QolloQ :**
- Modèle `User` uniquement — chaque projet a sa propre base de données et ses
  propres tables. Pas de données croisées.
- Design system (CSS, composants Alpine.js) — à dupliquer et adapter.

---

## Positionnement

- Projet Django **séparé** d'Edito (repo distinct, base de données distincte).
- Compte utilisateur **commun** : un chercheur qui utilise Edito et QolloQ n'a
  qu'un seul compte. Mécanisme exact (SSO ou inscription distincte) non arrêté.
- À terme : hébergés sous un domaine commun (ex. `edito.nom.fr` / `qolloq.nom.fr`).
- Outil de comparaison direct : **SciencesConf** (CCSD/CNRS) — fonctionnel mais
  interface datée et surdimensionné pour les petits événements. QolloQ cible les
  petits et moyens événements (journées d'étude, workshops, colloques ~50-300 pers.).

---

## Architecture technique

```
QolloQ/
├── apps/
│   ├── accounts/       — User partagé (même modèle qu'Edito)
│   ├── events/         — Événement, Membership (rôles)
│   ├── submissions/    — Propositions, Évaluations
│   ├── programme/      — Sessions, Communications, Événements annexes
│   ├── logistics/      — Formulaire logistique, Réponses
│   ├── documents/      — Fichiers attachés (réutilisé depuis Edito)
│   └── emails/         — Campagnes email
├── templates/
├── static/
└── config/
```

**Stack :** Django 6 + Alpine.js + PostgreSQL + Tailwind + WeasyPrint
**Pas de dépendances supplémentaires** par rapport à Edito, sauf éventuellement
une librairie email (à évaluer selon le périmètre des campagnes email).

---

## Modèle de données (esquisse)

```
Utilisateur (compte partagé avec Edito)
└── Membre d'un ou plusieurs Événements
    (rôle : organisateur / comité scientifique / intervenant)

Événement
├── Propositions de communication
│   └── Évaluations (avis par membre du comité)
├── Intervenants (confirmés après acceptation)
│   └── Réponse formulaire logistique
├── Formulaire logistique (champs configurés par l'organisateur)
├── Programme
│   ├── Sessions (créneau + lieu + modérateur)
│   │   └── Communications programmées (ordre, durée)
│   └── Événements annexes (repas, pauses, plénières)
├── Documents (hébergement simple)
└── Campagnes email
```

---

## Fonctionnalités identifiées

### Soumission de propositions ⚠️ flux public à rediscuter

**L'organisateur peut toujours saisir ou modifier n'importe quelle soumission depuis
son interface**, sans passer par le lien public — pour les soumissions hors délai
reçues par email, les intervenants invités, ou les corrections à faire pour quelqu'un.

Pistes discutées pour le flux public, non encore arrêtées :
- Lien public par événement (`/soumettre/ev-slug/`) diffusé par l'organisateur.
- Ouverture/fermeture des soumissions configurable (date limite).
- Formulaire en ligne : titre, résumé (textarea), mots-clés, format souhaité,
  auteurs (prénom, nom, institution, email), disponibilités.
- Pas de fichier Word/PDF à ce stade — résumé saisi directement dans le formulaire.
- Pas de compte obligatoire : confirmation par email avec lien personnel tokenisé
  permettant de consulter, modifier ou retirer la soumission jusqu'à la date limite.
- Renvoi du lien possible en entrant son email sur la page publique.

### Évaluation par le comité scientifique

Outil de **délibération**, pas de vote majoritaire automatique.

**Principe :**
- Chaque évaluateur donne son avis indépendamment (pour / contre / hésitant + commentaire libre).
- Les avis alimentent la discussion collective — la décision finale est prise par l'organisateur
  manuellement, pas par algorithme.
- Pas de calcul "majorité = accepté".

**Options configurables par événement :**
- **Visibilité des avis** : les évaluateurs voient les avis des autres après avoir soumis
  le leur / ou seulement après ouverture explicite d'une phase de délibération par l'organisateur.
- **Anonymat entre évaluateurs** : chacun voit qui a dit quoi / les avis sont anonymisés
  entre membres du comité.
- **Assignation** : manuelle par l'organisateur (chaque évaluateur reçoit un sous-ensemble
  de propositions) / tout le comité évalue toutes les propositions.

**Option double-aveugle** (anonymisation des propositions vis-à-vis des évaluateurs) :
configurable séparément.

### Programme
- Sessions : créneau horaire + lieu + modérateur + communications ordonnées avec durées.
- Événements annexes intercalés : pauses, repas, conférences plénières, AG, etc.
- Interface semi-structurée (formulaire structuré, pas forcément drag-and-drop).
- Export PDF du programme (WeasyPrint, déjà en place dans Edito).
- Exports complémentaires envisageables : HTML public, iCal.

### Vue calendrier
- Grille temporelle : jours en colonnes, heures en lignes, sessions placées dans leur créneau.
- Gestion des sessions parallèles (plusieurs salles en simultané sur le même créneau).
- Deux contextes d'utilisation :
  - **Organisateur** : vue édition pour visualiser et construire le programme.
  - **Participant** : vue lecture, exportable dans le site statique public.
- Rendu CSS pur (`grid-template-rows` par tranches horaires) — pas de librairie
  calendrier externe nécessaire pour un événement de 1 à 5 jours.

### Formulaire logistique (post-acceptation)
- Formulaire envoyé par lien aux intervenants confirmés.
- Champs configurables par l'organisateur : jours de participation, régime alimentaire,
  allergènes, hébergement, heure d'arrivée, etc.
- Réponses centralisées et consultables par les organisateurs.

### Documents
- Hébergement simple de fichiers (reçus, devis, bons de commande, infos pratiques).
- Même module que `_documents_panel` dans Edito — réutilisable directement.

### Emails collectifs
- Envoi ciblé : tous les acceptés, tous les intervenants d'un panel, tous les participants.
- Suivi d'envoi minimal.

### Site public statique
- Bouton "Publier le site" dans l'interface organisateur.
- Django génère un dossier HTML autonome (`render_to_string` + copie des assets).
- Pages : index (infos générales), programme détaillé, intervenants et résumés.
- Templates dédiés "mode export" avec URLs relatives.
- Hébergement : sous-dossier nginx sur le VPS, GitHub Pages, Netlify, ou archive ZIP.
- Limite assumée : pas de formulaire interactif (inscriptions → lien externe).
- Zéro dépendance supplémentaire sur le VPS.

---

## Réutilisabilité depuis Edito

### Drag-and-drop (implémenté dans Edito, juin 2026)

| Edito | QolloQ |
|---|---|
| `Section` | `Session` |
| `Article` | `Communication` |
| `SectionReorderView` | `SessionReorderView` |
| `ArticleReorderView` | `CommunicationReorderView` |

**Ce qui se réutilise tel quel :**
- `sortable.min.js` — même fichier static
- Pattern backend : POST `[{id, order}]` → `bulk_update` avec validation complète
  (doublons, IDs valides, état archivé/clôturé)
- Pattern frontend : `initList()`, `reorderAll()`, `postJson()`, groupe Sortable
  permettant le déplacement d'une session à l'autre
- CSS : `.drag-handle`, `.sortable-ghost`

**Ce qui change :**
- Noms de modèles et URLs
- Condition d'édition (événement clôturé vs numéro archivé)
- Template HTML des panneaux

---

## Estimation de la complexité

- **~1,5x Edito** avec un constructeur de programme semi-structuré.
- **~2x Edito** si on ajoute du drag-and-drop dans le constructeur de programme.
- Les modules soumission, évaluation, formulaire logistique et documents sont du CRUD
  bien structuré, comparable à ce qu'Edito fait déjà.
- Le constructeur de programme et la vue calendrier sont les morceaux les plus nouveaux.

---

## Infrastructure

- Même VPS (2 vCPU, 4 Go RAM) : largement suffisant.
- Même instance PostgreSQL, même gunicorn, même nginx — un bloc de config supplémentaire.
- Domaine : soit sous-domaine d'un domaine commun, soit domaine séparé (~10-15€/an).
- Migration depuis `edito-revue.fr` vers un domaine global à faire avant le lancement
  public de QolloQ, pas avant.

---

## Ce qui reste ouvert

- Nom du projet global (portail commun Edito + QolloQ) et domaine associé.
- Mécanisme de compte partagé (SSO léger ou inscription distincte).
- Flux public de soumission : voir section dédiée ⚠️.
- Périmètre exact du formulaire logistique (champs fixes vs entièrement configurables).
- Niveau de sophistication du constructeur de programme (formulaire vs drag-and-drop).
- Périmètre des campagnes email (simple envoi vs suivi d'ouverture, etc.).
