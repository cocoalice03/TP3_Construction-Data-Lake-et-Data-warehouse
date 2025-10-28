"""
Gestionnaire de Permissions
Gère les droits d'accès au Data Lake et Data Warehouse
"""
import logging
import sys
from datetime import datetime
from typing import List, Dict, Optional
import mysql.connector
from mysql.connector import Error

from data_lake_config import LOGS_DIR


# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            LOGS_DIR / f"permissions_{datetime.now().strftime('%Y%m')}.log"
        )
    ]
)
logger = logging.getLogger(__name__)


class PermissionsManager:
    """Gestionnaire de permissions"""
    
    def __init__(self, mysql_config: dict):
        """Initialise le gestionnaire de permissions"""
        self.mysql_config = mysql_config
        self.mysql_connection = None
        self.mysql_cursor = None
        
        logger.info("PermissionsManager initialisé")
    
    def connect_mysql(self):
        """Établit la connexion à MySQL"""
        try:
            self.mysql_connection = mysql.connector.connect(**self.mysql_config)
            self.mysql_cursor = self.mysql_connection.cursor(dictionary=True)
            logger.info("✓ Connexion à MySQL établie")
        except Error as e:
            logger.error(f"Erreur de connexion à MySQL: {e}")
            raise
    
    def disconnect_mysql(self):
        """Ferme la connexion à MySQL"""
        if self.mysql_cursor:
            self.mysql_cursor.close()
        if self.mysql_connection:
            self.mysql_connection.close()
        logger.info("Connexion à MySQL fermée")
    
    # ========================================================================
    # Gestion des utilisateurs
    # ========================================================================
    
    def create_user(self, username: str, email: str, full_name: str,
                   department: str, role: str = 'viewer') -> int:
        """Crée un nouvel utilisateur"""
        query = """
        INSERT INTO users (username, email, full_name, department, role)
        VALUES (%s, %s, %s, %s, %s)
        """
        
        try:
            self.mysql_cursor.execute(query, (username, email, full_name, department, role))
            self.mysql_connection.commit()
            user_id = self.mysql_cursor.lastrowid
            logger.info(f"✓ Utilisateur créé: {username} (ID: {user_id})")
            return user_id
        except Error as e:
            logger.error(f"Erreur lors de la création de l'utilisateur: {e}")
            raise
    
    def get_user(self, username: str) -> Optional[Dict]:
        """Récupère un utilisateur par son username"""
        query = "SELECT * FROM users WHERE username = %s"
        
        try:
            self.mysql_cursor.execute(query, (username,))
            user = self.mysql_cursor.fetchone()
            return user
        except Error as e:
            logger.error(f"Erreur lors de la récupération de l'utilisateur: {e}")
            return None
    
    def list_users(self, role: Optional[str] = None, is_active: bool = True) -> List[Dict]:
        """Liste les utilisateurs"""
        if role:
            query = "SELECT * FROM users WHERE role = %s AND is_active = %s"
            params = (role, is_active)
        else:
            query = "SELECT * FROM users WHERE is_active = %s"
            params = (is_active,)
        
        try:
            self.mysql_cursor.execute(query, params)
            users = self.mysql_cursor.fetchall()
            return users
        except Error as e:
            logger.error(f"Erreur lors de la liste des utilisateurs: {e}")
            return []
    
    def update_user_role(self, username: str, new_role: str) -> bool:
        """Met à jour le rôle d'un utilisateur"""
        query = "UPDATE users SET role = %s WHERE username = %s"
        
        try:
            self.mysql_cursor.execute(query, (new_role, username))
            self.mysql_connection.commit()
            logger.info(f"✓ Rôle mis à jour: {username} -> {new_role}")
            return True
        except Error as e:
            logger.error(f"Erreur lors de la mise à jour du rôle: {e}")
            return False
    
    def deactivate_user(self, username: str) -> bool:
        """Désactive un utilisateur"""
        query = "UPDATE users SET is_active = FALSE WHERE username = %s"
        
        try:
            self.mysql_cursor.execute(query, (username,))
            self.mysql_connection.commit()
            logger.info(f"✓ Utilisateur désactivé: {username}")
            return True
        except Error as e:
            logger.error(f"Erreur lors de la désactivation: {e}")
            return False
    
    # ========================================================================
    # Permissions Data Lake
    # ========================================================================
    
    def grant_data_lake_permission(self, username: str, folder_path: str,
                                   permission_type: str, granted_by: str,
                                   expires_at: Optional[str] = None) -> bool:
        """Accorde une permission sur le Data Lake"""
        # Récupérer les IDs
        user = self.get_user(username)
        granter = self.get_user(granted_by)
        
        if not user or not granter:
            logger.error("Utilisateur ou accordeur non trouvé")
            return False
        
        query = """
        INSERT INTO data_lake_permissions 
        (user_id, folder_path, permission_type, granted_by, expires_at)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            granted_by = VALUES(granted_by),
            granted_at = CURRENT_TIMESTAMP,
            expires_at = VALUES(expires_at),
            is_active = TRUE
        """
        
        try:
            self.mysql_cursor.execute(query, (
                user['user_id'], folder_path, permission_type,
                granter['user_id'], expires_at
            ))
            self.mysql_connection.commit()
            logger.info(f"✓ Permission accordée: {username} -> {folder_path} ({permission_type})")
            return True
        except Error as e:
            logger.error(f"Erreur lors de l'octroi de permission: {e}")
            return False
    
    def revoke_data_lake_permission(self, username: str, folder_path: str,
                                    permission_type: str) -> bool:
        """Révoque une permission sur le Data Lake"""
        user = self.get_user(username)
        if not user:
            logger.error("Utilisateur non trouvé")
            return False
        
        query = """
        UPDATE data_lake_permissions
        SET is_active = FALSE
        WHERE user_id = %s AND folder_path = %s AND permission_type = %s
        """
        
        try:
            self.mysql_cursor.execute(query, (user['user_id'], folder_path, permission_type))
            self.mysql_connection.commit()
            logger.info(f"✓ Permission révoquée: {username} -> {folder_path} ({permission_type})")
            return True
        except Error as e:
            logger.error(f"Erreur lors de la révocation: {e}")
            return False
    
    def check_data_lake_permission(self, username: str, folder_path: str,
                                   permission_type: str) -> bool:
        """Vérifie si un utilisateur a une permission sur le Data Lake"""
        user = self.get_user(username)
        if not user:
            return False
        
        # Admin a tous les droits
        if user['role'] == 'admin':
            return True
        
        query = """
        SELECT COUNT(*) as count
        FROM data_lake_permissions
        WHERE user_id = %s
          AND folder_path LIKE %s
          AND permission_type IN (%s, 'admin')
          AND is_active = TRUE
          AND (expires_at IS NULL OR expires_at > NOW())
        """
        
        try:
            # Vérifier le chemin exact et les chemins parents
            self.mysql_cursor.execute(query, (user['user_id'], f"{folder_path}%", permission_type))
            result = self.mysql_cursor.fetchone()
            return result['count'] > 0
        except Error as e:
            logger.error(f"Erreur lors de la vérification: {e}")
            return False
    
    def list_user_data_lake_permissions(self, username: str) -> List[Dict]:
        """Liste les permissions Data Lake d'un utilisateur"""
        user = self.get_user(username)
        if not user:
            return []
        
        query = """
        SELECT 
            folder_path,
            permission_type,
            granted_at,
            expires_at,
            is_active
        FROM data_lake_permissions
        WHERE user_id = %s AND is_active = TRUE
        ORDER BY folder_path, permission_type
        """
        
        try:
            self.mysql_cursor.execute(query, (user['user_id'],))
            permissions = self.mysql_cursor.fetchall()
            return permissions
        except Error as e:
            logger.error(f"Erreur lors de la liste des permissions: {e}")
            return []
    
    # ========================================================================
    # Permissions Data Warehouse
    # ========================================================================
    
    def grant_warehouse_permission(self, username: str, table_name: str,
                                   permission_type: str, granted_by: str,
                                   expires_at: Optional[str] = None) -> bool:
        """Accorde une permission sur le Data Warehouse"""
        user = self.get_user(username)
        granter = self.get_user(granted_by)
        
        if not user or not granter:
            logger.error("Utilisateur ou accordeur non trouvé")
            return False
        
        query = """
        INSERT INTO data_warehouse_permissions 
        (user_id, table_name, permission_type, granted_by, expires_at)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            granted_by = VALUES(granted_by),
            granted_at = CURRENT_TIMESTAMP,
            expires_at = VALUES(expires_at),
            is_active = TRUE
        """
        
        try:
            self.mysql_cursor.execute(query, (
                user['user_id'], table_name, permission_type,
                granter['user_id'], expires_at
            ))
            self.mysql_connection.commit()
            logger.info(f"✓ Permission accordée: {username} -> {table_name} ({permission_type})")
            return True
        except Error as e:
            logger.error(f"Erreur lors de l'octroi de permission: {e}")
            return False
    
    def check_warehouse_permission(self, username: str, table_name: str,
                                   permission_type: str) -> bool:
        """Vérifie si un utilisateur a une permission sur une table"""
        user = self.get_user(username)
        if not user:
            return False
        
        # Admin a tous les droits
        if user['role'] == 'admin':
            return True
        
        query = """
        SELECT COUNT(*) as count
        FROM data_warehouse_permissions
        WHERE user_id = %s
          AND (table_name = %s OR table_name = '*')
          AND (permission_type = %s OR permission_type = 'all')
          AND is_active = TRUE
          AND (expires_at IS NULL OR expires_at > NOW())
        """
        
        try:
            self.mysql_cursor.execute(query, (user['user_id'], table_name, permission_type))
            result = self.mysql_cursor.fetchone()
            return result['count'] > 0
        except Error as e:
            logger.error(f"Erreur lors de la vérification: {e}")
            return False
    
    # ========================================================================
    # Audit
    # ========================================================================
    
    def log_access(self, username: str, action_type: str, resource_type: str,
                   resource_path: str, status: str, error_message: Optional[str] = None,
                   query_text: Optional[str] = None) -> bool:
        """Enregistre un accès dans le journal d'audit"""
        user = self.get_user(username)
        user_id = user['user_id'] if user else None
        
        query = """
        INSERT INTO access_audit_log 
        (user_id, action_type, resource_type, resource_path, query_text, status, error_message)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        try:
            self.mysql_cursor.execute(query, (
                user_id, action_type, resource_type, resource_path,
                query_text, status, error_message
            ))
            self.mysql_connection.commit()
            return True
        except Error as e:
            logger.error(f"Erreur lors de l'enregistrement de l'audit: {e}")
            return False
    
    def get_user_audit_log(self, username: str, limit: int = 100) -> List[Dict]:
        """Récupère le journal d'audit d'un utilisateur"""
        user = self.get_user(username)
        if not user:
            return []
        
        query = """
        SELECT 
            action_type,
            resource_type,
            resource_path,
            status,
            accessed_at
        FROM access_audit_log
        WHERE user_id = %s
        ORDER BY accessed_at DESC
        LIMIT %s
        """
        
        try:
            self.mysql_cursor.execute(query, (user['user_id'], limit))
            logs = self.mysql_cursor.fetchall()
            return logs
        except Error as e:
            logger.error(f"Erreur lors de la récupération de l'audit: {e}")
            return []


def main():
    """Point d'entrée principal"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Gestionnaire de permissions"
    )
    parser.add_argument(
        "--mysql-password",
        type=str,
        default="",
        help="Mot de passe MySQL"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commandes disponibles')
    
    # Créer un utilisateur
    create_user_parser = subparsers.add_parser('create-user', help='Créer un utilisateur')
    create_user_parser.add_argument('--username', required=True)
    create_user_parser.add_argument('--email', required=True)
    create_user_parser.add_argument('--full-name', required=True)
    create_user_parser.add_argument('--department', required=True)
    create_user_parser.add_argument('--role', default='viewer')
    
    # Accorder une permission Data Lake
    grant_dl_parser = subparsers.add_parser('grant-datalake', help='Accorder permission Data Lake')
    grant_dl_parser.add_argument('--username', required=True)
    grant_dl_parser.add_argument('--folder', required=True)
    grant_dl_parser.add_argument('--permission', required=True, choices=['read', 'write', 'delete', 'admin'])
    grant_dl_parser.add_argument('--granted-by', required=True)
    
    # Lister les permissions
    list_perms_parser = subparsers.add_parser('list-permissions', help='Lister les permissions')
    list_perms_parser.add_argument('--username', required=True)
    
    args = parser.parse_args()
    
    mysql_config = {
        "host": "localhost",
        "port": 3306,
        "database": "data_warehouse",
        "user": "root",
        "password": args.mysql_password,
        "charset": "utf8mb4",
        "use_unicode": True
    }
    
    try:
        manager = PermissionsManager(mysql_config)
        manager.connect_mysql()
        
        if args.command == 'create-user':
            manager.create_user(
                args.username, args.email, args.full_name,
                args.department, args.role
            )
        
        elif args.command == 'grant-datalake':
            manager.grant_data_lake_permission(
                args.username, args.folder, args.permission, args.granted_by
            )
        
        elif args.command == 'list-permissions':
            perms = manager.list_user_data_lake_permissions(args.username)
            print(f"\nPermissions Data Lake pour {args.username}:")
            for perm in perms:
                print(f"  - {perm['folder_path']}: {perm['permission_type']}")
        
        manager.disconnect_mysql()
    
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
