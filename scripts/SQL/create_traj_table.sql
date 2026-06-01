CREATE TABLE road_attributes (
    osm_id BIGINT PRIMARY KEY,
	-- 7 attributes for now
    oneway INT, -- 0 (two way), 1 (one-way), 2 (one-way the other way)
	road_type INT, -- 0 (residential), 1 ()
	width FLOAT, -- () meters
	nlanes INT, -- values > 0
	max_speed FLOAT, -- speed measured in km/h
	min_speed FLOAT, -- speed measured in km/h
	-- parking INT, -- 0 no parking, 1 drop in/off, 2 parking
	-- 672 attributes for now
	avg_speed NUMERIC[] DEFAULT array_fill(NULL::numeric, ARRAY[672]), -- speed measured in km/h
	
	-- source of attributes
	 -- 0 OSM, 1 gpsTraj, 2 OD, 3 IntraLearn, 4 InterLearn
    oneway_source INT,
	road_type_source INT,
	width_source INT,
	nlanes_source INT,
	max_speed_source INT,
	min_speed_source INT,
	-- parking_source INT,
	avg_speed_source INT[] DEFAULT array_fill(NULL::numeric, ARRAY[672]),

	-- confidence of attributes
	-- Range (0 -> 1)
    oneway_conf FLOAT,
	road_type_conf FLOAT,
	width_conf FLOAT,
	nlanes_conf FLOAT,
	max_speed_conf FLOAT,
	min_speed_conf FLOAT,
	-- parking_conf FLOAT,
	avg_speed_conf FLOAT[] DEFAULT array_fill(NULL::numeric, ARRAY[672]), 
	
    geometry GEOMETRY(LineString, 4326) NOT NULL
);

CREATE TABLE gps_points (
    id SERIAL PRIMARY KEY,
    dataset INT,
    traj_id INT,
    order_id INT,
    "timestamp" TIMESTAMP,
    speed DOUBLE PRECISION,
    angle DOUBLE PRECISION,
    accuracy DOUBLE PRECISION,
    processed BOOLEAN DEFAULT FALSE,
    matched_road_osm_id BIGINT,
    geom geometry(Point, 4326) NOT NULL
);

-- creating index on the road attributes table
CREATE INDEX idx_road_attributes_geom
ON road_attributes
USING GIST (geometry);

-- creating index on the road attributes table
CREATE INDEX idx_gps_points_geom
ON gps_points
USING GIST (geometry);
