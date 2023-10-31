## ------ CREATE MOVES INPUT FILE ------ ##
#   Tim O'Leary 2023/10/3
#   Script borrows from original SAS script 'create.moves.input.file.imversion.sas',
#   originally written by Craig Heither.
#   Script reads model output generated by punchmoves.py and formats it for input into 
#   MOVES. Two spreadsheets are created:
#     - one containing data for the Vehicle Inspection and Maintenance area in the IL portion of the non-attainment area.
#     - one containing data for the non-Vehicle Inspection and Maintenance area in the IL portion of the non-attainment area.
# ---------------------------------------
#
# MOVES Data Conversion Dictionary:
#
#     Road Types:
#         MOVES Type & Description                  Model VDF
#         -----------------------------             ---------------
#          1: Off-Network                     -     N/A
#          2: Rural Restricted Access         -     rural 2,3,4,5,7,8
#          3: Rural Unrestricted Access       -     rural 1,6
#          4: Urban Restricted Access         -     urban 2,3,4,5,7,8
#          5: Urban Unrestricted Access       -     urban 1,6
#
#     Source Types:
#         MOVES Type & Description                  HPMS Type & Description                 VHT Distribution Source from model
#         -----------------------------             -------------------------               ----------------------------------
#          11: Motorcycle                     -     10: Motorcycles                    -    (use auto distribution)
#          21: Passenger Car                  -     20: Passenger Cars                 -    autos
#          31: Passenger Truck                -     30: Other 2 axle-4 tire vehicles   -    autos
#          32: Light Commercial Truck         -     30: Other 2 axle-4 tire vehicles   -    b-plates
#          41: Intercity Bus                  -     40: Buses                          -    (use transit bus distribution)
#          42: Transit Bus                    -     40: Buses                          -    transit bus
#          43: School Bus                     -     40: Buses                          -    (use transit bus distribution)
#          51: Refuse Truck                   -     50: Single Unit Trucks             -    (use medium duty trucks under 200 miles distribution)
#          52: Single Unit Short-haul Truck   -     50: Single Unit Trucks             -    light trucks + medium duty trucks under 200 miles
#          53: Single Unit Long-haul Truck    -     50: Single Unit Trucks             -    medium duty trucks 200+ miles
#          54: Motor Home                     -     50: Single Unit Trucks             -    (use medium duty trucks 200+ miles distribution)
#          61: Combination Short-haul Truck   -     60: Combination Trucks             -    heavy duty trucks under 200 miles
#          62: Combination Long-haul Truck    -     60: Combination Trucks             -    heavy duty trucks 200+ miles


## ------ IMPORT MODULES ------ ##

import os
import re
import pandas as pd, numpy as np
import datetime as dt
import openpyxl
from itertools import product


## ------ PARAMETERS ------ ##
workspace = os.path.dirname(os.path.dirname(os.getcwd()))
#get model version and scenario year - for output filenames
#looks for a string of the form 'c??q?_?00' where '?' is any numerical digit
model_year = re.findall(r'c\d{2}q\d{1}_\d{1}00',workspace)  #e.g., 'c23q4_400'
model = model_year[0][0:5]                                  # e.g., 'c23q4'
scenyear = model_year[0][-3:]                               # e.g., '400'

#bring in punch moves link data
linkdata = pd.read_csv(workspace + '\\Database\\data\\punchlink.csv')

#output excel worksheets
excel_file_IM = workspace + f'\\Database\\data\\MOVES_{model}_scen{scenyear}_IM.xlsx'
excel_file_noIM = workspace + f'\\Database\\data\\MOVES_{model}_scen{scenyear}_noIM.xlsx'

##create excel workbook to write worksheets to
xlsx_IM = pd.ExcelWriter(excel_file_IM)
xlsx_noIM = pd.ExcelWriter(excel_file_noIM)


## ------ CLEAN-UP DATASET ------ ##

#clean up column names
collist = linkdata.columns.tolist()
cols_to_rename = [a for a in collist if a.startswith('@')]
coldict = dict([[a, a[1:]] for a in cols_to_rename])
coldict['tmpl2'] = 'isramp'
linkdata.rename(columns=coldict, inplace=True)

#column data types
for x in ['i_node', 'j_node', 'timeperiod', 'lan', 'vdf', 'zone', 'imarea', 'atype']:
    linkdata[x] = linkdata[x].astype(int)
for x in ['len', 'emcap', 'timau', 'ftime', 'avauv', 'avh2v', 'avh3v', 'avbqv', 'avlqv',
          'avmqv', 'avhqv', 'atype', 'busveq']:
    linkdata[x] = linkdata[x].astype(float)

#flag ramp links
linkdata.loc[linkdata['vdf'].isin([3,5,8]),'isramp']=1

#include only non-attainment zones
na_zones = [
    list(range(1,2305)),
    list(range(2309,2314)),
    list(range(2317,2320)),
    list(range(2326,2927)),
    [2941,2943,2944,2949]
]

na_zones = [item for sublist in na_zones for item in sublist]
links = linkdata.loc[linkdata['zone'].isin(na_zones)].copy()


## ------ LINK CALCULATIONS ------ ##

