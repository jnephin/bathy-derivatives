###############################################################################
# Description:
#    Functions to create a bathymetric position index (BPI) raster, which
#    measures the average value in a 'donut' of locations, excluding
#    cells too close to the origin point, and outside a set distance.
# Requirements: Spatial Analyst
# Authors: Jessica Nephin
# Affiliation:  Fisheries and Oceans Canada (DFO)
# Group:        Marine Spatial Ecology and Analysis
# Location:     Institute of Ocean Sciences
# Contact:      e-mail: jessica.nephin@dfo-mpo.gc.ca | tel: 250.363.6564
# Acknowledgements:
#    Functions from the BTM package writen by
#    Dawn J. Wright, Emily R. Lundblad, Emily M. Larkin, Ronald W. Rinehart,
#    Shaun Walbridge, Emily C. Huntley
###############################################################################

# Import system modules
from __future__ import absolute_import
import os
import sys
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
