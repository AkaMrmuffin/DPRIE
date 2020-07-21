from __future__ import print_function
import arcpy
from arcpy import env
from arcpy.sa import *
import numpy as np
import netCDF4 as nc


def windcal(u,v):
    """
    windcal can calculate the overall wind direction based on
    Input u and v wind component
    the out put wind direction represent the wind is blowing to, if you want find wind is coming from, you need to uncomment lats step
    """

    ws = (u**2 + v**2)**0.5
    wd = np.arctan2(v,u)
    wd_ang = wd *180/np.pi
    wd_ang = wd_ang + 180

    return wd_ang,ws

def geo_idx(dd, dd_array):
    """
    dd - the decimal degree (latitude or longitude)
    dd_array - the list of decimal degrees to search.
    search for nearest decimal degree in an array of decimal degrees and return the index.
    np.argmin returns the indices of minium value along an axis.
    so subtract dd from all values in dd_array, take absolute value and find index of minium.
    """
    geo_idx = (np.abs(dd_array - dd)).argmin()
    return geo_idx

def extract_wind(comp,wind_path,source,lat,lon,t):
    """
    extract_wind can extract the wind direction (& speed) from wind data
    and write the windspeed into the input source feature class and shapefile

    comp - define the input wind data: True for ERA u&v wind componnets and False for other reaster datta
    wind_path - path of wind data
    source - path of source feature class or shapefile
    lat - field name of latitude
    lon - field name of longitude
    t - time step of ERA file

    if you are using standard raster wind data
    the function arguments can be: extract_wind(comp,wind_path,source,0,0,0)

    extract_wind returns field name of wind direction in the source feature class

    """
    if comp:
        # read ERA wind data
        wind_data = nc.Dataset(wind_path,'r')
        lats = wind_data.variables['latitude'][:]
        lons = wind_data.variables['longitude'][:]
        u = wind_data.variables['u10'][t,:,:]
        v = wind_data.variables['v10'][t,:,:]
        wind_data.close()
        wd,ws = windcal(u,v)

        # create wind direction and wind speed list to record wind speed & direction for all emission sources
        site_wd = []
        site_ws = []

        # create search cursor to read source feature class/ shapefile
        T1 = ['OBJECTID','SHAPE@',lat,lon]
        c1 =arcpy.da.SearchCursor(source,T1)
        for row in c1:
            s_id = row[0]
            s_geometry = row[1]

            if row[1] == None:
                pass
            else:
                in_lat = row[2]
                in_lon = row[3]
                # since lons are 0 thru 360, convert to -180 thru 180
                converted_lons = lons - ( lons.astype(np.int32) / 180) * 360
                # get cell of facility
                lat_idx = geo_idx(in_lat, lats)
                lon_idx = geo_idx(in_lon, converted_lons)

                #extract winddirection and wind speed from that cell
                d = wd[lat_idx,lon_idx]
                s = ws[lat_idx,lon_idx]

                site_wd.append(d)
                site_ws.append(s)


        # create attributes/fields to record wind speed & direction
        inFeatures = source
        # 1. create wind speed attribute
        fieldName = "windspeed"
        field_type = "DOUBLE"
        arcpy.AddField_management(inFeatures, fieldName,field_type,
                                  field_is_nullable="NULLABLE")

        # 2. create wind direction attribute
        fieldName = "winddir"
        field_type = "DOUBLE"
        arcpy.AddField_management(inFeatures, fieldName,field_type,
                              field_is_nullable="NULLABLE")

        # insert extracted ERA wind speed & direction into the source feature class
        # 1. update wind speed
        fn = ["windspeed","winddir"]
        with arcpy.da.UpdateCursor(inFeatures,fn) as cursor:
            index = 0
            for row in cursor:
                row[0] = site_ws[index]
                row[1] = site_wd[index]
                cursor.updateRow(row)
                index = index + 1
        del cursor
        print ("Extracting wind....")
        return fn[1]

    else:

        # if you are using rater data
        # Check out the ArcGIS Spatial Analyst extension license
        arcpy.CheckOutExtension("Spatial")
        fn = wind_path
        # Execute ExtractValuesToPoints
        ExtractMultiValuesToPoints(source, wind_path)
        print ("Extracting wind....")
        return fn