# reset total mtruck/htruck veh equivalents to short-haul veh equivalents
links['m200'] = np.minimum(links['m200'], links['avmqv'])      # m200 cannot exceed final MSA balanced volau
links['avmqv'] = np.maximum(links['avmqv']-links['m200'], 0)   # now only short haul
links['h200'] = np.minimum(links['h200'], links['avhqv'])      # h200 cannot exceed final MSA balanced volau
links['avhqv'] = np.maximum(links['avhqv']-links['h200'], 0)   # now only short haul

#total volume in vehicle equivalents
links.eval('volau = avauv + avh2v + avh3v + avbqv + avlqv + avmqv + m200 + avhqv + h200', inplace=True)

# volume in # vehicles (for VMT/VHT)
links['sov'] = np.maximum(links['avauv'],0)
links['hov2'] = np.maximum(links['avh2v'],0)
links['hov3'] = np.maximum(links['avh3v'],0)
links.eval('auto = sov + hov2 + hov3', inplace=True)
links['bplate'] = np.maximum(links['avbqv'],0)
links['ltruck'] = np.maximum(links['avlqv'],0)
links['mtruck'] = np.maximum(links['avmqv']/2,0)
links.eval('sush = ltruck + mtruck', inplace=True)
links['htruck'] = np.maximum(links['avhqv']/3,0)
links['bus'] = np.maximum(links['busveq']/3,0)
links['mtrucklh'] = np.maximum(links['m200']/2,0)
links['htrucklh'] = np.maximum(links['h200']/3,0)
links.eval('vehicles = auto + bplate + sush + mtrucklh + htruck + htrucklh + bus', inplace=True)

##link capacity calculations 

# lines 230-234
# number of hrs per time period (for capacity calcs)
hours = {1:5, 2:1, 3:2, 4:1, 5:4, 6:2, 7:2, 8:2} ## dict format => {'timeperiod': 'number of hours'}
links['hours'] = links['timeperiod'].map(hours)
links.eval('capacity = lan * emcap * hours', inplace=True)

# lines 238-243
# arterial speed adjustment due to LOS C used in VDF (for VHT calculations)
links['fmph'] = np.where((links['ftime'] > 0), (links['len']/(links['ftime']/60)), 20)
links['mph'] = np.where((links['timau'] > 0), (links['len']/(links['timau']/60)), 20)
## - NOTE: old SAS script used minimum of 0 mph. this has no difference computationally (already adjusted in model)

# congested speed calc
#links.loc[(links['vdf'] == 1), 'mph'] = links['fmph'] * (1/((np.log(links['fmph']) * 0.249) + 0.153 * (links['volau'] / (links['capacity']*0.75))**3.98))
links['mph'] = np.where(links['vdf']==1, links['fmph'] * (1/((np.log(links['fmph'])*0.249)+0.153*(links['volau']/(links['capacity']*0.75))**3.98)), links['mph'])

## -- Vehicle Miles Traveled and Vehicle Hours Traveled 

#vehicle types to be calculated
vehicle_cols = [
    'sov', 'hov2', 'hov3', 'auto', 'bplate', 'ltruck', 
    'mtruck', 'sush', 'htruck', 'bus', 'mtrucklh', 'htrucklh'
]

#vmt
for c in vehicle_cols:
    links.eval(f'{c}_vmt = {c} * len', inplace=True)
links.eval('all_vmt = vehicles * len', inplace=True)

#vht
for c in vehicle_cols:
    links[f'{c}_vht'] = np.where((links['mph'] > 0), links[f'{c}_vmt']/links['mph'], 0)
links['all_vht'] = np.where((links['mph'] > 0), links['all_vmt']/links['mph'], 0)


## -- Setup MOVES variables 
#create avgSpeedBinID by reclassifying mph
def speed_class(mph):
    if mph < 2.5:
        return 1
    elif mph < 7.5:
        return 2
    elif mph < 12.5:
        return 3
    elif mph < 17.5:
        return 4
    elif mph < 22.5:
        return 5
    elif mph < 27.5:
        return 6
    elif mph < 32.5:
        return 7
    elif mph < 37.5:
        return 8
    elif mph < 42.5:
        return 9
    elif mph < 47.5:
        return 10
    elif mph < 52.5:
        return 11
    elif mph < 57.5:
        return 12
    elif mph < 62.5:
        return 13
    elif mph < 67.5:
        return 14
    elif mph < 72.5:
        return 15
    else:
        return 16
links['avgSpeedBinID'] = links['mph'].map(speed_class)

#create facility types
#for vdf = 1 or 6
links.loc[(links['vdf'].isin([1,6]))&(links['atype']<9), 'roadTypeID']=5 #urban arterial
links.loc[(links['vdf'].isin([1,6]))&~(links['atype']<9), 'roadTypeID']=3 #rural arterial
# for vdf != 1 or 6
links.loc[~(links['vdf'].isin([1,6]))&(links['atype']<9), 'roadTypeID']=4 #urban freeway
links.loc[~(links['vdf'].isin([1,6]))&~(links['atype']<9), 'roadTypeID']=2 #rural freeway


## ------ Create MOVES 'initial_model_output' Table ------ ##

