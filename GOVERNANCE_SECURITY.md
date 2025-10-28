# 🔐 Gouvernance et Sécurité

## 📋 Vue d'ensemble

Ce document décrit le système complet de gouvernance et sécurité pour le Data Lake et le Data Warehouse.

---

## 🏗️ Architecture de Sécurité

```
┌─────────────────────────────────────────────────────────────┐
│                      UTILISATEURS                            │
│  • Admin, Data Engineer, Analyst, Viewer                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                SYSTÈME DE PERMISSIONS                        │
│  • Data Lake Permissions (par dossier)                      │
│  • Data Warehouse Permissions (par table)                   │
│  • Expiration automatique                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
┌───────────────────┐     ┌──────────────────────┐
│  DATA LAKE        │     │  DATA WAREHOUSE      │
│  • Streams        │     │  • Tables            │
│  • Tables         │     │  • Vues              │
└───────────────────┘     └──────────────────────┘
        │                         │
        └────────────┬────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    AUDIT & MONITORING                        │
│  • Journal d'accès                                          │
│  • Journal de suppression                                   │
│  • Alertes de sécurité                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 👥 Gestion des Utilisateurs

### Rôles Disponibles

| Rôle | Description | Permissions par Défaut |
|------|-------------|----------------------|
| **admin** | Administrateur système | Tous les droits |
| **data_engineer** | Ingénieur données | Read/Write Data Lake + DW |
| **analyst** | Analyste données | Read Data Lake + DW |
| **viewer** | Visualiseur | Read limité |

### Créer un Utilisateur

```bash
# Via script Python
python permissions_manager.py create-user \
  --username john.doe \
  --email john.doe@company.com \
  --full-name "John Doe" \
  --department "Analytics" \
  --role analyst \
  --mysql-password ""

# Via SQL
mysql -u root -p data_warehouse << EOF
INSERT INTO users (username, email, full_name, department, role)
VALUES ('john.doe', 'john.doe@company.com', 'John Doe', 'Analytics', 'analyst');
EOF
```

### Lister les Utilisateurs

```bash
# Via SQL
mysql -u root -p -e "
USE data_warehouse;
SELECT username, email, role, is_active, created_at
FROM users
WHERE is_active = TRUE
ORDER BY role, username;
"
```

### Modifier un Rôle

```bash
# Via SQL
mysql -u root -p data_warehouse << EOF
UPDATE users
SET role = 'data_engineer'
WHERE username = 'john.doe';
EOF
```

### Désactiver un Utilisateur

```bash
# Via SQL
mysql -u root -p data_warehouse << EOF
UPDATE users
SET is_active = FALSE
WHERE username = 'john.doe';
EOF
```

---

## 🗂️ Permissions Data Lake

### Structure des Permissions

Les permissions sont définies **par dossier** dans le Data Lake:

```
/data_lake/
├── streams/
│   ├── transaction_stream/          ← Permission: /data_lake/streams/transaction_stream/
│   ├── transaction_flattened/       ← Permission: /data_lake/streams/transaction_flattened/
│   └── ...
└── tables/
    ├── user_transaction_summary/    ← Permission: /data_lake/tables/user_transaction_summary/
    └── ...
```

### Types de Permissions

| Permission | Description | Actions Autorisées |
|-----------|-------------|-------------------|
| **read** | Lecture seule | Lire les fichiers Parquet |
| **write** | Écriture | Lire + Écrire de nouveaux fichiers |
| **delete** | Suppression | Lire + Écrire + Supprimer |
| **admin** | Administration | Tous les droits + Gestion permissions |

### Accorder une Permission

```bash
# Via script Python
python permissions_manager.py grant-datalake \
  --username john.doe \
  --folder "/data_lake/streams/transaction_stream/" \
  --permission read \
  --granted-by admin \
  --mysql-password ""

# Via SQL
mysql -u root -p data_warehouse << EOF
INSERT INTO data_lake_permissions (user_id, folder_path, permission_type, granted_by)
SELECT 
    u.user_id,
    '/data_lake/streams/transaction_stream/',
    'read',
    (SELECT user_id FROM users WHERE username = 'admin')
FROM users u
WHERE u.username = 'john.doe';
EOF
```

### Accorder avec Expiration

```bash
# Permission temporaire (expire dans 30 jours)
mysql -u root -p data_warehouse << EOF
INSERT INTO data_lake_permissions (user_id, folder_path, permission_type, granted_by, expires_at)
SELECT 
    u.user_id,
    '/data_lake/streams/transaction_stream/',
    'read',
    (SELECT user_id FROM users WHERE username = 'admin'),
    DATE_ADD(NOW(), INTERVAL 30 DAY)
