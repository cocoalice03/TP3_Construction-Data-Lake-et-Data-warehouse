"""
Utilitaires pour la gestion des métadonnées du Data Lake
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd

from data_lake_config import (
    STREAMS_DIR, TABLES_DIR, DATA_LAKE_ROOT
)


class MetadataReader:
    """Lecteur de métadonnées du Data Lake"""
    
    @staticmethod
    def read_metadata(path: Path) -> Optional[Dict]:
        """Lit le fichier de métadonnées d'un stream ou table"""
        metadata_file = path / "_metadata.json"
        
        if not metadata_file.exists():
            return None
        
        with open(metadata_file, 'r') as f:
            return json.load(f)
    
    @staticmethod
    def list_all_metadata() -> Dict[str, Dict]:
        """Liste toutes les métadonnées du data lake"""
        all_metadata = {
            "streams": {},
            "tables": {}
        }
        
        # Lire les métadonnées des streams
        if STREAMS_DIR.exists():
            for stream_dir in STREAMS_DIR.iterdir():
                if stream_dir.is_dir():
                    metadata = MetadataReader.read_metadata(stream_dir)
                    if metadata:
                        all_metadata["streams"][stream_dir.name] = metadata
        
        # Lire les métadonnées des tables
        if TABLES_DIR.exists():
            for table_dir in TABLES_DIR.iterdir():
                if table_dir.is_dir():
                    metadata = MetadataReader.read_metadata(table_dir)
                    if metadata:
                        all_metadata["tables"][table_dir.name] = metadata
        
        return all_metadata
    
    @staticmethod
    def get_statistics() -> Dict:
        """Calcule les statistiques globales du data lake"""
        all_metadata = MetadataReader.list_all_metadata()
        
        stats = {
            "total_streams": len(all_metadata["streams"]),
            "total_tables": len(all_metadata["tables"]),
            "total_records": 0,
            "total_size_mb": 0,
            "total_partitions": 0,
            "last_exports": []
        }
        
        # Agréger les statistiques des streams
        for stream_name, metadata in all_metadata["streams"].items():
            stats["total_records"] += metadata.get("total_records", 0)
            stats["total_size_mb"] += metadata.get("total_size_mb", 0)
            stats["total_partitions"] += len(metadata.get("partitions", []))
            
            if "last_export" in metadata:
                stats["last_exports"].append({
                    "name": stream_name,
                    "type": "stream",
                    "last_export": metadata["last_export"]
                })
        
        # Agréger les statistiques des tables
        for table_name, metadata in all_metadata["tables"].items():
            stats["total_records"] += metadata.get("total_records", 0)
            stats["total_size_mb"] += metadata.get("total_size_mb", 0)
            stats["total_partitions"] += len(metadata.get("partitions", []))
            
            if "last_export" in metadata:
                stats["last_exports"].append({
                    "name": table_name,
                    "type": "table",
                    "last_export": metadata["last_export"]
                })
        
        # Trier les derniers exports par date
        stats["last_exports"].sort(
            key=lambda x: x["last_export"],
            reverse=True
        )
        
        return stats
    
    @staticmethod
    def get_partition_info(path: Path) -> List[Dict]:
        """Récupère les informations des partitions d'un stream ou table"""
        partitions = []
        
        # Chercher les partitions par date (year=YYYY/month=MM/day=DD)
        for year_dir in path.glob("year=*"):
            year = int(year_dir.name.split("=")[1])
            
            for month_dir in year_dir.glob("month=*"):
                month = int(month_dir.name.split("=")[1])
                
                for day_dir in month_dir.glob("day=*"):
                    day = int(day_dir.name.split("=")[1])
                    
                    # Compter les fichiers et calculer la taille
                    files = list(day_dir.glob("*.parquet"))
                    total_size = sum(f.stat().st_size for f in files)
                    
                    partitions.append({
                        "type": "date",
                        "year": year,
                        "month": month,
                        "day": day,
                        "path": str(day_dir.relative_to(path)),
                        "files_count": len(files),
                        "size_mb": round(total_size / (1024 * 1024), 2)
                    })
        
        # Chercher les partitions par version (version=vX)
        for version_dir in path.glob("version=v*"):
            version = int(version_dir.name.split("=v")[1])
            
            # Compter les fichiers et calculer la taille
            files = list(version_dir.glob("*.parquet"))
            total_size = sum(f.stat().st_size for f in files)
            
            partitions.append({
                "type": "version",
                "version": version,
                "path": str(version_dir.relative_to(path)),
                "files_count": len(files),
                "size_mb": round(total_size / (1024 * 1024), 2)
            })
        
        return partitions


