CREATE OR REPLACE FUNCTION ensure_group(p_group_name VARCHAR)
RETURNS INTEGER AS $$
DECLARE
    v_group_id INTEGER;
BEGIN
    INSERT INTO groups(name)
    VALUES (COALESCE(NULLIF(TRIM(p_group_name), ''), 'Other'))
    ON CONFLICT (name) DO NOTHING;

    SELECT id INTO v_group_id
    FROM groups
    WHERE name = COALESCE(NULLIF(TRIM(p_group_name), ''), 'Other');

    RETURN v_group_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE PROCEDURE upsert_contact(
    p_name VARCHAR,
    p_phone VARCHAR,
    p_email VARCHAR DEFAULT NULL,
    p_birthday DATE DEFAULT NULL,
    p_group_name VARCHAR DEFAULT 'Other',
    p_phone_type VARCHAR DEFAULT 'mobile'
)
LANGUAGE plpgsql AS $$
DECLARE
    v_contact_id INTEGER;
    v_group_id INTEGER;
BEGIN
    v_group_id := ensure_group(p_group_name);

    INSERT INTO contacts(name, email, birthday, group_id)
    VALUES (p_name, p_email, p_birthday, v_group_id)
    ON CONFLICT (name) DO UPDATE
       SET email = EXCLUDED.email,
           birthday = EXCLUDED.birthday,
           group_id = EXCLUDED.group_id
    RETURNING id INTO v_contact_id;

    IF p_phone IS NOT NULL AND TRIM(p_phone) <> '' THEN
        INSERT INTO phones(contact_id, phone, type)
        VALUES (v_contact_id, p_phone, p_phone_type)
        ON CONFLICT (contact_id, phone) DO UPDATE SET type = EXCLUDED.type;
    END IF;
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
        IF p_phones[i] !~ '^\+?[0-9]{7,15}$' THEN
            p_invalid := array_append(p_invalid, p_names[i] || ': ' || p_phones[i]);
        ELSE
            CALL upsert_contact(p_names[i], p_phones[i], NULL, NULL, 'Other', 'mobile');
        END IF;
    END LOOP;
END;
$$;

CREATE OR REPLACE PROCEDURE delete_contact(p_value VARCHAR)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM contacts c
    WHERE c.name = p_value
       OR EXISTS (
           SELECT 1 FROM phones p
           WHERE p.contact_id = c.id AND p.phone = p_value
       );
END;
$$;

CREATE OR REPLACE PROCEDURE add_phone(
    p_contact_name VARCHAR,
    p_phone VARCHAR,
    p_type VARCHAR
)
LANGUAGE plpgsql AS $$
DECLARE
    v_contact_id INTEGER;
BEGIN
    SELECT id INTO v_contact_id FROM contacts WHERE name = p_contact_name;

    IF v_contact_id IS NULL THEN
        RAISE EXCEPTION 'Contact % does not exist', p_contact_name;
    END IF;

    INSERT INTO phones(contact_id, phone, type)
    VALUES (v_contact_id, p_phone, p_type)
    ON CONFLICT (contact_id, phone) DO UPDATE SET type = EXCLUDED.type;
END;
$$;

CREATE OR REPLACE PROCEDURE move_to_group(
    p_contact_name VARCHAR,
    p_group_name VARCHAR
)
LANGUAGE plpgsql AS $$
DECLARE
    v_group_id INTEGER;
BEGIN
    v_group_id := ensure_group(p_group_name);

    UPDATE contacts
    SET group_id = v_group_id
    WHERE name = p_contact_name;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Contact % does not exist', p_contact_name;
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION search_contacts(p_query TEXT)
RETURNS TABLE(
    contact_id INTEGER,
    name VARCHAR,
    email VARCHAR,
    birthday DATE,
    group_name VARCHAR,
    phones TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT c.id,
           c.name,
           c.email,
           c.birthday,
           g.name AS group_name,
           COALESCE(string_agg(p.phone || ' (' || p.type || ')', ', ' ORDER BY p.type), '') AS phones
    FROM contacts c
    LEFT JOIN groups g ON g.id = c.group_id
    LEFT JOIN phones p ON p.contact_id = c.id
    GROUP BY c.id, c.name, c.email, c.birthday, g.name
    HAVING c.name ILIKE '%' || p_query || '%'
        OR COALESCE(c.email, '') ILIKE '%' || p_query || '%'
        OR COALESCE(string_agg(p.phone, ' '), '') ILIKE '%' || p_query || '%'
    ORDER BY c.name;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_contacts_page(p_limit INTEGER, p_offset INTEGER)
RETURNS TABLE(
    contact_id INTEGER,
    name VARCHAR,
    email VARCHAR,
    birthday DATE,
    group_name VARCHAR,
    phones TEXT,
    created_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT c.id,
           c.name,
           c.email,
           c.birthday,
           g.name AS group_name,
           COALESCE(string_agg(p.phone || ' (' || p.type || ')', ', ' ORDER BY p.type), '') AS phones,
           c.created_at
    FROM contacts c
    LEFT JOIN groups g ON g.id = c.group_id
    LEFT JOIN phones p ON p.contact_id = c.id
    GROUP BY c.id, c.name, c.email, c.birthday, g.name, c.created_at
    ORDER BY c.name
    LIMIT p_limit OFFSET p_offset;
END;
$$ LANGUAGE plpgsql;

