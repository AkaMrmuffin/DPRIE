from __future__ import print_function # for python 2 users
import arcpy
from arcpy import env
from arcpy.sa import *
import numpy as np
import netCDF4 as nc
import pandas as pd


# import DPRIE functions
from ArcGIS_DPRIE_funcs import *

##################################################### Workflow ######################################################

# define arcpy environment
arcpy.env.workspace =r"D:\DPRIE_Test\DPRIE.gdb"
source = 'source'
wind = "WindDirection"

##### 1. extract wind (I used raster data) #####
fn = extract_wind(False,wind,source,0,0,0)

##### 2. defined distance #####
dn = def_dist(source,500)

##### 3. create virtual downiwnd trajectory #####
# re-define arcpy environemnt
arcpy.env.workspace =r"D:\DPRIE_Test\DPRIE.gdb"
road = "road"
DPRIPs = "DPRIP"
bl = "bearline"
# define the spatial reference
sr = arcpy.SpatialReference(54002) #WKID of equidistant cylinderical
bl_path = arcpy.BearingDistanceToLine_management(source, bl, 'X', 'Y',
                                       dn,"METERS",fn, "DEGREES",'GEODESIC',spatial_reference = sr)
print ("creating virtual downiwnd trajectory....")

##### 4. find all DPRIPs #####
dps_path = arcpy.Intersect_analysis ([road, bl],DPRIPs, "", "", 'POINT')

##### 5.find nearest DPRIPs for each source, calculate nearest downiwnd distance #####
# record coordinates of nearest DPRIPs
print ("calculating DPRIPs....")
ID_list,D_wind,Int_x,Int_y,SX,SY = find_n_DPRIP(source,DPRIPs)

# output results to .csv file 
d = {"source_X":SX,"source_Y":SY,"source_ID":ID_list,
    "Downwind_dist":D_wind,"p_x":Int_x,"p_y":Int_y}

df = pd.DataFrame(data=d,columns = ["source_ID","source_X","source_Y",
                                   "p_x","p_y","Downwind_dist"])
ndf = df[df.Downwind_dist!= -999]

allsource = r"D:\DPRIE_Test\allsource.csv"
df.to_csv(allsource)
DPRIP_t = r"D:\DPRIE_Test\eff_source.csv"
ndf.to_csv(DPRIP_t)

print ("Part I finished!!!Outputing results....")

# re-define arcpy environemnt
arcpy.env.workspace =r"D:\DPRIE_Test\DPRIE.gdb"
out_lines = "nsri_line"
input_table = DPRIP_t

##### 6.create virtual plume line #####
arcpy.XYToLine_management(input_table,out_lines,
                         "source_X","source_Y","p_x",
                         "p_y","GEODESIC","source_ID",sr)

# calculate width of plume for each source & nearest DPRIP
pl = ndf.Downwind_dist
# calculate plume width 50% of plume length
pw = np.array(pl)/4
pw = np.round(pw)
# define the width of plume
wn = def_width(out_lines,pw)
# create virtual plume buffer
buffer = "line_buffer"
arcpy.Buffer_analysis(out_lines, buffer, wn, "Full", "FLAT")
print ("We got Plume")

##### 7.Zonal Statistics #####
# zonal statistics -> find dominant landcover type and output landcover type info
arcpy.env.workspace =r"D:\DPRIE_Test\DPRIE.gdb"
ras = r"D:\DPRIE_Test\DPRIE.gdb\landcover"
csv_path = r"D:\DPRIE_Test"
csv_name = "lancover_test.csv"
dbf_name = r"D:\DPRIE_Test\lc_test.dbf"
zoneField = "OID"
outTable = dbf_name
stat = "MAJORITY"
ZonalStatisticsAsTable(buffer, zoneField,ras,dbf_name, "DATA", stat)
arcpy.TableToTable_conversion(dbf_name, csv_path, csv_name)
# zonal statistics -> find the elevation range
ras = r"D:\DPRIE_Test\DPRIE.gdb\DEM"
csv_path = r"D:\DPRIE_Test"
csv_name = "DEM_test.csv"
dbf_name = r"D:\DPRIE_Test\DEM_test.dbf"
zoneField = "OID"
outTable = dbf_name
stat = "Range"
ZonalStatisticsAsTable(buffer, zoneField,ras,dbf_name, "DATA", stat)
arcpy.TableToTable_conversion(dbf_name, csv_path, csv_name)
print ("Part II finished!!!!")