class MetadataAnalyzer:
    """Analyseur de métadonnées pour générer des rapports"""
    
    @staticmethod
    def generate_report() -> str:
        """Génère un rapport complet du data lake"""
        stats = MetadataReader.get_statistics()
        all_metadata = MetadataReader.list_all_metadata()
        
        report = []
        report.append("=" * 80)
        report.append("📊 RAPPORT DU DATA LAKE")
        report.append("=" * 80)
        report.append(f"Généré le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Statistiques globales
        report.append("📈 STATISTIQUES GLOBALES")
        report.append("-" * 80)
        report.append(f"  Streams: {stats['total_streams']}")
        report.append(f"  Tables: {stats['total_tables']}")
        report.append(f"  Total d'enregistrements: {stats['total_records']:,}")
        report.append(f"  Taille totale: {stats['total_size_mb']:.2f} MB")
        report.append(f"  Nombre de partitions: {stats['total_partitions']}")
        report.append("")
        
        # Derniers exports
        report.append("🕐 DERNIERS EXPORTS")
        report.append("-" * 80)
        for export in stats['last_exports'][:10]:
            report.append(
                f"  {export['name']} ({export['type']}): {export['last_export']}"
            )
        report.append("")
        
        # Détails des streams
        if all_metadata["streams"]:
            report.append("📡 STREAMS")
            report.append("-" * 80)
            for stream_name, metadata in sorted(all_metadata["streams"].items()):
                report.append(f"\n  {stream_name}")
                report.append(f"    Description: {metadata.get('description', 'N/A')}")
                report.append(f"    Enregistrements: {metadata.get('total_records', 0):,}")
                report.append(f"    Taille: {metadata.get('total_size_mb', 0):.2f} MB")
                report.append(f"    Partitions: {len(metadata.get('partitions', []))}")
                report.append(f"    Dernier export: {metadata.get('last_export', 'N/A')}")
            report.append("")
        
        # Détails des tables
        if all_metadata["tables"]:
            report.append("📋 TABLES")
            report.append("-" * 80)
            for table_name, metadata in sorted(all_metadata["tables"].items()):
                report.append(f"\n  {table_name}")
                report.append(f"    Description: {metadata.get('description', 'N/A')}")
                report.append(f"    Enregistrements: {metadata.get('total_records', 0):,}")
                report.append(f"    Taille: {metadata.get('total_size_mb', 0):.2f} MB")
                report.append(f"    Versions: {len(metadata.get('partitions', []))}")
                report.append(f"    Dernier export: {metadata.get('last_export', 'N/A')}")
            report.append("")
        
        report.append("=" * 80)
        
        return "\n".join(report)
    
    @staticmethod
    def export_to_csv(output_file: str = "data_lake_report.csv"):
        """Exporte les métadonnées en CSV"""
        all_metadata = MetadataReader.list_all_metadata()
        
        rows = []
        
        # Ajouter les streams
        for stream_name, metadata in all_metadata["streams"].items():
            rows.append({
                "name": stream_name,
                "type": "stream",
                "storage_mode": metadata.get("storage_mode", "N/A"),
                "partitioning": metadata.get("partitioning", "N/A"),
                "total_records": metadata.get("total_records", 0),
                "total_size_mb": metadata.get("total_size_mb", 0),
                "partitions_count": len(metadata.get("partitions", [])),
                "last_export": metadata.get("last_export", "N/A"),
                "created_at": metadata.get("created_at", "N/A")
            })
        
        # Ajouter les tables
        for table_name, metadata in all_metadata["tables"].items():
            rows.append({
                "name": table_name,
                "type": "table",
                "storage_mode": metadata.get("storage_mode", "N/A"),
                "partitioning": metadata.get("partitioning", "N/A"),
                "total_records": metadata.get("total_records", 0),
                "total_size_mb": metadata.get("total_size_mb", 0),
                "partitions_count": len(metadata.get("partitions", [])),
                "last_export": metadata.get("last_export", "N/A"),
                "created_at": metadata.get("created_at", "N/A")
            })
        
        df = pd.DataFrame(rows)
        df.to_csv(output_file, index=False)
        
        return output_file


def main():
    """Point d'entrée pour générer un rapport"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Utilitaires de métadonnées du Data Lake"
    )
    parser.add_argument(
        '--report',
        action='store_true',
        help='Générer un rapport complet'
    )
    parser.add_argument(
        '--csv',
        type=str,
        help='Exporter les métadonnées en CSV'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Afficher les statistiques globales'
    )
    
    args = parser.parse_args()
    
    if args.report:
        report = MetadataAnalyzer.generate_report()
        print(report)
    
    elif args.csv:
        output_file = MetadataAnalyzer.export_to_csv(args.csv)
        print(f"✓ Métadonnées exportées vers: {output_file}")
    
    elif args.stats:
        stats = MetadataReader.get_statistics()
        print("\n📊 Statistiques du Data Lake")
        print("-" * 40)
        print(f"Streams: {stats['total_streams']}")
        print(f"Tables: {stats['total_tables']}")
        print(f"Total d'enregistrements: {stats['total_records']:,}")
        print(f"Taille totale: {stats['total_size_mb']:.2f} MB")
        print(f"Partitions: {stats['total_partitions']}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
