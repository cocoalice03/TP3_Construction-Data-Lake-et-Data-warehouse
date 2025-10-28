# 🎯 Guide de Décision - Data Lake

Ce guide vous aide à prendre les bonnes décisions lors de la configuration de nouveaux feeds.

---

## 📊 Choix du Type de Feed

### Stream vs Table

| Critère | Stream | Table |
|---------|--------|-------|
| **Nature des données** | Événements individuels | Agrégations calculées |
| **Mutabilité** | Immuable | Mutable (recalculé) |
| **Historique** | Complet, chaque événement | Snapshots périodiques |
| **Taille** | Croissance continue | Taille relativement stable |
| **Exemple** | Transactions, logs, clics | Totaux, moyennes, compteurs |

### Arbre de Décision

```
Vos données représentent-elles des événements individuels ?
│
├─ OUI → Est-ce que chaque événement doit être conservé ?
│         │
│         ├─ OUI → STREAM (mode APPEND)
│         │        Exemple: transaction_stream
│         │
│         └─ NON → TABLE (mode OVERWRITE)
│                  Exemple: daily_summary
│
└─ NON → S'agit-il d'agrégations ou de calculs ?
          │
          ├─ OUI → TABLE (mode OVERWRITE)
          │        Exemple: user_transaction_summary
          │
          └─ NON → Revoir la nature des données
```

---

## 🗂️ Choix du Partitionnement

### Date vs Version

| Critère | Date | Version |
|---------|------|---------|
| **Type de données** | Événements temporels | Snapshots d'état |
| **Requêtes typiques** | Par période | Dernière version |
| **Croissance** | Linéaire dans le temps | Contrôlée (rétention) |
| **Maintenance** | Suppression par date | Suppression par version |
| **Exemple** | Transactions quotidiennes | Agrégations hebdomadaires |

### Arbre de Décision

```
Vos requêtes filtrent-elles par date ?
│
├─ OUI → Les données arrivent-elles en continu ?
│         │
│         ├─ OUI → PARTITIONNEMENT PAR DATE
│         │        Structure: year=YYYY/month=MM/day=DD/
│         │
│         └─ NON → PARTITIONNEMENT PAR VERSION
│                  Structure: version=vX/
│
└─ NON → Avez-vous besoin d'historique de versions ?
          │
          ├─ OUI → PARTITIONNEMENT PAR VERSION
          │        Rétention: 7-30 versions
          │
          └─ NON → PARTITIONNEMENT PAR DATE
                   (par défaut pour streams)
```

---

## 💾 Choix du Mode de Stockage

### APPEND vs OVERWRITE vs IGNORE

| Mode | Utilisation | Avantages | Inconvénients |
|------|-------------|-----------|---------------|
| **APPEND** | Événements immuables | Historique complet, audit | Croissance continue |
| **OVERWRITE** | Agrégations, snapshots | Pas de duplication | Perte de l'historique |
| **IGNORE** | Données de référence | Pas de réécriture | Pas de mise à jour |

### Matrice de Décision

| Type de Données | Besoin d'Historique | Mode Recommandé |
|-----------------|---------------------|-----------------|
| Transactions | ✅ Oui | **APPEND** |
| Logs | ✅ Oui | **APPEND** |
| Événements | ✅ Oui | **APPEND** |
| Agrégations quotidiennes | ❌ Non | **OVERWRITE** |
| Totaux calculés | ❌ Non | **OVERWRITE** |
| Données de référence | ❌ Non | **IGNORE** |
| Snapshots | ⚠️ Partiel | **OVERWRITE** |

### Arbre de Décision

```
Les données peuvent-elles changer ?
│
├─ NON → Les données sont-elles immuables ?
│         │
│         ├─ OUI → MODE APPEND
│         │        Chaque événement est unique
│         │
│         └─ NON → MODE IGNORE
│                  Données de référence statiques
│
└─ OUI → Avez-vous besoin de l'historique complet ?
          │
          ├─ OUI → MODE APPEND
          │        Conserver toutes les versions
          │
          └─ NON → MODE OVERWRITE
                   Seul l'état actuel compte
```

---

## 📅 Choix de la Rétention

### Streams (jours)

| Type de Données | Rétention Recommandée | Justification |
|-----------------|----------------------|---------------|
| Transactions financières | 730 jours (2 ans) | Conformité légale |
| Transactions anonymisées | 730 jours (2 ans) | Conformité RGPD |
| Logs applicatifs | 90 jours | Debugging |
| Événements utilisateur | 365 jours (1 an) | Analyse comportementale |
| Données de test | 30 jours | Nettoyage régulier |

### Tables (versions)

