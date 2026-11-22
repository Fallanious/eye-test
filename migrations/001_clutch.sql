ALTER TABLE clips ADD COLUMN IF NOT EXISTS is_clutch boolean GENERATED ALWAYS AS (
    period >= 4 AND game_clock BETWEEN interval '0 seconds' AND interval '5 minutes'
    AND abs((attributes->'pre_play_score'->>'away')::integer -
            (attributes->'pre_play_score'->>'home')::integer) <= 5
) STORED;
