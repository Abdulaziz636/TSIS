CREATE OR REPLACE FUNCTION ensure_group(p_name VARCHAR)
RETURNS INTEGER AS $$
DECLARE
    v_id INTEGER;
BEGIN
    INSERT INTO groups(name)
    VALUES (COALESCE(NULLIF(TRIM(p_name), ''), 'Other'))
    ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE PROCEDURE upsert_contact(
    p_name VARCHAR,
    p_phone VARCHAR,
    p_email VARCHAR DEFAULT NULL,
    p_birthday VARCHAR DEFAULT NULL,
    p_group_name VARCHAR DEFAULT 'Other',
    p_phone_type VARCHAR DEFAULT 'mobile'
)
LANGUAGE plpgsql AS $$
DECLARE
    v_contact_id INTEGER;
BEGIN
    INSERT INTO contacts(name, email, birthday, group_id)
    VALUES (p_name, p_email, p_birthday, ensure_group(p_group_name))
    ON CONFLICT (name) DO UPDATE SET
        email = EXCLUDED.email,
        birthday = EXCLUDED.birthday,
        group_id = EXCLUDED.group_id
    RETURNING id INTO v_contact_id;

    IF COALESCE(TRIM(p_phone), '') <> '' THEN
        INSERT INTO phones(contact_id, phone, type)
        VALUES (v_contact_id, p_phone, p_phone_type)
        ON CONFLICT (contact_id, phone) DO UPDATE SET type = EXCLUDED.type;
    END IF;
END;
$$;

CREATE OR REPLACE PROCEDURE add_phone(p_contact_name VARCHAR, p_phone VARCHAR, p_type VARCHAR)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO phones(contact_id, phone, type)
    SELECT id, p_phone, p_type
    FROM contacts
    WHERE name = p_contact_name
    ON CONFLICT (contact_id, phone) DO UPDATE SET type = EXCLUDED.type;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Contact % does not exist', p_contact_name;
    END IF;
END;
$$;

CREATE OR REPLACE PROCEDURE move_to_group(p_contact_name VARCHAR, p_group_name VARCHAR)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE contacts
    SET group_id = ensure_group(p_group_name)
    WHERE name = p_contact_name;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Contact % does not exist', p_contact_name;
    END IF;
END;
$$;

CREATE OR REPLACE PROCEDURE delete_contact(p_value VARCHAR)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM contacts c
    WHERE c.name = p_value
       OR EXISTS (SELECT 1 FROM phones p WHERE p.contact_id = c.id AND p.phone = p_value);
END;
$$;

CREATE OR REPLACE PROCEDURE bulk_insert_contacts(
    p_names VARCHAR[],
    p_phones VARCHAR[],
    INOUT p_invalid TEXT[] DEFAULT ARRAY[]::TEXT[]
)
LANGUAGE plpgsql AS $$
DECLARE
    i INTEGER;
BEGIN
    FOR i IN 1..COALESCE(array_length(p_names, 1), 0) LOOP
        CALL upsert_contact(p_names[i], p_phones[i], NULL, NULL, 'Other', 'mobile');
    END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION contact_rows()
RETURNS TABLE(
    contact_id INTEGER,
    name VARCHAR,
    email VARCHAR,
    birthday VARCHAR,
    group_name VARCHAR,
    phones TEXT,
    created_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT c.id, c.name, c.email, c.birthday, g.name,
           COALESCE(string_agg(p.phone || ' (' || p.type || ')', ', ' ORDER BY p.type), ''),
           c.created_at
    FROM contacts c
    LEFT JOIN groups g ON g.id = c.group_id
    LEFT JOIN phones p ON p.contact_id = c.id
    GROUP BY c.id, c.name, c.email, c.birthday, g.name, c.created_at;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION search_contacts(p_query TEXT)
RETURNS TABLE(
    contact_id INTEGER,
    name VARCHAR,
    email VARCHAR,
    birthday VARCHAR,
    group_name VARCHAR,
    phones TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT r.contact_id, r.name, r.email, r.birthday, r.group_name, r.phones
    FROM contact_rows() r
    WHERE r.name ILIKE '%' || p_query || '%'
       OR COALESCE(r.email, '') ILIKE '%' || p_query || '%'
       OR r.phones ILIKE '%' || p_query || '%'
    ORDER BY r.name;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_contacts_page(p_limit INTEGER, p_offset INTEGER)
RETURNS TABLE(
    contact_id INTEGER,
    name VARCHAR,
    email VARCHAR,
    birthday VARCHAR,
    group_name VARCHAR,
    phones TEXT,
    created_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT *
    FROM contact_rows() r
    ORDER BY r.name
    LIMIT p_limit OFFSET p_offset;
END;
$$ LANGUAGE plpgsql;
