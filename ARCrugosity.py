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

# force all to str
if sys.version_info < (3, 0):
    str = unicode

# Settings
arcpy.env.overwriteOutput = True

# Check out any necessary licenses
arcpy.CheckOutExtension("Spatial")
arcpy.CheckOutExtension("3D")
arcpy.CheckOutExtension("GeoStats")

# Arc Chord Rugosity function
def ARCrug(in_raster=None, areaOfInterest=None, saveTINs=False,
         out_workspace=None):

    if isinstance(saveTINs, str) and saveTINs.lower() == 'false':
        saveTINs = False
    if isinstance(saveTINs, str) and saveTINs.lower() == 'true':
        saveTINs = True

    rastName = os.path.splitext(os.path.split(in_raster)[1])[0]
    bathyRaster = Raster(in_raster)
    cellSize = bathyRaster.meanCellHeight

    with TempDir() as d:
        # Check if multipart polygon and convert to singlepart if true
        with arcpy.da.SearchCursor(areaOfInterest, ["SHAPE@"]) as cursor:
            for row in cursor:
                geometry = row[0]
                if geometry.isMultipart is True:
                    utils.msg("Converting multipart geometry to single parts...")
                    singlepart = os.path.join(d, 'singlepart.shp')
                    arcpy.MultipartToSinglepart_management(areaOfInterest,
                                                           singlepart)
                    arcpy.CopyFeatures_management(singlepart, areaOfInterest)

        # Name temporary files
        elevationTIN = os.path.join(d, 'elevationTIN')
        boundaryBuffer = os.path.join(d, 'bnd_buf.shp')
        boundaryRaster = os.path.join(d, 'bnd_rast.tif')
        boundaryPoints = os.path.join(d, 'bnd_pts.shp')
        pobfRaster = os.path.join(d, 'pobf_rast.tif')

        # Create elevation TIN
        utils.msg("Creating elevation TIN...")
        # just compute statitics
        utils.raster_properties(bathyRaster, attribute=None)
        zTolerance = abs((bathyRaster.maximum - bathyRaster.minimum)/10)
        arcpy.RasterTin_3d(bathyRaster, elevationTIN, str(zTolerance))
        arcpy.EditTin_3d(elevationTIN, ["#", "<None>", "<None>",
                                        "hardclip", "false"])

        # If more than one polygon in areaOfInterest,
        # split into separate files to process
        splitFiles = [areaOfInterest]
        multiple = False
        aoi_count = int(arcpy.GetCount_management(areaOfInterest).getOutput(0))
        if aoi_count > 1:
            multiple = True
            arcpy.AddField_management(areaOfInterest, "zzzName", "TEXT")
            splitFiles = []
            with arcpy.da.UpdateCursor(areaOfInterest,
                                       "zzzName") as cursor:
                for (i, row) in enumerate(cursor):
                    row[0] = "poly_{}".format(i)
                    splitFiles.append("in_memory\poly_{}".format(i))
                    cursor.updateRow(row)
            arcpy.Split_analysis(areaOfInterest, areaOfInterest,
                                 'zzzName', 'in_memory')

        # get full path for aoi
        aoi_path = arcpy.Describe(areaOfInterest).catalogPath

        # grab an output directory, we may need it if TINs are being saved
        if out_workspace is None or not os.path.exists(out_workspace):
            out_dir = os.path.split(aoi_path)[0]
        else:
            out_dir = out_workspace

        # Calculate ACR for each polygon
        num_polys = len(splitFiles)
        for (i, each) in enumerate(splitFiles, start=1):
            if num_polys == 1:
                acr_msg = "Calculating ACR Rugosity..."
            else:
                acr_msg = ("Calculating ACR Rugosity for Area "
                           "{} of {}...".format(i, num_polys))
            utils.msg(acr_msg)

            # Create POBF TIN
            arcpy.Buffer_analysis(each, boundaryBuffer,
                                  cellSize, "OUTSIDE_ONLY")
            arcpy.Clip_management(in_raster, '#', boundaryRaster,
                                  boundaryBuffer, '#',
                                  'ClippingGeometry', 'NO_MAINTAIN_EXTENT')
            arcpy.RasterToPoint_conversion(boundaryRaster,
                                           boundaryPoints, 'Value')
            arcpy.GlobalPolynomialInterpolation_ga(boundaryPoints, "grid_code",
                                                   "#", pobfRaster, cellSize)
            arcpy.CalculateStatistics_management(pobfRaster)
            if len(splitFiles) == 1:
                basename = '{}_planarTIN'.format(rastName)
            else:
                basename = '{}_planarTIN_{}'.format(rastName, i)
            pobf_temp = os.path.join(d, basename)
            pobf_perm = os.path.join(out_dir, basename)

            zTolerance = abs((int(Raster(pobfRaster).maximum) -
                              int(Raster(pobfRaster).minimum))/10)
            arcpy.RasterTin_3d(pobfRaster, pobf_temp, str(zTolerance))
            arcpy.EditTin_3d(pobf_temp, ["#", "<None>", "<None>",
                                         "hardclip", "false"])
            # Calculate Rugosity
            arcpy.PolygonVolume_3d(elevationTIN, each, "<None>",
                                   "BELOW", "Volume1", "Surf_Area")
            arcpy.PolygonVolume_3d(pobf_temp, each, "<None>",
                                   "BELOW", "Volume2", "Plan_Area")
            arcpy.AddField_management(each, "Rugosity", "DOUBLE")
            arcpy.CalculateField_management(each, "Rugosity",
                                            "!Surf_Area! / !Plan_Area!",
                                            "PYTHON_9.3")
            arcpy.DeleteField_management(each, "Volume2;Volume1;zzzName")
            # Calculate Slope and Aspect
            arcpy.AddField_management(each, "Slope", "DOUBLE")
            arcpy.AddField_management(each, "Aspect", "DOUBLE")
            pobfXSize = Raster(pobfRaster).meanCellWidth
            pobfYSize = Raster(pobfRaster).meanCellHeight
            pobfArray = arcpy.RasterToNumPyArray(pobfRaster,
                                                 None, 3, 3)
            dz_dx = ((pobfArray[0, 2] + 2 * pobfArray[1, 2] +
                      pobfArray[2, 2]) -
                     (pobfArray[0, 0] + 2 * pobfArray[1, 0] +
                      pobfArray[2, 0])) / (8.0 * pobfXSize)
            dz_dy = ((pobfArray[2, 0] + 2 * pobfArray[2, 1] +
                      pobfArray[2, 2]) -
                     (pobfArray[0, 0] + 2 * pobfArray[0, 1] +
                      pobfArray[0, 2])) / (8.0 * pobfYSize)
            raw_aspect = (180 / np.pi) * np.arctan2(dz_dy, -dz_dx)
            if np.equal(dz_dy, dz_dx) and np.equal(dz_dy, 0):
                aspect = -1
            else:
                if np.equal(raw_aspect, 0):
                    aspect = 90
                elif np.equal(raw_aspect, 90):
                    aspect = 0
                elif raw_aspect > 90:
                    aspect = 360.0 - raw_aspect + 90
                else:
                    aspect = 90.0 - raw_aspect
            with arcpy.da.UpdateCursor(each, ["Slope", "Aspect"]) as cursor:
                for rows in cursor:
                    rows[0] = np.arctan(np.sqrt(dz_dx**2 +
                                                dz_dy**2))*(180/np.pi)
                    rows[1] = aspect
                    cursor.updateRow(rows)
            if saveTINs:
                # clip the TIN to the polygon, write out
                utils.msg("CopyTin_3d({},{})".format(pobf_temp, pobf_perm))
                arcpy.CopyTin_3d(pobf_temp, pobf_perm)
                arcpy.EditTin_3d(pobf_perm, each, "DELAUNAY")

        # Merge split files and save to input file location
        if multiple:
            arcpy.Merge_management(splitFiles, areaOfInterest)

        utils.msg("Saving ACR results to {}".format(aoi_path))

        # Save TINs if requested
        if saveTINs:
            utils.msg("Saving elevation and planar TINs to {}".format(out_dir))
            arcpy.CopyTin_3d(elevationTIN,
                             os.path.join(out_dir,
                                          '{}_elevationTIN'.format(rastName)))
