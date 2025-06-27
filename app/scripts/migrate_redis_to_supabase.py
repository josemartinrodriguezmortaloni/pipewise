#!/usr/bin/env python3
"""
Script de migración de Redis a Supabase
Este script ayuda a migrar los datos de autenticación de Redis a Supabase
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, List, Any

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_supabase_auth_tables():
    """Crear las tablas necesarias en Supabase para autenticación"""
    try:
        from app.supabase.supabase_client import get_supabase_client

        client = get_supabase_client()

        # Leer y ejecutar el script SQL
        script_path = os.path.join(os.path.dirname(__file__), "create_auth_tables.sql")

        if not os.path.exists(script_path):
            logger.error(f"Script SQL no encontrado: {script_path}")
            return False

        with open(script_path, "r", encoding="utf-8") as f:
            sql_script = f.read()

        # Nota: Supabase Python client no puede ejecutar SQL raw directamente
        # Este script debe ejecutarse manualmente en el dashboard de Supabase
        logger.info("Script SQL listo para ejecutar en Supabase:")
        logger.info("=" * 60)
        logger.info(sql_script)
        logger.info("=" * 60)
        logger.info(
            "Por favor, ejecuta este script en el SQL Editor de Supabase Dashboard"
        )

        return True

    except Exception as e:
        logger.error(f"Error creando tablas de Supabase: {e}")
        return False


async def test_supabase_auth_connection():
    """Probar la conexión con el nuevo sistema de autenticación de Supabase"""
    try:
        from app.auth.supabase_auth_client import get_supabase_auth_client

        client = await get_supabase_auth_client()
        health = await client.health_check()

        if health["status"] == "healthy":
            logger.info("✅ Conexión con Supabase Auth exitosa")
            return True
        else:
            logger.error(f"❌ Problema con Supabase Auth: {health}")
            return False

    except Exception as e:
        logger.error(f"❌ Error probando conexión Supabase Auth: {e}")
        return False


async def test_basic_auth_operations():
    """Probar operaciones básicas del nuevo sistema de autenticación"""
    try:
        from app.auth.supabase_auth_client import get_supabase_auth_client

        client = await get_supabase_auth_client()

        # Probar rate limiting
        rate_limit_result = await client.check_rate_limit("test_user", 100, 3600)
        logger.info(f"✅ Rate limiting test: {rate_limit_result}")

        # Probar estadísticas
        stats = await client.get_auth_stats()
        logger.info(f"✅ Auth stats test: {stats}")

        # Probar limpieza
        cleaned = await client.cleanup_expired_keys()
        logger.info(f"✅ Cleanup test: cleaned {cleaned} keys")

        return True

    except Exception as e:
        logger.error(f"❌ Error en test de operaciones básicas: {e}")
        return False


async def cleanup_old_redis_references():
    """Identificar archivos que aún referencian Redis"""
    redis_files = []

    # Buscar en archivos Python
    for root, dirs, files in os.walk("app"):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if (
                            "redis" in content.lower()
                            and "redis_auth_client" in content
                        ):
                            redis_files.append(file_path)
                except Exception:
                    pass

    if redis_files:
        logger.warning("⚠️  Archivos que aún referencian Redis:")
        for file in redis_files:
            logger.warning(f"  - {file}")
        logger.warning("Estos archivos deben ser actualizados manualmente")
    else:
        logger.info("✅ No se encontraron referencias a Redis en el código")

    return redis_files


async def update_environment_variables():
    """Guía para actualizar variables de entorno"""
    logger.info("📝 Variables de entorno a actualizar:")
    logger.info("")
    logger.info("REMOVER:")
    logger.info("  - REDIS_URL")
    logger.info("  - CELERY_BROKER_URL (si usa Redis)")
    logger.info("  - CELERY_RESULT_BACKEND (si usa Redis)")
    logger.info("")
    logger.info("MANTENER/VERIFICAR:")
    logger.info("  - SUPABASE_URL")
    logger.info("  - SUPABASE_KEY")
    logger.info("  - SUPABASE_SERVICE_KEY (si es necesario)")
    logger.info("")
    logger.info("Ejemplo de .env actualizado:")
    logger.info("=" * 40)
    logger.info("SUPABASE_URL=https://your-project.supabase.co")
    logger.info("SUPABASE_KEY=your-anon-key")
    logger.info("OPENAI_API_KEY=your-openai-key")
    logger.info("SECRET_KEY=your-secret-key")
    logger.info("ENVIRONMENT=production")
    logger.info("=" * 40)


async def generate_migration_report():
    """Generar reporte de migración"""
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "steps_completed": [],
        "steps_pending": [],
        "files_to_update": [],
        "recommendations": [],
    }

    # Verificar tablas
    tables_created = await create_supabase_auth_tables()
    if tables_created:
        report["steps_completed"].append("SQL script generated for Supabase tables")
    else:
        report["steps_pending"].append("Create Supabase auth tables")

    # Verificar conexión
    connection_ok = await test_supabase_auth_connection()
    if connection_ok:
        report["steps_completed"].append("Supabase auth connection verified")
    else:
        report["steps_pending"].append("Fix Supabase auth connection")

    # Verificar operaciones
    operations_ok = await test_basic_auth_operations()
    if operations_ok:
        report["steps_completed"].append("Basic auth operations tested")
    else:
        report["steps_pending"].append("Fix basic auth operations")

    # Verificar archivos
    redis_files = await cleanup_old_redis_references()
    report["files_to_update"] = redis_files

    # Recomendaciones
    report["recommendations"].extend(
        [
            "Execute the SQL script in Supabase Dashboard",
            "Update environment variables (remove Redis, keep Supabase)",
            "Update deployment configurations",
            "Run tests to verify migration",
            "Monitor application logs after deployment",
        ]
    )

    return report


async def main():
    """Función principal de migración"""
    logger.info("🚀 Iniciando migración de Redis a Supabase")
    logger.info("=" * 50)

    # Paso 1: Crear tablas en Supabase
    logger.info("1️⃣  Generando script SQL para Supabase...")
    await create_supabase_auth_tables()

    # Paso 2: Probar conexión
    logger.info("\n2️⃣  Probando conexión con Supabase...")
    await test_supabase_auth_connection()

    # Paso 3: Probar operaciones básicas
    logger.info("\n3️⃣  Probando operaciones básicas...")
    await test_basic_auth_operations()

    # Paso 4: Limpiar referencias
    logger.info("\n4️⃣  Verificando referencias a Redis...")
    await cleanup_old_redis_references()

    # Paso 5: Guía de variables de entorno
    logger.info("\n5️⃣  Guía de variables de entorno:")
    await update_environment_variables()

    # Paso 6: Generar reporte
    logger.info("\n6️⃣  Generando reporte de migración...")
    report = await generate_migration_report()

    logger.info("\n📊 REPORTE DE MIGRACIÓN")
    logger.info("=" * 50)
    logger.info(f"Pasos completados: {len(report['steps_completed'])}")
    for step in report["steps_completed"]:
        logger.info(f"  ✅ {step}")

    if report["steps_pending"]:
        logger.info(f"\nPasos pendientes: {len(report['steps_pending'])}")
        for step in report["steps_pending"]:
            logger.info(f"  ⏳ {step}")

    if report["files_to_update"]:
        logger.info(f"\nArchivos a actualizar: {len(report['files_to_update'])}")
        for file in report["files_to_update"]:
            logger.info(f"  📝 {file}")

    logger.info("\n🎯 PRÓXIMOS PASOS:")
    for i, rec in enumerate(report["recommendations"], 1):
        logger.info(f"  {i}. {rec}")

    logger.info("\n✅ Migración completada! Revisa los pasos pendientes.")


if __name__ == "__main__":
    asyncio.run(main())
