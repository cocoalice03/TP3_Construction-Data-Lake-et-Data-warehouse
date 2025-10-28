-- ============================================================================
-- Requêtes Analytiques Exemples - Data Warehouse
-- ============================================================================
-- Description: Exemples de requêtes pour exploiter le Data Warehouse
-- Version: 1.0
-- Date: Janvier 2025
-- ============================================================================

USE data_warehouse;

-- ============================================================================
-- 1. ANALYSE DES UTILISATEURS
-- ============================================================================

-- Top 10 utilisateurs par montant total
SELECT 
    u.user_id,
    u.user_name,
    u.user_country,
    u.user_city,
    SUM(f.total_amount) as total_spent,
    SUM(f.transaction_count) as total_transactions,
    AVG(f.avg_amount) as avg_transaction_amount
FROM dim_users u
JOIN fact_user_transaction_summary f ON u.user_id = f.user_id
WHERE f.snapshot_date = (SELECT MAX(snapshot_date) FROM fact_user_transaction_summary)
GROUP BY u.user_id, u.user_name, u.user_country, u.user_city
ORDER BY total_spent DESC
LIMIT 10;

-- Distribution des utilisateurs par pays
SELECT 
    u.user_country,
    COUNT(DISTINCT u.user_id) as user_count,
    SUM(f.total_amount) as total_revenue,
    AVG(f.avg_amount) as avg_transaction_amount
FROM dim_users u
LEFT JOIN fact_user_transaction_summary f ON u.user_id = f.user_id
WHERE f.snapshot_date = CURDATE() OR f.snapshot_date IS NULL
GROUP BY u.user_country
ORDER BY total_revenue DESC;

-- ============================================================================
-- 2. ANALYSE DES TRANSACTIONS
-- ============================================================================

-- Résumé par type de transaction
SELECT 
    transaction_type,
    COUNT(DISTINCT user_id) as unique_users,
    SUM(total_amount) as total_amount,
    SUM(transaction_count) as total_transactions,
    AVG(avg_amount) as avg_amount,
    MAX(max_amount) as max_transaction,
    MIN(min_amount) as min_transaction
FROM fact_user_transaction_summary
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM fact_user_transaction_summary)
GROUP BY transaction_type
ORDER BY total_amount DESC;

-- Évolution des transactions dans le temps
SELECT 
    snapshot_date,
    SUM(total_amount) as daily_total,
    SUM(transaction_count) as daily_count,
    AVG(avg_amount) as daily_avg
FROM fact_user_transaction_summary
GROUP BY snapshot_date
ORDER BY snapshot_date DESC
LIMIT 30;

-- ============================================================================
-- 3. ANALYSE DES MÉTHODES DE PAIEMENT
-- ============================================================================

-- Performance par méthode de paiement
SELECT 
    pm.payment_method_name,
    pm.payment_method_category,
    SUM(f.total_amount) as total_revenue,
    SUM(f.transaction_count) as total_transactions,
    AVG(f.avg_amount) as avg_transaction_amount,
    (SUM(f.total_amount) / (SELECT SUM(total_amount) FROM fact_payment_method_totals WHERE snapshot_date = CURDATE()) * 100) as revenue_percentage
FROM dim_payment_methods pm
JOIN fact_payment_method_totals f ON pm.payment_method_id = f.payment_method_id
WHERE f.snapshot_date = CURDATE()
GROUP BY pm.payment_method_name, pm.payment_method_category
ORDER BY total_revenue DESC;

-- Comparaison des catégories de paiement
SELECT 
    pm.payment_method_category,
    COUNT(DISTINCT pm.payment_method_id) as methods_count,
    SUM(f.total_amount) as total_revenue,
    SUM(f.transaction_count) as total_transactions
FROM dim_payment_methods pm
JOIN fact_payment_method_totals f ON pm.payment_method_id = f.payment_method_id
WHERE f.snapshot_date = (SELECT MAX(snapshot_date) FROM fact_payment_method_totals)
GROUP BY pm.payment_method_category
ORDER BY total_revenue DESC;

-- ============================================================================
-- 4. ANALYSE DES PRODUITS
-- ============================================================================

