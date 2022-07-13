import os
import param
import altair as alt
import panel as pn
import numpy as np
pn.extension('plotly','vega')
import pandas as pd

####################################################################################################
#SEEME Fast version
#
####################################################################################################
def get_file_data(out_file):
    # name of the CSV
    n_file = out_file      # file name
    location = 'Output_Data'               # file address 
    n_file_r = pd.read_csv(os.path.join(location , n_file), low_memory=False)
    #names of tech  The file Tech_names contains a dictionary with the techs and easy names for the Goa model
    
    #names of tech elecetrcity
    elec_en = pd.read_excel('Tech_names_Goa.xlsx', sheet_name='Power', usecols='A,B,D')
    #names of other sectors
    fe_en = pd.read_excel('Tech_names_Goa.xlsx', sheet_name='sectoral_mix', usecols='A,D')
    #tn names of all tech joined for emissions
    emi_en = pd.concat([elec_en,fe_en], ignore_index=True)
    # alias for primary names
    pe_en = pd.read_excel('Tech_names_Goa.xlsx', sheet_name='primary_e', usecols='A,B')
    #sectorial mix
    sector_names = pd.read_excel('Tech_names_Goa.xlsx', usecols='A, B,C,D', sheet_name='sectoral_mix')
    #Transport names
    sector_namesT = sector_names[sector_names['Sector'].isin(['Public','Private','Freight'])] # to use in rate of use by tech for the transport
    # Other Demand sectors
    sector_namesOTH = sector_names[~sector_names['Sector'].isin(['Public','Private','Freight'])]
    
    ## Reading csv file and segregating
    act = n_file_r.loc[n_file_r.NAME=='ProdByTech']
    pe = n_file_r.loc[n_file_r.NAME=='ProdAnn']
    new_cap = n_file_r.loc[n_file_r.NAME=='NewCapacity']
    tot_cap = n_file_r.loc[n_file_r.NAME=='TotCapacityAnn']
    dem = n_file_r.loc[n_file_r.NAME=='RateOfUseByTech']
    aet = n_file_r.loc[n_file_r.NAME=='AnnTechEmission']
    inv = n_file_r.loc[n_file_r.NAME=='DiscCapitalInvestment']

    sply = act.copy()
    sply = (pd.merge(sply, pe_en[['TECHNOLOGY', 'primary_names']] , on='TECHNOLOGY'))
    sply = sply.groupby(['YEAR','primary_names'], as_index=False).sum()
    sply = sply[sply['VALUE'] > 0]

    trp = (pd.merge(dem.copy(), sector_namesT[['TECHNOLOGY', 'Tech_name','Sector','Fuel']] , on='TECHNOLOGY'))
    trp = trp.groupby(['YEAR','Tech_name','Sector','Fuel'], as_index=False).mean()

    oth = (pd.merge(act.copy(), sector_namesOTH[['TECHNOLOGY', 'Tech_name','Sector','Fuel']] , on='TECHNOLOGY'))

    final_energy_all = pd.concat([trp,oth])
    final_energy_fuel = final_energy_all.groupby(['YEAR','Fuel'], as_index=False).sum()
    final_energy_sec = final_energy_all.groupby(['YEAR','Sector'], as_index=False).sum()

    final_energy_fuel = final_energy_fuel[final_energy_fuel['VALUE'] > 0]
    final_energy_sec = final_energy_sec[final_energy_sec['VALUE'] > 0]
    
    #Emissions

    #annual emission by tech
    aet = (pd.merge(aet, emi_en, on='TECHNOLOGY'))
    aet = aet.groupby(['YEAR','Tech_name'], as_index=False).sum()
    aet = aet[aet['VALUE'] > 0]
    #remove unused categories
    aet.drop(aet.columns[3:], axis=1, inplace=True)
    # To aggregate by sector
    aet["Sector"] = [sector[0] for sector in aet['Tech_name'].str.split('-')]
    # Capital Investments
    
    trp_corr = pd.read_excel('Transport_correction.xlsx').set_index('Tech_name').to_dict()
    new_inv = inv.copy()
    new_inv = (pd.merge(new_inv, emi_en, on='TECHNOLOGY'))
    new_inv.drop(new_inv.iloc[:, 2:13], axis=1, inplace=True)
    for key,value in trp_corr['km'].items():
        new_inv.loc[new_inv['Tech_name'].str.contains(key+'-'), 'VALUE'] /= value
    new_inv.drop(new_inv.columns[-1], axis=1, inplace=True)
    new_inv["Sector"] = [sector[0] for sector in new_inv['Tech_name'].str.split('-')]
    #  Electrcity Production

    p_tech = act.copy()
    #only for the electricity sector
    p_tech = p_tech.loc[p_tech['FUEL'].isin(np.array(elec_en['Electr']))]
    p_tech = (pd.merge(p_tech, elec_en[['TECHNOLOGY', 'Tech_name']] , on='TECHNOLOGY'))
    p_tech = p_tech.groupby(['YEAR','Tech_name', 'TIMESLICE'], as_index=False).sum() 
    p_tech.drop(p_tech.columns[4:], axis=1, inplace=True)
    #  Electrcity Capacity
    tot_cap = tot_cap.loc[tot_cap['TECHNOLOGY'].isin(np.array(elec_en['TECHNOLOGY']))]
    tot_cap = (pd.merge(tot_cap, elec_en[['TECHNOLOGY', 'Tech_name']] , on='TECHNOLOGY'))
    tot_cap = tot_cap.groupby(['YEAR','Tech_name'], as_index=False).sum()
    tot_cap.drop(tot_cap[tot_cap.Tech_name == 'IEX-Imports'].index, inplace=True)
    tot_cap.drop(tot_cap[tot_cap.Tech_name == 'RE-Imports'].index, inplace=True)
    tot_cap.drop(tot_cap.columns[3:], axis=1, inplace=True)
    return {'Primary':sply,
    'Final_Fuel':final_energy_fuel, 
    'Final_Sector':final_energy_sec, 
    'Emissions':aet, 
    'Investments':new_inv,
    "Electricity":p_tech,
    "Power_Plants":tot_cap,
    "Sectoral_Mix":final_energy_all
    }