#line 305
#grab columns we want to aggregate
b1_columns = [[f'{c}_vmt', f'{c}_vht'] for c in ['auto','bplate','sush','mtrucklh','htrucklh','htruck','bus']]
b1_columns = [a for sublist in b1_columns for a in sublist]
aggsums = {}
for a in b1_columns:
    aggsums[a] = 'sum'

groupcols = ['imarea', 'roadTypeID', 'timeperiod', 'avgSpeedBinID', 'hours']

b1 = links.groupby(groupcols).agg(aggsums).reset_index()

# #vmt verification
# #line 308-313

# print('Totals Before')
# links.groupby(['imarea']).agg(aggsums)
#disaggregate to hourly data
#lines 316-324

#timeperiod = 1 is 10 hours, others are still fine
b1.loc[b1['timeperiod']==1, 'hours']=10

#changing values to be normalized by # hours in timeperiod
for c in b1_columns:
    b1.eval(f'{c} = {c} / hours', inplace=True)


#we need to duplicate each row to include each hour-of-day value
#will do this by appending rows to a new dataframe using some dictionaries

#this sets up hour of day, will call this below
times = {1:[21,22,23,24,1,2,3,4,5,6], 
         2:[7], 
         3:[8,9], 
         4:[10], 
         5:[11,12,13,14], 
         6:[15,16],
         7:[17,18],
         8:[19,20]
        }

#create new df of each timeperiod
b1_dfs = []
for tp in times:
    b_tp = b1.loc[b1['timeperiod']==tp].copy(deep=True)
    #create new df for each hour-of-day within each timeperiod, then append to b1_dfs as an item in list
    for hour in times[tp]:
        bb = b_tp.copy(deep=True)
        bb['hr'] = hour
        b1_dfs.append(bb)

#concatenate all timeperiod dataframes in b1_dfs into one df
b1 = pd.concat(b1_dfs, ignore_index=True)
b1['hourDayID'] = b1['hr']*10+5     #'5' indicates a weekday'
b1.sort_values(['imarea','roadTypeID','avgSpeedBinID','timeperiod','hourDayID'], inplace=True)

#need to make separate rows for vmt/vht of each vehicle class
#will do this by creating a separate df for each vehicle class, then recombine

common_columns = ['roadTypeID', 'timeperiod', 'avgSpeedBinID', 'hourDayID', 'imarea']
#passenger car - 21
b2 = b1[common_columns + ['auto_vmt', 'auto_vht']].copy().rename(columns={'auto_vmt':'vmt', 'auto_vht':'vht'})
b2['sourceTypeID'] = 21
#passenger truck - 31
b3 = b1[common_columns + ['auto_vmt', 'auto_vht']].copy().rename(columns={'auto_vmt':'vmt', 'auto_vht':'vht'})
b3['sourceTypeID'] = 31
#light commercial truck - 32
b4 = b1[common_columns + ['bplate_vmt', 'bplate_vht']].copy().rename(columns={'bplate_vmt':'vmt', 'bplate_vht':'vht'})
b4['sourceTypeID'] = 32
#SU short haul truck - 52
b5 = b1[common_columns + ['sush_vmt', 'sush_vht']].copy().rename(columns={'sush_vmt':'vmt', 'sush_vht':'vht'})
b5['sourceTypeID'] = 52
#SU long-haul truck - 53
b6 = b1[common_columns + ['mtrucklh_vmt', 'mtrucklh_vht']].copy().rename(columns={'mtrucklh_vmt':'vmt', 'mtrucklh_vht':'vht'})
b6['sourceTypeID'] = 53
#MU short haul - 61
b7 = b1[common_columns + ['htruck_vmt', 'htruck_vht']].copy().rename(columns={'htruck_vmt':'vmt', 'htruck_vht':'vht'})
b7['sourceTypeID'] = 61
#MU long haul - 62
b8 = b1[common_columns + ['htrucklh_vmt', 'htrucklh_vht']].copy().rename(columns={'htrucklh_vmt':'vmt', 'htrucklh_vht':'vht'})
b8['sourceTypeID'] = 62
#transit bus - 42
b9 = b1[common_columns + ['bus_vmt', 'bus_vht']].copy().rename(columns={'bus_vmt':'vmt', 'bus_vht':'vht'})
b9['sourceTypeID'] = 42
#intercity bus - 41 -- apply transit bus distribution to intercity bus
b10 = b9.copy()
b10['sourceTypeID'] = 41
#school bus - 43 -- apply transit bus distribution to school bus
b11 = b9.copy()
b11['sourceTypeID'] = 43
#motorcycle - 11 -- apply auto distribution to motorcycles
b12 = b2.copy()
b12['sourceTypeID'] = 11
#refuse trucks - 51 -- apply single unit short-haul distribution to refuse trucks
b13 = b5.copy()
b13['sourceTypeID'] = 51
#motor homes - 54 -- apply single unit long-haul distribution to motor homes
b14 = b6.copy()
b14['sourceTypeID'] = 54

b = pd.concat([b2, b3, b4, b5, b6, b7, b8, b9, b10, b11, b12, b13, b14], ignore_index=True)
b.sort_values(['imarea', 'sourceTypeID', 'roadTypeID', 'hourDayID', 'avgSpeedBinID'], inplace=True)


