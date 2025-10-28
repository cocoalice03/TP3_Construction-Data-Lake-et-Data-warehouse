-- ============================================================================
-- Script de Création des Tables de Faits
-- ============================================================================
-- Description: Création des tables de faits du Data Warehouse
-- Version: 1.0
-- Date: Janvier 2025
-- ============================================================================

USE data_warehouse;

-- ============================================================================
-- Table: fact_user_transaction_summary
-- Description: Résumé des transactions par utilisateur et type (depuis ksqlDB)
-- Type: Table de faits avec snapshots versionnés
-- ============================================================================

CREATE TABLE fact_user_transaction_summary (
    -- Clé primaire
    summary_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT 'Identifiant unique du résumé',
    
    -- Clés étrangères
    user_id VARCHAR(50) NOT NULL COMMENT 'Référence à l''utilisateur',
    
    -- Dimensions
    transaction_type VARCHAR(50) NOT NULL COMMENT 'Type de transaction',
    
    -- Métriques
    total_amount DECIMAL(15, 2) NOT NULL COMMENT 'Montant total des transactions',
    transaction_count INT NOT NULL COMMENT 'Nombre de transactions',
    avg_amount DECIMAL(15, 2) COMMENT 'Montant moyen par transaction',
    min_amount DECIMAL(15, 2) COMMENT 'Montant minimum',
    max_amount DECIMAL(15, 2) COMMENT 'Montant maximum',
    last_transaction_date TIMESTAMP COMMENT 'Date de la dernière transaction',
    
    -- Versioning (snapshots)
    snapshot_date DATE NOT NULL COMMENT 'Date du snapshot',
    snapshot_version INT NOT NULL COMMENT 'Version du snapshot',
    
    -- Métadonnées
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Date de création',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Date de mise à jour',
    
    -- Contraintes de clé étrangère
    FOREIGN KEY (user_id) REFERENCES dim_users(user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    
    -- Index pour optimiser les requêtes
    INDEX idx_user_type (user_id, transaction_type),
    INDEX idx_snapshot (snapshot_date, snapshot_version),
    INDEX idx_amount (total_amount),
    INDEX idx_transaction_count (transaction_count),
    
    -- Contrainte d'unicité pour éviter les doublons
    UNIQUE KEY uk_user_type_snapshot (user_id, transaction_type, snapshot_date, snapshot_version),
    
    -- Contraintes de validation
    CONSTRAINT chk_positive_amount CHECK (total_amount >= 0),
    CONSTRAINT chk_positive_count CHECK (transaction_count > 0),
    CONSTRAINT chk_positive_version CHECK (snapshot_version > 0)
    
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Table de faits: résumé des transactions par utilisateur';

-- ============================================================================
-- Table: fact_user_transaction_summary_eur
-- Description: Résumé des transactions en EUR par utilisateur (depuis ksqlDB)
-- Type: Table de faits avec snapshots versionnés
-- ============================================================================

CREATE TABLE fact_user_transaction_summary_eur (
    -- Clé primaire
    summary_eur_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT 'Identifiant unique du résumé EUR',
    
    -- Clés étrangères
    user_id VARCHAR(50) NOT NULL COMMENT 'Référence à l''utilisateur',
    
    -- Dimensions
    transaction_type VARCHAR(50) NOT NULL COMMENT 'Type de transaction',
    
    -- Métriques en EUR
    total_amount_eur DECIMAL(15, 2) NOT NULL COMMENT 'Montant total en EUR',
    transaction_count INT NOT NULL COMMENT 'Nombre de transactions',
    avg_amount_eur DECIMAL(15, 2) COMMENT 'Montant moyen en EUR',
    exchange_rate DECIMAL(10, 6) COMMENT 'Taux de change utilisé',
    
    -- Versioning (snapshots)
    snapshot_date DATE NOT NULL COMMENT 'Date du snapshot',
    snapshot_version INT NOT NULL COMMENT 'Version du snapshot',
    
    -- Métadonnées
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Date de création',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Date de mise à jour',
    
    -- Contraintes de clé étrangère
    FOREIGN KEY (user_id) REFERENCES dim_users(user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    
    -- Index pour optimiser les requêtes
    INDEX idx_user_type (user_id, transaction_type),
    INDEX idx_snapshot (snapshot_date, snapshot_version),
    INDEX idx_amount_eur (total_amount_eur),
    
    -- Contrainte d'unicité
    UNIQUE KEY uk_user_type_snapshot (user_id, transaction_type, snapshot_date, snapshot_version),
    
    -- Contraintes de validation
    CONSTRAINT chk_positive_amount_eur CHECK (total_amount_eur >= 0),
    CONSTRAINT chk_positive_count_eur CHECK (transaction_count > 0),
    CONSTRAINT chk_positive_version_eur CHECK (snapshot_version > 0)
    
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Table de faits: résumé des transactions en EUR';

-- ============================================================================
-- Table: fact_payment_method_totals
-- Description: Totaux par méthode de paiement (depuis ksqlDB)
-- Type: Table de faits avec snapshots versionnés
-- ============================================================================

CREATE TABLE fact_payment_method_totals (
    -- Clé primaire
    payment_total_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT 'Identifiant unique du total',
    
    -- Clés étrangères
    payment_method_id INT NOT NULL COMMENT 'Référence à la méthode de paiement',
    
    -- Attribut dénormalisé pour performance
    payment_method_name VARCHAR(50) NOT NULL COMMENT 'Nom de la méthode (dénormalisé)',
    
    -- Métriques
    total_amount DECIMAL(15, 2) NOT NULL COMMENT 'Montant total',
    transaction_count INT NOT NULL COMMENT 'Nombre de transactions',
    avg_amount DECIMAL(15, 2) COMMENT 'Montant moyen',
    
    -- Versioning (snapshots)
    snapshot_date DATE NOT NULL COMMENT 'Date du snapshot',
    snapshot_version INT NOT NULL COMMENT 'Version du snapshot',
    
    -- Métadonnées
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Date de création',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Date de mise à jour',
    
    -- Contraintes de clé étrangère
    FOREIGN KEY (payment_method_id) REFERENCES dim_payment_methods(payment_method_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    
    -- Index pour optimiser les requêtes
    INDEX idx_payment_method (payment_method_id),
    INDEX idx_snapshot (snapshot_date, snapshot_version),
    INDEX idx_amount (total_amount),
    
    -- Contrainte d'unicité
    UNIQUE KEY uk_payment_snapshot (payment_method_id, snapshot_date, snapshot_version),
    
    -- Contraintes de validation
    CONSTRAINT chk_positive_amount_payment CHECK (total_amount >= 0),
    CONSTRAINT chk_positive_count_payment CHECK (transaction_count > 0),
    CONSTRAINT chk_positive_version_payment CHECK (snapshot_version > 0)
    
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Table de faits: totaux par méthode de paiement';

-- ============================================================================
-- Table: fact_product_purchase_counts
-- Description: Compteurs d'achats par produit (depuis ksqlDB)
-- Type: Table de faits avec snapshots versionnés
-- ============================================================================

CREATE TABLE fact_product_purchase_counts (
    -- Clé primaire
    product_count_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT 'Identifiant unique du compteur',
    
    -- Dimensions
    product_id VARCHAR(50) NOT NULL COMMENT 'Identifiant du produit',
    product_name VARCHAR(200) COMMENT 'Nom du produit',
    product_category VARCHAR(100) COMMENT 'Catégorie du produit',
    
    -- Métriques
    purchase_count INT NOT NULL COMMENT 'Nombre d''achats',
    total_revenue DECIMAL(15, 2) COMMENT 'Revenu total généré',
    avg_price DECIMAL(15, 2) COMMENT 'Prix moyen',
    unique_buyers INT COMMENT 'Nombre d''acheteurs uniques',
    
    -- Versioning (snapshots)
    snapshot_date DATE NOT NULL COMMENT 'Date du snapshot',
    snapshot_version INT NOT NULL COMMENT 'Version du snapshot',
    
    -- Métadonnées
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Date de création',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Date de mise à jour',
    
    -- Index pour optimiser les requêtes
    INDEX idx_product (product_id),
    INDEX idx_category (product_category),
    INDEX idx_snapshot (snapshot_date, snapshot_version),
    INDEX idx_purchase_count (purchase_count DESC),
    INDEX idx_revenue (total_revenue DESC),
    
    -- Contrainte d'unicité
    UNIQUE KEY uk_product_snapshot (product_id, snapshot_date, snapshot_version),
    
    -- Contraintes de validation
    CONSTRAINT chk_positive_count_product CHECK (purchase_count > 0),
    CONSTRAINT chk_positive_revenue CHECK (total_revenue >= 0),
    CONSTRAINT chk_positive_version_product CHECK (snapshot_version > 0)
    
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Table de faits: compteurs d''achats par produit';

-- ============================================================================
-- Vérification des tables créées
-- ============================================================================

SELECT 'Tables de faits créées avec succès' AS Status;

-- Affichage des tables créées
SHOW TABLES LIKE 'fact_%';
