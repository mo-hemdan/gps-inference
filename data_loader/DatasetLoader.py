# %%
import pandas as pd
import geopandas as gpd
import psycopg2
from io import StringIO
from tqdm import tqdm

class DatasetLoader: # responsible for handling the parsing or GPS trajectories and uploading to our DB
    def __init__(self):
        pass
    
    def read_data(self, filename, format):
        if format == 'parquet': # that includes both folder and files both
            df = pd.read_parquet(filename)
        elif format == 'csv':
            df = pd.read_csv(filename)
        else:
            raise NotImplementedError(f'format not implemented')
        
        return df
    
    def adjust_format(self, df, colnames, config):
        df.rename(columns={colnames[k]:k for k in colnames}, inplace=True)
        df = df.sort_values(['traj_id', 'timestamp'])
        df['dataset'] = config['dataset']

        if config['crs'] != 'EPSG:4326':
            raise NotImplementedError('only EPSG:4326 is supported now')

        return df
    
    def create_gdf(self, df):
        geom = gpd.points_from_xy(df['lng'], df['lat']),
        # df must have columns: 'lng' and 'lat'
        gdf = gpd.GeoDataFrame(
            df,
            geometry= geom[0],
            crs="EPSG:4326"     # WGS84 lat/lon
        )
        gdf.drop(columns=['lng', 'lat'], inplace=True)

        return gdf
    
    def prepare_for_postgis(self, gdf, time_unit='s', utc=True):
        gdf['order_id'] = gdf.groupby('traj_id').cumcount()
        gdf['timestamp'] = pd.to_datetime(gdf['timestamp'], unit=time_unit, utc=utc)
        gdf['processed'] = False
        gdf.reset_index(drop=True, inplace=True)
        return gdf
    
    def sql(self, v):
        return "\\N" if v is None else str(v)

    def copy_geodataframe_in_batches(self, gdf, table_name, conn, batch_size=10_000):
        """
        COPY GeoDataFrame to PostGIS in batches using psycopg2.
        Very efficient for millions of rows.
        """
        cur = conn.cursor()

        # columns except geometry
        non_geom_cols = [c for c in gdf.columns if c != "geometry"]
        columns = non_geom_cols + ["geometry"]

        total = len(gdf)
        print(f"Total rows: {total}")


        for start in tqdm(range(0, total, batch_size), desc="Sending batches"):
            end = min(start + batch_size, total)
            chunk = gdf.iloc[start:end]

            buffer = StringIO()

            # write batch rows
            for _, row in chunk.iterrows():
                geom = row.geometry
                if geom is None:
                    geom_wkt = "\\N"
                else:
                    geom_wkt = f"{geom.wkt}"

                values = [self.sql(row[c]) for c in non_geom_cols] + [geom_wkt]
                buffer.write("\t".join(values) + "\n")
            buffer.seek(0)


            buffer.seek(0)

            # print(f"COPY {start:,} → {end:,} ...")

            cur.copy_from(
                buffer,
                table_name,
                sep="\t",
                null="\\N",
                columns=columns
            )

            conn.commit()

        cur.close()
        print("Done!")

    def connect_to_postgis(self): #, host, dbname, user, password, port=5432):
        conn = psycopg2.connect(
            host='cs-u-spatial-406.cs.umn.edu',
            dbname='gis',
            user='gis',
            password='gis',
            port=5432
        )
        return conn
    
    def load_dataset_to_postgis(self, filepath, file_type, colnames, conf, batch_size=10_000):
        print(f'Reading dataset from {filepath} of type {file_type}')
        df = self.read_data(filepath, file_type)
        print(f'Adjusting format')
        df = self.adjust_format(df, colnames, conf)
        print(f'Creating GeoDataFrame')
        gdf = self.create_gdf(df)
        print(f'Preparing for PostGIS')
        gdf = self.prepare_for_postgis(gdf)
        print(f'Connecting to PostGIS')
        conn = self.connect_to_postgis()
        print(f'Copying GeoDataFrame in batches')
        self.copy_geodataframe_in_batches(gdf, "gps_points", conn, batch_size=batch_size)
        print(f'Loading Completed Successfully!')