#need to apply values onto a template that contains all possible combinations
#create template with all combinations
#line 369-374

#get unique values for each of the categories: sourceTypeID, roadTypeID, hourDayID, avgSpeedBinID, and imarea
veh = b['sourceTypeID'].unique().tolist()
road = b['roadTypeID'].unique().tolist()
hrday = b['hourDayID'].unique().tolist()
speed = b['avgSpeedBinID'].unique().tolist()
imcat = b['imarea'].unique().tolist()

#create cartesian product of the lists listed above
template_values = list(product(veh, road, hrday, speed, imcat))
template = pd.DataFrame(template_values, columns=['sourceTypeID', 'roadTypeID', 'hourDayID', 'avgSpeedBinID', 'imarea'])
template.sort_values(['imarea', 'sourceTypeID', 'roadTypeID', 'hourDayID', 'avgSpeedBinID'], inplace=True)
template.reset_index(drop=True, inplace=True)

#merge data with template
b = pd.merge(template, b, how='left', on=['imarea', 'sourceTypeID', 'roadTypeID', 'hourDayID', 'avgSpeedBinID'])
# b.fillna(0, inplace=True) #remove null values
b.drop(columns='timeperiod', inplace=True)

#remove negative vmt/vht values, if they exist, or fill with zeroes
def replace_neg_w_zero(x):
    return max(0,x)
b['vmt'] = b['vmt'].apply(replace_neg_w_zero)
b['vht'] = b['vht'].apply(replace_neg_w_zero)


#####################################
## -- INIITIAL MODEL OUTPUT TAB -- ##
#####################################
#line 462-473
#only include source types from actual modeled vehicle trips -- for QC

#initial_model_output tab in excel file
#imarea
outIM_initialmodeloutput = b.loc[~(b['sourceTypeID'].astype('int').isin([11,41,43,51,54]))&(b['imarea']==1)].copy(deep=True)
outIM_initialmodeloutput.to_excel(xlsx_IM, sheet_name='initial_model_output', index=False)

#non-imarea
outnoIM_initialmodeloutput = b.loc[~(b['sourceTypeID'].astype('int').isin([11,41,43,51,54]))&(b['imarea']==0)].copy(deep=True)
outnoIM_initialmodeloutput.to_excel(xlsx_noIM, sheet_name='initial_model_output', index=False)


##################################
## -- SPEED DISTRIBUTION TAB -- ##
##################################

#lines 479-482
#CALCULATE VHT SHARE BY SOURCETYPEID-ROADTYPEID-HOURDAYID
#then join back to table

casecols = ['imarea', 'sourceTypeID', 'roadTypeID', 'hourDayID']

sumvht = b.groupby(casecols).agg({'vht':'sum'})
sumvht.rename(columns={'vht':'allvht'}, inplace=True)
sumvht.reset_index(inplace=True)
share = pd.merge(b, sumvht, on=casecols, how='inner')


#lines 485-512
# -- USE SURROGATES TO REPLACE MISSING VALUES -- 

#bus, pt 1: use roadTypeID 4 to replace missing values for roadTypeID 2 for sourceTypeID 41,42,43 for IM area
fb1_a = share.loc[(share['sourceTypeID']==42)&(share['roadTypeID']==4)&(share['imarea']==1)].copy(deep=True)
fb1_a['roadTypeID'] = 2
fb1_b = fb1_a.copy()
fb1_b['sourceTypeID'] = 41
fb1_c = fb1_a.copy()
fb1_c['sourceTypeID'] = 43
fb1 = pd.concat([fb1_a, fb1_b, fb1_c])

#bus, pt2: use sourceTypeID 41,42,43 for IM area to replace missing values for non-IM area
fb2 = pd.concat([fb1, share.loc[(share['sourceTypeID'].isin([41,42,43]))&(share['imarea']==1)].copy(deep=True)])
fb2['imarea']=0

#SU long-haul truck, pt1: use sourceTypeID 52 to replace missing values for sourceTypeID 53,54 for IM area
fb3 = share.loc[(share['sourceTypeID']==52)&(share['imarea']==1)].copy(deep=True)
fb3_a = fb3.copy()
fb3_a['sourceTypeID'] = 53
fb3_b = fb3.copy()
fb3_b['sourceTypeID'] = 54
fb3 = pd.concat([fb3_a, fb3_b])

#SU long-haul truck, pt2: use sourceTypeID 52,53,54 for IM area to replace missing values for non-IM area
fb4 = pd.concat([fb3, share.loc[(share['sourceTypeID']==52)&(share['imarea']==1)]], ignore_index=True)
fb4['imarea'] = 0

#MU long-haul truck pt1: use sourceTypeID 61 to replace missing values for sourceTypeID 62 for IM area
fb5 = share.loc[(share['sourceTypeID']==61)&(share['imarea']==1)].copy(deep=True)
fb5['sourceTypeID'] = 62

#MU long-haul truck pt2: use sourceTypeID 61, 62 for IM area to replace missing values for non-IM area
fb6 = pd.concat([fb5, share.loc[(share['sourceTypeID']==61)&(share['imarea']==1)].copy(deep=True)])
fb6['imarea'] = 0