FROM users u
WHERE u.username = 'john.doe';
EOF
```

### Révoquer une Permission

```bash
# Via SQL
mysql -u root -p data_warehouse << EOF
UPDATE data_lake_permissions
SET is_active = FALSE
WHERE user_id = (SELECT user_id FROM users WHERE username = 'john.doe')
  AND folder_path = '/data_lake/streams/transaction_stream/'
  AND permission_type = 'read';
EOF
```

### Lister les Permissions d'un Utilisateur

```bash
# Via script Python
python permissions_manager.py list-permissions \
  --username john.doe \
  --mysql-password ""

# Via SQL
mysql -u root -p -e "
USE data_warehouse;
SELECT 
    u.username,
    p.folder_path,
    p.permission_type,
    p.granted_at,
    p.expires_at,
    p.is_active
FROM data_lake_permissions p
JOIN users u ON p.user_id = u.user_id
WHERE u.username = 'john.doe' AND p.is_active = TRUE
ORDER BY p.folder_path;
"
```

### Permissions Héritées

Les permissions sont **héritées** des dossiers parents:

```
Permission sur /data_lake/streams/
  → Accès à tous les sous-dossiers:
    - /data_lake/streams/transaction_stream/
    - /data_lake/streams/transaction_flattened/
    - etc.
```

---

## 🗄️ Permissions Data Warehouse

### Types de Permissions

| Permission | Description | Actions SQL Autorisées |
|-----------|-------------|----------------------|
| **select** | Lecture | SELECT |
| **insert** | Insertion | SELECT + INSERT |
| **update** | Mise à jour | SELECT + INSERT + UPDATE |
| **delete** | Suppression | SELECT + INSERT + UPDATE + DELETE |
| **all** | Tous droits | Toutes les opérations |

### Accorder une Permission

```bash
# Permission sur une table spécifique
mysql -u root -p data_warehouse << EOF
INSERT INTO data_warehouse_permissions (user_id, table_name, permission_type, granted_by)
SELECT 
    u.user_id,
    'fact_user_transaction_summary',
    'select',
    (SELECT user_id FROM users WHERE username = 'admin')
FROM users u
WHERE u.username = 'john.doe';
EOF

# Permission sur toutes les tables (*)
mysql -u root -p data_warehouse << EOF
INSERT INTO data_warehouse_permissions (user_id, table_name, permission_type, granted_by)
SELECT 
    u.user_id,
    '*',
    'select',
    (SELECT user_id FROM users WHERE username = 'admin')
FROM users u
WHERE u.username = 'john.doe';
EOF
```

### Lister les Permissions

```bash
mysql -u root -p -e "
USE data_warehouse;
SELECT 
    u.username,
    p.table_name,
    p.permission_type,
    p.granted_at,
    p.is_active
FROM data_warehouse_permissions p
JOIN users u ON p.user_id = u.user_id
WHERE u.username = 'john.doe' AND p.is_active = TRUE
ORDER BY p.table_name;
"
```

---

## 🗑️ Suppression des Données Historiques

### Politiques de Rétention

Les politiques définissent **combien de temps** conserver les données:

```sql
-- Voir les politiques actuelles
SELECT 
    feed_name,
    feed_type,
    retention_days,
    retention_versions,
    auto_delete,
    last_cleanup_at
FROM data_retention_policies
WHERE is_active = TRUE;
```

### Créer une Politique

```sql
-- Pour un stream (rétention en jours)
INSERT INTO data_retention_policies (feed_name, feed_type, retention_days, created_by)
VALUES ('transaction_stream', 'stream', 90, 1);

-- Pour une table (rétention en versions)
INSERT INTO data_retention_policies (feed_name, feed_type, retention_versions, created_by)
VALUES ('user_transaction_summary', 'table', 10, 1);
```

### Modifier une Politique

```sql
-- Changer la rétention
UPDATE data_retention_policies
SET retention_days = 180
WHERE feed_name = 'transaction_stream';
```

### Exécuter le Nettoyage

#### Mode Dry Run (Simulation)

```bash
# Simuler sans supprimer
python data_retention_manager.py \
  --mysql-password "" \
  --dry-run
```

#### Mode Production

```bash
# Supprimer réellement
python data_retention_manager.py \
  --mysql-password ""
```

### Automatiser le Nettoyage

#### Via Cron (Linux/macOS)

```bash
# Éditer le crontab
crontab -e

# Ajouter (exécution quotidienne à 2h du matin)
0 2 * * * cd /Users/alice/Downloads/data_lake && source venv/bin/activate && python data_retention_manager.py --mysql-password "" >> logs/retention_cron.log 2>&1
```

#### Via Launchd (macOS)

```xml
<!-- ~/Library/LaunchAgents/com.datalake.retention.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.datalake.retention</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/alice/Downloads/data_lake/venv/bin/python</string>
        <string>/Users/alice/Downloads/data_lake/data_retention_manager.py</string>
        <string>--mysql-password</string>
        <string></string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>2</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>WorkingDirectory</key>
    <string>/Users/alice/Downloads/data_lake</string>
