filename="nsog_5m.tif sesog_5m.tif swsog_5m.tif jdf_5m.tif qcstr_5m.tif"
out="SoG_5m.tif"
na="-3.4e+38"
python "C:/Anaconda/Scripts/gdal_merge.py" -of "GTiff" -co "TILED=YES" -co "COMPRESS=LZW" -co "BIGTIFF=YES" -a_nodata $na -init $na $filename -o $out
