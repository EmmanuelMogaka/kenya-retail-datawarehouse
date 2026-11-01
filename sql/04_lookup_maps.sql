-- 04_lookup_maps.sql
-- PURPOSE: lookup tables that translate messy raw spellings into standard values.
--
-- HOW THEY WORK: the cleaning step lowercases and trims a raw value, then looks it
-- up here. Found -> use the standard name. Not found -> the row is REJECTED
-- (we never guess). To support a new spelling later, add one row here.
--
-- Safe to rerun: we empty and refill the tables each time.

CREATE TABLE IF NOT EXISTS "dukafresh-dw".ref_store_name_map (
    raw_name       TEXT PRIMARY KEY,   -- lowercase, trimmed spelling seen in raw data
    standard_name  TEXT NOT NULL       -- the official store name
);

CREATE TABLE IF NOT EXISTS "dukafresh-dw".ref_payment_map (
    raw_name       TEXT PRIMARY KEY,
    standard_name  TEXT NOT NULL
);

TRUNCATE TABLE "dukafresh-dw".ref_store_name_map;
TRUNCATE TABLE "dukafresh-dw".ref_payment_map;

INSERT INTO "dukafresh-dw".ref_store_name_map (raw_name, standard_name) VALUES
    ('duka fresh westlands',   'Duka Fresh Westlands'),
    ('duka fresh westlnds',    'Duka Fresh Westlands'),
    ('duka fresh kilimani',    'Duka Fresh Kilimani'),
    ('duka fresh nyali',       'Duka Fresh Nyali'),
    ('duka fresh nyalli',      'Duka Fresh Nyali'),
    ('duka fresh milimani',    'Duka Fresh Milimani'),
    ('duka fresh milimani.',   'Duka Fresh Milimani'),
    ('duka fresh millimani',   'Duka Fresh Milimani'),
    ('duka fresh nakuru town', 'Duka Fresh Nakuru Town'),
    ('duka fresh nakuru',      'Duka Fresh Nakuru Town');

INSERT INTO "dukafresh-dw".ref_payment_map (raw_name, standard_name) VALUES
    ('m-pesa', 'M-Pesa'),
    ('mpesa',  'M-Pesa'),
    ('cash',   'Cash'),
    ('card',   'Card'),
    ('visa',   'Card');