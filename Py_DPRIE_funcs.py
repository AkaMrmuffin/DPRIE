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

def extract_wind(source,la,lo,lats,lons,wd,ws):
    """
    extract_wind can extract the wind direction (& speed) from wind data
    to the source dataframe. 
    
    source - source dataframe 
    la - latitude field 
    lo - longitude field 
    lats - latitue array of wind data 
    lons - longitude array of wind data 
    wd - calculated wind direction array 
    ws - calculated wind speed array 
    
    """
    lat = source[la]
    lon = source[lo]
    wdir = []
    wspd = [] 
    for coor in zip(lon,lat): 
        in_lon = coor[0]
        in_lat = coor[1]
        # since lons are 0 thru 360, convert to -180 thru 180
        converted_lons = lons - ( lons.astype(np.int32) / 180) * 360
        # get cell of facility
        lat_idx = geo_idx(in_lat, lats)
        lon_idx = geo_idx(in_lon, converted_lons)
        #extract winddirection and wind speed from that cell
        d = wd[:,lat_idx,lon_idx][0]
        wdir.append(d)
        s = ws[:,lat_idx,lon_idx][0]
        wspd.append(s)
    
    return wdir,wspd
	

def windcal(v,u):
    """
    # windcal can calculate the overall wind direction based on
    # Input u and v wind component
    # the out put wind direction represent the wind is blowing to, if you want find wind is coming from, you need to uncomment lats step
    
    v - v wind component
    u - u wind component
    
    """
    
    ws = (u**2 + v**2)**0.5
    wd = np.arctan2(u,v)
    wd_ang = wd *180/np.pi
    wd_ang = wd_ang + 180

    return wd_ang,ws
	
	
def list_to_gdf (lis):
    """
    convert a list of shapes to a geodataframe
    lis - input list 
    """
    gdf = gpd.GeoDataFrame(lis)
    # rename the column 
    gdf.rename(columns ={0:"geometry"},inplace=True)
    # define crs to dataframe
    gdf.crs = {'init' :'epsg:{}'.format(4326)} 
    gdf = gdf.to_crs(epsg = 4326)
    
    return gdf
	

def geo_idx(dd, dd_array):
    """
     - dd - the decimal degree (latitude or longitude)
     - dd_array - the list of decimal degrees to search.
     search for nearest decimal degree in an array of decimal degrees and return the index.
     np.argmin returns the indices of minium value along an axis.
     so subtract dd from all values in dd_array, take absolute value and find index of minium.
   """
    geo_idx = (np.abs(dd_array - dd)).argmin()
    return geo_idx
	
	
def bearline(source,la,lo,dist,wdir):
    """
    create a virtual wind trajectory line 
    
    source - source dataframe 
    la - latitude field 
    lo - longitude field 
    dist - user-defined distance threshold 
    wdir - wind direction field
    
    """
    
    
    bearlines =[]
    lon = source[lo]
    lat = source[la]
    wdir = source[wdir] 
    for coor in zip(lon,lat,wdir): 
        in_lon = coor[0]
        in_lat = coor[1]
        in_dir = coor[2]
        # start point of the line 
        origin = geopy.Point(in_lat,in_lon)
        # find the end point of the line 
        end_p = distance(kilometers=dist).destination(origin, in_dir)
        e_lat, e_lon = end_p.latitude, end_p.longitude
        # create points object for start point and end point 
        pt1 = Point(in_lon,in_lat)
        pt2 = Point(e_lon,e_lat)
        # create downwind trajectory 
        line = LineString([pt1,pt2])
        bearlines.append(line)  
    
    return bearlines  
	
	
def find_DPRIPs (roadline,windline):
    """
    find all intersection points between roads and virtual wind trajectories 
    roadline - road geodataframe  
    windline - virtual wind trajectory geodataframe
    
    """
    DPRIPs=[]
    ID = []
    i = 0 
    for w in windline:
        int_pt=[]
        for r in roadline:
            if w.intersection(r): 
                int_pt.append(w.intersection(r))
        if len(int_pt)!=0:        
            DPRIPs.append(int_pt)
            ID.append(1)
        else: 
            ID.append(-999)
        i = i + 1
    
    source['road_access'] = ID
    #source with road access downiwnd 
    swrad = source[source.road_access != -999]
    
    return swrad,DPRIPs
    
	
def find_nearest_DPRIPs (swrad,DPRIPs): 
    """
    #find nearest DPRIPs
    swrad - source geodataframe with road access downiwnd 
    DPRIPs - source geodataframe (for sources with road access downiwnd only) 
    """
    s_pt = swrad.geometry
    new2d =[] 
    for cood in s_pt: 
        pt_2d = Point(cood.x,cood.y)
        new2d.append(pt_2d)
    s_pt = new2d
    ND_list = [] 
    N_DPRIP = [] 
    # for all DPRIPs 
    for gp in zip(s_pt,DPRIPs):
        s = gp[0]
        DPRIP = gp[1]
        # Create empty list for storing distance 
        all_dist = [] 
        # check DPRIPs for each source 
        for pt in DPRIP: 
            if pt.type == "MultiPoint": 
                split_pt = [(n.x, n.y) for n in pt]
                for spt in split_pt: 
                    npt = Point(spt)
                    dist = npt.distance(s)
                    all_dist.append(dist)
            else: 
                dist = pt.distance(s)
                all_dist.append(dist)
            # find nearest intersection point index
            near_dist = min(all_dist)
            n_id = all_dist.index(near_dist)
            n_DPRIP = DPRIP[n_id]

        ND_list.append(near_dist)
        N_DPRIP.append(n_DPRIP)
    
    return ND_list,N_DPRIP
	

	
def plume_buffer(int_gdf,swrad):
    
    """
    create a virtual plume between sources and their DPRIPs 
    int_gdf - nearest DPRIPs geodataframe 
    swrad - source geodataframe (for sources with road access downiwnd only)
    """
    ni_pt = int_gdf.geometry
    s_pt = swrad.geometry
    new2d =[] 
    for cood in s_pt: 
        pt_2d = Point(cood.x,cood.y)
        new2d.append(pt_2d)
    s_pt = new2d
    downwind_line = []
    for gp in zip(s_pt,ni_pt):
        line = LineString([gp[0],gp[1]])
        downwind_line.append(line)

    Buffer = [] 
    for dl in zip(downwind_line,ND_list):
        buf = dl[0].buffer(dl[1]*0.2)
        Buffer.append(buf) 
        
    DB = list_to_gdf (Buffer)
    
    return DB