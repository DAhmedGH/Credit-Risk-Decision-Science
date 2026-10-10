-- Dedicated disposable-development database only; caller checks server identity.
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS curated;
CREATE TABLE IF NOT EXISTS raw.ingestions (
    source_sha256 text PRIMARY KEY CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),
    dataset_version text NOT NULL,
    rules_sha256 text NOT NULL,
    feature_contract_sha256 text NOT NULL,
    source_rows integer NOT NULL CHECK (source_rows >= 0),
    accepted_rows integer NOT NULL CHECK (accepted_rows >= 0),
    rejected_rows integer NOT NULL CHECK (rejected_rows >= 0),
    validation jsonb NOT NULL,
    ingested_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (source_rows = accepted_rows + rejected_rows)
);
CREATE TABLE IF NOT EXISTS raw.credit_clients (
    source_sha256 text NOT NULL REFERENCES raw.ingestions(source_sha256),
    client_id bigint NOT NULL CHECK (client_id > 0),
    source_row integer NOT NULL,
    source_values jsonb NOT NULL,
    accepted boolean NOT NULL,
    rejection_reasons jsonb NOT NULL,
    PRIMARY KEY (source_sha256, client_id)
);
CREATE TABLE IF NOT EXISTS curated.credit_clients (
    source_sha256 text NOT NULL REFERENCES raw.ingestions(source_sha256),
    client_id bigint NOT NULL CHECK (client_id > 0),
    limit_bal numeric NOT NULL CHECK (limit_bal > 0),
    pay_status_2005_04 smallint,
    pay_status_2005_05 smallint,
    pay_status_2005_06 smallint,
    pay_status_2005_07 smallint,
    pay_status_2005_08 smallint,
    pay_status_2005_09 smallint,
    bill_amt_2005_04 numeric,
    bill_amt_2005_05 numeric,
    bill_amt_2005_06 numeric,
    bill_amt_2005_07 numeric,
    bill_amt_2005_08 numeric,
    bill_amt_2005_09 numeric,
    pay_amt_2005_04 numeric,
    pay_amt_2005_05 numeric,
    pay_amt_2005_06 numeric,
    pay_amt_2005_07 numeric,
    pay_amt_2005_08 numeric,
    pay_amt_2005_09 numeric,
    default_next_month smallint NOT NULL CHECK (default_next_month IN (0, 1)),
    cleaning_flags jsonb NOT NULL DEFAULT '[]'::jsonb,
    PRIMARY KEY (source_sha256, client_id),
    FOREIGN KEY (source_sha256, client_id) REFERENCES raw.credit_clients(source_sha256, client_id)
);
CREATE TABLE IF NOT EXISTS curated.audit_attributes (
    source_sha256 text NOT NULL,
    client_id bigint NOT NULL,
    sex integer, age integer, education integer, marriage integer,
    sex_group text NOT NULL, education_group text NOT NULL, marriage_group text NOT NULL,
    PRIMARY KEY (source_sha256, client_id),
    FOREIGN KEY (source_sha256, client_id) REFERENCES curated.credit_clients(source_sha256, client_id)
);
