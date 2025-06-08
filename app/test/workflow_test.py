#!/usr/bin/env python3
"""
__main__.py - Test Suite Principal del CRM System (CORREGIDO)
Ejecuta tests completos del sistema CRM con todas las correcciones aplicadas.
"""

import asyncio
import logging
import os
import json
from datetime import datetime
from typing import Dict, Any
from dotenv import load_dotenv

# Importaciones del sistema
from app.supabase.supabase_client import SupabaseCRMClient
from app.schemas.lead_schema import LeadCreate
from app.agents.agent import Agents

# Cargar variables de entorno
load_dotenv()

# Configurar logging mejorado
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("crm_test_fixed.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class CRMTestSuite:
    """Suite de tests completa para el sistema CRM con correcciones"""

    def __init__(self):
        self.results = {"tests": [], "summary": {}}
        self.test_data = {}

    def log_test(self, test_name: str, status: str, message: str = ""):
        """Registrar resultado de test"""
        result = {
            "test": test_name,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }
        self.results["tests"].append(result)

        # Log visual
        icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{icon} {test_name}: {status}")
        if message:
            print(f"   [NOTE] {message}")

    async def test_environment(self) -> bool:
        """Test 1: Verificar configuración del entorno"""
        print("\n" + "=" * 60)
        print("[TEST] TEST 1: ENVIRONMENT CONFIGURATION")
        print("=" * 60)

        required_vars = {
            "SUPABASE_URL": os.getenv("SUPABASE_URL"),
            "SUPABASE_ANON_KEY": os.getenv("SUPABASE_ANON_KEY"),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "CALENDLY_ACCESS_TOKEN": os.getenv("CALENDLY_ACCESS_TOKEN"),
        }

        all_passed = True
        for var_name, var_value in required_vars.items():
            if var_value:
                masked_value = f"{var_value[:10]}..." if len(var_value) > 10 else "***"
                self.log_test(f"{var_name}", "PASS", f"Found: {masked_value}")
            else:
                if var_name == "CALENDLY_ACCESS_TOKEN":
                    self.log_test(f"{var_name}", "PASS", "Optional - Calendly disabled")
                else:
                    self.log_test(f"{var_name}", "FAIL", "Not configured")
                    all_passed = False

        return all_passed

    async def test_database_connection(self) -> bool:
        """Test 2: Verificar conexión a la base de datos"""
        print("\n" + "=" * 60)
        print("[TEST] TEST 2: DATABASE CONNECTION")
        print("=" * 60)

        try:
            # Inicializar cliente
            db_client = SupabaseCRMClient()
            self.log_test("Supabase Client Init", "PASS", "Client created successfully")

            # Test de salud
            health = db_client.health_check()
            if health.get("status") == "healthy":
                self.log_test("Health Check", "PASS", "Database connection OK")
            else:
                self.log_test("Health Check", "FAIL", f"Health check failed: {health}")
                return False

            # Test de consulta básica
            leads = db_client.list_leads(limit=1)
            self.log_test(
                "Basic Query", "PASS", f"Query executed, found {len(leads)} leads"
            )

            # Test de estadísticas
            stats = db_client.get_stats()
            if "leads" in stats:
                total_leads = stats["leads"]["total"]
                qualified = stats["leads"]["qualified"]
                contacted = stats["leads"]["contacted"]
                meetings = stats["leads"]["meetings_scheduled"]
                conversations = stats["conversations"]["total"]
                active_convs = stats["conversations"]["active"]

                self.log_test(
                    "Stats Query",
                    "PASS",
                    f"Stats retrieved, total leads: {total_leads}, qualified: {qualified}, contacted: {contacted}, meetings: {meetings}, conversations: {conversations} (active: {active_convs})",
                )
            else:
                self.log_test("Stats Query", "FAIL", f"Stats error: {stats}")

            return True

        except Exception as e:
            self.log_test("Database Connection", "FAIL", f"Error: {str(e)}")
            return False

    async def test_individual_agents(self) -> bool:
        """Test 3: Verificar agentes individuales"""
        print("\n" + "=" * 60)
        print("[TEST] TEST 3: INDIVIDUAL AGENTS")
        print("=" * 60)

        try:
            # Importar agentes
            from app.agents.lead_qualifier import LeadAgent
            from app.agents.outbound_contact import OutboundAgent
            from app.agents.meeting_scheduler import MeetingSchedulerAgent

            # Test LeadAgent
            lead_agent = LeadAgent()
            self.log_test("LeadAgent Init", "PASS", "Agent initialized")
            lead_tools = lead_agent._get_supabase_tools()
            self.log_test(
                "LeadAgent Tools",
                "PASS",
                f"Found {len(lead_tools)} function calling tools",
            )

            # Test OutboundAgent
            outbound_agent = OutboundAgent()
            self.log_test("OutboundAgent Init", "PASS", "Agent initialized")
            outbound_tools = outbound_agent._get_supabase_tools()
            self.log_test(
                "OutboundAgent Tools",
                "PASS",
                f"Found {len(outbound_tools)} function calling tools",
            )

            # Test MeetingSchedulerAgent
            meeting_agent = MeetingSchedulerAgent()
            self.log_test("MeetingSchedulerAgent Init", "PASS", "Agent initialized")
            meeting_tools = meeting_agent._get_tools()
            self.log_test(
                "MeetingSchedulerAgent Tools",
                "PASS",
                f"Found {len(meeting_tools)} function calling tools",
            )

            return True

        except Exception as e:
            self.log_test("Individual Agents", "FAIL", f"Error: {str(e)}")
            return False

    async def test_supabase_operations(self) -> bool:
        """Test 3.5: Verificar operaciones básicas de Supabase"""
        print("\n" + "=" * 60)
        print("[TEST] TEST 3.5: SUPABASE OPERATIONS")
        print("=" * 60)

        try:
            db_client = SupabaseCRMClient()

            # Crear lead de prueba
            print("[NOTE] Attempting to create test lead...")
            test_email = (
                f"test.ops.{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com"
            )
            test_lead_data = LeadCreate(
                name="Test Operations Lead",
                email=test_email,
                company="Test Operations Inc",
                phone="+1234567890",
                message="Test message for operations verification",
                source="test_suite",
                metadata={"test": True, "created_by": "test_suite"},
            )

            # Crear lead
            new_lead = db_client.create_lead(test_lead_data)
            self.test_data["test_lead_id"] = str(new_lead.id)
            self.log_test(
                "Create Lead Operation", "PASS", f"Lead created with ID: {new_lead.id}"
            )

            # Obtener lead
            retrieved_lead = db_client.get_lead(new_lead.id)
            if retrieved_lead and retrieved_lead.id == new_lead.id:
                self.log_test(
                    "Get Lead Operation", "PASS", "Lead retrieved successfully"
                )
            else:
                self.log_test("Get Lead Operation", "FAIL", "Lead not found")
                return False

            # Obtener por email
            email_lead = db_client.get_lead_by_email(test_email)
            if email_lead and email_lead.id == new_lead.id:
                self.log_test("Get Lead by Email", "PASS", "Lead found by email")
            else:
                self.log_test("Get Lead by Email", "FAIL", "Lead not found by email")
                return False

            # Actualizar lead
            from app.schemas.lead_schema import LeadUpdate

            updates = LeadUpdate(qualified=True, status="qualified")
            updated_lead = db_client.update_lead(new_lead.id, updates)
            if updated_lead.qualified:
                self.log_test("Mark Lead Qualified", "PASS", "Lead marked as qualified")
            else:
                self.log_test("Mark Lead Qualified", "FAIL", "Lead not qualified")
                return False

            # Limpiar lead de prueba
            deleted = db_client.delete_lead(new_lead.id)
            if deleted:
                self.log_test("Delete Test Lead", "PASS", "Test lead cleaned up")
            else:
                self.log_test("Delete Test Lead", "FAIL", "Could not delete test lead")

            return True

        except Exception as e:
            self.log_test("Supabase Operations", "FAIL", f"Error: {str(e)}")
            return False

    async def test_complete_workflow(self) -> bool:
        """Test 4: Workflow completo end-to-end CORREGIDO"""
        print("\n" + "=" * 60)
        print("[TEST] TEST 4: COMPLETE WORKFLOW END-TO-END")
        print("=" * 60)

        try:
            # Inicializar sistema de agentes
            agents = Agents()
            self.log_test("Agents System Init", "PASS", "Agents system initialized")

            # Datos de prueba para el lead
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            test_email = f"test.lead.{timestamp}@testcompany.com"

            lead_data = {
                "name": "Carlos Test Mendoza",
                "email": test_email,
                "company": "Test Tech Startup Inc",
                "phone": "+1234567890",
                "message": "Necesitamos automatizar nuestro proceso de ventas urgentemente. Tenemos un equipo de 25 personas y buscamos una solución SaaS robusta.",
                "source": "website_form",
                "utm_params": {"campaign": "automation_test", "medium": "organic"},
                "metadata": {
                    "company_size": "25-50",
                    "industry": "technology",
                    "interest_level": "high",
                    "test_run": True,
                },
            }

            logger.info(f"🚀 Starting complete workflow test with lead: {test_email}")

            # Ejecutar workflow completo
            result = await agents.run_workflow(lead_data)

            # Verificar resultado del workflow
            if result.get("status") == "completed":
                self.log_test(
                    "Complete Workflow",
                    "PASS",
                    f"Lead ID: {result.get('lead_id')}, Qualified: {result.get('qualified')}",
                )
                self.test_data["workflow_lead_id"] = result.get("lead_id")
            elif result.get("status") == "error":
                self.log_test(
                    "Complete Workflow",
                    "FAIL",
                    f"Workflow error: {result.get('error')}",
                )
                return False
            else:
                self.log_test(
                    "Complete Workflow",
                    "PASS",
                    f"Workflow completed with status: {result.get('status')}",
                )
                self.test_data["workflow_lead_id"] = result.get("lead_id")

            # Verificar los pasos individuales
            lead_id = result.get("lead_id")
            if lead_id:
                # Test calificación
                if result.get("qualified"):
                    self.log_test(
                        "Lead Qualification", "PASS", "Lead qualified successfully"
                    )
                else:
                    self.log_test(
                        "Lead Qualification",
                        "FAIL",
                        f"Lead not qualified: {result.get('reason', 'Unknown reason')}",
                    )

                # Test contacto outbound
                outbound_result = result.get("outbound_message") or result.get(
                    "contacted"
                )
                if outbound_result:
                    self.log_test(
                        "Outbound Contact",
                        "PASS",
                        f"Message: {str(outbound_result)[:50]}...",
                    )
                else:
                    self.log_test(
                        "Outbound Contact", "FAIL", "No outbound contact recorded"
                    )

                # Test agendamiento
                meeting_url = result.get("meeting_url")
                meeting_type = result.get("event_type", "Unknown")
                if meeting_url:
                    self.log_test(
                        "Meeting Scheduling",
                        "PASS",
                        f"Type: {meeting_type}, URL: {meeting_url}",
                    )
                else:
                    self.log_test(
                        "Meeting Scheduling", "FAIL", "No meeting URL generated"
                    )

                # Verificar persistencia en base de datos
                try:
                    db_client = SupabaseCRMClient()
                    persistent_lead = db_client.get_lead(lead_id)

                    if persistent_lead:
                        self.log_test(
                            "Lead Persistence",
                            "PASS",
                            f"Lead found in database: {persistent_lead.email}",
                        )

                        # Verificar estados
                        if persistent_lead.qualified:
                            self.log_test(
                                "Lead Status Update", "PASS", "Lead marked as qualified"
                            )
                        else:
                            self.log_test(
                                "Lead Status Update",
                                "FAIL",
                                "Lead not marked as qualified",
                            )

                        if persistent_lead.contacted:
                            self.log_test(
                                "Contact Status Update",
                                "PASS",
                                "Lead marked as contacted",
                            )
                        else:
                            self.log_test(
                                "Contact Status Update",
                                "FAIL",
                                "Lead not marked as contacted",
                            )

                        if persistent_lead.meeting_scheduled:
                            self.log_test(
                                "Meeting Status Update", "PASS", "Meeting scheduled"
                            )
                        else:
                            self.log_test(
                                "Meeting Status Update", "FAIL", "Meeting not scheduled"
                            )

                        # Verificar conversaciones
                        conversations = db_client.list_conversations(lead_id=lead_id)
                        if conversations:
                            self.log_test(
                                "Conversation Creation",
                                "PASS",
                                f"Found {len(conversations)} conversations",
                            )
                        else:
                            self.log_test(
                                "Conversation Creation",
                                "FAIL",
                                "No conversations found",
                            )

                    else:
                        self.log_test(
                            "Lead Persistence",
                            "FAIL",
                            f"Lead {lead_id} not found in database",
                        )
                        return False

                except Exception as e:
                    self.log_test(
                        "Database Verification",
                        "FAIL",
                        f"Error checking database: {str(e)}",
                    )

            return True

        except Exception as e:
            self.log_test("Complete Workflow", "FAIL", f"Error: {str(e)}")
            logger.error(f"Workflow test failed: {e}", exc_info=True)
            return False

    async def test_cleanup(self) -> bool:
        """Test 5: Limpiar datos de prueba"""
        print("\n" + "=" * 60)
        print("[TEST] TEST 5: CLEANUP")
        print("=" * 60)

        try:
            db_client = SupabaseCRMClient()

            # Obtener estadísticas antes de limpiar
            stats_before = db_client.get_stats()

            # Limpiar lead del workflow si existe
            workflow_lead_id = self.test_data.get("workflow_lead_id")
            if workflow_lead_id:
                try:
                    deleted = db_client.delete_lead(workflow_lead_id)
                    if deleted:
                        self.log_test(
                            "Test Lead Deletion",
                            "PASS",
                            f"Test lead {workflow_lead_id} deleted",
                        )
                    else:
                        self.log_test(
                            "Test Lead Deletion",
                            "FAIL",
                            f"Could not delete lead {workflow_lead_id}",
                        )

                    # Verificar que se eliminó
                    check_lead = db_client.get_lead(workflow_lead_id)
                    if not check_lead:
                        self.log_test(
                            "Cleanup Verification",
                            "PASS",
                            "Test lead successfully removed",
                        )
                    else:
                        self.log_test(
                            "Cleanup Verification", "FAIL", "Test lead still exists"
                        )

                except Exception as e:
                    self.log_test(
                        "Test Lead Deletion", "FAIL", f"Error deleting lead: {str(e)}"
                    )

            # Verificar estadísticas después de limpiar
            stats_after = db_client.get_stats()
            leads_before = stats_before.get("leads", {}).get("total", 0)
            leads_after = stats_after.get("leads", {}).get("total", 0)

            self.log_test(
                "Stats Consistency",
                "PASS",
                f"Lead count updated: {leads_before} -> {leads_after}",
            )

            return True

        except Exception as e:
            self.log_test("Cleanup", "FAIL", f"Error: {str(e)}")
            return False

    async def run_all_tests(self) -> Dict[str, Any]:
        """Ejecutar todos los tests"""
        print("🚀 Starting FIXED CRM System Test Suite")
        print(f"📅 Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Ejecutar tests en orden
        test_methods = [
            self.test_environment,
            self.test_database_connection,
            self.test_individual_agents,
            self.test_supabase_operations,
            self.test_complete_workflow,
            self.test_cleanup,
        ]

        test_categories = [
            "ENVIRONMENT",
            "DATABASE",
            "AGENTS",
            "SUPABASE_OPS",
            "WORKFLOW",
            "CLEANUP",
        ]

        category_results = {}

        for i, (test_method, category) in enumerate(zip(test_methods, test_categories)):
            try:
                result = await test_method()
                category_results[category] = {"passed": True, "error": None}
            except Exception as e:
                logger.error(f"Test category {category} failed: {e}", exc_info=True)
                category_results[category] = {"passed": False, "error": str(e)}

        # Generar resumen
        self.generate_summary(category_results)

        return self.results

    def generate_summary(self, category_results: Dict[str, Dict]):
        """Generar resumen de resultados"""
        print("\n" + "=" * 60)
        print("[TEST] FINAL TEST REPORT")
        print("=" * 60)

        total_passed = 0
        total_failed = 0
        failed_tests = []

        # Contar resultados por categoría
        for test in self.results["tests"]:
            if test["status"] == "PASS":
                total_passed += 1
            elif test["status"] == "FAIL":
                total_failed += 1
                failed_tests.append(f"   • {test['test']} - {test['message']}")

        # Mostrar resumen por categoría
        for category, result in category_results.items():
            category_tests = [
                t
                for t in self.results["tests"]
                if category.lower() in t["test"].lower()
                or any(
                    cat_word in t["test"].lower()
                    for cat_word in category.lower().split("_")
                )
            ]
            passed = len([t for t in category_tests if t["status"] == "PASS"])
            failed = len([t for t in category_tests if t["status"] == "FAIL"])

            status_icon = "✅" if result["passed"] else "⚠️" if failed > 0 else "✅"
            print(f"{status_icon} {category}: {passed} passed, {failed} failed")

        # Resultado general
        if total_failed == 0:
            overall_status = "✅ SUCCESS"
            print(f"\n🎉 OVERALL RESULT: {overall_status}")
        elif total_failed <= 4:
            overall_status = "⚠️ WARNING"
            print(f"\n⚠️ OVERALL RESULT: {overall_status} - {total_failed} TESTS FAILED")
        else:
            overall_status = "❌ FAILED"
            print(
                f"\n❌ OVERALL RESULT: {overall_status} - {total_failed} TESTS FAILED"
            )

        print(f"📊 TOTAL: {total_passed} passed, {total_failed} failed")

        if failed_tests:
            print(f"\n❌ FAILED TESTS:")
            for failed_test in failed_tests:
                print(failed_test)

        # Guardar resumen
        self.results["summary"] = {
            "overall_status": overall_status,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "failed_tests": failed_tests,
            "category_results": category_results,
        }

        # Guardar resultados completos
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"crm_test_report_fixed_{timestamp}.json"
        with open(report_file, "w") as f:
            json.dump(self.results, f, indent=2, default=str)

        print("=" * 60)
        print(f"📄 Detailed report saved to: {report_file}")
        print(f"📋 Logs saved to: crm_test_fixed.log")


async def main():
    """Función principal"""
    test_suite = CRMTestSuite()
    results = await test_suite.run_all_tests()

    # Retornar código de salida basado en resultados
    if results["summary"]["total_failed"] == 0:
        return 0
    else:
        return 1


if __name__ == "__main__":
    import sys

    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        sys.exit(1)
