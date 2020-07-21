from Py_DPRIE_funcs import *
import geopandas as gpd
import numpy as np
import pandas as pd
import geopy 
from shapely.geometry import LineString, Point,Polygon
from geopy.distance import distance
import netCDF4 as nc 
import shapely
from math import pi
from rasterstats import zonal_stats


workspace = r"D:\DPRIE_Test\Workspace_DPRIE"

source = gpd.read_file("{}\shapefiles\source.shp".format(workspace))
road = gpd.read_file(r"{}\shapefiles\road.shp".format(workspace))
wind = r'{}\SampleERA.nc'.format(workspace)
ls_ras = r'{}\landcover'.format(workspace)
dem_ras = r'{}\DEM'.format(workspace)

# read wind data 
data = nc.Dataset(wind)
lats = data.variables['latitude'][:]
lons = data.variables['longitude'][:]
u = data.variables['u10'][:]
v = data.variables['v10'][:]
data.close()

##### 1.extract wind for each source #####
wd,ws = windcal(v,u)
wdir,wspd = extract_wind(source,'lat','lon',lats,lons,wd,ws)
source['wspd'] = wspd 
source['wdir'] = wdir
bl = bearline(source,'lat','lon',0.5,"wdir")
##### 2.create downwind trajecories geodataframe #####
beartra = list_to_gdf (bl)
##### 3.fined All DPRIPs ##### 
roadline = road.geometry
windline = beartra.geometry 
swrad,DPRIPs = find_DPRIPs (roadline,windline)
##### 4.find nearest DPRIPs #####
ND_list,N_DPRIP = find_nearest_DPRIPs (swrad,DPRIPs)
int_gdf = list_to_gdf (N_DPRIP)
# recreate the windline and wind buffer 
DB = plume_buffer(int_gdf,swrad)
##### 5.zonal statistics ##### 
dom_lc = zonal_stats(DB,ls_ras, stats="majority")
dem_min_max = zonal_stats(DB,dem_ras, stats=['min','max'])

# Organize Results 
lc_list = [] 
for ele in dom_lc: 
    lc_list.append(ele['majority'])
    
dem_list = [] 
for ele in dem_min_max:
    if ele['max']!=None:
        ran = ele['max'] - ele['min']
        dem_list.append(round(ran))
    else: 
        print ("your sources are not overlay the DEM")
        
nDPRIPs_x = [] 
nDPRIPs_y = []
for DPRIP in N_DPRIP:
    nDPRIPs_x.append(DPRIP.x) 
    nDPRIPs_y.append(DPRIP.y)

# Output to a csv file 
Output_df = pd.DataFrame()
Output_df['facility'] = swrad['facility_I']   
Output_df['lat'] = swrad['lat']  
Output_df['lon'] = swrad['lon']
Output_df['wind_speed'] = swrad['wspd']
Output_df['wind_direction'] = swrad['wdir'] 
Output_df['nDPRIPX'] = nDPRIPs_x 
Output_df['nDPRIPY'] = nDPRIPs_y 
Output_df['Dominant_LC'] = lc_list
Output_df['Ele_Range'] = dem_list

Output_df.to_csv("{}\outputDPRIP.csv".format(workspace),sep =',')