#combining this whole mess together
fallback = pd.concat([fb1, fb2, fb3, fb4, fb5, fb6], ignore_index=True)
fallback.rename(columns={'vht':'vht2', 'allvht':'allvht2'}, inplace=True)
fallback.drop(columns='vmt', inplace=True)
fallback.drop_duplicates(['imarea', 'sourceTypeID', 'roadTypeID', 'hourDayID', 'avgSpeedBinID'], inplace=True)
fallback.sort_values(['imarea', 'sourceTypeID', 'roadTypeID', 'hourDayID', 'avgSpeedBinID'], inplace=True)

share = pd.merge(share, fallback, how='left', on=['imarea', 'sourceTypeID', 'roadTypeID', 'hourDayID', 'avgSpeedBinID'])
share.loc[(share['allvht']==0)&~(share['allvht2'].isnull()), 'vht'] = share['vht2']
share.loc[(share['allvht']==0)&~(share['allvht2'].isnull()), 'allvht'] = share['allvht2']
share.eval('avgSpeedFraction = vht / allvht', inplace=True)


## -- AvgSpeedDistribution excel sheet -- ##

avg_speed_dist = share[['imarea', 'sourceTypeID', 'roadTypeID', 'hourDayID', 'avgSpeedBinID','avgSpeedFraction']]

outIM_avgspeeddistribution = avg_speed_dist.loc[(avg_speed_dist['imarea']==1)].drop(columns='imarea')
outIM_avgspeeddistribution.to_excel(xlsx_IM, sheet_name='AvgSpeedDistribution', index=False)

outnoIM_avgspeeddistribution = avg_speed_dist.loc[(avg_speed_dist['imarea']==0)].drop(columns='imarea')
outnoIM_avgspeeddistribution.to_excel(xlsx_noIM, sheet_name='AvgSpeedDistribution', index=False)


######################################
## -- road type distribution tab -- ##
######################################

roadtype = b.groupby(['imarea','sourceTypeID','roadTypeID']).agg({'vmt':'sum'}).reset_index()
roadtype2 = b.groupby(['imarea','sourceTypeID']).agg({'vmt':'sum'}).rename(columns={'vmt':'sourceVMT'}).reset_index()

roadtype = pd.merge(roadtype, roadtype2, how='left', on=['imarea','sourceTypeID'])

#ensure correct datatypes
for f in ['sourceTypeID', 'roadTypeID', 'imarea']:
    roadtype[f] = roadtype[f].astype('int')
for f in ['vmt','sourceVMT']:
    roadtype[f] = roadtype[f].astype('float')


# -- use surrogates to replace missing values if necessary

#bus part1: use roadTypeID 4 to replace missing values for roadTypeID 2 for sourceTypeID 41,42,43 for IM area
fb1 = roadtype.loc[(roadtype['sourceTypeID']==42)&(roadtype['roadTypeID']==4)&(roadtype['imarea']==1)].copy(deep=True)
fb1_a = fb1.copy()
fb1_a['roadTypeID'] = 2
fb1_b = fb1_a.copy()
fb1_b['sourceTypeID'] = 41
fb1_c = fb1_b.copy()
fb1_c['sourceTypeID'] = 43
fb1 = pd.concat([fb1_a, fb1_b, fb1_c], ignore_index=True)

#bus part2: use sourcetypeID 41, 42, 43 for IM area to replace missing values for non-IM area
fb2 = pd.concat([fb1, roadtype.loc[(roadtype['sourceTypeID'].isin([41,42,43]))&(roadtype['imarea']==1)].copy(deep=True)], ignore_index=True)
fb2['imarea'] = 0

#SU long-haul truck part1: use sourcetypeID 52 to replace missing values for sourceTypeID 53,54 for IM area
fb3 = roadtype.loc[(roadtype['sourceTypeID']==52)&(roadtype['imarea']==1)].copy(deep=True)
fb3_a = fb3.copy()
fb3_a['sourceTypeID'] = 53
fb3_b = fb3_a.copy()
fb3_b['sourceTypeID'] = 54
fb3 = pd.concat([fb3_a, fb3_b], ignore_index=True)

#SU long-hault truck part2: use sourcetypeID 52. 53. 54 for IM area to replace missing values for non-IM area
fb4 = pd.concat([fb3, roadtype.loc[(roadtype['sourceTypeID']==52)&roadtype['imarea']==1].copy(deep=True)])
fb4['imarea']=0

#MU long-haul truck part1: use sourceTypeID 61 to replace missing values for sourcetypeID 62 for IM area
fb5 = roadtype.loc[(roadtype['sourceTypeID']==61)&(roadtype['imarea']==1)].copy(deep=True)
fb5['sourceTypeID'] = 62

#MU long-haul truck part2: use sourceTypeID 61,62 for IM area to replace missing values for non-IM area
fb6 = pd.concat([fb5, roadtype.loc[(roadtype['sourceTypeID']==61)&(roadtype['imarea']==1)].copy(deep=True)])
fb6['imarea'] = 0

