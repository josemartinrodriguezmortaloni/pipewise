#!/usr/bin/env python3
"""
Script para configurar las tablas y funciones de contactos en Supabase
"""

import os
import sys
from pathlib import Path

# Agregar el directorio padre al path para importar módulos
sys.path.append(str(Path(__file__).parent.parent))

from supabase import create_client
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_contacts_database():
    """Configurar tablas y funciones de contactos en Supabase"""

    # Obtener credenciales de Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")  # Usamos anon key

    if not supabase_url or not supabase_key:
        logger.error("❌ SUPABASE_URL y SUPABASE_ANON_KEY son requeridas")
        logger.info("💡 Asegúrate de configurar estas variables de entorno")
        return False

    try:
        # Crear cliente de Supabase
        supabase = create_client(supabase_url, supabase_key)
        logger.info("✅ Conectado a Supabase")

        # Intentar crear las tablas una por una de forma simple
        logger.info("🔧 Creando estructura de base de datos...")

        # Leer y ejecutar el archivo SQL completo usando el approach directo
        sql_file = Path(__file__).parent.parent / "supabase" / "database_setup.sql"

        if not sql_file.exists():
            logger.error(f"❌ Archivo SQL no encontrado: {sql_file}")
            return False

        logger.info(f"📖 Leyendo archivo SQL: {sql_file}")
        sql_content = sql_file.read_text(encoding="utf-8")

        logger.info("📄 Contenido SQL leído exitosamente")
        logger.info(
            "💡 Para ejecutar este SQL, copia el contenido y ejecútalo en el SQL Editor de Supabase"
        )
        logger.info("🔗 https://supabase.com/dashboard/project/[tu-project-id]/sql")

        # Mostrar el contenido para que el usuario lo pueda copiar
        print("\n" + "=" * 80)
        print("COPIA Y EJECUTA EL SIGUIENTE SQL EN SUPABASE SQL EDITOR:")
        print("=" * 80)
        print(sql_content)
        print("=" * 80 + "\n")

        return True

    except Exception as e:
        logger.error(f"❌ Error configurando base de datos: {e}")
        return False


def test_database_setup():
    """Probar que la configuración funcionó"""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_key:
        return False

    try:
        supabase = create_client(supabase_url, supabase_key)

        # Probar la tabla contacts
        result = supabase.table("contacts").select("id").limit(1).execute()
        logger.info("✅ Tabla 'contacts' accesible")

        # Probar la tabla outreach_messages
        result = supabase.table("outreach_messages").select("id").limit(1).execute()
        logger.info("✅ Tabla 'outreach_messages' accesible")

        return True

    except Exception as e:
        logger.error(f"❌ Error probando configuración: {e}")
        return False


if __name__ == "__main__":
    logger.info("🚀 Iniciando configuración de base de datos de contactos...")

    success = setup_contacts_database()

    if success:
        logger.info("🎉 ¡SQL generado exitosamente!")
        logger.info("💡 Ejecuta el SQL mostrado arriba en el Supabase SQL Editor")

        input("\n🔄 Presiona Enter después de ejecutar el SQL en Supabase...")

        # Probar la configuración
        if test_database_setup():
            logger.info("🎉 ¡Configuración verificada exitosamente!")
        else:
            logger.warning(
                "⚠️ No se pudo verificar la configuración, pero el SQL fue generado"
            )
    else:
        logger.error("❌ La configuración falló")
        sys.exit(1)
