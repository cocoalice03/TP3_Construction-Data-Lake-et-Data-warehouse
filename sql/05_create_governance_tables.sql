-- ============================================================================
-- Tables de Gouvernance et Sécurité
-- ============================================================================

USE data_warehouse;

-- ----------------------------------------------------------------------------
-- Table: users - Utilisateurs du système
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255),
    department VARCHAR(100),
    role ENUM('admin', 'analyst', 'viewer', 'data_engineer') NOT NULL DEFAULT 'viewer',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_role (role),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Utilisateurs du système avec leurs rôles';

-- ----------------------------------------------------------------------------
-- Table: data_lake_permissions - Permissions par dossier du Data Lake
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS data_lake_permissions (
    permission_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    folder_path VARCHAR(500) NOT NULL,
    permission_type ENUM('read', 'write', 'delete', 'admin') NOT NULL DEFAULT 'read',
    granted_by INT,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by) REFERENCES users(user_id) ON DELETE SET NULL,
    
    INDEX idx_user_id (user_id),
    INDEX idx_folder_path (folder_path),
    INDEX idx_permission_type (permission_type),
    INDEX idx_is_active (is_active),
    INDEX idx_expires_at (expires_at),
    
    UNIQUE KEY unique_user_folder_permission (user_id, folder_path, permission_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Permissions d''accès par dossier du Data Lake';

-- ----------------------------------------------------------------------------
-- Table: data_warehouse_permissions - Permissions sur les tables MySQL
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS data_warehouse_permissions (
    permission_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    permission_type ENUM('select', 'insert', 'update', 'delete', 'all') NOT NULL DEFAULT 'select',
    granted_by INT,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by) REFERENCES users(user_id) ON DELETE SET NULL,
    
    INDEX idx_user_id (user_id),
    INDEX idx_table_name (table_name),
    INDEX idx_permission_type (permission_type),
    INDEX idx_is_active (is_active),
    
    UNIQUE KEY unique_user_table_permission (user_id, table_name, permission_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Permissions d''accès aux tables du Data Warehouse';

-- ----------------------------------------------------------------------------
-- Table: data_retention_policies - Politiques de rétention des données
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS data_retention_policies (
    policy_id INT AUTO_INCREMENT PRIMARY KEY,
    feed_name VARCHAR(100) NOT NULL,
    feed_type ENUM('stream', 'table') NOT NULL,
    retention_days INT NOT NULL,
    retention_versions INT NULL COMMENT 'Pour les tables versionnées',
    auto_delete BOOLEAN DEFAULT TRUE,
    last_cleanup_at TIMESTAMP NULL,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    
    FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL,
    
    INDEX idx_feed_name (feed_name),
    INDEX idx_feed_type (feed_type),
    INDEX idx_is_active (is_active),
    
    UNIQUE KEY unique_feed (feed_name, feed_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Politiques de rétention des données historiques';

-- ----------------------------------------------------------------------------
-- Table: data_deletion_log - Journal des suppressions de données
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS data_deletion_log (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    feed_name VARCHAR(100) NOT NULL,
    feed_type ENUM('stream', 'table') NOT NULL,
    folder_path VARCHAR(500) NOT NULL,
    deletion_type ENUM('retention', 'manual', 'gdpr') NOT NULL,
    files_deleted INT DEFAULT 0,
    size_deleted_mb DECIMAL(15,2) DEFAULT 0,
    deleted_by INT,
    deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    
    FOREIGN KEY (deleted_by) REFERENCES users(user_id) ON DELETE SET NULL,
    
    INDEX idx_feed_name (feed_name),
    INDEX idx_deletion_type (deletion_type),
    INDEX idx_deleted_at (deleted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Journal des suppressions de données';

-- ----------------------------------------------------------------------------
-- Table: access_audit_log - Journal d'audit des accès
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS access_audit_log (
    audit_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    action_type ENUM('read', 'write', 'delete', 'query', 'export') NOT NULL,
    resource_type ENUM('data_lake', 'data_warehouse', 'api') NOT NULL,
    resource_path VARCHAR(500),
    query_text TEXT,
    status ENUM('success', 'denied', 'error') NOT NULL,
    error_message TEXT,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL,
    
    INDEX idx_user_id (user_id),
    INDEX idx_action_type (action_type),
    INDEX idx_resource_type (resource_type),
    INDEX idx_status (status),
    INDEX idx_accessed_at (accessed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Journal d''audit de tous les accès aux données';

-- ----------------------------------------------------------------------------
-- Table: feed_registry - Registre de tous les feeds
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS feed_registry (
    feed_id INT AUTO_INCREMENT PRIMARY KEY,
    feed_name VARCHAR(100) NOT NULL UNIQUE,
    feed_type ENUM('stream', 'table') NOT NULL,
    source_type ENUM('kafka', 'ksqldb', 'api', 'file') NOT NULL,
    source_config JSON,
    kafka_topic VARCHAR(200),
    partitioning_strategy ENUM('date', 'version', 'custom') NOT NULL,
    storage_format ENUM('parquet', 'avro', 'json') DEFAULT 'parquet',
    compression ENUM('snappy', 'gzip', 'lz4', 'none') DEFAULT 'snappy',
    schema_definition JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_ingestion_at TIMESTAMP NULL,
    
    FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL,
    
    INDEX idx_feed_name (feed_name),
    INDEX idx_feed_type (feed_type),
    INDEX idx_source_type (source_type),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Registre centralisé de tous les feeds';

-- ----------------------------------------------------------------------------
-- Insertion des utilisateurs par défaut
-- ----------------------------------------------------------------------------
INSERT INTO users (username, email, full_name, department, role) VALUES
('admin', 'admin@company.com', 'System Administrator', 'IT', 'admin'),
('data_engineer', 'engineer@company.com', 'Data Engineer', 'Data', 'data_engineer'),
('analyst', 'analyst@company.com', 'Data Analyst', 'Analytics', 'analyst'),
('viewer', 'viewer@company.com', 'Data Viewer', 'Business', 'viewer')
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

-- ----------------------------------------------------------------------------
-- Insertion des politiques de rétention par défaut
-- ----------------------------------------------------------------------------
INSERT INTO data_retention_policies (feed_name, feed_type, retention_days, retention_versions, created_by) VALUES
('transaction_stream', 'stream', 90, NULL, 1),
('transaction_flattened', 'stream', 90, NULL, 1),
('transaction_stream_anonymized', 'stream', 365, NULL, 1),
('transaction_stream_blacklisted', 'stream', 30, NULL, 1),
('user_transaction_summary', 'table', 365, 10, 1),
('user_transaction_summary_eur', 'table', 365, 10, 1),
('payment_method_totals', 'table', 365, 10, 1),
('product_purchase_counts', 'table', 365, 10, 1)
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

-- ----------------------------------------------------------------------------
-- Insertion des feeds dans le registre
-- ----------------------------------------------------------------------------
INSERT INTO feed_registry (feed_name, feed_type, source_type, kafka_topic, partitioning_strategy, created_by) VALUES
('transaction_stream', 'stream', 'kafka', 'transaction_stream', 'date', 1),
('transaction_flattened', 'stream', 'kafka', 'transaction_flattened', 'date', 1),
('transaction_stream_anonymized', 'stream', 'kafka', 'transaction_stream_anonymized', 'date', 1),
('transaction_stream_blacklisted', 'stream', 'kafka', 'transaction_stream_blacklisted', 'date', 1),
('user_transaction_summary', 'table', 'kafka', 'user_transaction_summary', 'version', 1),
('user_transaction_summary_eur', 'table', 'kafka', 'user_transaction_summary_eur', 'version', 1),
('payment_method_totals', 'table', 'kafka', 'payment_method_totals', 'version', 1),
('product_purchase_counts', 'table', 'kafka', 'product_purchase_counts', 'version', 1)
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

-- ----------------------------------------------------------------------------
-- Permissions par défaut pour l'admin
-- ----------------------------------------------------------------------------
INSERT INTO data_lake_permissions (user_id, folder_path, permission_type, granted_by) VALUES
(1, '/data_lake/streams/', 'admin', 1),
(1, '/data_lake/tables/', 'admin', 1)
ON DUPLICATE KEY UPDATE is_active = TRUE;

INSERT INTO data_warehouse_permissions (user_id, table_name, permission_type, granted_by) VALUES
(1, '*', 'all', 1)
ON DUPLICATE KEY UPDATE is_active = TRUE;

-- ----------------------------------------------------------------------------
-- Vérification
-- ----------------------------------------------------------------------------
SELECT 'Tables de gouvernance créées avec succès' AS Status;

SELECT 
    'users' as table_name,
    COUNT(*) as row_count
FROM users
UNION ALL
SELECT 'data_retention_policies', COUNT(*) FROM data_retention_policies
UNION ALL
SELECT 'feed_registry', COUNT(*) FROM feed_registry
UNION ALL
SELECT 'data_lake_permissions', COUNT(*) FROM data_lake_permissions;
