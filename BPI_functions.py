###############################################################################
# Description:
#    Functions to create a bathymetric position index (BPI) raster, which
#    measures the average value in a 'donut' of locations, excluding
#    cells too close to the origin point, and outside a set distance, and
#    a terrain ruggedness raster, using the vector ruggedness measure (VRM).
#
# Requirements: Spatial Analyst
#
# Authors: Jessica Nephin (previous contributers listed in Acknowledgements)
# Affiliation:  Fisheries and Oceans Canada (DFO)
# Group:        Marine Spatial Ecology and Analysis
# Location:     Institute of Ocean Sciences
# Contact:      e-mail: jessica.nephin@dfo-mpo.gc.ca | tel: 250.363.6564
#
# Acknowledgements:
#    Based off scripts in the Benthic Terrain Modeler (BTM) 3.0 for ArcGIS
#    authored by Dawn J. Wright, Emily R. Lundblad, Emily M. Larkin, Ronald
#    W. Rinehart, Shaun Walbridge, Emily C. Huntley
#
# References:
#    Sappington et al., 2007. Quantifying Landscape Ruggedness for
#        Animal Habitat Analysis: A Case Study Using Bighorn Sheep in the
#        Mojave Desert. Journal of Wildlife Management. 71(5): 1419 -1426.
#    Weiss, A. (2001). Topographic position and landforms analysis. Poster
#        Presentation, ESRI User Conference, San Diego, CA, 64, 227–245.
#        https://doi.org/http://www.jennessent.com/downloads/TPI-poster-TNC_18x22.pdf
###############################################################################

# Import system modules
from __future__ import absolute_import
import os
import sys
import math
import utils
import config
import arcpy
from arcpy.sa import *

# BPI
def bpi(bathy=None, inner_radius=None, outer_radius=None,
         out_raster=None, bpi_type=None):

    # Calculate neighborhood
    neighborhood = NbrAnnulus(inner_radius, outer_radius, "CELL")

    #Calculate Focal Statistics
    out_focal_statistics = FocalStatistics(bathy, neighborhood, "MEAN")
    result_raster = Int(Plus(Minus(bathy, out_focal_statistics), 0.5))

    # Save output raster
    out_raster_path = utils.validate_path(out_raster)
    arcpy.CopyRaster_management(result_raster, out_raster_path)

# Standardizing BPI
def stdbpi(bpi_raster=None, out_raster=None):

    # Convert to a path
    desc = arcpy.Describe(bpi_raster)
    bpi_raster_path = desc.catalogPath

    # Calculate mean and stdev
    bpi_mean = utils.raster_properties(bpi_raster_path, "MEAN")
    bpi_std_dev = utils.raster_properties(bpi_raster_path, "STD")

    # Create the standardized raster
    arcpy.env.rasterStatistics = "STATISTICS"
    outRaster = Int(Plus(Times(Divide(
        Minus(bpi_raster_path, bpi_mean), bpi_std_dev), 100), 0.5))
    out_raster = utils.validate_path(out_raster)
    arcpy.CopyRaster_management(outRaster, out_raster)


# Conditionally evaluate raster range within bounds
def run_con(lower_bounds, upper_bounds, in_grid, true_val, true_alt=None):
    "Conditionally evaluate raster range within bounds."""

    if config.debug:
        utils.msg("run_con: lb: {} ub: {} grid: {}  val: {}, alt: {}".format(
            lower_bounds, upper_bounds, in_grid, true_val, true_alt))

    out_grid = None

    # if our initial desired output value isn't set, use the backup
    if true_val is None:
        true_val = true_alt
    # calculate our output grid
    if lower_bounds is not None:
        if upper_bounds is not None:
            out_grid_a = Con(
                in_grid, true_val, 0, "VALUE < {}".format(upper_bounds))
            out_grid = Con(
                in_grid, out_grid_a, 0, "VALUE > {}".format(lower_bounds))
        else:
            out_grid = Con(
                in_grid, true_val, 0, "VALUE >= {}".format(lower_bounds))
    elif upper_bounds is not None:
        out_grid = Con(
            in_grid, true_val, 0, "VALUE <= {}".format(upper_bounds))

    if type(out_grid).__name__ == 'NoneType' and \
       type(true_val) == arcpy.sa.Raster:
        out_grid = true_val

    return out_grid

# Perform raster classification, based on classification file and BPI rasters
class NoValidClasses(Exception):
    def __init__(self):
        Exception.__init__(self, "No valid output classes found")

