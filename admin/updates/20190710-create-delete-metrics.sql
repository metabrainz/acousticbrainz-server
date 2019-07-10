-- Adds a new row to similarity_metrics, containing metadata about a metric.
  INSERT INTO similarity_metrics (metric, is_hybrid, description, category, visible)
       VALUES (:metric, :hybrid, :description, :category, TRUE)
  ON CONFLICT (metric)
DO UPDATE SET visible=TRUE

-- Removes the metadata about a given metric.
DELETE FROM similarity_metrics
      WHERE metric = :metric

-- Adds metric column to similarity table, holding a vector for each recording.
  ALTER TABLE similarity
   ADD COLUMN
IF NOT EXISTS %s DOUBLE PRECISION[]
-- If clear, delete all existing rows.
DELETE FROM ONLY similarity

-- Removes a metric column.
ALTER TABLE similarity
DROP COLUMN
  IF EXISTS %s

-- Removes visibility of a metric in similarity_metrics table.
UPDATE similarity_metrics
   SET visible = FALSE
 WHERE metric = :metric