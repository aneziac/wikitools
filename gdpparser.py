import pandas as pd
from weo import download
from weo import WEO


def get_state_data(quarter, year, download_new=False):

    # read sheet
    states = pd.read_excel('data/gdp/BEA_2019-2020.xlsx', sheet_name='Table 3')

    # get data from specified quarter and year
    # calculate later
    col = 4

    states = states.iloc[5:64, [0, col]]

    # rename columns
    states.columns = ['Country', 'GDP']

    # clean up data 
    states['Country'] = states['Country'].str.strip()
    states = states[~states['Country'].isin(['New England', 'Mideast', 'Great Lakes', 'Plains', 'Southeast', 'Southwest', 'Rocky Mountain', 'Far West'])]
    states = states.replace('Georgia', 'Georgia (U.S. state)|name=Georgia')

    # convert gdp to float and create state column
    states['GDP'] = states['GDP'].astype(float)
    states['State?'] = True

    return states

def get_country_data(year, download_new=False):
    if download_new:
        download('2019-Oct', path='weo.csv', overwrite=True)

    # read sheet
    w = WEO('weo.csv')
    countries = w.df
    # countries = weo.weo.read_csv('WEOOct2020all.xls')

    # grab the right data
    countries = countries[countries['Subject Descriptor'] == 'Gross domestic product, current prices']
    countries = countries[countries['Units'] == 'U.S. dollars']
    countries = countries[['Country', year]]

    # rename columns
    countries.columns = ['Country', 'GDP']
    
    # clean up data
    countries['GDP'] = countries['GDP'].str.replace(',','')
    countries.loc[countries['Country'] == 'Syria', 'GDP'] = '60.043'
    countries['GDP'] = countries['GDP'].astype(float)
    countries['GDP'] *= 1000
    countries['State?'] = False

    # rename countries
    replacements = {
        'Korea': 'South Korea',
        'Taiwan Province of China': 'Taiwan',
        'Islamic Republic of Iran': 'Iran',
        'Hong Kong SAR': 'Hong Kong',
        'Slovak Republic': 'Slovakia',
        'Macao SAR': 'Macau',
        'Lao P.D.R.': 'Laos',
        'Brunei Darussalam': 'Brunei',
        'Kyrgyz Republic': 'Kyrgyzstan',
    }
    for item in replacements:
        countries = countries.replace(item, replacements[item])

    return countries

def combine_data(sheet1, sheet2):
    def add_note(country, note):
        data.loc[data['Country'] == country, 'Notes'] = note 

    # combine and sort data
    data = pd.concat([sheet1, sheet2])
    data.sort_values(by=['GDP'], inplace=True, ascending=False)
    data = data.reset_index(drop=True)
    data = data.fillna(0.0)

    # add notes
    data['Notes'] = ''
    add_note('China', 'Figures exclude Taiwan and special administrative regions of Hong Kong and Macau.')
    add_note('Syria', "Data for Syria's GDP is from the 2011 WEO Database, the latest available from the IMF.")
    add_note('Russia', 'Figures exclude Republic of Crimea and Sevastopol.')

    return data

def write_wikitable(year, data):

    # open file to write
    out = open('out/countrystate.txt', 'w')

    # create sortable centered wikitable with titles
    out.write('{| class="wikitable sortable" style="text-align: right; margin-left: auto; margin-right: auto; border: none;"')
    out.write('\n|+ National GDPs and U.S. State GDPs, ' + year)
    out.write('\n! Rank !! Country or U.S. State !! GDP (USD million)\n')

    # read data, add to file, and close file
    for row in range(len(data)):
        flag = '{{flag|' + data.iloc[row, 0] + '}}'

        # bold US states
        if data.iloc[row, 0] in ['Puerto Rico', 'District of Columbia', 'Hong Kong', 'Macau']:
            flag = "''" + flag + (' (China)' if data.iloc[row, 0] in ['Hong Kong', 'Macau'] else ' (United States)') + "''"
        elif data.iloc[row, 2]:
            flag = "'''" + flag + "'''"

        out.write('|-\n| ' + str(row + 1) + ' || align="left" | ' + flag)
        if data.iloc[row, 3] != '':
            out.write('{{refn|' + data.iloc[row, 3] + '}}')
        out.write(' || ' + f'{int(data.iloc[row, 1]):,}\n')

    out.write('|}')
    out.close()

def main():
    year = '2019'
    quarter = '2'

    states = get_state_data(quarter, year)
    countries = get_country_data(year)
    data = combine_data(states, countries)
    write_wikitable(year, data)


main()