-- Top 20 produits les plus vendus
SELECT 
    product_id,
    product_name,
    product_category,
    purchase_count,
    total_revenue,
    avg_price,
    unique_buyers,
    ROUND(total_revenue / purchase_count, 2) as revenue_per_purchase
FROM fact_product_purchase_counts
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM fact_product_purchase_counts)
ORDER BY purchase_count DESC
LIMIT 20;

-- Performance par catégorie de produit
SELECT 
    product_category,
    COUNT(DISTINCT product_id) as products_count,
    SUM(purchase_count) as total_purchases,
    SUM(total_revenue) as total_revenue,
    AVG(avg_price) as avg_product_price,
    SUM(unique_buyers) as total_unique_buyers
FROM fact_product_purchase_counts
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM fact_product_purchase_counts)
GROUP BY product_category
ORDER BY total_revenue DESC;

-- Produits avec le meilleur ratio acheteurs/achats
SELECT 
    product_name,
    product_category,
    purchase_count,
    unique_buyers,
    ROUND(purchase_count / unique_buyers, 2) as purchases_per_buyer,
    total_revenue
FROM fact_product_purchase_counts
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM fact_product_purchase_counts)
    AND unique_buyers > 0
ORDER BY purchases_per_buyer DESC
LIMIT 20;

-- ============================================================================
-- 5. ANALYSE MULTI-DEVISES (EUR)
-- ============================================================================

-- Comparaison montants originaux vs EUR
SELECT 
    u.user_id,
    u.user_name,
    u.user_country,
    SUM(f1.total_amount) as total_original,
    SUM(f2.total_amount_eur) as total_eur,
    AVG(f2.exchange_rate) as avg_exchange_rate
FROM dim_users u
JOIN fact_user_transaction_summary f1 ON u.user_id = f1.user_id
JOIN fact_user_transaction_summary_eur f2 ON u.user_id = f2.user_id 
    AND f1.transaction_type = f2.transaction_type
    AND f1.snapshot_date = f2.snapshot_date
WHERE f1.snapshot_date = (SELECT MAX(snapshot_date) FROM fact_user_transaction_summary)
GROUP BY u.user_id, u.user_name, u.user_country
ORDER BY total_eur DESC
LIMIT 10;

-- ============================================================================
-- 6. ANALYSES AVANCÉES
-- ============================================================================

-- Segmentation RFM (Recency, Frequency, Monetary)
SELECT 
    u.user_id,
    u.user_name,
    DATEDIFF(CURDATE(), MAX(f.last_transaction_date)) as recency_days,
    SUM(f.transaction_count) as frequency,
    SUM(f.total_amount) as monetary,
    CASE 
        WHEN DATEDIFF(CURDATE(), MAX(f.last_transaction_date)) <= 30 THEN 'Active'
        WHEN DATEDIFF(CURDATE(), MAX(f.last_transaction_date)) <= 90 THEN 'At Risk'
        ELSE 'Inactive'
    END as customer_status
FROM dim_users u
JOIN fact_user_transaction_summary f ON u.user_id = f.user_id
GROUP BY u.user_id, u.user_name
ORDER BY monetary DESC;

-- Analyse de cohort par pays
SELECT 
    u.user_country,
    COUNT(DISTINCT u.user_id) as total_users,
    SUM(f.total_amount) as total_revenue,
    AVG(f.total_amount) as avg_revenue_per_user,
    SUM(f.transaction_count) as total_transactions,
    AVG(f.transaction_count) as avg_transactions_per_user
FROM dim_users u
JOIN fact_user_transaction_summary f ON u.user_id = f.user_id
WHERE f.snapshot_date = (SELECT MAX(snapshot_date) FROM fact_user_transaction_summary)
GROUP BY u.user_country
HAVING total_users >= 5
ORDER BY total_revenue DESC;

