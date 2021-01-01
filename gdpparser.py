import pandas as pd
from weo import WEO, download
import datetime
# import datapungibea
import matplotlib.pyplot as plt


def get_state_data(year, download_new=False):

    # read sheet
    if year >= 2020:
        states = pd.read_excel('data/gdp/BEA_2019-2020.xlsx', sheet_name='Table 3')

        # get data from specified quarter and year
        data_years = list(states.iloc[2])
        if data_years.index(year) == 1:
            col = 4
        else:
            col = 4 + ((len(data_years) - 9) / 2)

        states = states.iloc[4:64, [0, col]]

    else:
        if year > 1997:
            states = pd.read_csv('data/gdp/BEA_1997-2019.csv')
            states = states[states['Description'] == 'Current-dollar GDP (millions of current dollars)']
        elif year >= 1963:
            states = pd.read_csv('data/gdp/BEA_1963-1997.csv')
            states = states[states['Description'] == 'All industry total']
        else:
            raise ValueError('There is no BEA data before 1963')
        states = states[['GeoName', str(year)]]

    # rename columns
    states.columns = ['Country', 'GDP']

    # clean up data
    states['Country'] = states['Country'].str.strip()
    states = states[~states['Country'].isin(['New England', 'Mideast', 'Great Lakes', 'Plains', 'Southeast', 'Southwest', 'Rocky Mountain', 'Far West'])]
    states = states.replace('Georgia', 'Georgia (U.S. state)')
    states = states[states['Country'] != 'United States']

    # convert gdp to float and create state column
    states['GDP'] = states['GDP'].astype(float)
    states['State?'] = True
    states['Notes'] = ''

    return states

def get_country_data(year, download_new=False):
    if year >= 2020:
        filename = 'data/gdp/IMF_1980-' + str(year) + '.csv'
    else:
        filename = 'data/gdp/IMF_1980-2019.csv'

    if download_new:
        if year >= 2020:
            raise ValueError('2020 and later data is not yet supported by the WEO package')
        if year <= 1980:
            raise ValueError('The IMF has no available data before 1980')
        download(str(year) + '-Oct', path=filename, overwrite=True)

    def add_note(country, note):
        countries.loc[countries['Country'] == country, 'Notes'] = note 

    # read sheet
    w = WEO(filename)
    countries = w.df

    # grab the right data
    countries = countries[countries['Subject Descriptor'] == 'Gross domestic product, current prices']
    countries = countries[countries['Units'] == 'U.S. dollars']
    countries = countries[['Country', str(year)]]

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

    # add notes
    countries['Notes'] = ''
    add_note('China', 'Figures exclude Taiwan and special administrative regions of Hong Kong and Macau.')
    add_note('Syria', "Data for Syria's GDP is from the 2011 WEO Database, the latest available from the IMF.")
    add_note('Russia', 'Figures exclude Republic of Crimea and Sevastopol.')

    return countries

def combine_data(sheet1, sheet2, sort):

    # combine and sort data
    data = pd.concat([sheet1, sheet2])
    if sort:
        data.sort_values(by=['GDP'], inplace=True, ascending=False)
    data = data.reset_index(drop=True)
    data = data.fillna(0.0)
    data['GDP'] = data['GDP'].astype(int)

    return data

def write_wikitable(year):
    current_date = str(datetime.date.today())
    data = get_data_year(year)
    world_gdp = data[~data['State?']]['GDP'].sum()

    # open file to write
    out = open('out/wikitables/countrystategdp.txt', 'w')

    # create sortable centered wikitable and include all settings and references
    out.write('{| class="wikitable sortable" style="text-align: right; margin-left: auto; margin-right: auto; border: none;"')
    out.write('\n|+ National GDPs and U.S. State GDPs, ' + str(year))
    out.write('<ref>{{cite web|title = World Economic Outlook Database|url=https://www.imf.org/en/Publications/WEO/weo-database/' + str(year) + '/October|access-date=' + current_date + '}}</ref>')
    out.write('\n! # !! Country or U.S. State !! GDP ([[USD]] million)\n')
    out.write('|- style="font-weight:bold; background: #eaecf0"\n')
    out.write("|   || align=\"left\" | {{noflag}} ''[[Gross world product|World]]'' || " + f'{world_gdp:,}\n')

    # read data, add to file, and close file
    for row in range(len(data)):
        if data.iloc[row, 0] == 'Georgia (U.S. state)':
            data.iloc[row, 0] += '|name=Georgia'
        flag = '{{flag|' + data.iloc[row, 0] + '}}'

        # add country descriptors for territories and bold US states
        if data.iloc[row, 0] in ['Puerto Rico', 'District of Columbia', 'Hong Kong', 'Macau']:
            flag = "''" + flag + (' (China)' if data.iloc[row, 0] in ['Hong Kong', 'Macau'] else ' (United States)') + "''"
        elif data.iloc[row, 2]:
            flag = "'''" + flag + "'''"

        out.write('|-\n| ' + str(row + 1) + ' || align="left" | ' + flag)
        if data.iloc[row, 3] != '':
            out.write('{{refn|' + data.iloc[row, 3] + '}}')
        out.write(' || ' + f'{data.iloc[row, 1]:,}\n')

    out.write('|}\n')
    out.close()

    print('Successfully created wikitable')

def get_data_year(year, sort=True):
    states = get_state_data(year)
    countries = get_country_data(year)
    return combine_data(states, countries, sort)

def get_data_year_range(start_year, end_year):
    year = start_year
    dataframes = []
    country_list = get_data_year(year, False)[['Country']]
    country_list.columns = ['Year']
    dataframes.append(country_list)

    for _ in range(end_year - start_year + 1):
        data = get_data_year(year, False)[['GDP']]
        data.columns = [str(year)]
        dataframes.append(data)
        year += 1

    data = pd.concat(dataframes, axis=1)
    data.set_index('Year', inplace=True)
    data = data.transpose()

    return data

def save_data():
    data = get_data_year_range(1980, 2019)
    data.to_csv('data/extracted/statecountry_1980-2019.csv', index=False)

def main():
    data = pd.read_csv('data/extracted/statecountry_1980-2019.csv')
    column = data[['United States', 'China', 'California', 'Italy', 'Germany', 'Japan', 'Texas', 'India']]
    column.plot()
    plt.yscale('log')
    plt.xlabel('Year')
    plt.ylabel('GDP (millions USD)')
    plt.savefig('out/charts/top_economies.png')


main()
