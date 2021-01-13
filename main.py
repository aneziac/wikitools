import pandas as pd
import weo
import datetime
# import datapungibea
import matplotlib.pyplot as plt
import matplotlib
import fiona
import geopandas as gp


class EconomicData:
    def __init__(self, data_year=2020):
        self.year = data_year
        self.data_sources = [
                StateData(data_year), # US States
                CountryData(data_year) # countries of the world
            ]
        self.data = pd.concat([source.get_data() for source in self.data_sources], ignore_index=True)

    def get_sorted_data(self):
        return self.data.sort_values(by=['GDP'], ascending=False)

    def write_wikitable(self):
        data = self.get_sorted_data()[['Region', 'GDP', 'State?', 'Notes']]
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

    def make_chart(self, start_year=1980, end_year=2020):
        data = self.data
        # data = self.data[self.data['Type'] == 'US State']
        data = data[data[str(end_year)].notna()].sort_values(by=str(end_year)).tail(8)
        data = data.set_index('Region')[[str(start_year + y) for y in range(end_year - start_year - 1)]].transpose()
        data.plot()
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
        # gdf = gdf.drop(gdf.index[159])

        # read country data
        data = self.data[~self.data['State?']][['Country Code', 'GDP']]
        data.columns = ['country_code', 'gdp']

        data = gdf.merge(data, on='country_code', how='left').dropna()

        # combine regions into self.data as designated by IMF
        data['Region'] = data['region']
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
            data.loc[data['region'] == item, 'Region'] = replacements[item]
        data = data.dissolve(by='Region')

        fig, ax = plt.subplots()
        ax.axis('off')
        print(data)

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
            #missing_kwds={
            #    'color': 'lightgrey'
            #},
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
        self.data.loc[self.data['Region'] == country, 'Notes'] = note

    def get_data(self):
        return self.data

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

        self.year_range = [str(1980 + y) for y in range(self.year - 1979)]
        self.data = data[['Country', 'ISO'] + self.year_range]

    def clean(self):
        self.data.columns = ['Region', 'Code'] + self.year_range
        for year in self.year_range:
            self.data[year] = self.data[year].str.replace(',', '').astype(float)
        # self.data.loc[self.data['Region'] == 'Syria', 'GDP'] = '60.043'
        self.data[self.year_range] *= 1000
        self.data.insert(2, 'Type', 'Country')

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
        self.data.insert(3, 'Notes', '')
        self.add_note('China', 'Figures exclude Taiwan and special administrative regions of Hong Kong and Macau.')
        self.add_note('Syria', "Data for Syria's GDP is from the 2011 WEO Database, the latest available from the IMF.")
        self.add_note('Russia', 'Figures exclude Republic of Crimea and Sevastopol.')


class StateData(DataSource):
    def download(self):
        pass

    def read(self):
        early_data = pd.read_csv('data/gdp/BEA_1963-1997.csv')
        early_data = early_data[early_data['Description'] == 'All industry total']
        early_data = early_data.sort_values(by='GeoName')
        early_data = early_data[['GeoName'] + [str(1963 + y) for y in range(34)]]
        early_data = early_data.reset_index(drop=True)

        late_data = pd.read_csv('data/gdp/BEA_1997-2019.csv')
        late_data = late_data[late_data['Description'] == 'Current-dollar GDP (millions of current dollars)']
        late_data = late_data.sort_values(by='GeoName')
        late_data = late_data[[str(1997 + y) for y in range(23)]]
        late_data = late_data.reset_index(drop=True)

        recent_data = pd.read_excel('data/gdp/BEA_2019-2020.xlsx', sheet_name='Table 3')

        # get data from most recent quarter and year
        data_years = list(recent_data.iloc[2])
        if data_years.index(self.year) == 1:
            col = 4
        else:
            col = 4 + ((len(data_years) - 9) / 2)

        recent_data = recent_data.iloc[4:64, [0, col]]
        recent_data.columns = ['Region', str(self.year)]
        recent_data = recent_data.sort_values(by='Region')
        recent_data = recent_data[[str(self.year)]]
        recent_data = recent_data.reset_index(drop=True)

        self.data = pd.concat([early_data, late_data, recent_data], axis=1)

    def clean(self):
        # rename columns
        self.year_range = [str(1963 + y) for y in range(self.year - 1962)]
        self.data.columns = ['Region'] + self.year_range

        # clean up data
        # self.data = self.data[~self.data['Region'].isin(['New England', 'Mideast', 'Great Lakes', 'Plains', 'Southeast', 'Southwest', 'Rocky Mountain', 'Far West'])]
        # self.data = self.data.replace('Georgia', 'Georgia (U.S. state)')
        self.data = self.data[self.data['Region'] != 'United States']
        abbrevs = pd.read_csv('data/abbreviations/state_abbrevs.csv')
        abbrevs = abbrevs[['State', 'Code']]
        abbrevs.columns = ['Region', 'Code']
        self.data = pd.merge(abbrevs, self.data, on='Region')

        # convert gdp to float and create state column
        self.data[self.year_range] = self.data[self.year_range].astype(float)
        self.data.insert(2, 'Type', 'US State')
        self.data.insert(3, 'Notes', '')
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
    pd.set_option('display.max_rows', None)
    ed = EconomicData()
    ed.make_chart()
    # ed.write_wikitable()
    # ed.make_map(2019)


main()
