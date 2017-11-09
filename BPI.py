###############################################################################
# Description:
#  Creates several rasters of bathymetric derivatives:
#    1) Benthic Position index (BPI) fine and broad scale
#    2) Hillshade, Slope and Aspect
#    3) Classified bottom features using 1) and 2) and classification table
#    4) Terrain ruggedness, using the vector ruggedness measure (VRM)
#
# Authors: Jessica Nephin
# Affiliation:  Fisheries and Oceans Canada (DFO)
# Group:        Marine Spatial Ecology and Analysis
# Location:     Institute of Ocean Sciences
# Contact:      e-mail: jessica.nephin@dfo-mpo.gc.ca | tel: 250.363.6564
#
# Requirements: Spatial Analyst, utils.py, config.py and BPI_functions.py
#
# Instructions:
# 1) To run BPI.py without modification your files must be in the following
#    directory structure:
#      /<parent_folder>
#                     ----/Scripts
#                                 ---utils.py
#                                 ---config.py
#                                 ---BPI_functions.py
#                                 ---BPI.py
#                     ----/Bathy
#                                 ---<name_of_bathymetry_rater>.tif
#                     ---/Classify
#                                 ---<name_of_classify_table>.csv
# 2) <name_of_bathymetry_rater> must be of the format 'basename_res.tif'
# 3) Set 'basename' and 'res' variables in Global options line 32
# 4) Run in python window from /Scripts working directory
#
# Acknowledgements:
#    Based off scripts in the Benthic Terrain Modeler (BTM) 3.0 for ArcGIS
#    authored by Dawn J. Wright, Emily R. Lundblad, Emily M. Larkin, Ronald
#    W. Rinehart, Shaun Walbridge, Emily C. Huntley
#
# References:
#    Sappington et al., 2007. Quantifying Landscape Ruggedness for
#        Animal Habitat Analysis: A Case Study Using Bighorn Sheep in the
#        Mojave Desert. Journal of Wildlife Management. 71(5): 1419-1426.
#    Weiss, A. (2001). Topographic position and landforms analysis. Poster
#        Presentation, ESRI User Conference, San Diego, CA, 64, 227-245.
#        www.jennessent.com/downloads/TPI-poster-TNC_18x22.pdf
###############################################################################
# modules
from __future__ import absolute_import
import os
import sys
import math
import utils
import config
import arcpy
from arcpy.sa import *
from BPI_functions import *

# Global options to edit
basename = "SoG"
res = "5m"
classifytable = "bathy_classification1"

# move up one directory
os.chdir('..')

# Check out any necessary licenses
arcpy.CheckOutExtension("Spatial")

# Create output directories
if not os.path.exists(os.getcwd()+'/Tmp'):
    os.makedirs(os.getcwd()+'/Tmp')
if not os.path.exists(os.getcwd()+'/Derivatives'):
    os.makedirs(os.getcwd()+'/Derivatives')

# Workspace
arcpy.env.workspace = os.getcwd()
arcpy.env.scratchWorkspace = os.getcwd()+'/Tmp'

# Settings
arcpy.env.compression = "LZW"
arcpy.env.rasterStatistics = "STATISTICS"
arcpy.env.addOutputsToMap = 0
arcpy.env.overwriteOutput = True

# Filenames
bathy = os.getcwd()+'/Bathy/'+basename+'_'+res+'.tif'
fine_bpi = os.getcwd()+'/Derivatives/'+basename+'_BPI_fine_'+res+'.tif'
fine_std = os.getcwd()+'/Derivatives/'+basename+'_stdBPI_fine_'+res+'.tif'
broad_bpi = os.getcwd()+'/Derivatives/'+basename+'_BPI_broad_'+res+'.tif'
broad_std = os.getcwd()+'/Derivatives/'+basename+'_stdBPI_broad_'+res+'.tif'
hillshade_raster = os.getcwd()+'/Derivatives/'+basename+'_Hillshade_'+res+'.tif'
slope_raster = os.getcwd()+'/Derivatives/'+basename+'_Slope_'+res+'.tif'
aspect_raster = os.getcwd()+'/Derivatives/'+basename+'_Aspect_'+res+'.tif'
rug_raster = os.getcwd()+'/Derivatives/'+basename+'_Ruggedness_'+res+'.tif'
classification_dict = os.getcwd()+'/Classify/'+classifytable+'.csv'
classified_raster = os.getcwd()+'/Classify/'+ basename+'_'+'Classified_bpi_'+res+'.tif'

#------------------------------------------------------------------------------#

# ## Calculate broad BPI ##
# bpi_type = 'broad'
# inner_radius = 200
# outer_radius = 500
# # run
# bpi(bathy=bathy,
#     inner_radius=inner_radius,
#     outer_radius=outer_radius,
#     out_raster=broad_bpi,
#     bpi_type=bpi_type)
# stdbpi(bpi_raster=broad_bpi,
#        out_raster=broad_std)
#
# ## Calculate fine BPI ##
# bpi_type = 'fine'
# inner_radius = 5
# outer_radius = 200
# # run
# bpi(bathy=bathy,
#     inner_radius=inner_radius,
#     outer_radius=outer_radius,
#     out_raster=fine_bpi,
#     bpi_type=bpi_type)
# stdbpi(bpi_raster=fine_bpi,
#        out_raster=fine_std)
#
# ## Calculate Hillshade ##
# outHillshade = Hillshade(bathy, 180, 45, "NO_SHADOWS", 1)
# arcpy.CopyRaster_management(outHillshade, hillshade_raster)
#
# ## Calculate Slope ##
# outSlope = Slope(bathy, "DEGREE", 1)
# arcpy.CopyRaster_management(outSlope, slope_raster)
#
# ## Calculate Aspect ##
# outAspect = Aspect(bathy)
# arcpy.CopyRaster_management(outAspect, aspect_raster)

## Calculate Terrain Ruggedness ##
terrug(in_raster=bathy,
       neighborhood_size=15,
       out_raster=rug_raster,
       slope_raster=Raster(slope_raster),
       aspect_raster=Raster(aspect_raster))

# ## Zone Classification Builder ##
# classifyBPI(classification_file=classification_dict,
#               bpi_broad_std=broad_std,
#               bpi_fine_std=fine_std,
#               slope=slope_raster,
#               bathy=bathy,
#               out_raster=classified_raster)
