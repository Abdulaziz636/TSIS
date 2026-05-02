import csv
import json
from json import JSONDecodeError
from pathlib import Path

import psycopg2

from connect import BASE_DIR, get_connection, run_sql_file


REQUIRED_CSV_FIELDS = {"name", "phone"}


def ask(prompt, default=None):
    value = input(f"{prompt}{f' [{default}]' if default is not None else ''}: ").strip()
    return value or default


def require_value(value, field):
    if value is None or str(value).strip() == "":
        raise ValueError(f"{field} is required.")
    return str(value).strip()


def read_positive_int(prompt, default):
    while True:
        value = ask(prompt, str(default))
        try:
            number = int(value)
            if number > 0:
                return number
        except (TypeError, ValueError):
            pass
        print("Please enter a positive number.")


def print_error(error):
    if isinstance(error, psycopg2.Error):
        message = error.diag.message_primary or str(error)
    else:
        message = str(error)
    print(f"Error: {message}")


def setup_database():
    run_sql_file("schema.sql")
    run_sql_file("procedures.sql")
    print("Database is ready.")


def upsert(name, number, mail, birth=None, group="Other", kind="mobile"):
    name = require_value(name, "Name")
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
    csv_path = Path(path)
    imported = 0
    skipped = 0
    with csv_path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        missing_fields = REQUIRED_CSV_FIELDS - set(reader.fieldnames or [])
        if missing_fields:
            raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing_fields))}")

        for line_number, row in enumerate(reader, start=2):
            try:
                upsert(
                    row["name"],
                    row.get("phone"),
                    row.get("email"),
                    row.get("birthday") or None,
                    row.get("group") or "Other",
                    row.get("phone_type") or row.get("type") or "mobile",
                )
                imported += 1
            except (ValueError, psycopg2.Error) as error:
                skipped += 1
                print(f"Skipped CSV line {line_number}: {error}")
    print(f"CSV import finished. Imported: {imported}. Skipped: {skipped}.")


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

    json_path = Path(path)
    if json_path.parent and not json_path.parent.exists():
        raise FileNotFoundError(f"Folder does not exist: {json_path.parent}")
    json_path.write_text(json.dumps(contacts, indent=2, default=str), encoding="utf-8")
    print(f"Exported {len(contacts)} contacts.")


def import_json(path):
    contacts = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(contacts, list):
        raise ValueError("JSON root must be a list of contacts.")

    imported = 0
    skipped = 0
    with get_connection(dict_rows=True) as conn, conn.cursor() as cur:
        for index, contact in enumerate(contacts, start=1):
            if not isinstance(contact, dict):
                skipped += 1
                print(f"Skipped JSON item {index}: contact must be an object.")
                continue
            try:
                cur.execute("SAVEPOINT import_contact")
                name = require_value(contact.get("name"), "Name")
                cur.execute("SELECT id FROM contacts WHERE name = %s", (name,))
                old = cur.fetchone()
                if old and ask(f"Duplicate '{name}' (skip / overwrite)", "skip").lower() != "overwrite":
                    cur.execute("RELEASE SAVEPOINT import_contact")
                    skipped += 1
                    continue
                if old:
                    cur.execute("DELETE FROM contacts WHERE id = %s", (old["id"],))

                phones = contact.get("phones", [])
                if not isinstance(phones, list) or not phones:
                    raise ValueError("phones must be a non-empty list.")
                first = phones[0]
                if not isinstance(first, dict):
                    raise ValueError("phone item must be an object.")
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
                    if not isinstance(extra, dict):
                        raise ValueError("phone item must be an object.")
                    cur.execute("CALL add_phone(%s, %s, %s)", (name, extra.get("phone"), extra.get("type") or "mobile"))
                cur.execute("RELEASE SAVEPOINT import_contact")
                imported += 1
            except (ValueError, psycopg2.Error) as error:
                cur.execute("ROLLBACK TO SAVEPOINT import_contact")
                cur.execute("RELEASE SAVEPOINT import_contact")
                skipped += 1
                print(f"Skipped JSON item {index}: {error}")
                continue
    print(f"JSON import finished. Imported: {imported}. Skipped: {skipped}.")


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
    page_size = read_positive_int("Page size", 5)
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
        if cur.rowcount == 0 and field in {"email", "birthday", "name"}:
            print("Contact not found.")
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


def run_action(action):
    try:
        action()
    except (FileNotFoundError, PermissionError, OSError, ValueError, RuntimeError, JSONDecodeError, csv.Error, psycopg2.Error) as error:
        print_error(error)
    except KeyboardInterrupt:
        print("\nAction cancelled.")


def menu():
    print_controls()
    while True:
        print_menu()
        choice = input("Select action > ").strip()
        if choice == "0":
            break
        elif choice == "1":
            run_action(setup_database)
        elif choice == "2":
            run_action(add_contact_interactive)
        elif choice == "3":
            run_action(lambda: import_csv(ask("CSV path", str(BASE_DIR / "contacts.csv"))))
        elif choice == "4":
            run_action(search_contacts)
        elif choice == "5":
            run_action(list_filtered_sorted)
        elif choice == "6":
            run_action(paginated_navigation)
        elif choice == "7":
            run_action(update_contact)
        elif choice == "8":
            run_action(delete_contact)
        elif choice == "9":
            run_action(lambda: export_json(ask("JSON path", str(BASE_DIR / "contacts.json"))))
        elif choice == "10":
            run_action(lambda: import_json(ask("JSON path", str(BASE_DIR / "contacts.json"))))
        else:
            print("Unknown choice.")


if __name__ == "__main__":
    menu()
