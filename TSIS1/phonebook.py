import csv
import json
import re
from pathlib import Path

from psycopg2.extras import RealDictCursor

from connect import BASE_DIR, get_connection, run_sql_file


VALID_PHONE_TYPES = {"home", "work", "mobile"}
PHONE_TYPE_OPTIONS = "home / work / mobile"
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.com$")


def setup_database():
    run_sql_file("schema.sql")
    run_sql_file("procedures.sql")
    print("Database schema and procedures are ready.")


def ask(prompt, default=None):
    suffix = f" [{default}]" if default is not None else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def normalize_phone_type(value):
    phone_type = (value or "mobile").lower()
    if phone_type not in VALID_PHONE_TYPES:
        raise ValueError("Phone type must be one of: home, work, mobile")
    return phone_type


def normalize_email(value):
    email = (value or "").strip()
    if not EMAIL_RE.match(email):
        raise ValueError("Email must look like name@example.com")
    return email


def ask_email(prompt="Email"):
    while True:
        try:
            return normalize_email(ask(prompt))
        except ValueError as exc:
            print(exc)


def add_contact_interactive():
    name = ask("Name")
    phone = ask("Phone")
    email = ask_email()
    birthday = ask("Birthday YYYY-MM-DD", None)
    group = ask("Group", "Other")
    phone_type = normalize_phone_type(ask(f"Phone type ({PHONE_TYPE_OPTIONS})", "mobile"))

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "CALL upsert_contact(%s, %s, %s, %s, %s, %s)",
            (name, phone, email, birthday or None, group, phone_type),
        )
    print("Contact saved.")


