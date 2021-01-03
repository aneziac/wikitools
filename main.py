import pandas as pd
from weo import WEO, download
import datetime
# import datapungibea
import matplotlib.pyplot as plt
import matplotlib
import fiona
import geopandas as gp


def get_state_data(year, download_new=False):

    # read sheet
    if year > 2020:
        raise ValueError('There are no BEA estimates after 2020')
    if year == 2020:
        states = pd.read_excel('data/gdp/BEA_2019-2020.xlsx', sheet_name='Table 3')

        # get data from most recent quarter and year
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
    states.sort_values(by=['Country'], inplace=True)
    states['Country'] = states['Country'].str.strip()
    states = states[~states['Country'].isin(['New England', 'Mideast', 'Great Lakes', 'Plains', 'Southeast', 'Southwest', 'Rocky Mountain', 'Far West'])]
    states = states.replace('Georgia', 'Georgia (U.S. state)')
    states = states[states['Country'] != 'United States']

    # convert gdp to float and create state column
    states['GDP'] = states['GDP'].astype(float)
    states['State?'] = True
    states['Notes'] = ''
    if year == 2020:
        add_note(states, 'California', 'Note that these are Q3 estimates by the BEA.')

    return states

def get_country_data(year):
    if year >= 2026:
       raise ValueError('There are no available IMF estimates past 2025')
    elif year >= 2020:
        countries = pd.read_csv('data/gdp/IMF_2019-2025.csv')
    elif year < 1980:
        raise ValueError('The IMF has no available data before 1980')
    else:    
        w = WEO('data/gdp/IMF_1980-2019.csv')
        countries = w.df

        # grab the right data
        countries = countries[countries['Subject Descriptor'] == 'Gross domestic product, current prices']
        countries = countries[countries['Units'] == 'U.S. dollars']

    countries = countries[['Country', 'ISO', str(year)]]

    # rename columns
    countries.columns = ['Country', 'Country Code', 'GDP']

    # clean up data
    countries = countries[countries['Country'] != 'West Bank and Gaza']
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
    add_note(countries, 'China', 'Figures exclude Taiwan and special administrative regions of Hong Kong and Macau.')
    add_note(countries, 'Syria', "Data for Syria's GDP is from the 2011 WEO Database, the latest available from the IMF.")
    add_note(countries, 'Russia', 'Figures exclude Republic of Crimea and Sevastopol.')

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


class Reference:
    def __init__(self, title, url):
        self.title = title
        self.url = url

    @property
    def ref():
        return '<ref>{{cite web|title = ' + title + 'url=|' + url + '|access-date=' + current_date + '}}</ref>'

def write_wikitable(year):
    current_date = str(datetime.date.today())
    data = get_data_year(year)
    world_gdp = data[~data['State?']]['GDP'].sum()
    weo = Reference('World Economic Outlook Database', 'https://www.imf.org/en/Publications/WEO/weo-database/' + str(year) + '/October')

    # open file to write
    out = open('out/wikitables/countrystategdp.txt', 'w')

    # create sortable centered wikitable and include all settings and references
    out.write('{| class="wikitable sortable" style="text-align: right; margin-left: auto; margin-right: auto; border: none;"')
    out.write('\n|+ National GDPs and U.S. State GDPs, ' + str(year))
    out.write(weo.ref)
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

def add_note(df, country, note):
    df.loc[df['Country'] == country, 'Notes'] = note 

def get_data_year(year, sort=True):
    states = get_state_data(year)
    countries = get_country_data(year)[['Country', 'GDP', 'State?', 'Notes']]
    return combine_data(states, countries, sort)

def get_data_year_range(start_year, end_year):
    year = start_year
    dataframes = []
    dataframes.append(get_data_year(year, False)[['Country']])

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
    data = get_data_year_range(1980, 2020)
    data.to_csv('data/extracted/statecountry_1980-2020.csv')

def make_chart():
    data = pd.read_csv('data/extracted/statecountry_1980-2020.csv')
    data.set_index('Unnamed: 0', inplace=True)
    column = data[['United States', 'China', 'California', 'Italy', 'Germany', 'Japan', 'Texas', 'India']]
    column.plot()
    plt.yscale('log')
    plt.xlabel('Year')
    plt.ylabel('GDP (millions USD)')
    plt.savefig('out/charts/top_economies.png')
    plt.show()

def download_new(year):
    if year < 2019:
        raise ValueError('Data is already updated to 2019')
    elif year >= 2020:
        raise ValueError('2020 and later data is not yet supported by the WEO package')
    download(str(year) + '-Oct', path='data/gdp/IMF_1980-' + str(year) + '.csv', overwrite=True)

def make_map(year):
    # see https://towardsdatascience.com/a-complete-guide-to-an-interactive-geographical-map-using-python-f4c5197e23e0
    # read shapefile using Geopandas
    shapefile = 'data/maps/countries_110m/ne_110m_admin_0_countries.shp'
    gdf = gp.read_file(shapefile)[['ADMIN', 'ADM0_A3', 'geometry']]
    gdf.columns = ['region', 'country_code', 'geometry']

    # drop row corresponding to Antarctica
    gdf = gdf.drop(gdf.index[159])

    # read country data
    countries = get_country_data(year)[['Country Code', 'GDP']]
    countries.columns = ['country_code', 'gdp']

    data = gdf.merge(countries, on='country_code', how='left')
    pd.set_option('display.max_rows', None)

    # combine regions into countries as designated by IMF
    data['country'] = data['region']
    replacements = {
        'Kosovo': 'Republic of Serbia',
        'Western Sahara': 'Morocco',
        'Greenland': 'Denmark',
        'Somaliland': 'Somalia',
        'Falkland Islands': 'United Kingdom',
        'French Southern and Antarctic Lands': 'France',
        'New Caledonia': 'France'
    }
    for item in replacements:
        data.loc[data['region'] == item, 'country'] = replacements[item]
    data = data.dissolve(by='country')

    fig, ax = plt.subplots()
    ax.axis('off')

    # see https://geopandas.org/mapping.html
    data.plot(
        column='gdp',
        ax=ax,
        legend=True,
        legend_kwds={
            'label': 'GDP by Country (' + str(year) + ')',
            'orientation': 'horizontal'
        },
        # scheme='quantiles',
        missing_kwds={
            'color': 'lightgrey'
        },
        cmap='OrRd',
        norm=matplotlib.colors.LogNorm(vmin=data['gdp'].min(), vmax=data['gdp'].max())
    )
    plt.savefig('out/maps/world_economies.png')
    plt.show()


def main():
    make_map(2019)


main()
