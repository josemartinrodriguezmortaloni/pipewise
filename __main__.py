#!/usr/bin/env python3
"""
__main__.py - Test Autónomo del Sistema CRM con Function Calling

Ejecuta pruebas completas del sistema para verificar:
- Conexión a Supabase
- Agentes con function calling
- Workflow completo end-to-end
- Integración con Calendly
- Persistencia de datos

Uso: python __main__.py
"""

import asyncio
import json
import sys
import os
import logging
from datetime import datetime
from typing import Dict, Any, List
import traceback
from dotenv import load_dotenv

# Agregar el directorio raíz al path para importaciones
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("crm_test.log")],
)
logger = logging.getLogger(__name__)

# Importaciones del proyecto
try:
    from app.supabase.supabase_client import SupabaseCRMClient
    from app.schemas.lead_schema import LeadCreate
    from app.agents.agent import Agents
    from app.agents.lead_qualifier import LeadAgent
    from app.agents.outbound_contact import OutboundAgent
    from app.agents.meeting_scheduler import MeetingSchedulerAgent
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    print("Make sure you're running from the project root directory")
    print("Available modules:")
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".py"):
                print(f"  {os.path.join(root, file)}")
    sys.exit(1)


class CRMSystemTester:
    """Tester completo del sistema CRM"""

    def __init__(self):
        self.db_client = None
        self.agents = None
        self.test_results = {
            "environment": {"passed": 0, "failed": 0, "details": []},
            "database": {"passed": 0, "failed": 0, "details": []},
            "agents": {"passed": 0, "failed": 0, "details": []},
            "workflow": {"passed": 0, "failed": 0, "details": []},
            "cleanup": {"passed": 0, "failed": 0, "details": []},
        }
        self.test_lead_id = None

    def print_header(self, title: str):
        """Imprimir header de sección"""
        print(f"\n{'=' * 60}")
        print(f"🧪 {title}")
        print(f"{'=' * 60}")

    def print_test(self, test_name: str, status: str, details: str = ""):
        """Imprimir resultado de test"""
        icon = "✅" if status == "PASS" else "❌"
        print(f"{icon} {test_name}: {status}")
        if details:
            print(f"   📝 {details}")

    def record_result(
        self, category: str, test_name: str, passed: bool, details: str = ""
    ):
        """Registrar resultado de test"""
        if passed:
            self.test_results[category]["passed"] += 1
            self.print_test(test_name, "PASS", details)
        else:
            self.test_results[category]["failed"] += 1
            self.print_test(test_name, "FAIL", details)

        self.test_results[category]["details"].append(
            {
                "test": test_name,
                "passed": passed,
                "details": details,
                "timestamp": datetime.now().isoformat(),
            }
        )

    async def test_environment(self):
        """Test 1: Verificar configuración del entorno"""
        self.print_header("TEST 1: ENVIRONMENT CONFIGURATION")

        # Test variables de entorno
        required_vars = [
            ("SUPABASE_URL", "Supabase connection URL"),
            ("SUPABASE_ANON_KEY", "Supabase anonymous key"),
            ("OPENAI_API_KEY", "OpenAI API key"),
        ]

        for var_name, description in required_vars:
            value = os.getenv(var_name)
            if value:
                masked_value = f"{value[:10]}..." if len(value) > 10 else "***"
                self.record_result(
                    "environment", f"{var_name}", True, f"Found: {masked_value}"
                )
            else:
                self.record_result(
                    "environment", f"{var_name}", False, f"Missing: {description}"
                )

        # Test variable opcional
        calendly_token = os.getenv("CALENDLY_ACCESS_TOKEN")
        if calendly_token:
            self.record_result(
                "environment",
                "CALENDLY_ACCESS_TOKEN",
                True,
                "Calendly integration enabled",
            )
        else:
            self.record_result(
                "environment",
                "CALENDLY_ACCESS_TOKEN",
                False,
                "Calendly integration disabled (optional)",
            )

    async def test_database_connection(self):
        """Test 2: Verificar conexión a Supabase"""
        self.print_header("TEST 2: DATABASE CONNECTION")

        try:
            # Inicializar cliente
            self.db_client = SupabaseCRMClient()
            self.record_result(
                "database", "Supabase Client Init", True, "Client created successfully"
            )

            # Test health check (MÉTODO SÍNCRONO)
            health = self.db_client.health_check()
            if health.get("status") == "healthy":
                self.record_result(
                    "database", "Health Check", True, "Database connection OK"
                )
            else:
                self.record_result(
                    "database", "Health Check", False, f"Health check failed: {health}"
                )

            # Test básico de consulta (MÉTODO SÍNCRONO)
            leads = self.db_client.list_leads(limit=1)
            self.record_result(
                "database",
                "Basic Query",
                True,
                f"Query executed, found {len(leads)} leads",
            )

            # Test de estadísticas (MÉTODO SÍNCRONO)
            stats = self.db_client.get_stats()
            if "leads" in stats:
                total_leads = stats["leads"]["total"]
                self.record_result(
                    "database",
                    "Stats Query",
                    True,
                    f"Stats retrieved, total leads: {total_leads}",
                )
            else:
                self.record_result(
                    "database", "Stats Query", False, f"Stats error: {stats}"
                )

        except Exception as e:
            self.record_result(
                "database", "Database Connection", False, f"Connection failed: {str(e)}"
            )
            logger.error(f"Database connection error: {e}")
            logger.error(traceback.format_exc())

    async def test_individual_agents(self):
        """Test 3: Verificar agentes individuales"""
        self.print_header("TEST 3: INDIVIDUAL AGENTS")

        # Test LeadAgent
        try:
            lead_agent = LeadAgent()
            self.record_result("agents", "LeadAgent Init", True, "Agent initialized")

            # Verificar que tenga las funciones necesarias
            if hasattr(lead_agent, "_get_supabase_tools"):
                tools = lead_agent._get_supabase_tools()
                self.record_result(
                    "agents",
                    "LeadAgent Tools",
                    True,
                    f"Found {len(tools)} function calling tools",
                )
            else:
                self.record_result(
                    "agents",
                    "LeadAgent Tools",
                    False,
                    "Function calling tools not found",
                )

        except Exception as e:
            self.record_result("agents", "LeadAgent", False, f"Error: {str(e)}")
            logger.error(f"LeadAgent error: {e}")

        # Test OutboundAgent
        try:
            outbound_agent = OutboundAgent()
            self.record_result(
                "agents", "OutboundAgent Init", True, "Agent initialized"
            )

            # Verificar que tenga las funciones necesarias
            if hasattr(outbound_agent, "_get_supabase_tools"):
                tools = outbound_agent._get_supabase_tools()
                self.record_result(
                    "agents",
                    "OutboundAgent Tools",
                    True,
                    f"Found {len(tools)} function calling tools",
                )
            else:
                self.record_result(
                    "agents",
                    "OutboundAgent Tools",
                    False,
                    "Function calling tools not found",
                )

        except Exception as e:
            self.record_result("agents", "OutboundAgent", False, f"Error: {str(e)}")
            logger.error(f"OutboundAgent error: {e}")

        # Test MeetingSchedulerAgent
        try:
            meeting_agent = MeetingSchedulerAgent()
            self.record_result(
                "agents", "MeetingSchedulerAgent Init", True, "Agent initialized"
            )

            # Verificar que tenga las funciones necesarias
            if hasattr(meeting_agent, "_get_tools"):
                tools = meeting_agent._get_tools()
                self.record_result(
                    "agents",
                    "MeetingSchedulerAgent Tools",
                    True,
                    f"Found {len(tools)} function calling tools",
                )
            else:
                self.record_result(
                    "agents",
                    "MeetingSchedulerAgent Tools",
                    False,
                    "Function calling tools not found",
                )

        except Exception as e:
            self.record_result(
                "agents", "MeetingSchedulerAgent", False, f"Error: {str(e)}"
            )
            logger.error(f"MeetingSchedulerAgent error: {e}")

    async def test_supabase_operations(self):
        """Test 3.5: Verificar operaciones específicas de Supabase"""
        self.print_header("TEST 3.5: SUPABASE OPERATIONS")

        if not self.db_client:
            self.record_result(
                "database",
                "Supabase Operations",
                False,
                "Database client not available",
            )
            return

        # Crear lead de prueba para operaciones
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        test_lead_data = LeadCreate(
            name=f"Test Operations {timestamp}",
            email=f"test.ops.{timestamp}@example.com",
            company="Test Operations Company",
            phone="+1234567890",
            message="Test message for operations",
            source="test_operations",
        )

        try:
            # Test crear lead
            created_lead = self.db_client.create_lead(test_lead_data)
            if created_lead and created_lead.id:
                self.record_result(
                    "database",
                    "Create Lead Operation",
                    True,
                    f"Lead created with ID: {created_lead.id}",
                )
                test_lead_id = created_lead.id

                # Test obtener lead
                retrieved_lead = self.db_client.get_lead(test_lead_id)
                if retrieved_lead and retrieved_lead.email == test_lead_data.email:
                    self.record_result(
                        "database",
                        "Get Lead Operation",
                        True,
                        "Lead retrieved successfully",
                    )
                else:
                    self.record_result(
                        "database",
                        "Get Lead Operation",
                        False,
                        "Lead not retrieved correctly",
                    )

                # Test obtener lead por email
                email_lead = self.db_client.get_lead_by_email(test_lead_data.email)
                if email_lead and email_lead.id == test_lead_id:
                    self.record_result(
                        "database", "Get Lead by Email", True, "Lead found by email"
                    )
                else:
                    self.record_result(
                        "database",
                        "Get Lead by Email",
                        False,
                        "Lead not found by email",
                    )

                # Test marcar como calificado
                qualified_lead = self.db_client.mark_lead_as_qualified(test_lead_id)
                if qualified_lead and qualified_lead.qualified:
                    self.record_result(
                        "database",
                        "Mark Lead Qualified",
                        True,
                        "Lead marked as qualified",
                    )
                else:
                    self.record_result(
                        "database",
                        "Mark Lead Qualified",
                        False,
                        "Failed to mark lead as qualified",
                    )

                # Limpiar lead de prueba
                deleted = self.db_client.delete_lead(test_lead_id)
                if deleted:
                    self.record_result(
                        "database", "Delete Test Lead", True, "Test lead cleaned up"
                    )
                else:
                    self.record_result(
                        "database",
                        "Delete Test Lead",
                        False,
                        "Failed to delete test lead",
                    )

            else:
                self.record_result(
                    "database", "Create Lead Operation", False, "Failed to create lead"
                )

        except Exception as e:
            self.record_result(
                "database", "Supabase Operations", False, f"Operations failed: {str(e)}"
            )
            logger.error(f"Supabase operations error: {e}")
            logger.error(traceback.format_exc())

    async def test_complete_workflow(self):
        """Test 4: Verificar workflow completo end-to-end"""
        self.print_header("TEST 4: COMPLETE WORKFLOW END-TO-END")

        if not self.db_client:
            self.record_result(
                "workflow", "Workflow Test", False, "Database client not available"
            )
            return

        # Datos de test lead único
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        test_lead_data = {
            "name": f"Test Lead {timestamp}",
            "email": f"test.lead.{timestamp}@testcompany.com",
            "company": f"Test Company {timestamp}",
            "phone": "+1234567890",
            "message": "We need to automate our sales process. We have a team of 25 people and are looking for a comprehensive solution.",
            "source": "automated_test",
            "utm_params": {"campaign": "test", "source": "automation"},
            "metadata": {
                "test_run": True,
                "timestamp": timestamp,
                "company_size": "25-50",
                "industry": "technology",
            },
        }

        try:
            # Inicializar sistema de agentes
            self.agents = Agents()
            self.record_result(
                "workflow", "Agents System Init", True, "Agents system initialized"
            )

            # Ejecutar workflow completo
            logger.info(
                f"🚀 Starting complete workflow test with lead: {test_lead_data['email']}"
            )
            workflow_result = await self.agents.run_workflow(test_lead_data)

            # Verificar resultado del workflow
            if workflow_result.get("workflow_completed"):
                self.test_lead_id = workflow_result.get("lead_id")
                details = f"Lead ID: {self.test_lead_id}, Qualified: {workflow_result.get('qualified')}"
                self.record_result("workflow", "Complete Workflow", True, details)

                # Verificar componentes individuales del workflow
                if workflow_result.get("qualified"):
                    self.record_result(
                        "workflow",
                        "Lead Qualification",
                        True,
                        "Lead qualified successfully",
                    )
                else:
                    reason = workflow_result.get("reason", "No reason provided")
                    self.record_result(
                        "workflow",
                        "Lead Qualification",
                        False,
                        f"Lead not qualified: {reason}",
                    )

                if workflow_result.get("contacted"):
                    outbound_msg = workflow_result.get("outbound_message", "")
                    details = (
                        f"Message: {outbound_msg[:50]}..."
                        if len(outbound_msg) > 50
                        else f"Message: {outbound_msg}"
                    )
                    self.record_result("workflow", "Outbound Contact", True, details)
                else:
                    self.record_result(
                        "workflow", "Outbound Contact", False, "Lead contact failed"
                    )

                if workflow_result.get("meeting_scheduled"):
                    meeting_url = workflow_result.get("meeting_url", "")
                    event_type = workflow_result.get("event_type", "Unknown")
                    self.record_result(
                        "workflow",
                        "Meeting Scheduling",
                        True,
                        f"Type: {event_type}, URL: {meeting_url}",
                    )
                else:
                    self.record_result(
                        "workflow",
                        "Meeting Scheduling",
                        False,
                        "Meeting scheduling failed",
                    )

            else:
                error = workflow_result.get("error", "Unknown error")
                self.record_result(
                    "workflow", "Complete Workflow", False, f"Workflow failed: {error}"
                )

            # Verificar persistencia en base de datos
            if self.test_lead_id:
                await self._verify_data_persistence()

        except Exception as e:
            self.record_result(
                "workflow", "Complete Workflow", False, f"Exception: {str(e)}"
            )
            logger.error(f"Workflow test error: {e}")
            logger.error(traceback.format_exc())

    async def _verify_data_persistence(self):
        """Verificar que los datos se guardaron correctamente en la base de datos"""
        try:
            # Verificar lead creado (MÉTODO SÍNCRONO)
            lead = self.db_client.get_lead(self.test_lead_id)
            if lead:
                self.record_result(
                    "workflow",
                    "Lead Persistence",
                    True,
                    f"Lead found in database: {lead.email}",
                )

                # Verificar estado del lead
                if lead.qualified:
                    self.record_result(
                        "workflow",
                        "Lead Status Update",
                        True,
                        "Lead marked as qualified",
                    )
                else:
                    self.record_result(
                        "workflow",
                        "Lead Status Update",
                        False,
                        "Lead not marked as qualified",
                    )

                if lead.contacted:
                    self.record_result(
                        "workflow",
                        "Contact Status Update",
                        True,
                        "Lead marked as contacted",
                    )
                else:
                    self.record_result(
                        "workflow",
                        "Contact Status Update",
                        False,
                        "Lead not marked as contacted",
                    )

                if lead.meeting_scheduled:
                    meeting_url = ""
                    if lead.metadata and isinstance(lead.metadata, dict):
                        meeting_url = lead.metadata.get("meeting_url", "")
                    self.record_result(
                        "workflow",
                        "Meeting Status Update",
                        True,
                        f"Meeting scheduled: {meeting_url}",
                    )
                else:
                    self.record_result(
                        "workflow",
                        "Meeting Status Update",
                        False,
                        "Meeting not scheduled",
                    )

                # Verificar conversaciones (MÉTODO SÍNCRONO)
                conversations = self.db_client.list_conversations(lead_id=lead.id)
                if conversations:
                    self.record_result(
                        "workflow",
                        "Conversation Creation",
                        True,
                        f"Found {len(conversations)} conversations",
                    )

                    # Verificar mensajes
                    total_messages = 0
                    for conv in conversations:
                        messages = self.db_client.get_messages(conv.id)
                        total_messages += len(messages)

                    if total_messages > 0:
                        self.record_result(
                            "workflow",
                            "Message Creation",
                            True,
                            f"Found {total_messages} messages total",
                        )
                    else:
                        self.record_result(
                            "workflow", "Message Creation", False, "No messages found"
                        )
                else:
                    self.record_result(
                        "workflow",
                        "Conversation Creation",
                        False,
                        "No conversations found",
                    )

            else:
                self.record_result(
                    "workflow", "Lead Persistence", False, "Lead not found in database"
                )

        except Exception as e:
            self.record_result(
                "workflow", "Data Persistence Check", False, f"Error: {str(e)}"
            )
            logger.error(f"Data persistence check error: {e}")

    async def test_cleanup(self):
        """Test 5: Limpiar datos de prueba"""
        self.print_header("TEST 5: CLEANUP")

        if not self.db_client or not self.test_lead_id:
            self.record_result("cleanup", "Cleanup", False, "No test data to clean up")
            return

        try:
            # Obtener estadísticas antes de cleanup
            stats_before = self.db_client.get_stats()
            leads_before = stats_before.get("leads", {}).get("total", 0)

            # Eliminar lead de prueba (esto debería eliminar conversaciones y mensajes en cascada)
            deleted = self.db_client.delete_lead(self.test_lead_id)
            if deleted:
                self.record_result(
                    "cleanup",
                    "Test Lead Deletion",
                    True,
                    f"Test lead {self.test_lead_id} deleted",
                )
            else:
                self.record_result(
                    "cleanup", "Test Lead Deletion", False, "Failed to delete test lead"
                )

            # Verificar limpieza
            lead_check = self.db_client.get_lead(self.test_lead_id)
            if not lead_check:
                self.record_result(
                    "cleanup",
                    "Cleanup Verification",
                    True,
                    "Test lead successfully removed",
                )
            else:
                self.record_result(
                    "cleanup", "Cleanup Verification", False, "Test lead still exists"
                )

            # Verificar estadísticas después de cleanup
            stats_after = self.db_client.get_stats()
            leads_after = stats_after.get("leads", {}).get("total", 0)

            if leads_after < leads_before or leads_after == leads_before - 1:
                self.record_result(
                    "cleanup",
                    "Stats Consistency",
                    True,
                    f"Lead count updated: {leads_before} -> {leads_after}",
                )
            else:
                self.record_result(
                    "cleanup",
                    "Stats Consistency",
                    False,
                    f"Lead count inconsistent: {leads_before} -> {leads_after}",
                )

        except Exception as e:
            self.record_result(
                "cleanup", "Cleanup", False, f"Error during cleanup: {str(e)}"
            )
            logger.error(f"Cleanup error: {e}")

    def print_final_report(self):
        """Imprimir reporte final de todos los tests"""
        self.print_header("FINAL TEST REPORT")

        total_passed = 0
        total_failed = 0

        for category, results in self.test_results.items():
            passed = results["passed"]
            failed = results["failed"]
            total_passed += passed
            total_failed += failed

            status_icon = "✅" if failed == 0 else "⚠️" if passed > failed else "❌"
            print(f"{status_icon} {category.upper()}: {passed} passed, {failed} failed")

        print(f"\n{'=' * 60}")
        overall_status = (
            "✅ ALL TESTS PASSED"
            if total_failed == 0
            else f"⚠️ {total_failed} TESTS FAILED"
        )
        print(f"🎯 OVERALL RESULT: {overall_status}")
        print(f"📊 TOTAL: {total_passed} passed, {total_failed} failed")

        if total_failed > 0:
            print(f"\n❌ FAILED TESTS:")
            for category, results in self.test_results.items():
                if results["failed"] > 0:
                    for detail in results["details"]:
                        if not detail["passed"]:
                            print(
                                f"   • {category.upper()}: {detail['test']} - {detail['details']}"
                            )

        print(f"{'=' * 60}")

        # Guardar reporte detallado
        self._save_detailed_report()

        return total_failed == 0

    def _save_detailed_report(self):
        """Guardar reporte detallado en archivo JSON"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_passed": sum(r["passed"] for r in self.test_results.values()),
                "total_failed": sum(r["failed"] for r in self.test_results.values()),
            },
            "results": self.test_results,
            "environment": {
                "python_version": sys.version,
                "working_directory": os.getcwd(),
                "environment_variables": {
                    "SUPABASE_URL": "configured"
                    if os.getenv("SUPABASE_URL")
                    else "missing",
                    "SUPABASE_ANON_KEY": "configured"
                    if os.getenv("SUPABASE_ANON_KEY")
                    else "missing",
                    "OPENAI_API_KEY": "configured"
                    if os.getenv("OPENAI_API_KEY")
                    else "missing",
                    "CALENDLY_ACCESS_TOKEN": "configured"
                    if os.getenv("CALENDLY_ACCESS_TOKEN")
                    else "missing",
                },
            },
        }

        with open("crm_test_report.json", "w") as f:
            json.dump(report, f, indent=2)

        print(f"📄 Detailed report saved to: crm_test_report.json")
        print(f"📄 Logs saved to: crm_test.log")


async def main():
    """Función principal del test"""
    print("🚀 Starting CRM System Autonomous Test Suite")
    print(f"📅 Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    tester = CRMSystemTester()

    try:
        # Ejecutar todos los tests
        await tester.test_environment()
        await tester.test_database_connection()
        await tester.test_individual_agents()
        await tester.test_supabase_operations()
        await tester.test_complete_workflow()
        await tester.test_cleanup()

        # Reporte final
        success = tester.print_final_report()

        # Exit code
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during testing: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                    CRM SYSTEM TEST SUITE                    ║
    ║                                                              ║
    ║  This script will test your entire CRM system including:    ║
    ║  • Environment configuration                                 ║
    ║  • Database connectivity (UPDATED FOR SYNC METHODS)         ║
    ║  • Individual agents with function calling                  ║
    ║  • Supabase operations verification                         ║
    ║  • Complete workflow end-to-end                             ║
    ║  • Data persistence and cleanup                             ║
    ║                                                              ║
    ║  Make sure your .env file is configured with:               ║
    ║  • SUPABASE_URL                                             ║
    ║  • SUPABASE_ANON_KEY                                        ║
    ║  • OPENAI_API_KEY                                           ║
    ║  • CALENDLY_ACCESS_TOKEN (optional)                         ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

    # Ejecutar tests
    asyncio.run(main())
