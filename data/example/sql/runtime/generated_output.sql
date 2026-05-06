CREATE VIEW a_b_join_view AS
SELECT
  A.*,
  B.*
FROM A
JOIN B
  ON A.user_id = B.user_id;