def import_csv(path):
    with Path(path).open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        with get_connection() as conn, conn.cursor() as cur:
            for row in reader:
                try:
                    email = normalize_email(row.get("email"))
                    phone_type = normalize_phone_type(row.get("phone_type") or row.get("type"))
                except ValueError as exc:
                    print(f"Skipped {row.get('name', 'unknown')}: {exc}")
                    continue
                cur.execute(
                    "CALL upsert_contact(%s, %s, %s, %s, %s, %s)",
                    (
                        row["name"].strip(),
                        row.get("phone") or None,
                        email,
                        row.get("birthday") or None,
                        row.get("group") or "Other",
                        phone_type,
                    ),
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
            cur.execute(
                "SELECT phone, type FROM phones WHERE contact_id = %s ORDER BY type, phone",
                (contact["id"],),
            )
            contact["phones"] = cur.fetchall()

    Path(path).write_text(json.dumps(contacts, indent=2, default=str), encoding="utf-8")
    print(f"Exported {len(contacts)} contacts to {path}.")


def import_json(path):
    contacts = json.loads(Path(path).read_text(encoding="utf-8"))
    with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        for contact in contacts:
            name = contact["name"]
            cur.execute("SELECT id FROM contacts WHERE name = %s", (name,))
            existing = cur.fetchone()
            if existing:
                choice = ask(f"Duplicate '{name}' (skip / overwrite)", "skip").lower()
                if choice != "overwrite":
                    continue
                cur.execute("DELETE FROM contacts WHERE id = %s", (existing["id"],))

            phones = contact.get("phones") or [{"phone": contact.get("phone"), "type": "mobile"}]
            first_phone = phones[0] if phones else {"phone": None, "type": "mobile"}
            try:
                email = normalize_email(contact.get("email"))
            except ValueError as exc:
                print(f"Skipped {name}: {exc}")
                continue
            cur.execute(
                "CALL upsert_contact(%s, %s, %s, %s, %s, %s)",
                (
                    name,
                    first_phone.get("phone"),
                    email,
                    contact.get("birthday"),
                    contact.get("group_name") or contact.get("group") or "Other",
                    normalize_phone_type(first_phone.get("type")),
                ),
            )
            for phone in phones[1:]:
                cur.execute(
                    "CALL add_phone(%s, %s, %s)",
                    (name, phone["phone"], normalize_phone_type(phone.get("type"))),
                )
    print("JSON import finished.")


def search_contacts():
    query = ask("Search")
    with get_connection(dict_rows=True) as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM search_contacts(%s)", (query,))
        print_rows(cur.fetchall())


def list_filtered_sorted():
    group = ask("Group filter (empty for all)", "")
    email = ask("Email contains (empty for all)", "")
    sort_key = ask("Sort by (name / birthday / created_at)", "name")
    allowed_sort = {"name": "c.name", "birthday": "c.birthday", "created_at": "c.created_at"}
    order_by = allowed_sort.get(sort_key, "c.name")

    with get_connection(dict_rows=True) as conn, conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT c.id AS contact_id, c.name, c.email, c.birthday, g.name AS group_name,
                   COALESCE(string_agg(p.phone || ' (' || p.type || ')', ', '), '') AS phones,
                   c.created_at
            FROM contacts c
            LEFT JOIN groups g ON g.id = c.group_id
            LEFT JOIN phones p ON p.contact_id = c.id
            WHERE (%s = '' OR g.name = %s)
              AND (%s = '' OR c.email ILIKE '%%' || %s || '%%')
            GROUP BY c.id, c.name, c.email, c.birthday, g.name, c.created_at
            ORDER BY {order_by} NULLS LAST
            """,
            (group, group, email, email),
        )
        print_rows(cur.fetchall())


def paginated_navigation():
    # Здесь используется функция пагинации из Practice 8, а Python только
    # переключает страницы командами next / prev / quit.
    page_size = int(ask("Page size", "5"))
    offset = 0
    while True:
        with get_connection(dict_rows=True) as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM get_contacts_page(%s, %s)", (page_size, offset))
            rows = cur.fetchall()
        print(f"\nPage starting at {offset}")
        print_rows(rows)
        command = ask("Command (next / prev / quit)", "next").lower()
        if command == "next":
            offset += page_size
        elif command == "prev":
            offset = max(0, offset - page_size)
        elif command == "quit":
            break


def update_contact():
    # Обновление из Practice 7 расширено новыми полями контакта.
    name = ask("Contact name to update")
    field = ask("Field (name / email / birthday / group / phone)", "phone")
    value = ask_email("New email") if field == "email" else ask("New value")
    with get_connection() as conn, conn.cursor() as cur:
        if field == "group":
            cur.execute("CALL move_to_group(%s, %s)", (name, value))
        elif field == "phone":
            cur.execute("CALL add_phone(%s, %s, %s)", (name, value, normalize_phone_type(ask(f"Type ({PHONE_TYPE_OPTIONS})", "mobile"))))
        elif field == "email":
            cur.execute("UPDATE contacts SET email = %s WHERE name = %s", (normalize_email(value), name))
        elif field in {"name", "birthday"}:
            cur.execute(f"UPDATE contacts SET {field} = %s WHERE name = %s", (value, name))
        else:
            print("Unknown field.")
            return
    print("Updated.")


def delete_contact():
    # Удаление делегируется процедуре из Practice 8.
    value = ask("Name or phone to delete")
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("CALL delete_contact(%s)", (value,))
    print("Deleted if a matching contact existed.")


def print_rows(rows):
    # Простой вывод строк без сторонних библиотек для таблиц.
    if not rows:
        print("No rows.")
        return
    for row in rows:
        print(" | ".join(f"{key}={value}" for key, value in dict(row).items()))


def menu():
    actions = {
        "1": setup_database,
        "2": add_contact_interactive,
        "3": lambda: import_csv(ask("CSV path", str(BASE_DIR / "contacts.csv"))),
        "4": search_contacts,
        "5": list_filtered_sorted,
        "6": paginated_navigation,
        "7": update_contact,
        "8": delete_contact,
        "9": lambda: export_json(ask("JSON path", str(BASE_DIR / "contacts.json"))),
        "10": lambda: import_json(ask("JSON path", str(BASE_DIR / "contacts.json"))),
    }
    while True:
        print(
            "\n1 setup DB | 2 add/upsert | 3 import CSV | 4 search | 5 filter/sort | "
            "6 pages | 7 update | 8 delete | 9 export JSON | 10 import JSON | 0 quit"
        )
        choice = ask("Choose", "0")
        if choice == "0":
            break
        action = actions.get(choice)
        if action:
            action()
        else:
            print("Unknown choice.")


if __name__ == "__main__":
    menu()
