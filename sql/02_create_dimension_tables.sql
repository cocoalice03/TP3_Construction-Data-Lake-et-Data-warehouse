-- ============================================================================
-- Script de Création des Tables de Dimension
-- ============================================================================
-- Description: Création des tables de dimension du Data Warehouse
-- Version: 1.0
-- Date: Janvier 2025
-- ============================================================================

USE data_warehouse;

-- ============================================================================
-- Table: dim_users
-- Description: Table de dimension pour les utilisateurs
-- Type: Slowly Changing Dimension (SCD) Type 1
-- ============================================================================

CREATE TABLE dim_users (
    -- Clé primaire
    user_id VARCHAR(50) PRIMARY KEY COMMENT 'Identifiant unique de l''utilisateur',
    
    -- Attributs de l'utilisateur
    user_name VARCHAR(100) COMMENT 'Nom complet de l''utilisateur',
    user_email VARCHAR(100) COMMENT 'Email de l''utilisateur',
    user_country VARCHAR(50) COMMENT 'Pays de l''utilisateur',
    user_city VARCHAR(100) COMMENT 'Ville de l''utilisateur',
    
    -- Métadonnées
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Date de création',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Date de dernière mise à jour',
    
    -- Index pour optimiser les requêtes
    INDEX idx_country (user_country),
    INDEX idx_city (user_city),
    INDEX idx_email (user_email)
    
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Table de dimension des utilisateurs';

-- ============================================================================
-- Table: dim_payment_methods
-- Description: Table de dimension pour les méthodes de paiement
-- Type: Slowly Changing Dimension (SCD) Type 1
-- ============================================================================

CREATE TABLE dim_payment_methods (
    -- Clé primaire
    payment_method_id INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Identifiant unique de la méthode de paiement',
    
    -- Attributs de la méthode de paiement
    payment_method_name VARCHAR(50) UNIQUE NOT NULL COMMENT 'Nom de la méthode de paiement',
    payment_method_category VARCHAR(50) COMMENT 'Catégorie de la méthode (carte, virement, etc.)',
    is_active BOOLEAN DEFAULT TRUE COMMENT 'Indique si la méthode est active',
    
    -- Métadonnées
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Date de création',
    
    -- Index pour optimiser les requêtes
    INDEX idx_category (payment_method_category),
    INDEX idx_active (is_active)
    
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Table de dimension des méthodes de paiement';

-- ============================================================================
-- Insertion des méthodes de paiement par défaut
-- ============================================================================

INSERT INTO dim_payment_methods (payment_method_name, payment_method_category, is_active) VALUES
    ('credit_card', 'card', TRUE),
    ('debit_card', 'card', TRUE),
    ('paypal', 'digital_wallet', TRUE),
    ('bank_transfer', 'transfer', TRUE),
    ('cash', 'physical', TRUE),
    ('apple_pay', 'digital_wallet', TRUE),
    ('google_pay', 'digital_wallet', TRUE),
    ('stripe', 'payment_gateway', TRUE);

-- ============================================================================
-- Vérification des tables créées
-- ============================================================================

SELECT 'Tables de dimension créées avec succès' AS Status;

-- Affichage du nombre de méthodes de paiement insérées
SELECT COUNT(*) AS payment_methods_count FROM dim_payment_methods;
