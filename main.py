import pandas as pd
import weo
import datetime
# import datapungibea
import matplotlib.pyplot as plt
import matplotlib
import fiona
import geopandas as gp


class EconomicData:
    def __init__(self, year=2020):
        self.year = year
        self.data_sources = [
                CountryData(year), # countries of the world
                StateData(year) # US States
            ]
        self.data = self.combine_data([source.data for source in self.data_sources])

    def combine_data(self, dataframes):
        # combine and sort data
        combined_data = pd.concat(dataframes)
        combined_data = combined_data.reset_index(drop=True)
        combined_data = combined_data.fillna(0.0)
        combined_data['GDP'] = combined_data['GDP'].astype(int)

        return combined_data

    def get_sorted_data(self):
        return self.data.sort_values(by=['GDP'], ascending=False)

    def write_wikitable(self):
        data = self.get_sorted_data()[['Country', 'GDP', 'State?', 'Notes']]
        world_gdp = data[~data['State?']]['GDP'].sum()

        weo = Reference('World Economic Outlook Database', 'https://www.imf.org/en/Publications/WEO/weo-database/' + str(self.year) + '/October')

        # open file to write
        out = open('out/wikitables/countrystategdp.txt', 'w')

        # create sortable centered wikitable and include all settings and references
        out.write('{| class="wikitable sortable" style="text-align: right; margin-left: auto; margin-right: auto; border: none;"')
        out.write('\n|+ National GDPs and U.S. State GDPs, ' + str(self.year))
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

#    def get_data_year(year, sort=True):
#        states = get_state_data(year)
#        self.data = get_country_data(year)[['Country', 'GDP', 'State?', 'Notes']]
#        return combine_data(states, self.data, sort)

    def get_data_year_range(self, start_year, end_year):
        year = start_year
        dataframes = []
        dataframes.append(self.data[['Country']])

        for _ in range(end_year - start_year + 1):
            data = self.data[['GDP']]
            data.columns = [str(year)]
            dataframes.append(data)
            year += 1

        data = pd.concat(dataframes, axis=1)
        data.set_index('Year', inplace=True)
        data = data.transpose()

        return data

    def save_data(self):
        data = self.get_data_year_range(1980, 2020)
        data.to_csv('data/extracted/statecountry_1980-2020.csv')

    def make_chart(self):
        data = pd.read_csv('data/extracted/statecountry_1980-2020.csv')
        data.set_index('Unnamed: 0', inplace=True)
        column = data[['United States', 'China', 'California', 'Italy', 'Germany', 'Japan', 'Texas', 'India']]
        column.plot()
        plt.yscale('log')
        plt.xlabel('Year')
        plt.ylabel('GDP (millions USD)')
        plt.savefig('out/charts/top_economies.png')
        plt.show()

    def make_map(self, year):
        # see https://towardsdatascience.com/a-complete-guide-to-an-interactive-geographical-map-using-python-f4c5197e23e0
        # read shapefile using Geopandas
        shapefile = 'data/maps/countries_110m/ne_110m_admin_0_countries.shp'
        gdf = gp.read_file(shapefile)[['ADMIN', 'ADM0_A3', 'geometry']]
        gdf.columns = ['region', 'country_code', 'geometry']

        # drop row corresponding to Antarctica
        gdf = gdf.drop(gdf.index[159])

        # read country data
        data = self.data[self.data['State?']][['Country Code', 'GDP']]
        data.columns = ['country_code', 'gdp']

        data = gdf.merge(data, on='country_code', how='left')
        pd.set_option('display.max_rows', None)

        # combine regions into self.data as designated by IMF
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


class DataSource():
    def __init__(self, year):
        self.year = year
        self.download()
        self.read()
        self.clean()

    def add_note(self, country, note):
        self.data.loc[self.data['Country'] == country, 'Notes'] = note


