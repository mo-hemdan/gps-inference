from data_loader.DatasetLoader import DatasetLoader

loader = DatasetLoader()

colnames = {
    'lng': 'rawlng',
    'lat': 'rawlat',
    'speed': 'speed',
    'angle': 'bearing',
    'accuracy': 'accuracy',
    'timestamp': 'pingtimestamp',
    'traj_id': 'trj_id',
    'driving_mode': 'driving_mode',
    'osname': 'osname'
}


conf = {
    'crs': 'EPSG:4326', # TODO: check this
    'dataset': 1
}

# 0 for Jakarta
# 1 for Singapore
# 2 GrabPosis 
# 3 

loader.load_dataset_to_postgis('./gps_data/city=Singapore', 'parquet', colnames, conf, batch_size=50_000)