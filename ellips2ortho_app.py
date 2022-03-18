import pandas as pd
import requests
import streamlit as st
import pydeck as pdk
import zipfile


st.title('Ellipsoidal to Orthometric Heights')
st.caption('The application uses the NGS Geoid API to look up the geoid height at a particular location and uses this value to then compute the orthometric height based on the desired units of the user.')

uploaded_csvs = st.file_uploader('Please Select Geotags CSV.', accept_multiple_files=True)

uploaded = False

for uploaded_csv in uploaded_csvs: 
    if uploaded_csv is not None:
        uploaded = True
    else:
        uplaoded = False

if uploaded:
    dfs = []
    filenames = []
    df_dict = {}
    ctr = 0
    for uploaded_csv in uploaded_csvs:
        df = pd.read_csv(uploaded_csv, index_col=False)       
        dfs.append(df)
        df_dict[uploaded_csv.name] = ctr
        filenames.append(uploaded_csv.name)
        ctr += 1
    st.success('All CSCvs uploaded successfully.')
    
    options = filenames.copy()
    options.insert(0, '<select>')
    option = st.selectbox('Select geotags CSV to visualize', options)
    
    lat = 'latitude [decimal degrees]'
    lon = 'longitude [decimal degrees]'
    height = 'altitude [meter]'
    
    if option != '<select>':
        points_df = pd.concat([dfs[df_dict[option]][lat], dfs[df_dict[option]][lon]], axis=1, keys=['lat','lon'])
        
        st.pydeck_chart(pdk.Deck(
        map_style='mapbox://styles/mapbox/satellite-streets-v11',
        initial_view_state=pdk.ViewState(
            latitude=points_df['lat'].mean(),
            longitude=points_df['lon'].mean(),
            zoom=14,
            pitch=0,
         ),
         layers=[
             pdk.Layer(
                 'ScatterplotLayer',
                 data=points_df,
                 get_position='[lon, lat]',
                 get_color='[70, 130, 180, 200]',
                 get_radius=20,
             ),
             ],
         ))

    # Select Geoid Model

    geoid_dict = {'GEOID99': 1,
                  'G99SSS': 2,
                  'GEOID03': 3,
                  'USGG2003': 4,
                  'GEOID06': 5,
                  'USGG2009': 6,
                  'GEOID09': 7,
                  'The latest experimental Geoid (XUSHG)': 9,
                  'USGG2012': 11,
                  'GEOID12A': 12,
                  'GEOID12B': 13,
                  'GEOID18': 14}
    units_dict ={'Meters': 1, 'US Feet': 2}
    
    geoid_select = st.selectbox('Please Choose Desired Geoid', ('<select>',
                                                                'GEOID99',
                                                                'G99SSS',
                                                                'GEOID03',
                                                                'USGG2003',
                                                                'GEOID06',
                                                                'USGG2009',
                                                                'GEOID09',
                                                                'The latest experimental Geoid (XUSHG)',
                                                                'USGG2012',
                                                                'GEOID12A',
                                                                'GEOID12B',
                                                                'GEOID18'))
    
    if not geoid_select=='<select>':
        st.write('You selected:', geoid_select)
        geoid = geoid_dict[geoid_select]
    
    units_select = st.selectbox('Please Select Desired Units', ('<select>', 'Meters','US Feet'))
    
    if not units_select=='<select>':
        st.write('You selected:', units_select)
        units = units_dict[units_select]
    
    if uploaded and not geoid_select=='<select>' and not units_select=='<select>':
        if st.button('CONVERT HEIGHTS'):
            file_ctr = 0
            for df in dfs:
                st.text('Processing ' + filenames[file_ctr] + '.')
                my_bar = st.progress(0)
                cmd = 'https://geodesy.noaa.gov/api/geoid/ght?'
                
                ortho = []
                for x in range(len(df[lat])):
                    lat_req = str(df[lat][x])
                    lon_req = str(df[lon][x])
                    ellip = df[height][x]
                    req = cmd + 'lat=' + lat_req + '&lon=' + lon_req + '&model=' + str(geoid)
                        
                    try:
                        responseGeoid = requests.get(req)
                        responseGeoid.raise_for_status()
                    except requests.HTTPError  as errh:
                        msg = "Error Connecting: " + str(errh)
                        st.error(msg)
                        st.stop()
                    except requests.ConnectionError as errc:
                        msg = "Error Connecting: " + str(errc)
                        st.error(msg)
                        st.stop()
                    except requests.Timeout as errt:
                        msg = "Error Connecting: " + str(errt)
                        st.error(msg)
                        st.stop()
                    except requests.RequestException as err:
                        msg = "Error Connecting: " + str(err)
                        st.error(msg)
                        st.stop()
                
                    my_bar.progress((x+1)/len(df[lat]))     
                    ortho_height = ellip - responseGeoid.json()['geoidHeight']
                        
                    if units==1:
                        ortho.append(ortho_height)
                    else:
                        ortho.append(ortho_height*3.2808399)
        
                df[height] = ortho
                file_ctr += 1
                if units==1:
                    df.rename(columns={height: 'orthometric height [meter]'}, inplace=True)
                else:
                    df['accuracy horizontal [meter]'] = df['accuracy horizontal [meter]'].apply(lambda x: x*3.2808399)
                    df['accuracy vertical [meter]'] = df['accuracy vertical [meter]'].apply(lambda x: x*3.2808399)
                    df.rename(columns={height: 'orthometric height [feet]',
                                       'accuracy horizontal [meter]': 'accuracy horizontal [feet]', 
                                       'accuracy vertical [meter]': 'accuracy vertical [feet]'}, inplace=True)
            
            st.success('Height conversion finished. Click button below to download converted files.')
            
            
            # Create the zip file and convert the dataframes to CSV
            
            with zipfile.ZipFile('Converted_CSV.zip', 'w') as csv_zip:
                file_ctr = 0
                for df in dfs:
                    csv_zip.writestr(filenames[file_ctr].split('.')[0] + '_orthometric.csv', df.to_csv(index=False).encode('utf-8'))
                    file_ctr += 1   
            
            # Download button for the zipped CSVs
            
            fp = open('Converted_CSV.zip', 'rb')
            st.download_button(
                label="Download Converted Geotags CSV",
                data=fp,
                file_name='Converted_CSV.zip',
                mime='application/zip',
            )
    st.stop()
else:
    st.stop()
