# TSIS1 - Extended PhoneBook

Base files used: `practice7.md` and `practice8.md`.

Implemented from the base practices:
- PostgreSQL PhoneBook schema, connection helpers and console CRUD.
- CSV import, console insert/update/delete and filtering by name/phone.
- PL/pgSQL pattern search, upsert, bulk insert with validation, pagination and delete procedure.

Added from TSIS1:
- Extended schema with `contacts`, `phones` and `groups`.
- Contact email, birthday, group and multiple phone numbers.
- Search across name, email and all phones.
- Filter by group, partial email search, sorting by name, birthday or creation date.
- Console pagination with `next`, `prev` and `quit`.
- JSON export/import with duplicate handling.
- Procedures `add_phone` and `move_to_group`.

Run:
```bash
pip install -r requirements.txt
python phonebook.py
```

Before running, create a PostgreSQL database or set environment variables:
`PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`.
The default database name is `phonebook_tsis1`.

Assumption: phone numbers are validated as 7-15 digits with an optional leading `+`.