fallback = pd.concat([fb1,fb2,fb3,fb4,fb5,fb6]).rename(columns={'vmt':'vmt2', 'sourceVMT':'sourceVMT2'}).sort_values(['imarea','sourceTypeID','roadTypeID']).drop_duplicates(['imarea','sourceTypeID','roadTypeID'])

roadtype = pd.merge(roadtype, fallback, how='left', on=['imarea', 'sourceTypeID', 'roadTypeID'])
# roadtype.loc[(roadtype['sourceVMT']==0)&~(roadtype['sourceVMT2'].isnull()), ['vmt', 'sourceVMT']] = roadtype[['vmt2', 'sourceVMT2']]
roadtype.loc[(roadtype['sourceVMT']==0)&~(roadtype['sourceVMT2'].isnull()), 'vmt'] = roadtype['vmt2']
roadtype.loc[(roadtype['sourceVMT']==0)&~(roadtype['sourceVMT2'].isnull()), 'sourceVMT'] = roadtype['sourceVMT2']

#prevent division by zero
def abovezero(x):
    return np.maximum(x,0.000001)
roadtype['sourceVMT'] = roadtype['sourceVMT'].apply(abovezero)

roadtype.eval('roadTypeVMTFraction = vmt / sourceVMT', inplace=True)
roadtype['roadTypeVMTFraction'] = roadtype['roadTypeVMTFraction'].round(6)


## -- RoadTypeDistribution excel sheet -- ##
outIM_roadtypedistribution = roadtype.loc[roadtype['imarea']==1,['sourceTypeID','roadTypeID','roadTypeVMTFraction']].copy()
outIM_roadtypedistribution.to_excel(xlsx_IM, sheet_name='RoadTypeDistribution', index=False)

outnoIM_roadtypedistribution = roadtype.loc[(roadtype['imarea']==0),['sourceTypeID', 'roadTypeID', 'roadTypeVMTFraction']].copy()
outnoIM_roadtypedistribution.to_excel(xlsx_noIM, sheet_name='RoadTypeDistribution', index=False)


#############################
## -- Ramp Fraction Tab -- ##
#############################

rmp = links.loc[links['roadTypeID'].isin([2,4])].copy(deep=True)
rmp.eval('fwyvht = auto_vht + bplate_vht + sush_vht + mtrucklh_vht + htruck_vht + htrucklh_vht + bus_vht', inplace=True)
rmp.eval('fwyvmt = auto_vmt + bplate_vmt + sush_vmt + mtrucklh_vmt + htruck_vmt + htrucklh_vmt + bus_vmt', inplace=True)
rmp['rampvht'] = np.where(rmp['isramp']==1, rmp['fwyvht'], 0)
rmp['rampvmt'] = np.where(rmp['isramp']==1, rmp['fwyvmt'], 0)

ramp = rmp.groupby(['imarea','roadTypeID']).agg({'fwyvht':'sum','rampvht':'sum','fwyvmt':'sum','rampvmt':'sum'}).reset_index()
ramp.eval('rampFraction = rampvht/fwyvht', inplace=True)
ramp['rampFraction'] = ramp['rampFraction'].round(6)
ramp.eval('vmtFraction = rampvmt/fwyvmt', inplace=True)
ramp['vmtFraction'] = ramp['vmtFraction'].round(6)

#ramp fraction to excel
outIM_rampfraction = ramp.loc[ramp['imarea']==1,['roadTypeID','rampFraction']]
outIM_rampfraction.to_excel(xlsx_IM, sheet_name='RampFraction', index=False)

outnoIM_rampfraction = ramp.loc[(ramp['imarea']==0),['roadTypeID','rampFraction']]
outnoIM_rampfraction.to_excel(xlsx_noIM, sheet_name='RampFraction', index=False)


###################################
## -- Hourly VMT Fraction Tab -- ##
###################################

#create template of all combos -- sourceTypeID, roadTypeID, dayID, hourID, imarea
    #the following exist further up the script: 
        # veh = b['sourceTypeID'].unique().tolist()
road = b['roadTypeID'].unique().tolist()
        # hrday = b['hourDayID'].unique().tolist()
        # imcat = b['imarea'].unique().tolist()

#add roadtype 1:
road.append(1)

#create separate hrID and dayID
hourID = []
for item in hrday:
    hourID.append((item - 5)/10)
dayID = [5]

#cartesian product of the lists listed above
template_values = list(product(veh, road, hourID, dayID, imcat))
template2 = pd.DataFrame(template_values, columns=['sourceTypeID', 'roadTypeID', 'hourID', 'dayID', 'imarea'])
template2.sort_values(['imarea', 'sourceTypeID', 'roadTypeID', 'hourID'], inplace=True)
vmt = b.copy()
vmt['hourID'] = (vmt['hourDayID'] - 5)/10

hourvmt = vmt.groupby(['imarea','sourceTypeID','roadTypeID','hourID']).agg({'vmt':'sum'}).reset_index()
sumvmt = hourvmt.groupby(['imarea', 'sourceTypeID','roadTypeID']).agg({'vmt':'sum'}).reset_index()
sumvmt.rename(columns={'vmt':'allvmt'},inplace=True)

