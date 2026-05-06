-- Migration demo schema (PostgreSQL)
-- Three base tables + one materialized view (refreshed on a schedule / by procedure).

BEGIN;

DROP MATERIALIZED VIEW IF EXISTS patient_care_summary CASCADE;
DROP PROCEDURE IF EXISTS proc_transform_and_summarize();
DROP PROCEDURE IF EXISTS proc_load_patients_from_csv(TEXT);
DROP TABLE IF EXISTS raw_patient_staging CASCADE;
DROP TABLE IF EXISTS x_tbl_ptnt_d CASCADE;
DROP TABLE IF EXISTS departments CASCADE;

-- Staging table filled from CSV (clean column names).
CREATE TABLE raw_patient_staging (
    patient_id           INTEGER PRIMARY KEY,
    first_name           VARCHAR(100) NOT NULL,
    last_name            VARCHAR(100) NOT NULL,
    date_of_birth        DATE NOT NULL,
    admission_date       DATE NOT NULL,
    department_code      VARCHAR(20) NOT NULL,
    diagnosis_code       VARCHAR(30) NOT NULL,
    attending_physician  VARCHAR(120) NOT NULL
);

-- Legacy / ill-designed static reference: obscure columns, no PK, denormalized blob.
CREATE TABLE x_tbl_ptnt_d (
    fld1 TEXT,
    fld2 TEXT,
    fld3 TEXT,
    fld4 TEXT,
    data_blob TEXT
);

-- Small reference dimension for joins.
CREATE TABLE departments (
    dept_code      VARCHAR(20) PRIMARY KEY,
    dept_name      VARCHAR(120) NOT NULL,
    floor_number   SMALLINT NOT NULL,
    head_physician VARCHAR(120) NOT NULL
);

-- "View" maintained on a schedule: materialized view = snapshot refreshed after loads/transforms.
CREATE MATERIALIZED VIEW patient_care_summary AS
SELECT
    r.patient_id,
    trim(both ' ' FROM r.first_name || ' ' || r.last_name) AS full_name,
    upper(trim(both ' ' FROM r.diagnosis_code)) AS diagnosis_code_normalized,
    r.admission_date,
    d.dept_name,
    d.floor_number,
    d.head_physician AS department_head,
    (r.admission_date - r.date_of_birth) / 365 AS approx_age_at_admission_years,
    r.attending_physician,
    -- Nonsense legacy join: fld1 sometimes matches department_code; blob is denormalized junk.
    split_part(COALESCE(l.data_blob, ''), ',', 2) AS legacy_blob_field2,
    l.fld3 AS legacy_misc
FROM raw_patient_staging r
JOIN departments d ON d.dept_code = r.department_code
LEFT JOIN x_tbl_ptnt_d l ON l.fld1 = r.department_code
WITH NO DATA;

COMMENT ON TABLE x_tbl_ptnt_d IS 'Legacy dump: fld* meaningless, data_blob packs multiple facts; no PK by design.';
COMMENT ON MATERIALIZED VIEW patient_care_summary IS 'Refreshed by proc_transform_and_summarize (simulates scheduled ETL).';

-- Procedure 1: load CSV from server-visible path into staging.
CREATE OR REPLACE PROCEDURE proc_load_patients_from_csv(csv_server_path TEXT)
LANGUAGE plpgsql
AS $$
BEGIN
    TRUNCATE TABLE raw_patient_staging;
    EXECUTE format(
        $f$
        COPY raw_patient_staging (
            patient_id,
            first_name,
            last_name,
            date_of_birth,
            admission_date,
            department_code,
            diagnosis_code,
            attending_physician
        )
        FROM %L
        WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
        $f$,
        csv_server_path
    );
END;
$$;

-- Procedure 2: transform + join is encoded in the MV definition; refresh applies it to current data.
CREATE OR REPLACE PROCEDURE proc_transform_and_summarize()
LANGUAGE plpgsql
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW patient_care_summary;
END;
$$;

COMMIT;
