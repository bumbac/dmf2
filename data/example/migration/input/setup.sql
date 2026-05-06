-- Master setup for migration demo (healthcare).
-- 1) Creates schema (tables + materialized view + procedures)
-- 2) Seeds static / reference rows
-- 3) Loads CSV via proc_load_patients_from_csv
-- 4) Refreshes materialized summary via proc_transform_and_summarize
--
-- Run with psql variable abs_csv pointing at patients_import.csv (server-readable path):
--   ./run_setup.sh
-- or:
--   psql -v ON_ERROR_STOP=1 -v abs_csv="/absolute/path/to/patients_import.csv" -f setup.sql

\ir schema.sql

BEGIN;

INSERT INTO departments (dept_code, dept_name, floor_number, head_physician) VALUES
    ('CARD', 'Cardiology', 3, 'Dr. Rivera'),
    ('ER',   'Emergency', 1, 'Dr. Singh'),
    ('ORTH', 'Orthopedics', 2, 'Dr. Chen'),
    ('PULM', 'Pulmonology', 4, 'Dr. Okafor'),
    ('NEU',  'Neurology', 5, 'Dr. Nielsen')
ON CONFLICT (dept_code) DO NOTHING;

-- Static legacy junk: fld1 occasionally lines up with department_code for accidental joins.
INSERT INTO x_tbl_ptnt_d (fld1, fld2, fld3, fld4, data_blob) VALUES
    ('CARD', 'x', 'legacy_note_cardiology', '99', 'RIVERA,CARD-BLOB,extra|noise'),
    ('ER',   'y', 'legacy_note_er',         '12', 'SINGH,ER-BLOB,garbage'),
    ('ORTH', 'z', 'legacy_note_orth',       '7',  'CHEN,ORTH-BLOB,more,junk'),
    ('PULM', 'q', 'legacy_note_pulm',       '4',  'OKAFOR,PULM-BLOB,;;;'),
    ('NEU',  'n', 'legacy_note_neuro',      '55', 'NIELSEN,NEU-BLOB,tab	here');

COMMIT;

-- Requires psql -v abs_csv=/absolute/path/patients_import.csv (file must be readable by PostgreSQL server for COPY).
CALL proc_load_patients_from_csv(:'abs_csv');

CALL proc_transform_and_summarize();

-- Quick verification (prints to stdout when run with psql -f)
SELECT 'raw_patient_staging' AS section, count(*) AS row_count FROM raw_patient_staging
UNION ALL
SELECT 'patient_care_summary (MV)', count(*) FROM patient_care_summary
UNION ALL
SELECT 'departments', count(*) FROM departments
UNION ALL
SELECT 'x_tbl_ptnt_d (legacy)', count(*) FROM x_tbl_ptnt_d;

SELECT patient_id, full_name, dept_name, approx_age_at_admission_years, legacy_blob_field2
FROM patient_care_summary
ORDER BY patient_id
LIMIT 5;
