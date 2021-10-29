import csv 
import time 
import subprocess as sp
import re
import datetime as dt
import pandas as pd 
import numpy as np 
import geopandas as gpd

#wt = 5 # Wait time -- I purposefully make it wait before the shell command
#accuracy = 3 #Starting desired accuracy is fine and builds at x1.5 per loop

# plot trajectories 
traj =pd.read_csv(r"traj.csv",sep=',')
trajs = gpd.GeoDataFrame(traj,geometry=gpd.points_from_xy(traj.lons,traj.lats))
# projection
trajs = trajs.set_crs("EPSG:4326")
trajs.geometry = trajs.geometry.to_crs(epsg=26911)

# lat_value = 0 
# lon_value = 0
# hour = dt.datetime.now().hour

lons_list = np.array(trajs.geometry.x)
lats_list = np.array(trajs.geometry.y) 
time_list = list(trajs.times)

lat_value = lats_list[0] 
lon_value = lons_list[0]
hour = time_list[0].split(' ')[1].split(':')[0]

fieldnames = ['lons','lats','time']


with open ('mydesktop.csv','w') as csv_file: 
    csv_writer = csv.DictWriter(csv_file, fieldnames = fieldnames)
    csv_writer.writeheader()

Day = True
i = 1  
while Day:
    if i > len(lons_list): 
        Day = False 
        break
        
    with open('mydesktop.csv', 'a') as csv_file:
        csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

        info = {
            "lons": lon_value,
            "lats": lat_value,
            "time": hour
        }

        csv_writer.writerow(info)
        
        
#         # time.sleep(wt)
#         # pshellcomm = ['powershell']
#         # pshellcomm.append('add-type -assemblyname system.device; '\
#         #                   '$loc = new-object system.device.location.geocoordinatewatcher;'\
#         #                   '$loc.start(); '\
#         #                   'while(($loc.status -ne "Ready") -and ($loc.permission -ne "Denied")) '\
#         #                   '{start-sleep -milliseconds 100}; '\
#         #                   '$acc = %d; '\
#         #                   'while($loc.position.location.horizontalaccuracy -gt $acc) '\
#         #                   '{start-sleep -milliseconds 100; $acc = [math]::Round($acc*1.5)}; '\
#         #                   '$loc.position.location.latitude; '\
#         #                   '$loc.position.location.longitude; '\
#         #                   '$loc.stop()' %(accuracy))
    
    
#         # p = sp.Popen(pshellcomm, stdin = sp.PIPE, stdout = sp.PIPE, stderr = sp.STDOUT, text=True)
#         # (out, err) = p.communicate()
#         # out = re.split('\n', out)
    
        # lat = float(out[0])
        # lon = float(out[1])
        # hour_a_day = dt.datetime.now().hour
        
        
        lat_value = lats_list[i] 
        lon_value = lons_list[i]
        hour = time_list[i].split(' ')[1].split(':')[0]

        print(lat_value, lon_value, hour)
    i += 1        
    time.sleep(2)