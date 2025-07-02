#!/usr/bin/env python3
"""
Test OAuth Routes After Fix - PipeWise
Prueba que las rutas OAuth estén registradas correctamente después de la corrección.
"""

import requests
import sys
import time
from typing import Dict, Any

# Configuración
BACKEND_URL = "http://localhost:8001"
FRONTEND_URL = "http://localhost:3000"


class OAuthRoutesTester:
    def __init__(self):
        self.session = requests.Session()

    def test_backend_health(self) -> bool:
        """Verificar que el backend esté disponible"""
        try:
            print("🔍 Verificando salud del backend...")
            response = self.session.get(f"{BACKEND_URL}/health", timeout=5)

            if response.status_code == 200:
                print(f"✅ Backend disponible en {BACKEND_URL}")
                return True
            else:
                print(f"❌ Backend responde con código: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Backend no disponible: {e}")
            return False

    def test_oauth_routes_accessibility(self) -> Dict[str, Any]:
        """Probar que las rutas OAuth estén registradas (sin autenticación)"""
        print("\n🔍 Probando accesibilidad de rutas OAuth...")

        oauth_routes = [
            "/api/integrations/calendly/oauth/start",
            "/api/integrations/google_calendar/oauth/start",
            "/api/integrations/pipedrive/oauth/start",
            "/api/integrations/salesforce_rest_api/oauth/start",
            "/api/integrations/zoho_crm/oauth/start",
            "/api/integrations/twitter_account/oauth/start",
            "/api/integrations/instagram_account/oauth/start",
            "/api/integrations/sendgrid_email/oauth/start",
        ]

        results = {}

        for route in oauth_routes:
            try:
                url = f"{BACKEND_URL}{route}?redirect_url={FRONTEND_URL}/integrations"
                response = self.session.get(url, timeout=5, allow_redirects=False)

                # Esperamos 403 (no autenticado) o 302 (redirección) o 422 (validación)
                # NO esperamos 404 (no encontrado)
                if response.status_code == 404:
                    results[route] = {
                        "status": "❌ RUTA NO ENCONTRADA",
                        "code": response.status_code,
                        "error": "La ruta OAuth no está registrada",
                    }
                elif response.status_code == 403:
                    results[route] = {
                        "status": "✅ RUTA REGISTRADA",
                        "code": response.status_code,
                        "note": "Requiere autenticación (comportamiento esperado)",
                    }
                elif response.status_code == 302:
                    results[route] = {
                        "status": "✅ RUTA FUNCIONANDO",
                        "code": response.status_code,
                        "note": "Redirigiendo correctamente",
                    }
                elif response.status_code == 422:
                    results[route] = {
                        "status": "✅ RUTA REGISTRADA",
                        "code": response.status_code,
                        "note": "Error de validación (ruta funcional)",
                    }
                elif response.status_code == 500:
                    results[route] = {
                        "status": "⚠️ RUTA REGISTRADA",
                        "code": response.status_code,
                        "note": "Error interno (configuración incorrecta)",
                    }
                else:
                    results[route] = {
                        "status": "❓ RESPUESTA INESPERADA",
                        "code": response.status_code,
                        "note": f"Código inesperado: {response.status_code}",
                    }

            except requests.exceptions.RequestException as e:
                results[route] = {
                    "status": "❌ ERROR DE CONEXIÓN",
                    "code": None,
                    "error": str(e),
                }

        return results

    def test_oauth_documentation(self) -> bool:
        """Verificar que las rutas OAuth aparezcan en la documentación de OpenAPI"""
        try:
            print("\n🔍 Verificando documentación OpenAPI...")
            response = self.session.get(f"{BACKEND_URL}/openapi.json", timeout=5)

            if response.status_code == 200:
                openapi_spec = response.json()
                paths = openapi_spec.get("paths", {})

                oauth_paths_found = []
                for path in paths.keys():
                    if "/oauth/start" in path and "/api/integrations/" in path:
                        oauth_paths_found.append(path)

                if oauth_paths_found:
                    print(
                        f"✅ Rutas OAuth encontradas en documentación: {len(oauth_paths_found)}"
                    )
                    for path in oauth_paths_found:
                        print(f"   - {path}")
                    return True
                else:
                    print("❌ No se encontraron rutas OAuth en la documentación")
                    return False
            else:
                print(
                    f"❌ No se pudo obtener documentación OpenAPI: {response.status_code}"
                )
                return False

        except Exception as e:
            print(f"❌ Error verificando documentación: {e}")
            return False

    def run_full_test(self):
        """Ejecutar prueba completa"""
        print("=" * 60)
        print("🧪 PRUEBA DE RUTAS OAUTH - PIPEWISE")
        print("=" * 60)

        # 1. Verificar backend
        if not self.test_backend_health():
            print(
                "\n❌ Backend no disponible. Asegúrese de que esté ejecutándose en puerto 8001"
            )
            return False

        # 2. Probar rutas OAuth
        oauth_results = self.test_oauth_routes_accessibility()

        print("\n📊 RESULTADOS DE RUTAS OAUTH:")
        print("-" * 50)

        routes_working = 0
        routes_total = len(oauth_results)

        for route, result in oauth_results.items():
            service = route.split("/")[3]  # Extraer nombre del servicio
            status = result["status"]
            code = result.get("code", "N/A")
            note = result.get("note", result.get("error", ""))

            print(f"{service:<20} | {status:<25} | {code:<3} | {note}")

            if "✅" in status or "⚠️" in status:
                routes_working += 1

        print("-" * 50)
        print(f"📈 RESUMEN: {routes_working}/{routes_total} rutas OAuth funcionando")

        # 3. Verificar documentación
        docs_working = self.test_oauth_documentation()

        # 4. Evaluación final
        print("\n" + "=" * 60)

        if routes_working == routes_total and docs_working:
            print("🎉 ¡TODAS LAS RUTAS OAUTH FUNCIONANDO CORRECTAMENTE!")
            print("✅ El problema 404 ha sido solucionado")
            print("\n📝 PRÓXIMOS PASOS:")
            print("1. Reiniciar el servidor backend")
            print("2. Reiniciar el servidor frontend")
            print("3. Probar conexión desde la interfaz web")
            return True
        elif routes_working > 0:
            print("⚠️ ALGUNAS RUTAS FUNCIONANDO, OTRAS CON PROBLEMAS")
            print("🔧 Puede haber problemas de configuración")
            return False
        else:
            print("❌ NINGUNA RUTA OAUTH FUNCIONA")
            print("🚨 Verificar que el servidor haya sido reiniciado")
            return False


def main():
    """Función principal"""
    tester = OAuthRoutesTester()
    success = tester.run_full_test()

    if success:
        print("\n🚀 ¡Listo para probar integraciones OAuth!")
        sys.exit(0)
    else:
        print("\n🔍 Revisar configuración y reiniciar servidores")
        sys.exit(1)


if __name__ == "__main__":
    main()
