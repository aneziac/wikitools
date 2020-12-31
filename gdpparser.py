import pandas as pd
from weo import WEO, download
import datetime
# import datapungibea


def get_state_data(year, download_new=False):

    # read sheet
    if int(year) >= 2020:
        states = pd.read_excel('data/gdp/BEA_2019-2020.xlsx', sheet_name='Table 3')

        # get data from specified quarter and year
        data_years = list(states.iloc[2])
        if data_years.index(int(year)) == 1:
            col = 4
        else:
            col = 4 + ((len(data_years) - 9) / 2)

        states = states.iloc[4:64, [0, col]]

    else:
        if int(year) > 1997:
            states = pd.read_csv('data/gdp/BEA_1997-2019.csv')
            states = states[states['Description'] == 'Current-dollar GDP (millions of current dollars)']
        elif int(year) >= 1963:
            states = pd.read_csv('data/gdp/BEA_1963-1997.csv')
            states = states[states['Description'] == 'All industry total']
        else:
            raise ValueError('There is no BEA data before 1963')
        states = states[['GeoName', year]]

    # rename columns
    states.columns = ['Country', 'GDP']

    # clean up data
    states['Country'] = states['Country'].str.strip()
    states = states[~states['Country'].isin(['New England', 'Mideast', 'Great Lakes', 'Plains', 'Southeast', 'Southwest', 'Rocky Mountain', 'Far West'])]
    states = states.replace('Georgia', 'Georgia (U.S. state)|name=Georgia')
    states = states[states['Country'] != 'United States']

    # convert gdp to float and create state column
    states['GDP'] = states['GDP'].astype(float)
    states['State?'] = True
    states['Notes'] = ''

    return states

def get_country_data(year, download_new=False):
    if int(year) >= 2020:
        filename = 'data/gdp/IMF_1980-' + year + '.csv'
    else:
        filename = 'data/gdp/IMF_1980-2019.csv'

    if download_new:
        if int(year) >= 2020:
            raise ValueError('2020 and later data is not yet supported by the WEO package')
        if int(year) <= 1980:
            raise ValueError('The IMF has no available data before 1980')
        download(year + '-Oct', path=filename, overwrite=True)

    def add_note(country, note):
        countries.loc[countries['Country'] == country, 'Notes'] = note 

    # read sheet
    w = WEO(filename)
    countries = w.df

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

    # add notes
    countries['Notes'] = ''
    add_note('China', 'Figures exclude Taiwan and special administrative regions of Hong Kong and Macau.')
    add_note('Syria', "Data for Syria's GDP is from the 2011 WEO Database, the latest available from the IMF.")
    add_note('Russia', 'Figures exclude Republic of Crimea and Sevastopol.')

    return countries

def combine_data(sheet1, sheet2):

    # combine and sort data
    data = pd.concat([sheet1, sheet2])
    data.sort_values(by=['GDP'], inplace=True, ascending=False)
    data = data.reset_index(drop=True)
    data = data.fillna(0.0)

    return data

def write_wikitable(year, data):
    current_date = str(datetime.date.today())
    world_gdp = int(data[~data['State?']]['GDP'].sum())

    # open file to write
    out = open('out/countrystate.txt', 'w')

    # create sortable centered wikitable and include all settings and references
    out.write('{| class="wikitable sortable" style="text-align: right; margin-left: auto; margin-right: auto; border: none;"')
    out.write('\n|+ National GDPs and U.S. State GDPs, ' + year)
    out.write('<ref>{{cite web|title = World Economic Outlook Database|url=https://www.imf.org/en/Publications/WEO/weo-database/' + year + '/October|access-date=' + current_date + '}}</ref>')
    out.write('\n! # !! Country or U.S. State !! GDP ([[USD]] million)\n')
    out.write('|- style="font-weight:bold; background: #eaecf0"\n')
    out.write("|   || align=\"left\" | {{noflag}} ''[[Gross world product|World]]'' || " + f'{world_gdp:,}\n')

    # read data, add to file, and close file
    for row in range(len(data)):
        flag = '{{flag|' + data.iloc[row, 0] + '}}'

        # add country descriptors for territories and bold US states
        if data.iloc[row, 0] in ['Puerto Rico', 'District of Columbia', 'Hong Kong', 'Macau']:
            flag = "''" + flag + (' (China)' if data.iloc[row, 0] in ['Hong Kong', 'Macau'] else ' (United States)') + "''"
        elif data.iloc[row, 2]:
            flag = "'''" + flag + "'''"

        out.write('|-\n| ' + str(row + 1) + ' || align="left" | ' + flag)
        if data.iloc[row, 3] != '':
            out.write('{{refn|' + data.iloc[row, 3] + '}}')
        out.write(' || ' + f'{int(data.iloc[row, 1]):,}\n')

    out.write('|}\n')
    out.close()

    print('Successfully created wikitable')

def main():
    year = '2003'

    states = get_state_data(year)
    countries = get_country_data(year)
    data = combine_data(states, countries)
    write_wikitable(year, data)

main()