def get_charts(all_data):
    ######################
    # PRIMARY ENERGY
    ######################
    base = alt.Chart(all_data["Primary"].dropna(),width=614,height=437)
    selection = alt.selection_multi(fields=['primary_names'],bind='legend')
    grouped = base.mark_area().encode(
                    alt.X("YEAR:N",axis=alt.Axis(labelFontSize=15,labelAngle=270,titleFontSize=20)),
                    alt.Y("sum(VALUE)",title='Primary Energy in PJ',axis=alt.Axis(labelFontSize=15,labelAngle=0,titleFontSize=20)),
                    alt.Color('primary_names'),
                    opacity = alt.condition(selection, alt.value(1), alt.value(0.1)),
                    tooltip=['primary_names','YEAR','sum(VALUE)']
                ).add_selection(selection).interactive()
    text = base.mark_text(dx=0,dy=-40, color='black').encode(
        x=alt.X('YEAR:N', stack='zero'),
        y=alt.Y('sum(VALUE)'),
        text=alt.Text('sum(VALUE)', format='.2f')
    )

    # Each sector plot filtered by clicking the stacked plot
    one_group = grouped.mark_bar().encode(
        alt.Y("sum(VALUE)",title='Primary Energy in PJ',axis=alt.Axis(labelFontSize=15,labelAngle=0,titleFontSize=20)),
        alt.Color('primary_names'), 
        tooltip=['primary_names','sum(VALUE)','YEAR'],
        row='primary_names',
    ).transform_filter( 
        selection
    ).interactive()
    pe_chart = grouped&one_group
    ######################
    ## Final Energy by Fuel and Sectors
    ######################
    fe_fuel = alt.Chart(all_data["Final_Fuel"].dropna(),width=614,height=437)
    fe_sec = alt.Chart(all_data["Final_Sector"].dropna(),width=614,height=437)

    selection = alt.selection_multi(fields=['Fuel'],bind='legend')

    fe_by_fuel = fe_fuel.mark_area().encode(
                    alt.X("YEAR:N",axis=alt.Axis(labelFontSize=15,labelAngle=270,titleFontSize=20)),
                    alt.Y("sum(VALUE)",title='Final Energy in PJ',axis=alt.Axis(labelFontSize=15,labelAngle=0,titleFontSize=20)),
                    alt.Color('Fuel'),
                    opacity = alt.condition(selection, alt.value(1), alt.value(0.1)),
                    tooltip=['Fuel','YEAR','sum(VALUE)']
                ).add_selection(selection).interactive()

    fe_by_sec = fe_sec.mark_area().encode(
                    alt.X("YEAR:N",axis=alt.Axis(labelFontSize=15,labelAngle=270,titleFontSize=20)),
                    alt.Y("sum(VALUE)",title='Final Energy in PJ',axis=alt.Axis(labelFontSize=15,labelAngle=0,titleFontSize=20)),
                    alt.Color('Sector'),
                    opacity = alt.condition(selection, alt.value(1), alt.value(0.1)),
                    tooltip=['Sector','YEAR','sum(VALUE)']
                ).add_selection(selection).interactive()

    # Each sector plot filtered by clicking the stacked plot
    one_fuel = fe_by_fuel.mark_area().encode(
        alt.Y("sum(VALUE)",title='Final Energy in PJ',axis=alt.Axis(labelFontSize=15,labelAngle=0,titleFontSize=20)),
        alt.Color('Fuel'), 
        tooltip=['Fuel','sum(VALUE)','YEAR'],
        row='Fuel',
    ).transform_filter( 
        selection
    ).interactive()

    one_sec = fe_by_sec.mark_area().encode(
        alt.Y("sum(VALUE)",title='Final Energy in PJ',axis=alt.Axis(labelFontSize=15,labelAngle=0,titleFontSize=20)),
        alt.Color('Sector'), 
        tooltip=['Sector','sum(VALUE)','YEAR'],
        row='Sector',
    ).transform_filter( 
        selection
    ).interactive()
    
    fe_fuel_chart = fe_by_fuel&one_fuel
    fe_sec_chart = fe_by_sec&one_sec
    ######################
    ## Emissions
    ######################
    emissions = alt.Chart(all_data["Emissions"].dropna(),width=614,height=437)
    selection = alt.selection_multi(fields=['Sector'],bind='legend')
    tot_emi_by_year = emissions.mark_area().encode(
                    alt.X("YEAR:N",axis=alt.Axis(labelFontSize=15,labelAngle=270,titleFontSize=20)),
                    alt.Y("sum(VALUE)",title='Emissions in TTCO2e',axis=alt.Axis(labelFontSize=15,labelAngle=0,titleFontSize=20)),
                    alt.Color('Sector'),
                    opacity = alt.condition(selection, alt.value(1), alt.value(0.1)),
                    tooltip=['YEAR','Sector','sum(VALUE)']
                ).add_selection(selection).interactive()
    # Each sector plot filtered by clicking the stacked plot
    one_emi = tot_emi_by_year.mark_bar().encode(
        alt.Y("sum(VALUE)",title='Emissions in TTCO2e',axis=alt.Axis(labelFontSize=15,labelAngle=0,titleFontSize=20)),
        alt.Color('Sector'), 
        tooltip=['Tech_name','sum(VALUE)','YEAR'],
        row='Sector',
    ).transform_filter( 
        selection
    ).interactive()
    emi_chart = tot_emi_by_year&one_emi
    ######################
    ## CAP INVESTMENT BY SECTOR
    ######################
    capinv = alt.Chart(all_data["Investments"].dropna(),width=614,height=437)
    selection = alt.selection_multi(fields=['Sector'],bind='legend')
    tot_inv_by_year = capinv.mark_area().encode(
                    alt.X("YEAR:N",axis=alt.Axis(labelFontSize=15,labelAngle=270,titleFontSize=20)),
                    alt.Y("sum(VALUE)",title='New Investments in INR Crore',axis=alt.Axis(labelFontSize=15,labelAngle=0,titleFontSize=20)),
                    alt.Color('Sector'),
                    opacity = alt.condition(selection, alt.value(1), alt.value(0.1)),
                    tooltip=['YEAR','Sector','sum(VALUE)']
                ).add_selection(selection).interactive()

    # Each sector plot filtered by clicking the stacked plot
    one_inv = tot_inv_by_year.mark_bar().encode(
        alt.Y("sum(VALUE)",title='New Investments in INR Crore',axis=alt.Axis(labelFontSize=15,labelAngle=0,titleFontSize=20)),
        alt.X("Tech_name",title='Technology',axis=alt.Axis(labelFontSize=15,labelAngle=270,titleFontSize=20)),
        alt.Color('Sector'), 
        tooltip=['Tech_name','sum(VALUE)','YEAR'],
        row='Sector',
    ).transform_filter( 
        selection
    ).interactive()
    inv_chart = tot_inv_by_year & one_inv

    generation = alt.Chart(all_data["Electricity"].dropna(),width=800,height=437)
    selection = alt.selection_multi(fields=['Tech_name'],bind='legend')
    generation_by_year = generation.mark_area().encode(
                    alt.X("YEAR:N",axis=alt.Axis(labelFontSize=15,labelAngle=270,titleFontSize=20)),
                    alt.Y("sum(VALUE)",title='Electricity Generation in PJ',axis=alt.Axis(labelFontSize=15,labelAngle=0,titleFontSize=20)),
                    alt.Color('Tech_name'),
                    opacity = alt.condition(selection, alt.value(1), alt.value(0.1)),
                    tooltip=['YEAR','Tech_name','sum(VALUE)']
                ).add_selection(selection).interactive()
    # Each sector plot filtered by clicking the stacked plot
    one_year = generation_by_year.mark_bar().encode(
        alt.Y("sum(VALUE)",title='Electricity Generation in PJ',axis=alt.Axis(labelFontSize=15,labelAngle=0,titleFontSize=20)),
        alt.X("TIMESLICE:N",title='Electricity Generation in PJ',axis=alt.Axis(labelFontSize=15,labelAngle=0,titleFontSize=20)),
        alt.Color('Tech_name'), 
        tooltip=['Tech_name','sum(VALUE)','YEAR'],
        row='YEAR',
    ).transform_filter( 
        selection
    ).interactive()
    elec_chart = generation_by_year&one_year
    ######################
    ## Total Capacity
    ######################
    totcap = alt.Chart(all_data['Power_Plants'].dropna(),width=614,height=437)
    selection = alt.selection_multi(fields=['Tech_name'],bind='legend')
    tot_cap_by_year = totcap.mark_area().encode(
                    alt.X("YEAR:N",axis=alt.Axis(labelFontSize=15,labelAngle=270,titleFontSize=20)),
                    alt.Y("sum(VALUE)",title='Electricity Capacity in GW',axis=alt.Axis(labelFontSize=15,labelAngle=0,titleFontSize=20)),
                    alt.Color('Tech_name'),
                    opacity = alt.condition(selection, alt.value(1), alt.value(0.1)),
                    tooltip=['YEAR','Tech_name','sum(VALUE)']
                ).add_selection(selection).interactive()
    # Each sector plot filtered by clicking the stacked plot
    one_cap = tot_cap_by_year.mark_bar().encode(
        alt.Y("sum(VALUE)",title='Electricity Generation in PJ',axis=alt.Axis(labelFontSize=15,labelAngle=0,titleFontSize=20)),
        alt.Color('Tech_name'), 
        tooltip=['Tech_name','sum(VALUE)','YEAR'],
        row='Tech_name',
    ).transform_filter( 
        selection
    ).interactive()
    pp_chart = tot_cap_by_year&one_cap
    ######################
    ## Sectoral Mix
    ######################
    sectors = all_data["Sectoral_Mix"].Sector.drop_duplicates().tolist()
    def fe_chart(sector):
        fe_dem = all_data["Sectoral_Mix"].loc[all_data["Sectoral_Mix"].Sector==sector,['YEAR','Tech_name','VALUE']]
        sec_chart = alt.Chart(fe_dem.dropna(),width=614,height=437)
        chart = sec_chart.mark_area().encode(
                    alt.X("YEAR:N",axis=alt.Axis(labelFontSize=15,labelAngle=270,titleFontSize=20)),
                    alt.Y("sum(VALUE)",title='Energy in PJ',axis=alt.Axis(labelFontSize=15,labelAngle=0,titleFontSize=20)),
                    alt.Color('Tech_name'),
                    tooltip=['YEAR','Tech_name','sum(VALUE)']
                )
        return pn.pane.Vega(chart)
        
    sec_chart = pn.interact(fe_chart,sector=sectors)


    return pn.Tabs(('Primary', pe_chart),('Final_Fuel', fe_fuel_chart),('Final_Sector', fe_sec_chart),('Emissions', emi_chart),
    ('Investments', inv_chart),('Electricity', elec_chart),('Power_Plants', pp_chart),('Sectoral_Mix', sec_chart) )