-- Tendances temporelles avec fenêtres glissantes
SELECT 
    snapshot_date,
    SUM(total_amount) as daily_revenue,
    AVG(SUM(total_amount)) OVER (
        ORDER BY snapshot_date 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) as moving_avg_7days,
    LAG(SUM(total_amount), 1) OVER (ORDER BY snapshot_date) as prev_day_revenue,
    ROUND(
        (SUM(total_amount) - LAG(SUM(total_amount), 1) OVER (ORDER BY snapshot_date)) / 
        LAG(SUM(total_amount), 1) OVER (ORDER BY snapshot_date) * 100, 
        2
    ) as growth_percentage
FROM fact_user_transaction_summary
GROUP BY snapshot_date
ORDER BY snapshot_date DESC
LIMIT 30;

-- ============================================================================
-- 7. VUES MATÉRIALISÉES (Optionnel - pour performance)
-- ============================================================================

-- Vue: Résumé quotidien global
CREATE OR REPLACE VIEW v_daily_summary AS
SELECT 
    f.snapshot_date,
    COUNT(DISTINCT f.user_id) as active_users,
    SUM(f.total_amount) as total_revenue,
    SUM(f.transaction_count) as total_transactions,
    AVG(f.avg_amount) as avg_transaction_amount
FROM fact_user_transaction_summary f
GROUP BY f.snapshot_date;

-- Vue: Top produits par catégorie
CREATE OR REPLACE VIEW v_top_products_by_category AS
SELECT 
    product_category,
    product_name,
    purchase_count,
    total_revenue,
    RANK() OVER (PARTITION BY product_category ORDER BY purchase_count DESC) as rank_in_category
FROM fact_product_purchase_counts
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM fact_product_purchase_counts);

-- Vue: Métriques utilisateur enrichies
CREATE OR REPLACE VIEW v_user_metrics AS
SELECT 
    u.user_id,
    u.user_name,
    u.user_country,
    u.user_city,
    SUM(f.total_amount) as lifetime_value,
    SUM(f.transaction_count) as total_transactions,
    AVG(f.avg_amount) as avg_transaction,
    MAX(f.last_transaction_date) as last_purchase_date,
    DATEDIFF(CURDATE(), MAX(f.last_transaction_date)) as days_since_last_purchase
FROM dim_users u
LEFT JOIN fact_user_transaction_summary f ON u.user_id = f.user_id
GROUP BY u.user_id, u.user_name, u.user_country, u.user_city;

-- ============================================================================
-- 8. REQUÊTES DE MAINTENANCE
-- ============================================================================

-- Vérifier l'intégrité référentielle
SELECT 
    'Orphan records in fact_user_transaction_summary' as check_name,
    COUNT(*) as count
FROM fact_user_transaction_summary f
LEFT JOIN dim_users u ON f.user_id = u.user_id
WHERE u.user_id IS NULL

UNION ALL

SELECT 
    'Orphan records in fact_payment_method_totals' as check_name,
    COUNT(*) as count
FROM fact_payment_method_totals f
LEFT JOIN dim_payment_methods pm ON f.payment_method_id = pm.payment_method_id
WHERE pm.payment_method_id IS NULL;

-- Statistiques des tables
SELECT 
    table_name,
    table_rows,
    ROUND(data_length / 1024 / 1024, 2) as data_size_mb,
    ROUND(index_length / 1024 / 1024, 2) as index_size_mb,
    ROUND((data_length + index_length) / 1024 / 1024, 2) as total_size_mb
FROM information_schema.tables
WHERE table_schema = 'data_warehouse'
ORDER BY (data_length + index_length) DESC;

-- Dernières synchronisations
SELECT 
    'fact_user_transaction_summary' as table_name,
    MAX(snapshot_date) as last_snapshot,
    MAX(snapshot_version) as last_version,
    COUNT(*) as total_records
FROM fact_user_transaction_summary

UNION ALL

SELECT 
    'fact_payment_method_totals' as table_name,
    MAX(snapshot_date) as last_snapshot,
    MAX(snapshot_version) as last_version,
    COUNT(*) as total_records
FROM fact_payment_method_totals

UNION ALL

SELECT 
    'fact_product_purchase_counts' as table_name,
    MAX(snapshot_date) as last_snapshot,
    MAX(snapshot_version) as last_version,
    COUNT(*) as total_records
FROM fact_product_purchase_counts;
