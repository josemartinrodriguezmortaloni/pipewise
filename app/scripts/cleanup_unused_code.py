#!/usr/bin/env python3
"""
Clean up unused functions in supabase_client.py
Removes functions that reference tables that have been dropped.

Run this AFTER executing cleanup_unused_tables.sql
"""

import os
import re
from pathlib import Path


def backup_file(file_path: Path) -> Path:
    """Create a backup of the original file"""
    backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
    backup_path.write_text(file_path.read_text(encoding="utf-8"))
    print(f"✅ Backup created: {backup_path}")
    return backup_path


def remove_unused_functions():
    """Remove functions that reference dropped tables"""

    # Path to supabase_client.py
    client_file = Path(__file__).parent.parent / "supabase" / "supabase_client.py"

    if not client_file.exists():
        print(f"❌ File not found: {client_file}")
        return

    # Create backup
    backup_file(client_file)

    # Read the current content
    content = client_file.read_text(encoding="utf-8")

    # Functions to remove (those that use dropped tables)
    functions_to_remove = [
        # Conversation functions
        "create_conversation",
        "get_conversation",
        "list_conversations",
        "update_conversation",
        "close_conversation",
        "get_active_conversations",
        "get_lead_with_conversations",
        "get_conversation_with_messages",
        # Message functions
        "create_message",
        "get_messages",
        "get_messages_with_filters",
        # Contact functions
        "create_contact",
        "get_contact",
        "get_contact_by_platform",
        "list_contacts",
        "update_contact",
        "get_contact_stats",
        "get_contact_messages",
        # Outreach message functions
        "create_outreach_message",
        # Async versions
        "async_create_conversation",
        "async_get_conversation",
        "async_list_conversations",
        "async_update_conversation",
        "async_create_message",
        "async_get_messages",
    ]

    print(f"🧹 Cleaning up {len(functions_to_remove)} unused functions...")

    # Remove each function
    updated_content = content
    functions_removed = []

    for func_name in functions_to_remove:
        # Pattern to match function definition until next function or class
        pattern = (
            rf"(    def {func_name}\([^)]*\).*?)(?=    def |    async def |class |\Z)"
        )
        matches = re.findall(pattern, updated_content, re.DOTALL)

        if matches:
            # Remove the function
            updated_content = re.sub(pattern, "", updated_content, flags=re.DOTALL)
            functions_removed.append(func_name)
            print(f"  ✅ Removed: {func_name}")

    # Remove unused imports
    unused_imports = [
        "from app.schemas.conversations_schema import ConversationCreate, ConversationUpdate",
        "from app.schemas.messsage_schema import MessageCreate",
        "from app.schemas.contacts_schema import ContactCreate, ContactUpdate, OutreachMessageCreate",
        "from app.models.conversation import Conversation",
        "from app.models.message import Message",
    ]

    for import_line in unused_imports:
        if import_line in updated_content:
            updated_content = updated_content.replace(import_line + "\n", "")
            print(f"  ✅ Removed import: {import_line.split('import')[1].strip()}")

    # Clean up any remaining references to dropped tables in comments
    table_references = ["conversations", "messages", "contacts", "outreach_messages"]
    for table in table_references:
        # Update comments that mention these tables
        pattern = rf"# ===================== OPERACIONES {table.upper()} ====================="
        updated_content = re.sub(pattern, "", updated_content)

    # Remove empty lines (more than 2 consecutive)
    updated_content = re.sub(r"\n\n\n+", "\n\n", updated_content)

    # Write the cleaned content
    client_file.write_text(updated_content, encoding="utf-8")

    print(f"\n✅ Cleanup completed!")
    print(f"   - Functions removed: {len(functions_removed)}")
    print(f"   - File updated: {client_file}")
    print(f"   - Backup available: {client_file.with_suffix('.py.backup')}")

    if functions_removed:
        print(f"\n📋 Removed functions:")
        for func in functions_removed:
            print(f"   - {func}")


def remove_unused_imports_from_agents():
    """Remove unused imports from agents.py that reference dropped tables"""

    agents_file = Path(__file__).parent.parent / "agents" / "agents.py"

    if not agents_file.exists():
        print(f"❌ File not found: {agents_file}")
        return

    # Create backup
    backup_file(agents_file)

    content = agents_file.read_text(encoding="utf-8")

    # Remove unused schema imports
    unused_imports = [
        "from app.schemas.conversations_schema import ConversationCreate",
        "from app.schemas.messsage_schema import MessageCreate",
    ]

    updated_content = content
    for import_line in unused_imports:
        if import_line in updated_content:
            updated_content = updated_content.replace(import_line + "\n", "")
            print(f"  ✅ Removed from agents.py: {import_line}")

    agents_file.write_text(updated_content, encoding="utf-8")
    print(f"✅ Cleaned up agents.py imports")


if __name__ == "__main__":
    print("🧹 Starting cleanup of unused code...")
    print("=" * 50)

    print("\n1. Cleaning supabase_client.py...")
    remove_unused_functions()

    print("\n2. Cleaning agents.py imports...")
    remove_unused_imports_from_agents()

    print("\n" + "=" * 50)
    print("🎉 Code cleanup completed!")
    print("\n📝 NEXT STEPS:")
    print("1. Test the system to ensure everything still works")
    print("2. Run the database cleanup script if tables need to be dropped")
    print("3. Commit the changes if everything looks good")
