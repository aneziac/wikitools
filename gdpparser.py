import pandas as pd
from weo import download
from weo import WEO

year = '2020'
quarter = 2

# calculate later
col = 4

# create csv
states = pd.read_excel('data/gdp/BEA_2019-2020.xlsx', sheet_name='Table 3', engine='openpyxl')
states = states.iloc[5:64, [0, col]]
states.columns = ['State/Country', '2019 GDP']
states['State/Country'] = states['State/Country'].str.strip()
states = states[~states['State/Country'].isin(['New England', 'Mideast', 'Great Lakes', 'Plains', 'Southeast', 'Southwest', 'Rocky Mountain', 'Far West'])]
states = states.replace('Georgia', 'Georgia (U.S. state)|name=Georgia')
states['2019 GDP'] = states['2019 GDP'].astype(float)
states['State?'] = True

# download('2019-Oct', path='weo.csv', overwrite=True)
# add automatic bea getter

w = WEO('weo.csv')
countries = w.df
countries = countries[countries['Subject Descriptor'] == 'Gross domestic product, current prices']
countries = countries[countries['Units'] == 'U.S. dollars']
countries = countries[['Country', '2019']]
countries.columns = ['State/Country', '2019 GDP']
countries['2019 GDP'] = countries['2019 GDP'].str.replace(',','')
countries.loc[countries['State/Country'] == 'Syria', '2019 GDP'] = '60.043'
countries['2019 GDP'] = countries['2019 GDP'].astype(float)
countries['2019 GDP'] *= 1000
countries['State?'] = False

data = pd.concat([states, countries])
data.sort_values(by=['2019 GDP'], inplace=True, ascending=False)
data = data.reset_index(drop=True)
data = data.fillna(0.0)

data['Notes'] = ''
data.loc[data['State/Country'] == 'China', 'Notes'] = 'Figures exclude Taiwan and special administrative regions of Hong Kong and Macau.'
data.loc[data['State/Country'] == 'Syria', 'Notes'] = "Data for Syria's GDP is from the 2011 WEO Database, the latest available from the IMF."
data.loc[data['State/Country'] == 'Russia', 'Notes'] = 'Figures exclude Republic of Crimea and Sevastopol.'

out = open('out/countrystate.txt', 'w')
out.write('{| class="wikitable sortable" style="text-align: right; margin-left: auto; margin-right: auto; border: none;"\n|+ National GDPs and U.S. State GDPs, ' + year)
out.write('\n! Rank !! Country or U.S. state !! GDP (USD million)\n')

for row in range(len(data)):
    color = ('style = "background: #D3D3D3; "' if data.iloc[row, 2] else '')
    out.write('|-\n| ' + str(row + 1) + ' || align="left" ' + color + '| {{flag|' + data.iloc[row, 0] + '}}')
    if data.iloc[row, 3] != '':
        out.write('{{refn|' + data.iloc[row, 3] + '}}')
    out.write(' || ' + f'{int(data.iloc[row, 1]):,}\n')

out.write('|}')
out.close()