def def_dist(source,dist):
    """
    def_dist function creates a distance field and writes the user-defined disatnce to the source feature class
    it returns fieldname of distance field

    source - source feature class or shapefile
    dist - user-defined maximum downiwnd distance threshold

    """
    # Update the distance field
    fieldName = "Distance"
    field_type = "DOUBLE"
    arcpy.AddField_management(source, fieldName,field_type,
                                  field_is_nullable="NULLABLE")
    # update maximum downwind distance (length of wind line)
    with arcpy.da.UpdateCursor(source,fieldName) as cursor:
        for row in cursor:
            # OTM 33A downwind distance 200 meters
            cursor.updateRow([dist])
    del cursor

    print ("defining distance....")

    return fieldName

def find_n_DPRIP (source,DPRIPs):
    """
    find_n_DPRIP finds nearest DPRIP for each source, calculates and records nearest downiwnd distance,
    records coordinates of nearest DPRIPs

    source - source feature class or shapefile
    dist - user defined maximum downiwnd distance threshold

    find_n_DPRIP returns six lists
    ID_list - ID of source
    D_wind - downiwnd distance to nearest DPRIP
    Int_x - longitude of DPRIP
    Int_y - latitude of DPRIP
    SX - longitude of source
    SY - latitude of source
    """
    # build 1st search cursor for source feature class
    F1 = ['OBJECTID','SHAPE@','SHAPE@X','SHAPE@Y']
    # list used to record results
    ID_list =[]
    D_wind = []
    Int_x =[]
    Int_y =[]
    SX = []
    SY = []
    c1 =arcpy.da.SearchCursor(source,F1)
    i = 0
    for row1 in c1:
        s_id = row1[0]
        s_geometry = row1[1]
        s_lon = row1[2]
        s_lat = row1[3]
        # temporary list used to record results
        distlist = []
        xlist = []
        ylist = []
        # build 1st search cursor for DPRIPs feature class
        F2 = ['FID_bearline','SHAPE@','SHAPE@X','SHAPE@Y']
        c2 = arcpy.da.SearchCursor(DPRIPs,F2)
        for row2 in c2:
            i_id  = row2[0]
            i_geometry = row2[1]
            i_lon = row2[2]
            i_lat = row2[3]

            if i_id == s_id:
                dis = i_geometry.distanceTo(s_geometry)
                distlist.append(dis)
                xlist.append(i_lon)
                ylist.append(i_lat)
        # if there is no DPRIPs
        if len(distlist) == 0:
            fac_dist = -999
            nt_x =-999
            nt_y = -999
        # if there is DPRIPs and find the nearest DPRIP
        else:
            fac_dist = min(distlist)
            near_ind = distlist.index(min(distlist))

            nt_x = xlist[near_ind]
            nt_y = ylist[near_ind]

        Int_x.append(nt_x)
        Int_y.append(nt_y)
        D_wind.append(fac_dist)
        SX.append(s_lon)
        SY.append(s_lat)
        ID_list.append(s_id)

        print (i)
        i += 1

    print ("found all nearest DPRIPs")
    return ID_list,D_wind,Int_x,Int_y,SX,SY

def def_width(source,width):
    """
    def_width function creates a width of plume field and writes the field into the plume line feature class

    source - source feature class or shapefile
    width - width of plume determined by downiwnd distance to nearest DPRIP

    """
    # Update the plume width field
    fieldName = "Width"
    field_type = "DOUBLE"
    arcpy.AddField_management(source, fieldName,field_type,
                                  field_is_nullable="NULLABLE")
    # update cursor
    with arcpy.da.UpdateCursor(source,fieldName) as cursor:
        index = 0
        for row in cursor:
            # update width
            row[0] = width[index]
            cursor.updateRow(row)
            index = index + 1
    del cursor

    print ("Defining width of plume....")

    return fieldName
