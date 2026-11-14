# Requêtes Flux (InfluxDB)

Requêtes temporelles du projet RFID, testées sur les données générées par `backend/generateur.py`.

## Paramètres de la base

| Élément | Valeur |
|---|---|
| URL | `http://localhost:8086` |
| Organisation | `projet` |
| Bucket des événements | `acces` (rétention 90 jours) |
| Bucket du résumé horaire | `acces_horaire` (rétention 1 an) |

## Modèle de données

### Bucket `acces` : un point par passage de badge

| Élément | Contenu |
|---|---|
| Mesure | `access_events` |
| Tags (indexés, pour filtrer) | `room` (salle), `role`, `result` (`granted` ou `denied`) |
| Champs (valeurs) | `uid_hash` (UID haché), `nom`, `reason`, `latency_ms` |
| Horodatage | automatique (heure de l'événement) |

Valeurs possibles de `reason` : `ok`, `badge_inconnu`, `badge_revoque`, `salle_non_autorisee`.

L'UID du badge n'est **jamais** stocké en clair : seul un hachage (`uid_hash`) est enregistré, et ce n'est pas un tag. Un tag par UID créerait une série par badge et ferait exploser l'index (problème de cardinalité).

### Bucket `acces_horaire` : un total par heure

| Élément | Contenu |
|---|---|
| Mesure | `access_hourly` |
| Tags | `room`, `role`, `result` |
| Champ | `count` (nombre d'accès dans l'heure) |

Ce bucket est rempli automatiquement par la tâche `downsample_acces_horaire`, exécutée toutes les heures.

## Mise en place d'InfluxDB (à faire une fois par machine)

Chaque personne a son propre InfluxDB local (volume Docker) : le bucket `acces_horaire` et la tâche de downsampling ne se transmettent pas par Git. Il faut les créer sur chaque machine qui doit produire le résumé horaire.

### 0. Prérequis

```bash
cd backend
docker compose up -d
```

Ouvrir `http://localhost:8086` et se connecter avec le username et le mot de passe définis dans `backend/docker-compose.yml` (variables `DOCKER_INFLUXDB_INIT_*`).

### 1. Bucket `acces` (créé automatiquement)

Créé au démarrage par le `docker-compose.yml`. Vérifier dans **Load Data**, **Buckets** que la rétention est de **90 jours**.

### 2. Créer le bucket `acces_horaire`

1. **Load Data**, **Buckets**, **Create Bucket**.
2. Name : `acces_horaire`.
3. Delete Data : **Older Than**, **1 year**.
4. **Create**.

### 3. Créer la tâche de downsampling

1. Menu **Tasks**, **Create Task**, **New Task**.
2. À gauche : Name = `downsample_acces_horaire`, Schedule = **Every**, Every = `1h`.
3. Dans l'éditeur, coller **uniquement** la requête ci-dessous (sans ligne `option task`, l'interface l'ajoute elle-même) :

```flux
from(bucket: "acces")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "access_events" and r._field == "latency_ms")
  |> group(columns: ["room", "role", "result"])
  |> aggregateWindow(every: 1h, fn: count, createEmpty: false)
  |> set(key: "_measurement", value: "access_hourly")
  |> set(key: "_field", value: "count")
  |> to(bucket: "acces_horaire", org: "projet")
```

4. **Save**. La tâche doit apparaître avec le statut **Active**.

Cette tâche compte, toutes les heures, les accès de la dernière heure par salle, rôle et résultat, et écrit le total dans `acces_horaire`. Les lignes `set` sont indispensables : sans la colonne `_field`, `to()` échoue (erreur `table has no _field column`).

### 4. Vérifier que tout marche

```bash
cd backend
source venv/bin/activate
python generateur.py --test-tache
```

Puis dans InfluxDB : **Tasks**, la tâche, **Run Task**, et vérifier que le dernier run est en **success**. Ensuite :

```bash
docker compose exec influxdb influx query 'from(bucket:"acces_horaire") |> range(start:-3h) |> filter(fn:(r)=>r._measurement=="access_hourly")'
```

Des lignes avec `_field` = `count` et une valeur dans `_value` confirment que le downsampling fonctionne. Les lancements manuels produisent aussi des points partiels (horodatés à l'heure du lancement) : les exécutions automatiques, elles, tombent à l'heure pile.

## Remarques communes aux requêtes

- Les heures sont en **UTC**. L'Algérie est en UTC+1 : ajouter 1 heure pour l'heure locale. Grafana convertit tout seul dans le fuseau du navigateur.
- On filtre sur le champ `latency_ms` parce que chaque événement en possède un. Cela évite de compter plusieurs fois le même accès (un point contient 4 champs).
- Pour exécuter une requête : InfluxDB, **Data Explorer**, **Script Editor**, coller le code, **Submit**. Une seule requête à la fois par onglet.

## Requête 1 : entrées acceptées par heure et par salle

```flux
from(bucket: "acces")
  |> range(start: -7d)
  |> filter(fn: (r) => r._measurement == "access_events" and r._field == "latency_ms" and r.result == "granted")
  |> group(columns: ["room"])
  |> aggregateWindow(every: 1h, fn: count, createEmpty: false)
```

Résultat : un tableau par salle, avec une ligne par heure (`_time`, fin de la fenêtre) et le nombre d'entrées dans `_value`.

Pour compter les **refus** au lieu des entrées, remplacer `"granted"` par `"denied"`. Pour compter **tous** les passages, supprimer la condition `and r.result == "granted"`.

## Requête 2 : détection d'anomalie, plus de 5 refus de suite dans une salle

```flux
from(bucket: "acces")
  |> range(start: -30d)
  |> filter(fn: (r) => r._measurement == "access_events" and r._field == "latency_ms")
  |> group(columns: ["room"])
  |> sort(columns: ["_time"])
  |> stateCount(fn: (r) => r.result == "denied", column: "refus_de_suite")
  |> filter(fn: (r) => r.refus_de_suite > 5)
```

Principe : `stateCount` ajoute une colonne `refus_de_suite` qui compte les refus consécutifs dans la salle et repasse à `-1` dès qu'un accès est accepté. Le filtre final ne garde que les refus au-delà du 5e d'une même série.

Résultat : une ligne par refus au-delà du 5e. Une série de 10 refus produit donc 5 lignes (valeurs 6 à 10). La valeur maximale d'une série donne sa longueur.

## Requête 3 : lire le résumé horaire (bucket `acces_horaire`)

```flux
from(bucket: "acces_horaire")
  |> range(start: -30d)
  |> filter(fn: (r) => r._measurement == "access_hourly")
```

Résultat : les comptages par heure, avec les tags `room`, `role` et `result`. Ce bucket étant conservé plus longtemps que `acces`, c'est lui qu'il faut interroger pour les graphiques sur de longues périodes.

## Utilisation dans Grafana

Dans un panneau Grafana avec la source de données InfluxDB (langage Flux), remplacer les bornes fixes par les variables Grafana :

```flux
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
```

et, pour la fenêtre d'agrégation de la requête 1, `every: 1h` peut être gardé tel quel (comptage par heure) ou remplacé par `every: v.windowPeriod` pour qu'elle s'adapte au zoom.

Ces adaptations Grafana n'ont pas encore été testées : les requêtes 1, 2 et 3 ci-dessus l'ont été dans InfluxDB.

## Générer des données de test

```bash
cd backend
source venv/bin/activate
python generateur.py                # 30 jours d'historique
python generateur.py --jours 14     # 14 jours
python generateur.py --test-tache   # 30 événements dans la dernière heure (test du downsampling)
```

Le générateur n'écrit jamais d'événement de plus de 85 jours (sinon la rétention de 90 jours les supprimerait aussitôt) et ajoute quelques rafales de plus de 5 refus de suite pour tester la requête 2.