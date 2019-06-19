CREATE OR REPLACE FUNCTION vector_bpm(jsonb) RETURNS DOUBLE PRECISION[]
LANGUAGE plpgsql IMMUTABLE
AS
$$
DECLARE temp double precision;
BEGIN
  temp := $1->'rhythm'->'bpm';
  temp := log(2.0, temp::numeric);
  RETURN ARRAY[cos(temp), sin(temp)];
END
$$;