def classifyBPI(classification_file, bpi_broad_std, bpi_fine_std,
                slope, bathy, out_raster=None):

    # Allow overwriteOutput
    arcpy.env.overwriteOutput = True

    # Read in the classification file
    btm_doc = utils.BtmDocument(classification_file)
    classes = btm_doc.classification()

    # loop through classes
    grids = []
    key = {'0': 'None'}
    for item in classes:
        cur_class = str(item["Class"])
        cur_name = str(item["Zone"])
        utils.msg("Calculating grid for {}...".format(cur_name))
        key[cur_class] = cur_name
        out_con = None
        # Conditional statements:
        out_con = run_con(item["Depth_LowerBounds"],
                          item["Depth_UpperBounds"],
                          bathy, cur_class)
        out_con2 = run_con(item["Slope_LowerBounds"],
                           item["Slope_UpperBounds"],
                           slope, out_con, cur_class)
        out_con3 = run_con(item["LSB_LowerBounds"],
                           item["LSB_UpperBounds"],
                           bpi_fine_std, out_con2, cur_class)
        out_con4 = run_con(item["SSB_LowerBounds"],
                           item["SSB_UpperBounds"],
                           bpi_broad_std, out_con3, cur_class)

        if type(out_con4) == arcpy.sa.Raster:
            rast = utils.save_raster(out_con4, "con_{}.tif".format(cur_name))
            grids.append(rast)
        else:
            # fall-through: no valid values detected for this class.
            warn_msg = ("WARNING, no valid locations found for class"
                        " {}:\n".format(cur_name))
            classifications = {
                'depth': (item["Depth_LowerBounds"], item["Depth_UpperBounds"]),
                'slope': (item["Slope_LowerBounds"], item["Slope_UpperBounds"]),
                'broad': (item["SSB_LowerBounds"], item["SSB_UpperBounds"]),
                'fine': (item["LSB_LowerBounds"], item["LSB_UpperBounds"])
            }
            for (name, vrange) in classifications.items():
                (vmin, vmax) = vrange
                if vmin or vmax is not None:
                    if vmin is None:
                        vmin = ""
                    if vmax is None:
                        vmax = ""
                    warn_msg += "  {}: {{{}:{}}}\n".format(name, vmin, vmax)

    if len(grids) == 0:
        raise NoValidClasses

    #Creating Benthic Terrain Classification Dataset
    merge_grid = grids[0]
    for i in range(1, len(grids)):
        merge_grid = Con(merge_grid, grids[i], merge_grid, "VALUE = 0")
    arcpy.CopyRaster_management(merge_grid, out_raster)
    arcpy.AddField_management(out_raster, 'Zone', 'TEXT')
    arcpy.Delete_management(merge_grid)
    cursor = arcpy.UpdateCursor(out_raster)
    for row in cursor:
        val = str(row.getValue('VALUE'))
        if val in key:
            row.setValue('Zone', key[val])
            cursor.updateRow(row)
        else:
            row.setValue('Zone', 'No Matching Zone')
            cursor.updateRow(row)
    del(cursor)
    del(row)

# Terrain ruggedness function
def terrug(in_raster=None, neighborhood_size=None,
           out_raster=None, slope_raster=None, aspect_raster=None):

    # moving window size
    hood_size = int(neighborhood_size)

    # settings
    pyramid_orig = arcpy.env.pyramid
    arcpy.env.rasterStatistics = "STATISTICS"
    arcpy.env.pyramid = "NONE"
    arcpy.env.overwriteOutput = True
    arcpy.env.compression = 'LZW'

    # Convert Slope and Aspect rasters to radians
    slope_rad = slope_raster * (math.pi / 180)
    aspect_rad = aspect_raster * (math.pi / 180)

    # Calculate x, y, and z rasters
    xy_raster_calc = Sin(slope_rad)
    z_raster_calc = Cos(slope_rad)
    x_raster_calc = Con(aspect_raster == -1, 0, Sin(aspect_rad)) * xy_raster_calc
    y_raster_calc = Con(aspect_raster == -1, 0, Cos(aspect_rad)) * xy_raster_calc

    # Calculate sums of x, y, and z rasters for selected neighborhood size
    hood = NbrRectangle(hood_size, hood_size, "CELL")
    x_sum_calc = FocalStatistics(x_raster_calc, hood, "SUM", "NODATA")
    y_sum_calc = FocalStatistics(y_raster_calc, hood, "SUM", "NODATA")
    z_sum_calc = FocalStatistics(z_raster_calc, hood, "SUM", "NODATA")

    # Calculate the resultant vector
    result_vect = (x_sum_calc**2 + y_sum_calc**2 + z_sum_calc**2)**0.5

    # Calculate the Ruggedness raster
    ruggedness = 1 - (result_vect / hood_size**2)
    arcpy.CopyRaster_management(ruggedness, out_raster)