class Plotter(param.Parameterized):
    files = [file for file in os.listdir('Output_Data') if file.endswith('.csv')]
    file_name = param.ObjectSelector(default=files[0],objects=files)
    all_data  = get_file_data(files[0])
    charts = get_charts(all_data)
    
    @param.depends('file_name')
    
    def update_main_plot(self):
        self.all_data = get_file_data(self.file_name)
        self.charts = get_charts(self.all_data)    
        return self.charts
         

viewer = Plotter(name='DST')

from panel.template import DarkTheme

bootstrap = pn.template.BootstrapTemplate(busy_indicator=pn.indicators.LoadingSpinner(value=True, width=30, height=30),logo='tce_logo.jpg',
header_background='cornflowerblue',theme=DarkTheme,title=" Goa RE Plan")
pn.config.sizing_mode = 'stretch_width'
bootstrap.sidebar.append(viewer.param.file_name)
bootstrap.sidebar.append(pn.Column(pn.pane.JPG('tce_logo.jpg',height=50),"Copyright &copy; by The Celestial Earth.<br>All rights reserved.\
             <br>No part of this publication may be reproduced, distributed, or transmitted in any form or by any means, \
            <br>including photocopying, recording, or other electronic or mechanical methods, without the prior written permission \
            <br>of the publisher, except in the case of brief quotations embodied in critical reviews and certain other noncommercial\
            <br> uses permitted by copyright law. For permission requests, write to the publisher, addressed: anindya.b@thecelestialearth.org",
            "Discalimer: <br> This publication has been prepared for general guidance on matters of interest only, and does not constitute \
            <br>professional advice.  You should not act upon the information contained in this publication without obtaining specific professional\
            <br>advice.  No representation or warranty (express or implied) is given as to the accuracy or completeness of the information contained \
            <br> in this publication, and, to the extent permitted by law, The Celestial Earth, its members, employees and agents accept no liability,\
            <br> and disclaim all responsibility, for the consequences of you or anyone else acting, or refraining to act, in reliance on the information\
            <br> contained in this publication or for any decision based on it.",width=250,height=50)
            )
bootstrap.main.append(viewer.update_main_plot)

bootstrap.servable(title='DST')