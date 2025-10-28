# 🏢 Data Warehouse MySQL - Design et Architecture

## 📋 Vue d'ensemble

Ce document décrit le design du Data Warehouse MySQL qui stocke toutes les tables ksqlDB dans un schéma relationnel optimisé avec clés primaires, clés étrangères et relations entre tables.

---

## 🎯 Objectifs

1. **Stocker toutes les tables ksqlDB** dans MySQL
2. **Définir un schéma relationnel** avec intégrité référentielle
3. **Optimiser pour l'analytique** et les requêtes complexes
4. **Maintenir la cohérence** des données
5. **Faciliter les jointures** entre tables

---

## 🗂️ Schéma Relationnel MySQL

### Tables du Data Warehouse

Le Data Warehouse contient 4 tables principales correspondant aux tables ksqlDB, plus 2 tables de dimension pour normaliser le schéma.

#### 1. Table: `dim_users` (Dimension)

**Description**: Table de dimension pour les utilisateurs

```sql
CREATE TABLE dim_users (
    user_id VARCHAR(50) PRIMARY KEY,
    user_name VARCHAR(100),
    user_email VARCHAR(100),
    user_country VARCHAR(50),
    user_city VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_country (user_country),
    INDEX idx_city (user_city)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Clé primaire**: `user_id`

**Justification**:
- Table de dimension pour normaliser les informations utilisateur
- Évite la duplication dans les tables de faits
- Facilite les mises à jour des informations utilisateur

#### 2. Table: `dim_payment_methods` (Dimension)

**Description**: Table de dimension pour les méthodes de paiement

```sql
CREATE TABLE dim_payment_methods (
    payment_method_id INT AUTO_INCREMENT PRIMARY KEY,
    payment_method_name VARCHAR(50) UNIQUE NOT NULL,
    payment_method_category VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_category (payment_method_category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Clé primaire**: `payment_method_id`

**Justification**:
- Normalisation des méthodes de paiement
- Permet d'ajouter des métadonnées (catégorie, statut)
- Optimise les jointures

#### 3. Table: `fact_user_transaction_summary` (Fait)

**Description**: Résumé des transactions par utilisateur et type (depuis ksqlDB)

```sql
CREATE TABLE fact_user_transaction_summary (
    summary_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    total_amount DECIMAL(15, 2) NOT NULL,
    transaction_count INT NOT NULL,
    avg_amount DECIMAL(15, 2),
    min_amount DECIMAL(15, 2),
    max_amount DECIMAL(15, 2),
    last_transaction_date TIMESTAMP,
    snapshot_date DATE NOT NULL,
    snapshot_version INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES dim_users(user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    
    INDEX idx_user_type (user_id, transaction_type),
    INDEX idx_snapshot (snapshot_date, snapshot_version),
    INDEX idx_amount (total_amount),
    UNIQUE KEY uk_user_type_snapshot (user_id, transaction_type, snapshot_date, snapshot_version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Clé primaire**: `summary_id`  
**Clés étrangères**: `user_id` → `dim_users(user_id)`

**Justification**:
- Table de faits pour l'analyse des transactions par utilisateur
- Snapshot versioning pour historique
- Agrégations pré-calculées pour performance

#### 4. Table: `fact_user_transaction_summary_eur` (Fait)

**Description**: Résumé des transactions en EUR par utilisateur (depuis ksqlDB)

```sql
CREATE TABLE fact_user_transaction_summary_eur (
    summary_eur_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    total_amount_eur DECIMAL(15, 2) NOT NULL,
    transaction_count INT NOT NULL,
    avg_amount_eur DECIMAL(15, 2),
    exchange_rate DECIMAL(10, 6),
    snapshot_date DATE NOT NULL,
    snapshot_version INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES dim_users(user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    
    INDEX idx_user_type (user_id, transaction_type),
    INDEX idx_snapshot (snapshot_date, snapshot_version),
    INDEX idx_amount_eur (total_amount_eur),
    UNIQUE KEY uk_user_type_snapshot (user_id, transaction_type, snapshot_date, snapshot_version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Clé primaire**: `summary_eur_id`  
**Clés étrangères**: `user_id` → `dim_users(user_id)`

**Justification**:
- Conversion en EUR pour analyse multi-devises
- Stockage du taux de change pour traçabilité
- Séparation pour optimiser les requêtes EUR

#### 5. Table: `fact_payment_method_totals` (Fait)

**Description**: Totaux par méthode de paiement (depuis ksqlDB)

```sql
CREATE TABLE fact_payment_method_totals (
    payment_total_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    payment_method_id INT NOT NULL,
    payment_method_name VARCHAR(50) NOT NULL,
    total_amount DECIMAL(15, 2) NOT NULL,
    transaction_count INT NOT NULL,
    avg_amount DECIMAL(15, 2),
    snapshot_date DATE NOT NULL,
    snapshot_version INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (payment_method_id) REFERENCES dim_payment_methods(payment_method_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    
    INDEX idx_payment_method (payment_method_id),
    INDEX idx_snapshot (snapshot_date, snapshot_version),
    INDEX idx_amount (total_amount),
    UNIQUE KEY uk_payment_snapshot (payment_method_id, snapshot_date, snapshot_version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Clé primaire**: `payment_total_id`  
**Clés étrangères**: `payment_method_id` → `dim_payment_methods(payment_method_id)`

**Justification**:
- Analyse des méthodes de paiement
- Normalisation via table de dimension
- Historique des totaux par snapshot

#### 6. Table: `fact_product_purchase_counts` (Fait)

**Description**: Compteurs d'achats par produit (depuis ksqlDB)

```sql
CREATE TABLE fact_product_purchase_counts (
    product_count_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    product_id VARCHAR(50) NOT NULL,
    product_name VARCHAR(200),
    product_category VARCHAR(100),
    purchase_count INT NOT NULL,
    total_revenue DECIMAL(15, 2),
    avg_price DECIMAL(15, 2),
    unique_buyers INT,
    snapshot_date DATE NOT NULL,
    snapshot_version INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_product (product_id),
    INDEX idx_category (product_category),
    INDEX idx_snapshot (snapshot_date, snapshot_version),
    INDEX idx_purchase_count (purchase_count DESC),
    UNIQUE KEY uk_product_snapshot (product_id, snapshot_date, snapshot_version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Clé primaire**: `product_count_id`

**Justification**:
- Analyse des produits les plus vendus
- Métriques de performance produit
- Pas de FK car les produits peuvent être externes

---

## 📊 Diagramme Entité-Association (ERD)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DATA WAREHOUSE - SCHÉMA RELATIONNEL              │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐
│   dim_users          │ (DIMENSION)
├──────────────────────┤
│ PK user_id           │
│    user_name         │
│    user_email        │
│    user_country      │
│    user_city         │
│    created_at        │
│    updated_at        │
└──────────────────────┘
         │
         │ 1
         │
         │ N
         ├─────────────────────────────────────────┐
         │                                         │
         │                                         │
         ▼                                         ▼
┌──────────────────────────────────┐    ┌──────────────────────────────────┐
│ fact_user_transaction_summary    │    │ fact_user_transaction_summary_eur│
├──────────────────────────────────┤    ├──────────────────────────────────┤
│ PK summary_id                    │    │ PK summary_eur_id                │
│ FK user_id ────────────┐         │    │ FK user_id ────────────┐         │
│    transaction_type    │         │    │    transaction_type    │         │
│    total_amount        │         │    │    total_amount_eur    │         │
│    transaction_count   │         │    │    transaction_count   │         │
│    avg_amount          │         │    │    avg_amount_eur      │         │
│    min_amount          │         │    │    exchange_rate       │         │
│    max_amount          │         │    │    snapshot_date       │         │
│    last_transaction_date│        │    │    snapshot_version    │         │
│    snapshot_date       │         │    │    created_at          │         │
│    snapshot_version    │         │    │    updated_at          │         │
│    created_at          │         │    └──────────────────────────────────┘
│    updated_at          │         │
└──────────────────────────────────┘


┌──────────────────────────┐
│ dim_payment_methods      │ (DIMENSION)
├──────────────────────────┤
│ PK payment_method_id     │
│    payment_method_name   │
│    payment_method_category│
│    is_active             │
│    created_at            │
└──────────────────────────┘
         │
         │ 1
         │
         │ N
         ▼
┌──────────────────────────────────┐
│ fact_payment_method_totals       │
├──────────────────────────────────┤
│ PK payment_total_id              │
│ FK payment_method_id ──────┐     │
│    payment_method_name      │    │
│    total_amount             │    │
│    transaction_count        │    │
│    avg_amount               │    │
│    snapshot_date            │    │
│    snapshot_version         │    │
│    created_at               │    │
│    updated_at               │    │
└──────────────────────────────────┘


┌──────────────────────────────────┐
│ fact_product_purchase_counts     │ (INDÉPENDANTE)
├──────────────────────────────────┤
│ PK product_count_id              │
│    product_id                    │
│    product_name                  │
│    product_category              │
│    purchase_count                │
│    total_revenue                 │
│    avg_price                     │
│    unique_buyers                 │
│    snapshot_date                 │
│    snapshot_version              │
│    created_at                    │
│    updated_at                    │
└──────────────────────────────────┘


LÉGENDE:
─────────
PK = Primary Key (Clé Primaire)
FK = Foreign Key (Clé Étrangère)
1  = Relation un
N  = Relation plusieurs
```

---

## 🔗 Relations Entre Tables

### 1. dim_users → fact_user_transaction_summary

**Type**: One-to-Many (1:N)

**Relation**:
```
dim_users.user_id (1) ──→ fact_user_transaction_summary.user_id (N)
```

**Justification**:
- Un utilisateur peut avoir plusieurs résumés de transactions
- Chaque résumé appartient à un seul utilisateur
- Intégrité référentielle garantie

### 2. dim_users → fact_user_transaction_summary_eur

**Type**: One-to-Many (1:N)

**Relation**:
```
dim_users.user_id (1) ──→ fact_user_transaction_summary_eur.user_id (N)
```

**Justification**:
- Un utilisateur peut avoir plusieurs résumés en EUR
- Conversion multi-devises par utilisateur
- Historique des snapshots

### 3. dim_payment_methods → fact_payment_method_totals

**Type**: One-to-Many (1:N)

**Relation**:
```
dim_payment_methods.payment_method_id (1) ──→ fact_payment_method_totals.payment_method_id (N)
```

**Justification**:
- Une méthode de paiement peut avoir plusieurs totaux (snapshots)
- Normalisation des méthodes de paiement
- Facilite les analyses par catégorie

### 4. fact_product_purchase_counts (Indépendante)

**Type**: Aucune relation

**Justification**:
- Les produits peuvent provenir de systèmes externes
- Pas de table de dimension produit (pour l'instant)
- Analyse autonome des produits

---

## 🎯 Stratégie de Chargement

### Mode de Synchronisation

#### Tables de Dimension (SCD Type 1)

**Slowly Changing Dimension - Type 1**: Écrasement des valeurs

```sql
-- Exemple: Mise à jour d'un utilisateur
INSERT INTO dim_users (user_id, user_name, user_email, user_country, user_city)
VALUES ('user123', 'John Doe', 'john@example.com', 'France', 'Paris')
ON DUPLICATE KEY UPDATE
    user_name = VALUES(user_name),
    user_email = VALUES(user_email),
    user_country = VALUES(user_country),
    user_city = VALUES(user_city),
    updated_at = CURRENT_TIMESTAMP;
```

#### Tables de Faits (Snapshot)

**Mode**: Insertion de nouveaux snapshots

```sql
-- Exemple: Nouveau snapshot de résumé utilisateur
INSERT INTO fact_user_transaction_summary (
    user_id, transaction_type, total_amount, transaction_count,
    avg_amount, snapshot_date, snapshot_version
)
SELECT 
    user_id, transaction_type, total_amount, transaction_count,
    avg_amount, CURDATE(), 1
FROM ksqldb_user_transaction_summary;
```

---

## 📈 Optimisations

### Index Stratégiques

#### 1. Index sur les Clés Étrangères

```sql
-- Optimise les jointures
INDEX idx_user_id ON fact_user_transaction_summary(user_id);
INDEX idx_payment_method_id ON fact_payment_method_totals(payment_method_id);
```

#### 2. Index Composites

```sql
-- Optimise les requêtes par utilisateur et type
INDEX idx_user_type ON fact_user_transaction_summary(user_id, transaction_type);

-- Optimise les requêtes par snapshot
INDEX idx_snapshot ON fact_user_transaction_summary(snapshot_date, snapshot_version);
```

#### 3. Index sur les Montants

```sql
-- Optimise les requêtes de tri et agrégation
INDEX idx_amount ON fact_user_transaction_summary(total_amount);
INDEX idx_purchase_count ON fact_product_purchase_counts(purchase_count DESC);
```

### Contraintes d'Unicité

```sql
-- Évite les doublons de snapshots
UNIQUE KEY uk_user_type_snapshot (
    user_id, transaction_type, snapshot_date, snapshot_version
);

UNIQUE KEY uk_payment_snapshot (
    payment_method_id, snapshot_date, snapshot_version
);

UNIQUE KEY uk_product_snapshot (
    product_id, snapshot_date, snapshot_version
);
```

---

## 🔐 Intégrité Référentielle

### Actions sur Suppression/Mise à Jour

#### CASCADE

```sql
FOREIGN KEY (user_id) REFERENCES dim_users(user_id)
    ON DELETE CASCADE    -- Supprime les faits si l'utilisateur est supprimé
    ON UPDATE CASCADE;   -- Met à jour les faits si l'ID utilisateur change
```

**Justification**:
- Maintient la cohérence des données
- Évite les orphelins dans les tables de faits
- Simplifie la maintenance

### Validation des Données

```sql
-- Contraintes CHECK (MySQL 8.0+)
ALTER TABLE fact_user_transaction_summary
ADD CONSTRAINT chk_positive_amount CHECK (total_amount >= 0);

ALTER TABLE fact_user_transaction_summary
ADD CONSTRAINT chk_positive_count CHECK (transaction_count > 0);

ALTER TABLE fact_payment_method_totals
ADD CONSTRAINT chk_positive_amount CHECK (total_amount >= 0);
```

---

## 📊 Requêtes Analytiques Exemples

### 1. Top 10 Utilisateurs par Montant Total

```sql
SELECT 
    u.user_id,
    u.user_name,
    u.user_country,
    SUM(f.total_amount) as total_spent,
    SUM(f.transaction_count) as total_transactions
FROM dim_users u
JOIN fact_user_transaction_summary f ON u.user_id = f.user_id
WHERE f.snapshot_date = (SELECT MAX(snapshot_date) FROM fact_user_transaction_summary)
GROUP BY u.user_id, u.user_name, u.user_country
ORDER BY total_spent DESC
LIMIT 10;
```

### 2. Analyse par Méthode de Paiement

```sql
SELECT 
    pm.payment_method_name,
    pm.payment_method_category,
    SUM(f.total_amount) as total_revenue,
    SUM(f.transaction_count) as total_transactions,
    AVG(f.avg_amount) as avg_transaction_amount
FROM dim_payment_methods pm
JOIN fact_payment_method_totals f ON pm.payment_method_id = f.payment_method_id
WHERE f.snapshot_date = CURDATE()
GROUP BY pm.payment_method_name, pm.payment_method_category
ORDER BY total_revenue DESC;
```

### 3. Produits les Plus Vendus par Catégorie

```sql
SELECT 
    product_category,
    product_name,
    purchase_count,
    total_revenue,
    RANK() OVER (PARTITION BY product_category ORDER BY purchase_count DESC) as rank_in_category
FROM fact_product_purchase_counts
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM fact_product_purchase_counts)
ORDER BY product_category, rank_in_category;
```

### 4. Évolution des Transactions par Utilisateur

```sql
SELECT 
    u.user_name,
    f.snapshot_date,
    f.total_amount,
    f.transaction_count,
    LAG(f.total_amount) OVER (PARTITION BY f.user_id ORDER BY f.snapshot_date) as prev_amount,
    (f.total_amount - LAG(f.total_amount) OVER (PARTITION BY f.user_id ORDER BY f.snapshot_date)) as amount_change
FROM dim_users u
JOIN fact_user_transaction_summary f ON u.user_id = f.user_id
WHERE u.user_id = 'user123'
ORDER BY f.snapshot_date DESC;
```

---

## 🔄 Pipeline de Synchronisation

### Flux de Données: ksqlDB → MySQL

```
┌─────────────┐
│   ksqlDB    │
│   Tables    │
└─────────────┘
       │
       │ 1. Extract
       ▼
┌─────────────┐
│  Python     │
│  Script     │
└─────────────┘
       │
       │ 2. Transform
       ▼
┌─────────────┐
│  MySQL      │
│  Data       │
│  Warehouse  │
└─────────────┘
```

### Étapes de Synchronisation

1. **Extract**: Récupération des données depuis ksqlDB
2. **Transform**: Normalisation et enrichissement
3. **Load**: Insertion dans MySQL avec gestion des snapshots

---

## 📝 Nomenclature

### Conventions de Nommage

| Type | Convention | Exemple |
|------|------------|---------|
| **Tables de dimension** | `dim_<nom>` | `dim_users` |
| **Tables de faits** | `fact_<nom>` | `fact_user_transaction_summary` |
| **Clés primaires** | `<table>_id` | `user_id`, `summary_id` |
| **Clés étrangères** | `<table>_id` | `user_id`, `payment_method_id` |
| **Index** | `idx_<colonnes>` | `idx_user_type` |
| **Contraintes uniques** | `uk_<colonnes>` | `uk_user_type_snapshot` |

---

## 🎯 Avantages du Schéma

### 1. Normalisation

- ✅ Évite la duplication des données
- ✅ Facilite les mises à jour
- ✅ Réduit l'espace de stockage

### 2. Intégrité Référentielle

- ✅ Garantit la cohérence des données
- ✅ Évite les orphelins
- ✅ Cascade automatique

### 3. Performance

- ✅ Index optimisés pour les requêtes
- ✅ Jointures efficaces
- ✅ Agrégations pré-calculées

### 4. Historique

- ✅ Snapshots versionnés
- ✅ Analyse temporelle
- ✅ Audit trail complet

### 5. Extensibilité

- ✅ Facile d'ajouter de nouvelles tables
- ✅ Schéma modulaire
- ✅ Évolution sans impact

---

**Version**: 1.0  
**Date**: Janvier 2025  
**Statut**: ✅ Design Complet