</dict>
</plist>
```

```bash
# Charger
launchctl load ~/Library/LaunchAgents/com.datalake.retention.plist
```

### Journal des Suppressions

```sql
-- Voir l'historique des suppressions
SELECT 
    feed_name,
    feed_type,
    deletion_type,
    files_deleted,
    size_deleted_mb,
    deleted_at,
    notes
FROM data_deletion_log
ORDER BY deleted_at DESC
LIMIT 20;

-- Statistiques par feed
SELECT 
    feed_name,
    COUNT(*) as cleanup_count,
    SUM(files_deleted) as total_files_deleted,
    SUM(size_deleted_mb) as total_size_deleted_mb
FROM data_deletion_log
GROUP BY feed_name
ORDER BY total_size_deleted_mb DESC;
```

---

## 📊 Audit et Monitoring

### Journal d'Audit

Tous les accès sont enregistrés dans `access_audit_log`:

```sql
-- Voir les accès récents
SELECT 
    u.username,
    a.action_type,
    a.resource_type,
    a.resource_path,
    a.status,
    a.accessed_at
FROM access_audit_log a
LEFT JOIN users u ON a.user_id = u.user_id
ORDER BY a.accessed_at DESC
LIMIT 50;

-- Accès refusés
SELECT 
    u.username,
    a.resource_path,
    a.error_message,
    a.accessed_at
FROM access_audit_log a
LEFT JOIN users u ON a.user_id = u.user_id
WHERE a.status = 'denied'
ORDER BY a.accessed_at DESC;

-- Activité par utilisateur
SELECT 
    u.username,
    a.action_type,
    COUNT(*) as count
FROM access_audit_log a
JOIN users u ON a.user_id = u.user_id
WHERE a.accessed_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY u.username, a.action_type
ORDER BY count DESC;
```

### Enregistrer un Accès

```python
# Dans votre code Python
from permissions_manager import PermissionsManager

manager = PermissionsManager(mysql_config)
manager.connect_mysql()

# Enregistrer un accès réussi
manager.log_access(
    username="john.doe",
    action_type="read",
    resource_type="data_lake",
    resource_path="/data_lake/streams/transaction_stream/",
    status="success"
)

# Enregistrer un accès refusé
manager.log_access(
    username="john.doe",
    action_type="delete",
    resource_type="data_lake",
    resource_path="/data_lake/streams/transaction_stream/",
    status="denied",
    error_message="Permission denied: user does not have delete permission"
)

manager.disconnect_mysql()
```

---

## 🔒 Bonnes Pratiques de Sécurité

### 1. Principe du Moindre Privilège

- ✅ Accorder uniquement les permissions nécessaires
- ✅ Utiliser des permissions temporaires quand possible
- ✅ Réviser régulièrement les permissions

### 2. Séparation des Rôles

- ✅ Admin: Gestion système uniquement
- ✅ Data Engineer: Ingestion et transformation
- ✅ Analyst: Lecture et analyse
- ✅ Viewer: Visualisation limitée

### 3. Audit Régulier

```sql
-- Permissions expirées non révoquées
SELECT * FROM data_lake_permissions
WHERE expires_at < NOW() AND is_active = TRUE;

-- Utilisateurs inactifs avec permissions
SELECT u.username, u.last_login, COUNT(p.permission_id) as perm_count
FROM users u
JOIN data_lake_permissions p ON u.user_id = p.user_id
WHERE u.last_login < DATE_SUB(NOW(), INTERVAL 90 DAY)
  AND p.is_active = TRUE
GROUP BY u.user_id;
```

### 4. Rotation des Accès

```sql
-- Révoquer les permissions expirées
UPDATE data_lake_permissions
SET is_active = FALSE
WHERE expires_at < NOW() AND is_active = TRUE;

UPDATE data_warehouse_permissions
SET is_active = FALSE
WHERE expires_at < NOW() AND is_active = TRUE;
```

---

## 📋 Checklist de Sécurité

### Configuration Initiale
- [ ] Tables de gouvernance créées
- [ ] Utilisateurs admin créés
- [ ] Politiques de rétention définies
- [ ] Permissions par défaut configurées

### Opérations Régulières
- [ ] Révision des permissions (mensuelle)
- [ ] Nettoyage des données (automatique)
- [ ] Audit des accès (hebdomadaire)
- [ ] Révocation des permissions expirées (quotidienne)

### Monitoring
- [ ] Alertes sur accès refusés
- [ ] Alertes sur suppressions importantes
- [ ] Métriques de stockage
- [ ] Activité utilisateurs

---

**Version**: 1.0  
**Date**: Janvier 2025  
**Statut**: ✅ Production Ready