vmtshare = pd.merge(hourvmt, sumvmt, how='left', on=['imarea','sourceTypeID','roadTypeID'])
vmtshare.sort_values(['imarea','sourceTypeID','roadTypeID','hourID'],inplace=True)


## -- use surrogates to replace missing values, if necessary

#bus part 1: use sourcetypeid 42 to replace missing values for sourceTypeID 41,43 for IM area
fb1 = vmtshare.loc[(vmtshare['sourceTypeID']==42)&(vmtshare['imarea']==1)].copy()
fb1_a = fb1.copy()
fb1_a['sourceTypeID'] = 41
fb1_b = fb1.copy()
fb1_b['sourceTypeID'] = 43
fb1 = pd.concat([fb1_a, fb1_b], ignore_index=True)

#bus part2: use sourcetypeID 41,42,43 for IM area to replace missing values for non-IM area
fb2 = pd.concat([fb1, vmtshare.loc[(vmtshare['sourceTypeID'].isin([41,42,43]))&(vmtshare['imarea']==1)&(vmtshare['allvmt']>0)].copy()], ignore_index=True)
fb2['imarea'] = 0

#su long-haul truck part1: use sourceTypeID 52 to replace missing values for sourcetypeID 53,54 for im area
fb3 = vmtshare.loc[(vmtshare['sourceTypeID']==52)&(vmtshare['imarea']==1)].copy()
fb3_a = fb3.copy()
fb3_a['sourceTypeID'] = 53
fb3_b = fb3.copy()
fb3_b['sourceTypeID'] = 54
fb3 = pd.concat([fb3_a, fb3_b], ignore_index=True)

#su long haul truck part2: use sourceTypeID 52,53,54 for IM area to replace missing values for non-IM area
fb4 = pd.concat([fb3, vmtshare.loc[(vmtshare['sourceTypeID'].isin([52,53,54]))&(vmtshare['imarea']==1)&(vmtshare['allvmt']>0)].copy()], ignore_index=True)
fb4['imarea'] = 0

#mu long-haul truck part 1: use sourcetypeID 61 to replace missing values for sourcetypeid 62 for im area
fb5 = vmtshare.loc[(vmtshare['sourceTypeID']==61)&(vmtshare['imarea']==1)].copy()
fb5['sourceTypeID'] = 62

#mu long-haul truck part2: use sourcetypeid 61,62 for IM area to replace missing values for non-IM area
fb6 = pd.concat([fb5, vmtshare.loc[(vmtshare['sourceTypeID'].isin([61,62]))&(vmtshare['imarea']==1)&(vmtshare['allvmt']>0)].copy()],ignore_index=True)
fb6['imarea'] = 0

fallback = pd.concat([fb1, fb2, fb3, fb4, fb5, fb6], ignore_index=True).sort_values(['imarea','sourceTypeID','roadTypeID','hourID'])
fallback.rename(columns={'vmt':'vmt2', 'allvmt':'allvmt2'},inplace=True)
fallback.drop_duplicates(subset=['imarea','sourceTypeID','roadTypeID','hourID'], inplace=True)


vmtshare = pd.merge(vmtshare, fallback, how='left', on=['imarea', 'sourceTypeID', 'roadTypeID', 'hourID'])


#calculates hourvmtfraction based on original data
vmtshare['hourVMTFraction1'] = np.where(vmtshare['allvmt']>0.000001, vmtshare['vmt']/vmtshare['allvmt'], vmtshare['vmt']/0.000001)
#calculates hourvmtfraction based on fallback data
vmtshare.loc[~(vmtshare['vmt2'].isnull())&~(vmtshare['allvmt2'].isnull()), 'hourVMTFraction2'] = vmtshare['vmt2'] / vmtshare['allvmt2']


#for sourcetypes 53,54 if there is any data
#then use both the non-zero vmt and the fallback data to arrive at the hourVMTFraction

truckpart = vmtshare.loc[(vmtshare['sourceTypeID'].isin([53,54]))&(vmtshare['vmt']>0)].copy()
vmtcount = truckpart.groupby(['imarea','sourceTypeID','roadTypeID']).agg({'vmt':'count'}).reset_index()
vmtcount.rename(columns={'vmt':'vmtcount1'},inplace=True)


vmtweight = pd.merge(vmtshare, vmtcount, how='left', on=['imarea', 'sourceTypeID', 'roadTypeID'])
vmtweight2 = vmtweight.copy()
#use fallback vmtfraction for 0 vmt hours
vmtweight2.loc[(vmtweight2['sourceTypeID'].isin([53,54]))&(vmtweight2['allvmt']>0)&(vmtweight2['vmt']==0), 'hourVMTFractionpre'] = vmtweight2['hourVMTFraction2']

#use average of the original and fallback vmtfraction otherwise
#original data is weighted by number of hours with data
vmtweight2.loc[(vmtweight2['sourceTypeID'].isin([53,54]))&(vmtweight2['allvmt']>0)&(vmtweight2['vmt']>0), 'hourVMTFractionpre'] = (((vmtweight2['vmtcount1']/24)*vmtweight2['hourVMTFraction1'])+vmtweight2['hourVMTFraction2'])/((vmtweight2['vmtcount1']+24)/24)


