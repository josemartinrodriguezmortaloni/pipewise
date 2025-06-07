#!/usr/bin/env python3
"""
Script para iniciar el servidor FastAPI del backend
"""

import uvicorn
import os
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Iniciar servidor FastAPI"""
    try:
        logger.info("🚀 Starting PipeWise backend server...")

        # Configuración del servidor
        host = os.getenv("HOST", "0.0.0.0")
        port = int(os.getenv("PORT", "8000"))

        # Iniciar servidor
        uvicorn.run(
            "app.api.main:app",
            host=host,
            port=port,
            reload=True,  # Para desarrollo
            access_log=True,
            log_level="info",
        )

    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")


if __name__ == "__main__":
    main()