class CountryData(DataSource):
    def download(self):
        if self.year < 2020:
            raise ValueError('Data is already updated to 2020')
        self.filename = 'data/gdp/IMF_1980-' + str(self.year) + '.csv'
        weo.download(year=self.year, release='Oct', filename=self.filename)

    def read(self):
        if self.year >= 2026:
            raise ValueError('There are no available IMF estimates past 2025')
        elif self.year < 1980:
            raise ValueError('The IMF has no available data before 1980')
        else:
            w = weo.WEO(self.filename)
            data = w.df

            # grab the right data - maybe use WEO?
            data = data[data['Subject Descriptor'] == 'Gross domestic product, current prices']
            data = data[data['Units'] == 'U.S. dollars']

        self.data = data[['Country', 'ISO', str(self.year)]]

    def clean(self):     
        self.data.columns = ['Country', 'Country Code', 'GDP']

        # clean up data
        self.data = self.data[self.data['Country'] != 'West Bank and Gaza'] # FIX: should be included in wikitable, not in world map
        self.data['GDP'] = self.data['GDP'].str.replace(',','')
        self.data.loc[self.data['Country'] == 'Syria', 'GDP'] = '60.043'
        self.data['GDP'] = self.data['GDP'].astype(float)
        self.data['GDP'] *= 1000
        self.data['State?'] = False

        # rename self.data
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
            self.data = self.data.replace(item, replacements[item])

        # add notes
        self.data['Notes'] = ''
        self.add_note('China', 'Figures exclude Taiwan and special administrative regions of Hong Kong and Macau.')
        self.add_note('Syria', "Data for Syria's GDP is from the 2011 WEO Database, the latest available from the IMF.")
        self.add_note('Russia', 'Figures exclude Republic of Crimea and Sevastopol.')


class StateData(DataSource):
    def download(self):
        pass

    def read(self):
        # read sheet
        if self.year > 2020:
            raise ValueError('There are no BEA estimates from after 2020 yet')
        if self.year == 2020:
            self.data = pd.read_excel('data/gdp/BEA_2019-2020.xlsx', sheet_name='Table 3')

            # get data from most recent quarter and year
            data_years = list(self.data.iloc[2])
            if data_years.index(self.year) == 1:
                col = 4
            else:
                col = 4 + ((len(data_years) - 9) / 2)

            self.data = self.data.iloc[4:64, [0, col]]

        else:
            if year > 1997:
                self.data = pd.read_csv('data/gdp/BEA_1997-2019.csv')
                self.data = self.data[self.data['Description'] == 'Current-dollar GDP (millions of current dollars)']
            elif year >= 1963:
                self.data = pd.read_csv('data/gdp/BEA_1963-1997.csv')
                self.data = self.data[self.data['Description'] == 'All industry total']
            else:
                raise ValueError('There is no BEA data before 1963')

            self.data = self.data[['GeoName', str(self.year)]]

    def clean(self):
        # rename columns
        self.data.columns = ['Country', 'GDP']

        # clean up data
        self.data.sort_values(by=['Country'], inplace=True)
        self.data['Country'] = self.data['Country'].str.strip()
        self.data = self.data[~self.data['Country'].isin(['New England', 'Mideast', 'Great Lakes', 'Plains', 'Southeast', 'Southwest', 'Rocky Mountain', 'Far West'])]
        self.data = self.data.replace('Georgia', 'Georgia (U.S. state)')
        self.data = self.data[self.data['Country'] != 'United States']

        # convert gdp to float and create state column
        self.data['GDP'] = self.data['GDP'].astype(float)
        self.data['State?'] = True
        self.data['Notes'] = ''
        if self.year == 2020:
            self.add_note('California', 'Note that these are Q3 estimates by the BEA.')


class Reference:
    current_date = str(datetime.date.today())

    def __init__(self, title, url):
        self.title = title
        self.url = url
        info = f'cite web|title = {title}|url={url}|access-date={Reference.current_date}'
        self.ref = '<ref>{{' + info + '}}</ref>'


def main():
    ed = EconomicData()
    ed.write_wikitable()


main()
