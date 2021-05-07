# -*- coding: utf-8 -*-
"""
Created on Sat May  1 22:17:10 2021

@author: Miche
"""


import pandas as pd
import numpy as np
import os
from os.path import dirname, join

from bokeh.plotting import figure
from bokeh.io import show, output_notebook, curdoc
from bokeh.models import ColumnDataSource, FactorRange, Legend, HoverTool, GeoJSONDataSource, \
                        LinearColorMapper, ColorBar, NumeralTickFormatter, Div, Select, TableColumn, \
                        DataTable, CheckboxGroup, Tabs, Panel, CheckboxButtonGroup
from bokeh.application.handlers import FunctionHandler
from bokeh.application import Application
from bokeh.palettes import Category20c, Pastel1, Set3, Blues
from bokeh.layouts import column, row, WidgetBox, gridplot
from bokeh.embed import file_html
from bokeh.resources import CDN
from bokeh.tile_providers import get_provider, Vendors
from bokeh.transform import linear_cmap,factor_cmap

import pathlib

# Define paths.
dir_path = os.path.dirname(os.path.realpath(__file__))

PATH_DATA = pathlib.Path(os.path.join(dir_path, 'data'))
PATH_OUTPUT = pathlib.Path(os.path.join(dir_path, 'output'))
if not PATH_OUTPUT.exists():
    PATH_OUTPUT.mkdir()


df = pd.read_csv(PATH_DATA/'data.csv')

df_new = df #laziness 

# Define function to switch from lat/long to mercator coordinates
def x_coord(x, y):
    
    lat = x
    lon = y
    
    r_major = 6378137.000
    x = r_major * np.radians(lon)
    scale = x/lon
    y = 180.0/np.pi * np.log(np.tan(np.pi/4.0 + 
        lat * (np.pi/180.0)/2.0)) * scale
    return (x, y)


def make_dataset(selectedState, selectedKitchen, selectedType, selectedPrice):
    df_ = df_new.copy()
    df_empty = pd.DataFrame()
    if selectedPrice == 'No Preference':  
        if selectedState != 'All':
            df_ = df_[df_['state_name'] == selectedState]
        if selectedKitchen != 'All':
            df_ = df_[df_['cat_kitchen'] == selectedKitchen]
        if selectedType != 'All':
            df_ = df_[df_['cat_type'] == selectedType]
    else:
        for i, price in enumerate(selectedPrice):
            # Subset to the carrier
            subset = df_[df_['PriceRange'] == price]
            df_empty = df_empty.append(subset)
            
        if selectedState != 'All':
            df_empty = df_empty[df_empty['state_name'] == selectedState]
        if selectedKitchen != 'All':
            df_empty = df_empty[df_empty['cat_kitchen'] == selectedKitchen]
        if selectedType != 'All':
            df_empty = df_empty[df_empty['cat_type'] == selectedType]
    
    if selectedPrice == 'No Preference':
        df_ = df_
    else:
        df_ = df_empty


    # Preparing with long/lat coordinates 
    df_['coordinates'] = list(zip(df_['latitude'], df_['longitude']))
    # Obtain list of mercator coordinates
    mercators = [x_coord(x, y) for x, y in df_['coordinates'] ]

    # Create mercator column in our df
    df_['mercator'] = mercators
    # Split that column out into two separate columns - mercator_x and mercator_y
    df_[['mercator_x', 'mercator_y']] = df_['mercator'].apply(pd.Series)

    #title for the plot  
    div_title = Div(text="<b> Restaurant matching Preferences: {} </b>".format(len(df_['name'].unique())),
               style={'font-size': '150%'})
    
    # Convert dataframe to column data source
    return ColumnDataSource(df_), div_title

def make_plot(source):


    #table in the plot
    columns = [
        TableColumn(field="name", title="Restaurant Name", width=100),
        TableColumn(field="stars", title="Stars", width=50),
        TableColumn(field="state_name", title="State", width=80),
        TableColumn(field="city", title="City", width=80),
        TableColumn(field="cat_kitchen", title="Kitchen", width=110),
        TableColumn(field="cat_type", title="Type", width=100),
        TableColumn(field="PriceRange", title="Price", width=60)
    ]
    table = DataTable(source=source, columns=columns, width=660, height=200, fit_columns=False)

    #Map layout of North America
    tooltips = [("Restaurant","@name"), ("Stars", "@stars")]

    p = figure(x_axis_type="mercator", y_axis_type="mercator", 
           x_axis_label = 'Longitude', y_axis_label = 'Latitude', 
           tooltips = tooltips, plot_width=500, plot_height=500, 
           toolbar_location='below', tools="pan,wheel_zoom,reset", 
            active_scroll='auto')

    p.circle(x = 'mercator_x', y = 'mercator_y', color = 'lightblue', source=source, 
         size=10, fill_alpha = 0.7)

    chosentile = get_provider(Vendors.CARTODBPOSITRON)
    p.add_tile(chosentile)

    return table, p

# Update maps
def update(attr, old, new):
    
    # Get the list of carriers for the graph
    selectedState = select_state.value
    selectedKitchen = select_kitchen.value
    selectedType = select_type.value
    selectedPrice = [select_price.labels[i] for i in select_price.active]
    
    # Make a new dataset based on the selected filters and the make_dataset function defined earlier
    new_src, div_title = make_dataset(selectedState, selectedKitchen, selectedType, selectedPrice)
    # Update the source used in the quad glpyhs
    src.data.update(new_src.data)
    
    layout.children[0] = div_title

    
#selection the different filters
div_subtitle = Div(text="<i> Filter with the data and find your favorite restaurant </i>")

# User select: State
div_state = Div(text="<b> Select State </b>")
state = ['All']+df_new['state_name'].unique().tolist()
select_state = Select(options=state, value=state[0]) #by default All is chosen
select_state.on_change('value', update)

# User select: Kitchen
div_kitchen = Div(text="<b> Select Kitchen </b>")
kitchen = ['All']+df_new['cat_kitchen'].unique().tolist()
select_kitchen = Select(options=kitchen, value=kitchen[0]) #by default All is chosen
select_kitchen.on_change('value', update)

# User select: Type
div_type = Div(text="<b> Select Type </b>")
types = ['All']+df_new['cat_type'].unique().tolist()
select_type = Select(options=types, value=types[0]) #by default All is chosen
select_type.on_change('value', update)

# User select : Price Range
div_price = Div(text="<b> Select Price </b>")
price_range = ['$','$$','$$$','$$$$','Unknown']
select_price = CheckboxButtonGroup(labels=price_range, active=[2,3])
select_price.on_change('active', update)

#initial source and plot
initial_select_price = [select_price.labels[i] for i in select_price.active]

src, div_title = make_dataset(select_state.value,select_kitchen.value, select_type.value, initial_select_price)
table, p = make_plot(src)

# Combine all controls to get in column
col_tab_plot = row(table, p, height=200, width=1200)
col_filters_1 = column(div_state, select_state, div_kitchen, select_kitchen , width=290)
col_filters_2 = column(div_type, select_type, div_price, select_price, width=290)

# Layout
layout = column(div_title, div_subtitle, col_tab_plot, row(col_filters_1,col_filters_2)) 
#it is possible to add multiple col_filters in the row(), you just need to specify it above
curdoc().add_root(layout)


# [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/Restaurant-Guide/interactive-bokeh.git/main?urlpath=%2Fproxy%2F5006%2Fbokeh-app)
# https://mybinder.org/v2/gh/Restaurant-Guide/interactive-bokeh.git/main?urlpath=%2Fproxy%2F5006%2Fbokeh-app