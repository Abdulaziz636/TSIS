import csv
import json
from pathlib import Path

from connect import BASE_DIR, get_connection, run_sql_file


def ask(prompt, default=None):
    value = input(f"{prompt}{f' [{default}]' if default is not None else ''}: ").strip()
    return value or default


def setup_database():
    run_sql_file("schema.sql")
    run_sql_file("procedures.sql")
    print("Database is ready.")


def upsert(name, number, mail, birth=None, group="Other", kind="mobile"):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("CALL upsert_contact(%s, %s, %s, %s, %s, %s)", (name, number, mail, birth, group, kind))

def add_contact_interactive():
    upsert(
        ask("Name"),
        ask("Phone"),
        ask("Email"),
        ask("Birthday YYYY-MM-DD", "") or None,
        ask("Group", "Other"),
        ask("Phone type", "mobile"),
    )
    print("Contact saved.")


def import_csv(path):
    with Path(path).open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            upsert(
                row["name"].strip(),
                row.get("phone"),
                row.get("email"),
                row.get("birthday") or None,
                row.get("group") or "Other",
                row.get("phone_type") or row.get("type") or "mobile",
            )
    print("CSV import finished.")


def export_json(path):
    with get_connection(dict_rows=True) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.id, c.name, c.email, c.birthday, c.created_at, g.name AS group_name
            FROM contacts c
            LEFT JOIN groups g ON g.id = c.group_id
            ORDER BY c.name
            """
        )
        contacts = cur.fetchall()
        for contact in contacts:
            cur.execute("SELECT phone, type FROM phones WHERE contact_id = %s ORDER BY type, phone", (contact["id"],))
            contact["phones"] = cur.fetchall()

    Path(path).write_text(json.dumps(contacts, indent=2, default=str), encoding="utf-8")
    print(f"Exported {len(contacts)} contacts.")


def import_json(path):
    contacts = json.loads(Path(path).read_text(encoding="utf-8"))
    with get_connection(dict_rows=True) as conn, conn.cursor() as cur:
        for contact in contacts:
            name = contact["name"]
            cur.execute("SELECT id FROM contacts WHERE name = %s", (name,))
            old = cur.fetchone()
            if old and ask(f"Duplicate '{name}' (skip / overwrite)", "skip").lower() != "overwrite":
                continue
            if old:
                cur.execute("DELETE FROM contacts WHERE id = %s", (old["id"],))

            phones = contact.get("phones", [])
            if not phones:
                continue
            first = phones[0]
            cur.execute(
                "CALL upsert_contact(%s, %s, %s, %s, %s, %s)",
                (
                    name,
                    first.get("phone"),
                    contact.get("email"),
                    contact.get("birthday") or None,
                    contact.get("group_name") or contact.get("group") or "Other",
                    first.get("type") or "mobile",
                ),
            )
            for extra in phones[1:]:
                cur.execute("CALL add_phone(%s, %s, %s)", (name, extra.get("phone"), extra.get("type") or "mobile"))
    print("JSON import finished.")


def print_rows(rows):
    if not rows:
        print("No rows.")
        return
    for row in rows:
        print(" | ".join(f"{key}={value}" for key, value in dict(row).items()))


def search_contacts():
    with get_connection(dict_rows=True) as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM search_contacts(%s)", (ask("Search"),))
        print_rows(cur.fetchall())


def list_filtered_sorted():
    group = ask("Group filter (empty for all)", "")
    mail = ask("Email contains (empty for all)", "")
    sort = {"name": "c.name", "birthday": "c.birthday", "created_at": "c.created_at"}.get(
        ask("Sort by (name / birthday / created_at)", "name"),
        "c.name",
    )
    with get_connection(dict_rows=True) as conn, conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT c.id, c.name, c.email, c.birthday, g.name AS group_name,
                   COALESCE(string_agg(p.phone || ' (' || p.type || ')', ', '), '') AS phones,
                   c.created_at
            FROM contacts c
            LEFT JOIN groups g ON g.id = c.group_id
            LEFT JOIN phones p ON p.contact_id = c.id
            WHERE (%s = '' OR g.name = %s)
              AND (%s = '' OR c.email ILIKE '%%' || %s || '%%')
            GROUP BY c.id, c.name, c.email, c.birthday, g.name, c.created_at
            ORDER BY {sort} NULLS LAST
            """,
            (group, group, mail, mail),
        )
        print_rows(cur.fetchall())


def paginated_navigation():
    page_size = int(ask("Page size", "5"))
    offset = 0
    while True:
        with get_connection(dict_rows=True) as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM get_contacts_page(%s, %s)", (page_size, offset))
            print_rows(cur.fetchall())

        command = ask("Command (next / prev / quit)", "next").lower()
        if command == "quit":
            break
        offset = max(0, offset + page_size * (1 if command == "next" else -1))


def update_contact():
    name = ask("Contact name to update")
    field = ask("Field (name / email / birthday / group / phone)", "phone")
    with get_connection() as conn, conn.cursor() as cur:
        if field == "group":
            cur.execute("CALL move_to_group(%s, %s)", (name, ask("New group")))
        elif field == "phone":
            cur.execute("CALL add_phone(%s, %s, %s)", (name, ask("New phone"), ask("Phone type", "mobile")))
        elif field == "email":
            cur.execute("UPDATE contacts SET email = %s WHERE name = %s", (ask("New email"), name))
        elif field == "birthday":
            cur.execute("UPDATE contacts SET birthday = %s WHERE name = %s", (ask("New birthday YYYY-MM-DD", "") or None, name))
        elif field == "name":
            cur.execute("UPDATE contacts SET name = %s WHERE name = %s", (ask("New name"), name))
        else:
            print("Unknown field.")
            return
    print("Updated.")


def delete_contact():
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("CALL delete_contact(%s)", (ask("Name or phone to delete"),))
    print("Deleted if found.")


MENU_ITEMS = [
    ("1", "Setup database"),
    ("2", "Add contact"),
    ("3", "Import from CSV"),
    ("4", "Search contacts"),
    ("5", "List, filter and sort"),
    ("6", "Browse pages"),
    ("7", "Update contact"),
    ("8", "Delete contact"),
    ("9", "Export to JSON"),
    ("10", "Import from JSON"),
    ("0", "Quit"),
]


def print_menu():
    print("\n" + "=" * 42)
    print(" KBTU Contact Desk ".center(42, "="))
    print("=" * 42)
    for key, title in MENU_ITEMS:
        print(f"{key:>2}  {title}")
    print("-" * 42)


def print_controls():
    print("Controls: type a menu number and press Enter. Use 0 to quit.")
    print("Paths: press Enter on CSV/JSON prompts to use the default sample files.")


def menu():
    print_controls()
    while True:
        print_menu()
        choice = input("Select action > ").strip()
        if choice == "0":
            break
        elif choice == "1":
            setup_database()
        elif choice == "2":
            add_contact_interactive()
        elif choice == "3":
            import_csv(ask("CSV path", str(BASE_DIR / "contacts.csv")))
        elif choice == "4":
            search_contacts()
        elif choice == "5":
            list_filtered_sorted()
        elif choice == "6":
            paginated_navigation()
        elif choice == "7":
            update_contact()
        elif choice == "8":
            delete_contact()
        elif choice == "9":
            export_json(ask("JSON path", str(BASE_DIR / "contacts.json")))
        elif choice == "10":
            import_json(ask("JSON path", str(BASE_DIR / "contacts.json")))
        else:
            print("Unknown choice.")


if __name__ == "__main__":
    menu()