vmtpre = vmtweight2.groupby(['imarea','sourceTypeID','roadTypeID']).agg({'hourVMTFractionpre':'sum'}).reset_index()
vmtpre.rename(columns={'hourVMTFractionpre':'vmtpresum'},inplace=True)


vmtshare = pd.merge(vmtweight2, vmtpre, how='left', on=['imarea','sourceTypeID','roadTypeID']).sort_values(['imarea','sourceTypeID','roadTypeID','hourID'])
vmtshare.loc[vmtshare['allvmt']==0, 'vmt3'] = vmtshare['vmt']
vmtshare.loc[vmtshare['allvmt']==0, 'allvmt3'] = vmtshare['allvmt']


#substitution if no VMT for entire category
vmtshare.loc[(vmtshare['allvmt']==0)&(vmtshare['allvmt2']!=0), 'allvmt'] = vmtshare['allvmt2']
vmtshare.loc[(vmtshare['vmt']==0)&(vmtshare['vmt2']!=0), 'vmt'] = vmtshare['vmt2']
vmtshare.loc[((vmtshare['allvmt']==0)|(vmtshare['allvmt'].isnull()))&~(vmtshare['allvmt2'].isnull()), 'vmt'] = vmtshare['vmt2']
vmtshare.loc[((vmtshare['allvmt']==0)|(vmtshare['allvmt'].isnull()))&~(vmtshare['allvmt2'].isnull()), 'allvmt'] = vmtshare['allvmt2']

#prevent division by zero
vmtshare['allvmt'] = np.maximum(vmtshare['allvmt'], 0.000001)
vmtshare.eval('hourVMTFraction = vmt / allvmt', inplace=True)
vmtshare['hourVMTFraction'] = vmtshare['hourVMTFraction'].round(6)

vmtshare.loc[(vmtshare['sourceTypeID'].isin([53,54]))&(vmtshare['vmtpresum']>0), 'hourVMTFraction'] = vmtshare['hourVMTFractionpre'] / vmtshare['vmtpresum']
vmtshare['hourVMTFractionpre'] = vmtshare['hourVMTFractionpre'].round(6)

vmtshare.drop(columns=['vmtpresum','hourVMTFraction1','hourVMTFraction2','hourVMTFractionpre','vmtcount1'], inplace=True)

#apply urban arterial distribution to Off-Network type
vmtshare_b = vmtshare.copy()
vmtshare_b.loc[vmtshare_b['roadTypeID']==5, 'roadTypeID'] = 1 

vmtshare = pd.concat([vmtshare, vmtshare_b], ignore_index=True).sort_values(['imarea','sourceTypeID','roadTypeID','hourID'])

vmtshare = pd.merge(template2, vmtshare, how='left', on=['imarea','sourceTypeID','roadTypeID','hourID'])


#final vmt fraction to excel
outIM_hourvmtfraction = vmtshare.loc[vmtshare['imarea']==1, ['sourceTypeID','roadTypeID','dayID','hourID','hourVMTFraction']]
outIM_hourvmtfraction.to_excel(xlsx_IM, sheet_name='hourVMTFraction', index=False)

outnoIM_hourvmtfraction = vmtshare.loc[vmtshare['imarea']==0, ['sourceTypeID','roadTypeID','dayID','hourID','hourVMTFraction']]
outnoIM_hourvmtfraction.to_excel(xlsx_noIM, sheet_name='hourVMTFraction', index=False)


######################################################
## -- VMT by road type and HPMS vehicle type tab -- ##
######################################################

#modeled vehicle types only
hpms = b.loc[b['sourceTypeID'].isin([21,31,32,42,52,53,61,62])].copy()

# key = { 'sourceTypeID' : 'HPMSVtypeID' }
key = {
    21:25,
    32:25,
    42:40, #transit bus vmt only
    52:50,
    53:50,
    61:60,
    62:60
}

hpms['HPMSVtypeID'] = hpms['sourceTypeID'].map(key)
hpms1 = hpms.groupby(['imarea', 'roadTypeID', 'HPMSVtypeID']).agg({'vmt':'sum'}).reset_index()
hpms1.rename(columns={'vmt':'HPMSDailyVMT'}, inplace=True)

#final vmt fraction to excel
outIM_hpmsdailyvmt = hpms1.loc[hpms1['imarea']==1, ['roadTypeID','HPMSVtypeID','HPMSDailyVMT']]
outIM_hpmsdailyvmt['year'] = scenyear
outIM_hpmsdailyvmt.to_excel(xlsx_IM, sheet_name='HPMSDailyVMT', index=False)

outnoIM_hpmsdailyvmt = hpms1.loc[hpms1['imarea']==0, ['roadTypeID','HPMSVtypeID','HPMSDailyVMT']]
outnoIM_hpmsdailyvmt['year'] = scenyear
outnoIM_hpmsdailyvmt.to_excel(xlsx_noIM, sheet_name='HPMSDailyVMT', index=False)



xlsx_IM.close()
xlsx_noIM.close()

print('Done!')

## ---------------- END CREATE MOVES INPUT FILE (SAS) ------------------