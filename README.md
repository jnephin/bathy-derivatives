Description
-----------
Creates several rasters of bathymetric derivatives:
1. Benthic Position index (BPI) fine and broad scale    
2. Hillshade, Slope and Aspect
3. Classified bottom features using 1. and 2. and a classification table
4. Terrain ruggedness, using the vector ruggedness measure (VRM)

Contact
-------
Jessica Nephin    
Affiliation:  Fisheries and Oceans Canada (DFO)     
Group:        Marine Spatial Ecology and Analysis     
Location:     Institute of Ocean Sciences     
Contact:      e-mail: jessica.nephin@dfo-mpo.gc.ca | tel: 250.363.6564
 
Requirements
----------- 
Spatial Analyst, `utils.py`, `config.py` and `BPI_functions.py`

Instructions
------------
 1. To run `BPI.py` without modification your files must be in the following
    directory structure:
```
/<parent_folder>    
        /Scripts    
        |       ---`utils.py`    
        |       ---`config.py`    
        |       ---`BPI_functions.py`    
        |       ---`BPI.py`    
        /Bathy    
        |       ---<name_of_bathymetry_rater>.tif
        /Classify
                ---<name_of_classify_table>.csv
```
 2. <name_of_bathymetry_rater> must be of the format 'basename_res.tif'
 3. Set 'basename' and 'res' variables in Global options line 32
 4. Run in python window from /Scripts working directory

Acknowledgements
----------------
Based off scripts in the Benthic Terrain Modeler (BTM) 3.0 for ArcGIS authored by Dawn J. Wright, Emily R. Lundblad, Emily M. Larkin, Ronald W. Rinehart, Shaun Walbridge, Emily C. Huntley

References
----------
Sappington et al., 2007. Quantifying Landscape Ruggedness for Animal Habitat Analysis: A Case Study Using Bighorn Sheep in the Mojave Desert. Journal of Wildlife Management. 71(5): 1419 -1426.
    
Weiss, A. (2001). Topographic position and landforms analysis. Poster Presentation, ESRI User Conference, San Diego, CA, 64, 227–245. https://doi.org/http://www.jennessent.com/downloads/TPI-poster-TNC_18x22.pdf