import csv
import json
from pathlib import Path

from connect import BASE_DIR, get_connection, run_sql_file


def ask(prompt, default=None):
    value = input(f"{prompt}{f' [{default}]' if default is not None else ''}: ").strip()
    return value or default


def empty_to_none(value):
    return value or None


def setup_database():
    run_sql_file("schema.sql")
    run_sql_file("procedures.sql")
    print("Database is ready.")


def call_upsert(cur, name, number, mail, birth=None, group="Other", kind="mobile"):
    cur.execute("CALL upsert_contact(%s, %s, %s, %s, %s, %s)", (name, number, mail, birth, group, kind))


def upsert(name, number, mail, birth=None, group="Other", kind="mobile"):
    with get_connection() as conn, conn.cursor() as cur:
        call_upsert(cur, name, number, mail, birth, group, kind)


def add_contact_interactive():
    upsert(
        ask("Name"),
        ask("Phone"),
        ask("Email"),
        empty_to_none(ask("Birthday YYYY-MM-DD", "")),
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
                empty_to_none(row.get("birthday")),
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

            phones = contact.get("phones") or [{"phone": contact.get("phone"), "type": "mobile"}]
            first = phones[0]
            call_upsert(
                cur,
                name,
                first.get("phone"),
                contact.get("email"),
                empty_to_none(contact.get("birthday")),
                contact.get("group_name") or contact.get("group") or "Other",
                first.get("type") or "mobile",
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
            cur.execute("UPDATE contacts SET birthday = %s WHERE name = %s", (empty_to_none(ask("New birthday YYYY-MM-DD", "")), name))
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
        print("\n1 setup | 2 add | 3 CSV | 4 search | 5 filter | 6 pages | 7 update | 8 delete | 9 export | 10 import | 0 quit")
        choice = ask("Choose", "0")
        if choice == "0":
            break
        actions.get(choice, lambda: print("Unknown choice."))()


if __name__ == "__main__":
    menu()
