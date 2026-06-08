# QolloQ — Notes de conception

Outil de gestion d'événements scientifiques (colloques, journées d'étude, workshops).
Pensé en parallèle d'Edito, sur le même modèle : compte flottant, rattaché à plusieurs événements.

---

## Positionnement

- Outil distinct d'Edito, mais partageant le même compte utilisateur.
- À terme : hébergés sous un domaine commun (ex. `edito.nom.fr` / `qolloq.nom.fr`).
- Même stack technique : Django + Alpine.js + PostgreSQL + Tailwind.
- Pas de fusion des données — seul le modèle `User` est partagé.

---

## Fonctionnalités identifiées

### Soumission de propositions ⚠️ à rediscuter (flux public)

**L'organisateur peut toujours saisir ou modifier n'importe quelle soumission depuis
son interface**, sans passer par le lien public — pour les soumissions hors délai reçues
par email, les intervenants invités, ou les corrections à faire pour quelqu'un.



Pistes discutées, non arrêtées :
- Lien public par événement (`/soumettre/ev-slug/`) diffusé par l'organisateur.
- Ouverture/fermeture des soumissions configurable (date limite).
- Formulaire en ligne : titre, résumé (textarea), mots-clés, format souhaité,
  auteurs (prénom, nom, institution, email), disponibilités.
- Pas de fichier Word/PDF à ce stade — résumé saisi directement.
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
- Export PDF du programme (WeasyPrint, déjà utilisé dans Edito).
- Exports complémentaires envisageables : HTML public, iCal.

### Formulaire logistique (post-acceptation)
- Formulaire envoyé par lien aux intervenants confirmés.
- Champs configurables par l'organisateur : jours de participation, régime alimentaire,
  allergènes, hébergement, heure d'arrivée, etc.
- Réponses centralisées et consultables par les organisateurs.

### Documents
- Hébergement simple de fichiers (reçus, devis, bons de commande, infos pratiques).
- Même module que le `_documents_panel` d'Edito — réutilisable directement.

### Emails collectifs
- Envoi ciblé : tous les acceptés, tous les intervenants d'un panel, tous les participants.
- Suivi d'envoi minimal.

### Vue calendrier
- Grille temporelle : jours en colonnes, heures en lignes, sessions placées dans leur créneau.
- Gestion des sessions parallèles (plusieurs salles en simultané sur le même créneau).
- Deux contextes d'utilisation :
  - **Organisateur** : vue édition pour visualiser et construire le programme.
  - **Participant** : vue lecture, exportable dans le site statique public.
- Comparable à ce que génère SciencesConf — point fort à couvrir.
- Rendu CSS pur (grille `grid-template-rows` par tranches horaires) — pas de librairie
  calendrier externe nécessaire pour un événement de 1 à 5 jours.

### Site public statique
- Bouton "Publier le site" dans l'interface organisateur.
- Django génère un dossier HTML autonome (`render_to_string` + copie des assets).
- Pages : index (infos générales), programme détaillé, intervenants et résumés.
- Templates dédiés "mode export" avec URLs relatives (différents des templates d'administration).
- Hébergement : sous-dossier nginx sur le VPS, GitHub Pages, Netlify, ou archive ZIP.
- Outil de comparaison : SciencesConf génère aussi un site public — c'est un point fort
  qu'on veut couvrir, sans dépendance externe (pas de Quarto, pas de build step).
- Limite assumée : pas de formulaire interactif (inscriptions → lien externe).
- Zéro dépendance supplémentaire sur le VPS — 100% Django + WeasyPrint déjà en place.

---

## Modèle de données (esquisse)

```
Utilisateur (compte partagé avec Edito)
└── Membre d'un ou plusieurs Événements
    (rôle : organisateur / comité scientifique / intervenant)

Événement
├── Propositions de communication
│   └── Évaluations (vote comité)
├── Intervenants (confirmés)
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

## Estimation de la complexité

- **~1,5x Edito** avec un constructeur de programme semi-structuré.
- **~2x Edito** si on ajoute du drag-and-drop dans le constructeur de programme.
- Les modules soumission, vote, formulaire logistique et documents sont du CRUD
  bien structuré, comparable à ce qu'Edito fait déjà.
- Le constructeur de programme est le seul morceau vraiment nouveau et potentiellement
  complexe.

---

## Infrastructure

- Même VPS (2 vCPU, 4 Go RAM) : largement suffisant.
- Même instance PostgreSQL, même gunicorn, même nginx — un bloc de config supplémentaire.
- Domaine : soit sous-domaine d'un domaine commun, soit domaine séparé (~10-15€/an).
- Migration simple depuis `edito-revue.fr` si on passe à un domaine global — à faire
  avant le lancement public de QolloQ, pas avant.

---

## Réutilisabilité depuis Edito

### Drag-and-drop (implémenté dans Edito, juin 2026)

Edito a un système complet de drag-and-drop pour réordonner les articles entre sections.
Il se transpose directement à QolloQ :

| Edito | QolloQ |
|---|---|
| `Section` | `Session` |
| `Article` | `Communication` |
| `SectionReorderView` | `SessionReorderView` |
| `ArticleReorderView` | `CommunicationReorderView` |

**Ce qui se réutilise tel quel :**
- `sortable.min.js` — même fichier static
- Pattern backend : POST `[{id, order}]` → `bulk_update` avec validation complète
  (doublons, IDs valides, état archivé)
- Pattern frontend : `initList()`, `reorderAll()`, `postJson()`, groupe Sortable
  permettant le déplacement d'une session à l'autre
- CSS : `.drag-handle`, `.sortable-ghost`

**Ce qui change :**
- Noms de modèles et URLs
- Condition d'édition (événement clôturé vs numéro archivé)
- Template HTML des panneaux

---

## Ce qui reste ouvert

- Nom du projet global (portail commun Edito + QolloQ).
- Domaine associé.
- Périmètre exact du formulaire logistique (champs fixes vs configurables).
- Niveau de sophistication du constructeur de programme (formulaire vs drag-and-drop).
