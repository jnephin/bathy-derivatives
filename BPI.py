###############################################################################
# Description:
#  Creates several raster of bathymetric derivatives:
#    1) Benthic Position index (BPI)
#    2) Slope and Aspect
#    3) Classified bottom features using 1) and 2)
#    4) Terrain ruggedness, using the vector ruggedness measure (VRM)
# Requirements: Spatial Analyst, utils.py, config.py and BPI_functions.py
# Authors: Jessica Nephin
# Affiliation:  Fisheries and Oceans Canada (DFO)
# Group:        Marine Spatial Ecology and Analysis
# Location:     Institute of Ocean Sciences
# Contact:      e-mail: jessica.nephin@dfo-mpo.gc.ca | tel: 250.363.6564
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

# move up one directory
os.chdir('..')

# Global options
res = "5m"

# Check out any necessary licenses
arcpy.CheckOutExtension("Spatial")

# Workspace
arcpy.env.workspace = os.getcwd()
if not os.path.exists(os.getcwd()+'/Tmp'):
    os.makedirs(os.getcwd()+'/Tmp')
arcpy.env.scratchWorkspace = os.getcwd()+'/Tmp'

# Settings
arcpy.env.compression = "LZW"
arcpy.env.rasterStatistics = "STATISTICS"
arcpy.env.addOutputsToMap = 0
arcpy.env.overwriteOutput = True

# Filenames
bathy = os.getcwd()+'/Bathy/'+'SoG_'+res+'.tif'
fine_bpi = os.getcwd()+'/Derivatives/'+'SoG_BPI_fine_'+res+'.tif'
fine_std = os.getcwd()+'/Derivatives/'+'SoG_stdBPI_fine_'+res+'.tif'
broad_bpi = os.getcwd()+'/Derivatives/'+'SoG_BPI_broad_'+res+'.tif'
broad_std = os.getcwd()+'/Derivatives/'+'SoG_stdBPI_broad_'+res+'.tif'
slope_raster = os.getcwd()+'/Derivatives/'+'SoG_Slope_'+res+'.tif'
aspect_raster = os.getcwd()+'/Derivatives/'+'SoG_Aspect_'+res+'.tif'
rug_raster = os.getcwd()+'/Derivatives/'+'SoG_Ruggedness_'+res+'.tif'
classification_dict = os.getcwd()+'/Classify/'+ 'bathy_classification.csv'
classified_raster = os.getcwd()+'/Classify/'+ 'Classified_bpi_'+res+'.tif'


#------------------------------------------------------------------------------#

## Calculate broad BPI ##
bpi_type = 'broad'
inner_radius = 200
outer_radius = 500
# run
bpi(bathy=bathy,
    inner_radius=inner_radius,
    outer_radius=outer_radius,
    out_raster=broad_bpi,
    bpi_type=bpi_type)
stdbpi(bpi_raster=broad_bpi,
       out_raster=broad_std)

## Calculate fine BPI ##
bpi_type = 'fine'
inner_radius = 5
outer_radius = 200
# run
bpi(bathy=bathy,
    inner_radius=inner_radius,
    outer_radius=outer_radius,
    out_raster=fine_bpi,
    bpi_type=bpi_type)
stdbpi(bpi_raster=fine_bpi,
       out_raster=fine_std)

## Calculate Slope ##
outSlope = Slope(bathy, "DEGREE", 1)
arcpy.CopyRaster_management(outSlope, slope_raster)

## Calculate Aspect ##
outAspect = Aspect(bathy)
arcpy.CopyRaster_management(outAspect, aspect_raster)

## Calculate Terrain Ruggedness ##
terrug(in_raster=bathy,
       neighborhood_size=3,
       out_raster=rug_raster,
       slope_raster=outSlope,
       aspect_raster=outAspect)

## Zone Classification Builder ##
classifyBPI(classification_file=classification_dict,
              bpi_broad_std=broad_std,
              bpi_fine_std=fine_std,
              slope=slope_raster,
              bathy=bathy,
              out_raster=classified_raster)
