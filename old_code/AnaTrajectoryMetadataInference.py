'''
Metadata Inference from Trajectories (Ana's Implementation)
 
CREATED BY Ana Uribe
EDITED AND REFACTORED BY Mohamed Hemdan
'''

############### IMPORTS ##################
import json
import os
import pandas as pd
import osmnx as ox
import ast

from functions.get_trajectory_metadata_functions import get_compass_dir, get_day, get_day_type, get_time_type
from functions.get_map_matching_functions import get_graph_from_bb, assign_edges_nodes, compute_OSM_edge_vals, compute_OSM_node_vals
from functions.get_trajectory_segment_data_functions import get_trip_segment_metadata
from functions.get_map_metadata_functions import get_edge_metadata, get_node_metadata
from functions.utils import load_constants

# CONSTANTS_PATH = 'data/constants.json'

class AnaTrajectoryMetadataInference():
    
    def __init__(self, constants=None, constants_path=None):
        """
        Initializes the DataProcessor with a data source and batch size.

        Args:
            constants (dict): dictionary of all variables
        """
        self.df = None
        self.osm_n_df = None
        self.osm_e_df = None
        self.e_df = None 
        self.n_df = None
        self.e_s_df = None
        self.n_s_df = None
        self.e_f_df = None
        self.n_f_df = None
        self.G = None
        
        if not constants:
            if not constants_path:
                raise ValueError("Not constants path provided at least")
            with open(constants_path) as j_file:
                constants = json.load(j_file)  
        load_constants(self, constants)

    def set_dataset(self, filename=None, extention='parquet'):
        if filename: 
            if extention == 'parquet':
                self.df = pd.read_parquet(filename)
            elif extention == 'csv':
                self.df = pd.read_csv(filename, index_col=0)
        else: self.df = pd.read_csv(os.path.join(self.INPUT_DIR, self.INPUT_FILENAME))

    def add_metadata_columns(self):
        if self.df is None:
            raise ValueError("Not Dataset found. Make sure to set_dataset")
        
        # if needed, generate speed and heading columns
        if self.SPEED_BOOL == 0: 
            print('Calculating speed')
            # raise NotImplementedError('Calculating Speed not implemented!')
        if self.HEADING_BOOL == 0: 
            print('Calculating heading')
            # raise NotImplementedError('Calculating heading not implemented!')

        # generate compass directions, day type, time type columns
        self.df[self.CAMPASS_COLNAME] = self.df[self.HEADING_COLNAME].apply(get_compass_dir)
        self.df[self.DAY_COLNAME] = self.df[self.TIMESTAMP_COLNAME].apply(get_day)
        self.df[self.DAY_TYPE_COLNAME] = self.df[self.TIMESTAMP_COLNAME].apply(get_day_type)
        self.df[self.TIME_TYPE_COLNAME] = self.df[self.TIMESTAMP_COLNAME].apply(get_time_type)

        # generate time bin column
        self.df[self.TIME_BIN_COLNAME] = self.df[self.DAY_TYPE_COLNAME] + self.df[self.TIME_TYPE_COLNAME]
    
    def map_matching(self, save=False):
        if self.df is None:
            raise ValueError("Not Dataset found. Make sure to set_dataset()")
        if self.TIME_BIN_COLNAME not in self.df.columns:
            raise ValueError("Dataset columns are not prepared. Make sure to add_metadata_columns()")
        
        # grab latitude/longitude columns
        lat_col = self.df[self.LAT_COLNAME]
        long_col = self.df[self.LON_COLNAME]

        # get osmnx graph segment that corresponds
        print('Getting Graph from bounding box')
        self.G = get_graph_from_bb(lat_col, long_col, network_type=self.NETWORK_TYPE, verbose=True)

        # get edges, nodes for each point
        e, n, edges_vectors, unique_n, unique_n_dict = assign_edges_nodes(self.G, lat_col, long_col)
        print('Finished getting edge and node information')

        # get the OSM node and edge features you want for each edge
        nodes, edges = ox.graph_to_gdfs(self.G)

        self.osm_n_df = pd.DataFrame(unique_n, columns=['Node']).dropna(subset=['Node'])
        self.osm_e_df = pd.DataFrame(edges_vectors, columns=['Edge', 'Vector']).dropna(subset=['Edge'])

        print('Starting to get the OSM node values for each edge and node')
        self.osm_n_df[self.OSM_NODE_NEW_COLNAMES] = self.osm_n_df['Node'].apply(lambda x: pd.Series(compute_OSM_node_vals(x, self.OSM_NODE_COLNAMES, nodes, unique_n_dict)))
        self.osm_e_df[self.OSM_EDGE_NEW_COLNAMES] = self.osm_e_df['Edge'].apply(lambda x: pd.Series(compute_OSM_edge_vals(x, self.OSM_EDGE_COLNAMES, edges)))

        self.osm_n_df['Node'] = self.osm_n_df['Node'].astype(int)

        # add edges, nodes to df
        self.df[self.EDGE_COLNAME] = e
        self.df[self.NODE_COLNAME] = n

        # save df to processed data
        if save:
            print("Saving the dataframe")
            self.df.to_csv(os.path.join(self.PROCESS_DIR, self.MAPMATCHING_OUT_FILENAME), index=False)
            self.osm_n_df.to_csv(os.path.join(self.PROCESS_DIR, self.OSM_NODE_INFOFILE), index=False)
            self.osm_e_df.to_csv(os.path.join(self.PROCESS_DIR, self.OSM_EDGE_INFOFILE), index=False)
    
    def extract_trajectory_segment_data(self, load=False, save=False):
        print('Extracting the trajectory segement data')
        if load:
            print("Reading file")
            self.df = pd.read_csv(os.path.join(self.PROCESS_DIR, self.MAPMATCHING_OUT_FILENAME))
            self.osm_e_df = pd.read_csv(os.path.join(self.PROCESS_DIR, self.OSM_EDGE_INFOFILE))
        else:
            if self.df is None:
                raise ValueError("Not Dataset found. Make sure to set_dataset()")
            if self.TIME_BIN_COLNAME not in self.df.columns:
                raise ValueError("Dataset columns are not prepared. Make sure to add_metadata_columns()")
            if self.osm_e_df is None:
                raise ValueError("Some Matching information are missing. Make sure to do map_matching()")

        ########################################## MAIN ##########################################
        # get edge/node dataframes with trip segment metadata
        print('get trip segement metadata')
        self.e_df, self.n_df = get_trip_segment_metadata(self.df, self.TRIP_ID, self.NODE_COLNAME, self.EDGE_COLNAME, self.AVGSPEED_COLNAME, self.MAXSPEED_COLNAME, self.MINSPEED_COLNAME, self.CAMPASS_COLNAME, self.DAY_TYPE_COLNAME, self.TIME_TYPE_COLNAME, self.TRAVEL_TIME_COLNAME, self.osm_e_df, self.TIME_BIN_COLNAME, self.SPEED_COLNAME, self.TIMESTAMP_COLNAME, self.LAT_COLNAME, self.LON_COLNAME)
        
        # save edge and node dataframes to csv
        if save:
            print('saving to csv')
            self.e_df.to_csv(os.path.join(self.PROCESS_DIR, self.EDGE_DF_NAME), index=False)
            self.n_df.to_csv(os.path.join(self.PROCESS_DIR, self.NODE_DF_NAME), index=False)
        
    def intermediate_extract_map_metadata(self, load=False, save=False):
        print('intermediate extract map metadata')
        if load:
            self.e_df = pd.read_csv(os.path.join(self.PROCESS_DIR, self.EDGE_DF_NAME))
            self.n_df = pd.read_csv(os.path.join(self.PROCESS_DIR, self.NODE_DF_NAME))

            self.osm_n_df = pd.read_csv(os.path.join(self.PROCESS_DIR, self.OSM_NODE_INFOFILE))
            self.osm_e_df = pd.read_csv(os.path.join(self.PROCESS_DIR, self.OSM_EDGE_INFOFILE))
        self.osm_e_df = self.osm_e_df[['Edge','OSM_oneway','OSM_lanes','OSM_name','OSM_highway','OSM_maxspeed','OSM_length']]# don't need to save vector
        ########################################## HELPER FUNCTIONS ##########################################
        # get the edge/node functional and structural metadata 
        print('get edge metadata')
        self.e_s_df, self.e_f_df = get_edge_metadata(self.e_df, self.EDGE_COLNAME, self.TIME_BIN_COLNAME, self.AVGSPEED_COLNAME, self.AVGSPEED_CI_COLNAME, self.MAXSPEED_COLNAME, self.MINSPEED_COLNAME, self.TRAVEL_TIME_COLNAME, self.TRAVEL_TIME_CI_COLNAME, self.FLOW_COLNAME, self.TRAJ_COUNT_COLNAME, self.osm_e_df)
        print('get node metadata')
        self.n_s_df, self.n_f_df = get_node_metadata(self.n_df, self.NODE_COLNAME, self.TIME_BIN_COLNAME, self.AVGSPEED_COLNAME, self.AVGSPEED_CI_COLNAME, self.MAXSPEED_COLNAME, self.MINSPEED_COLNAME, self.TRAVEL_TIME_COLNAME, self.TRAVEL_TIME_CI_COLNAME, self.FLOW_COLNAME, self.TRAJ_COUNT_COLNAME, self.osm_n_df)            

        self.e_s_df['osmid'] = self.e_s_df.apply(lambda row: self.add_osmid(row), axis=1)
        self.e_f_df['osmid'] = self.e_f_df.apply(lambda row: self.add_osmid(row), axis=1)

        # # save all four dataframes to csv
        if save:
            print('saving to csv')
            self.e_s_df.to_csv(os.path.join(self.OUT_DIR, self.EDGE_STATIC_METADATA_OUT_FILENAME), index=False)
            self.e_f_df.to_csv(os.path.join(self.OUT_DIR, self.EDGE_FUNCTIONAL_METADATA_OUT_FILENAME), index=False)
            self.n_s_df.to_csv(os.path.join(self.OUT_DIR, self.NODE_STATIC_METADATA_OUT_FILENAME), index=False)
            self.n_f_df.to_csv(os.path.join(self.OUT_DIR, self.NODE_FUNCTIONAL_METADATA_OUT_FILENAME), index=False)
        
        return self.EDGE_FUNCTIONAL_METADATA_OUT_FILENAME

    def get_metadata(self):
        if self.e_f_df is not None:
            return self.e_s_df, self.e_f_df, self.n_s_df, self.e_f_df
        else: raise ValueError("Previous steps are not executed")
        
    def add_osmid(self, row):
        i = row['Edge']
        t = ast.literal_eval(i)
        return self.G[t[0]][t[1]][t[2]]['osmid']

    def extract_metadata(self, save=True):
        # TODO: Somehow there is a problem with using the internal dataframe. There is an issue with saving and loading
        #       Need to be inspected later
        # TODO: We need to delete the usage of self.df since we don't want to store the data. Instead, we want to pass
        # it between functions. However, we need to adjust the first problem first for this to work
        self.add_metadata_columns()
        self.map_matching(save=True)
        self.extract_trajectory_segment_data(load=True, save=True)
        self.intermediate_extract_map_metadata(load=True, save=save)
        return self.EDGE_FUNCTIONAL_METADATA_OUT_FILENAME
    
