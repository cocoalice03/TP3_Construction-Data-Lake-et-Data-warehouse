-- ============================================================================
-- Script de Création de la Base de Données Data Warehouse
-- ============================================================================
-- Description: Création de la base de données MySQL pour le Data Warehouse
-- Version: 1.0
-- Date: Janvier 2025
-- ============================================================================

-- Suppression de la base si elle existe (ATTENTION: perte de données)
DROP DATABASE IF EXISTS data_warehouse;

-- Création de la base de données
CREATE DATABASE data_warehouse
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- Utilisation de la base de données
USE data_warehouse;

-- Affichage de confirmation
SELECT 'Base de données data_warehouse créée avec succès' AS Status;