| Type de Table | Versions Recommandées | Justification |
|---------------|----------------------|---------------|
| Agrégations quotidiennes | 7 versions | 1 semaine d'historique |
| Agrégations hebdomadaires | 12 versions | 3 mois d'historique |
| Agrégations mensuelles | 24 versions | 2 ans d'historique |
| Snapshots critiques | 30 versions | Historique étendu |

### Calcul de la Rétention

```python
# Pour les streams (par date)
retention_days = {
    'legal_compliance': 730,      # 2 ans
    'gdpr_compliance': 730,        # 2 ans
    'analytics': 365,              # 1 an
    'debugging': 90,               # 3 mois
    'testing': 30                  # 1 mois
}

# Pour les tables (par version)
retention_versions = {
    'daily_aggregates': 7,         # 1 semaine
    'weekly_aggregates': 12,       # 3 mois
    'monthly_aggregates': 24,      # 2 ans
    'critical_snapshots': 30       # Étendu
}
```

---

## 🔐 Choix du Niveau de Sécurité

### Permissions

| Type de Données | Permissions | Utilisateurs |
|-----------------|-------------|--------------|
| Données brutes | 750 (rwxr-x---) | Admin uniquement |
| Données anonymisées | 755 (rwxr-xr-x) | Équipe data |
| Agrégations | 755 (rwxr-xr-x) | Tous |
| Données publiques | 755 (rwxr-xr-x) | Tous |

### Arbre de Décision

```
Les données contiennent-elles des informations personnelles ?
│
├─ OUI → Les données sont-elles anonymisées ?
│         │
│         ├─ OUI → Permissions: 755
│         │        Accès étendu OK
│         │
│         └─ NON → Permissions: 750
│                  Accès restreint
│
└─ NON → S'agit-il de données agrégées ?
          │
          ├─ OUI → Permissions: 755
          │        Accès étendu OK
          │
          └─ NON → Évaluer au cas par cas
```

---

## 📦 Choix de la Compression

### Types de Compression Parquet

| Compression | Ratio | Vitesse | Utilisation |
|-------------|-------|---------|-------------|
| **Snappy** | Moyen (60-70%) | Très rapide | **Recommandé** (défaut) |
| **GZIP** | Élevé (70-80%) | Lent | Archives |
| **ZSTD** | Très élevé (75-85%) | Moyen | Stockage long terme |
| **LZ4** | Faible (50-60%) | Ultra-rapide | Données temporaires |
| **None** | 0% | Instantané | Tests uniquement |

### Arbre de Décision

```
Quelle est votre priorité ?
│
├─ VITESSE → Fréquence d'accès ?
│             │
│             ├─ Élevée → SNAPPY (défaut)
│             │           Bon compromis
│             │
│             └─ Faible → LZ4
│                        Ultra-rapide
│
├─ ESPACE DISQUE → Accès fréquent ?
│                   │
│                   ├─ OUI → ZSTD
│                   │        Bon compromis
│                   │
│                   └─ NON → GZIP
│                           Max compression
│
└─ ÉQUILIBRÉ → SNAPPY (recommandé)
               Meilleur compromis général
```

---

## 🎯 Exemples de Configuration

### Exemple 1: Stream de Transactions

```json
{
  "feed_name": "transaction_stream",
  "feed_type": "stream",
  "ksqldb_source": "transaction_stream",
  "description": "Transactions brutes",
  "partitioning": {
    "type": "date",
    "columns": ["year", "month", "day"]
  },
  "storage_mode": "append",
  "format": "parquet",
  "retention_days": 365,
  "enabled": true
}
```

