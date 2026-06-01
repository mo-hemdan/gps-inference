# Metadata Inference

There is one implemented project until now which is Ana's Project. It's refactored and modularized.

If you want to use it, you can import it like this

```python
from modules.MetadataInference.AnaTrajectoryInference import AnaTrajectoryInference
```

and test it like this

```python
constants_path = 'data/constants.json'
data_filename = 'data/top_10_percentage.csv'

TrajInfer = AnaTrajectoryInference(constants_path=constants_path)
TrajInfer.set_dataset(data_filename)
output= TrajInfer.extract_metadata()
```



# Comments
- Currently the inference algorithm does take into consideration the edges even within the way itself so a way consists of edges. 
- For the current time being, we will assume the way is just the smallest unit and then we want go further, so we are going to group by an osmid and choose a representative value for it

- I Changed the simplify in the graph_from_bbox to be false since it misses up the osmids 
