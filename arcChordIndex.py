###############################################################################
# Description:
#    Create a bathymetric position index (BPI) raster, which
#    measures the average value in a 'donut' of locations, excluding
#    cells too close to the origin point, and outside a set distance.
# Requirements: Spatial Analyst
# Authors: Jessica Nephin
# Affiliation:  Fisheries and Oceans Canada (DFO)
# Group:        Marine Spatial Ecology and Analysis
# Location:     Institute of Ocean Sciences
# Contact:      e-mail: jessica.nephin@dfo-mpo.gc.ca | tel: 250.363.6564
# Acknowledgements:
#    Method developed by Cherisse Du Preez.
#    Based on function from the Benthic Terrain Modelling (BTM).
# References:
#   Du Preez, C. Landscape Ecol (2015) 30: 181.
#         https://doi.org/10.1007/s10980-014-0118-8
###############################################################################

# modules
from __future__ import absolute_import
from __future__ import unicode_literals
import arcpy
from arcpy.sa import *
import sys
import os
import numpy as np
import utils
import tempdir

# move up one directory
os.chdir('..')

# Global options
res = "100m"
basename = "SOG"

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

# Check out any necessary licenses
arcpy.CheckOutExtension("Spatial")
arcpy.CheckOutExtension("3D")
arcpy.CheckOutExtension("GeoStats")

# Filenames
bathy = os.getcwd()+'/Bathy/'+basename+'_'+res+'.tif'
elevationTIN = os.getcwd()+'/Tmp/'+basename+'_'+res+'_elevationTIN'
rasterDomain = os.getcwd()+'/Tmp/'+basename+'_'+res+'_rugIndex.shp'
boundaryBuffer = os.getcwd()+'/Tmp/'+basename+'_'+res+'_bnd_buf.shp'
boundaryRaster = os.getcwd()+'/Tmp/'+basename+'_'+res+'_bnd_rast.tif'
boundaryPoints = os.getcwd()+'/Tmp/'+basename+'_'+res+'_bnd_pts.shp'
pobfRaster = os.getcwd()+'/Tmp/'+basename+'_'+res+'_pobf_rast.tif'
pobf_temp = os.getcwd()+'/Tmp/'+basename+'_'+res+'_pobf_tmp.tif'

# Arc Chord Rugosity function
def ARCrug(in_raster=None):

# Bathymetry raster cell size
bathyRaster = Raster(in_raster)
cellSize = bathyRaster.meanCellHeight

# Create TIN
utils.raster_properties(bathyRaster, attribute=None)
zTolerance = abs((bathyRaster.maximum - bathyRaster.minimum)/10)
arcpy.RasterTin_3d(bathyRaster, elevationTIN, str(zTolerance))
arcpy.EditTin_3d(elevationTIN, ["#", "<None>", "<None>",
                                "hardclip", "false"])

# Get raster domain
arcpy.RasterDomain_3d(bathyRaster, rasterDomain, "POLYGON")

# Create planar TIN
arcpy.Buffer_analysis(rasterDomain, boundaryBuffer, cellSize, "OUTSIDE_ONLY")
arcpy.Clip_management(in_raster, '#', boundaryRaster, boundaryBuffer, '#',
                      'ClippingGeometry', 'NO_MAINTAIN_EXTENT')
arcpy.RasterToPoint_conversion(boundaryRaster, boundaryPoints, 'Value')
arcpy.GlobalPolynomialInterpolation_ga(boundaryPoints, "grid_code",
                                       "#", pobfRaster, cellSize)
arcpy.CalculateStatistics_management(pobfRaster)
zTolerance = abs((int(Raster(pobfRaster).maximum) -
                  int(Raster(pobfRaster).minimum))/10)
arcpy.RasterTin_3d(pobfRaster, pobf_temp, str(zTolerance))
arcpy.EditTin_3d(pobf_temp, ["#", "<None>", "<None>",
                             "hardclip", "false"])

# Calculate Rugosity
arcpy.PolygonVolume_3d(elevationTIN, rasterDomain, "<None>",
                       "BELOW", "Volume1", "Surf_Area")
arcpy.PolygonVolume_3d(pobf_temp, rasterDomain, "<None>",
                       "BELOW", "Volume2", "Plan_Area")
arcpy.AddField_management(rasterDomain, "Rugosity", "DOUBLE")
arcpy.CalculateField_management(rasterDomain, "Rugosity",
                                "!Surf_Area! / !Plan_Area!",
                                "PYTHON_9.3")
arcpy.DeleteField_management(rasterDomain, "Volume2;Volume1")