**Justification**:
- ✅ Type: Stream (événements individuels)
- ✅ Partitionnement: Date (requêtes par période)
- ✅ Mode: APPEND (historique complet)
- ✅ Rétention: 365 jours (1 an d'analyse)

### Exemple 2: Table d'Agrégation

```json
{
  "feed_name": "daily_user_summary",
  "feed_type": "table",
  "ksqldb_source": "user_transaction_summary",
  "description": "Résumé quotidien par utilisateur",
  "partitioning": {
    "type": "version",
    "columns": ["version"]
  },
  "storage_mode": "overwrite",
  "format": "parquet",
  "retention_versions": 7,
  "enabled": true
}
```

**Justification**:
- ✅ Type: Table (agrégation calculée)
- ✅ Partitionnement: Version (snapshots)
- ✅ Mode: OVERWRITE (état actuel)
- ✅ Rétention: 7 versions (1 semaine)

### Exemple 3: Stream Anonymisé

```json
{
  "feed_name": "transaction_stream_anonymized",
  "feed_type": "stream",
  "ksqldb_source": "transaction_stream_anonymized",
  "description": "Transactions anonymisées RGPD",
  "partitioning": {
    "type": "date",
    "columns": ["year", "month", "day"]
  },
  "storage_mode": "append",
  "format": "parquet",
  "retention_days": 730,
  "security": {
    "anonymized": true,
    "gdpr_compliant": true
  },
  "enabled": true
}
```

**Justification**:
- ✅ Type: Stream (événements)
- ✅ Partitionnement: Date
- ✅ Mode: APPEND
- ✅ Rétention: 730 jours (conformité RGPD)
- ✅ Sécurité: Anonymisé

---

## 🔄 Checklist de Configuration

### Avant de Créer un Feed

- [ ] Déterminer le type (Stream ou Table)
- [ ] Choisir le partitionnement (Date ou Version)
- [ ] Définir le mode de stockage (APPEND ou OVERWRITE)
- [ ] Calculer la rétention appropriée
- [ ] Évaluer le niveau de sécurité
- [ ] Vérifier la source ksqlDB existe
- [ ] Documenter la justification

### Après la Création

- [ ] Tester l'export: `python export_to_data_lake.py --stream <name>`
- [ ] Vérifier les métadonnées: `_metadata.json`
- [ ] Valider la structure des partitions
- [ ] Contrôler la taille des fichiers
- [ ] Tester une requête de lecture
- [ ] Documenter dans le README

---

## 📊 Tableau Récapitulatif

### Configuration Recommandée par Type

| Cas d'Usage | Type | Partitionnement | Mode | Rétention |
|-------------|------|-----------------|------|-----------|
| Transactions financières | Stream | Date | APPEND | 730 jours |
| Logs applicatifs | Stream | Date | APPEND | 90 jours |
| Événements utilisateur | Stream | Date | APPEND | 365 jours |
| Agrégations quotidiennes | Table | Version | OVERWRITE | 7 versions |
| Agrégations mensuelles | Table | Version | OVERWRITE | 24 versions |
| Snapshots de référence | Table | Version | OVERWRITE | 12 versions |
| Données anonymisées | Stream | Date | APPEND | 730 jours |
| Données de test | Stream | Date | APPEND | 30 jours |

---

## 🚨 Erreurs Courantes à Éviter

### ❌ Erreur 1: Mauvais Type de Feed

```
Problème: Utiliser un Stream pour des agrégations
Solution: Utiliser une Table avec mode OVERWRITE
```

### ❌ Erreur 2: Mauvais Partitionnement

```
Problème: Partitionner par version un stream d'événements
Solution: Utiliser le partitionnement par date
```

### ❌ Erreur 3: Mode de Stockage Incorrect

```
Problème: Mode OVERWRITE pour des événements immuables
Solution: Utiliser mode APPEND pour conserver l'historique
```

### ❌ Erreur 4: Rétention Trop Courte

```
Problème: 30 jours pour des données légales
Solution: Minimum 730 jours (2 ans) pour conformité
```

### ❌ Erreur 5: Permissions Trop Ouvertes

```
Problème: 777 sur des données sensibles
Solution: 750 pour données brutes, 755 pour anonymisées
```

---

## 💡 Conseils et Bonnes Pratiques

### 1. Nommage des Feeds

```
✅ BON: transaction_stream, user_summary_daily
❌ MAUVAIS: data1, temp_table, test
```

### 2. Documentation

```
✅ BON: Description claire et détaillée
❌ MAUVAIS: Description vide ou générique
```

### 3. Rétention

```
✅ BON: Basée sur les besoins métier et légaux
❌ MAUVAIS: Valeur arbitraire sans justification
```

### 4. Tests

```
✅ BON: Tester l'export avant la production
❌ MAUVAIS: Déployer sans validation
```

### 5. Monitoring

```
✅ BON: Vérifier régulièrement les métadonnées
❌ MAUVAIS: Ignorer les logs et erreurs
```

---

## 🎓 Quiz de Validation

### Question 1
Vous avez un flux de transactions bancaires. Quel type de feed ?
- [ ] Table avec OVERWRITE
- [x] Stream avec APPEND
- [ ] Stream avec OVERWRITE

**Réponse**: Stream avec APPEND (événements immuables)

### Question 2
Vous calculez des totaux quotidiens. Quel partitionnement ?
- [ ] Date
- [x] Version
- [ ] Aucun

**Réponse**: Version (snapshots quotidiens)

### Question 3
Rétention pour des données RGPD anonymisées ?
- [ ] 90 jours
- [ ] 365 jours
- [x] 730 jours

**Réponse**: 730 jours (2 ans minimum)

---

**Version**: 1.0  
**Dernière mise à jour**: Janvier 2025
