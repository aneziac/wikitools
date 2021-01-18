import pandas as pd
import weo
import datetime
import math
# import datapungibea
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import fiona
import geopandas as gp
from numpy import nan as NaN


class EconomicData:
    def __init__(self, data_year=2020):
        self.data_year = data_year
        self.data_sources = [
                StateData(data_year), # US States
                CountryData(data_year) # countries of the world
            ]
        self.data = pd.concat([source.get_data() for source in self.data_sources], ignore_index=True)

    def get_sorted_data(self, year):
        return self.data.sort_values(by=[str(year)], ascending=False)

    def write_wikitable(self, year):
        year = str(year)
        data = self.get_sorted_data(year)[['Region', year, 'Type', 'Notes']].dropna() # Fix dropna
        world_gdp = int(data[data['Type'] == 'Country'][year].sum())

        data.loc[(data['Region'] == 'Georgia') & (data['Type'] == 'US State'), 'Region'] = 'Georgia (U.S. state)|name=Georgia'

        for row in range(len(data)):
            data.iloc[row, 1] = f'{int(data.iloc[row, 1]):,}'

            if data.iloc[row, 0] in ['Puerto Rico', 'District of Columbia', 'Hong Kong', 'Macau']:
                data.iloc[row, 0] = "''{{flag|" + data.iloc[row, 0] + '}}' + (' (China)' if data.iloc[row, 0] in ['Hong Kong', 'Macau'] else ' (United States)') + "''"
            else:
                data.iloc[row, 0] = '{{flag|' + data.iloc[row, 0] + '}}'
                if data.iloc[row, 2] == 'US State':
                    data.iloc[row, 0] = f"'''{data.iloc[row, 0]}'''"
                if data.iloc[row, 3] != '':
                    data.iloc[row, 0] += '{{efn|' + data.iloc[row, 3] + '}}'

        data = data[['Region', year]]

        # create sortable centered wikitable and include all settings and references
        wt = Wikitable(
            data,
            title='National GDPs and U.S. State GDPs, ' + year,
            refs=[
                Reference('World Economic Outlook Database', 'https://www.imf.org/en/Publications/WEO/weo-database/' + str(self.data_year) + '/October')
            ],
            column_headers=['#', 'Country or U.S. State', 'GDP ([[USD]] million)'],
            column_flags=['', 'align="left"', ''],
            sortable=True,
            centered=True,
            right_align=True,
            special_rows=[
                "  || align=\"left\" | {{noflag}} ''[[Gross world product|World]]'' || " + f'{world_gdp:,}'
            ],
            special_row_style='style="font-weight:bold; background: #eaecf0"',
            row_style=['align="left"', '', ''],
        )

        wt.write('countrystategdp.txt')

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

    def make_map(self, year, continuous=True):
        # see https://towardsdatascience.com/a-complete-guide-to-an-interactive-geographical-map-using-python-f4c5197e23e0
        # read shapefile using Geopandas
        shapefile = 'data/maps/countries_110m/ne_110m_admin_0_countries.shp'
        gdf = gp.read_file(shapefile)[['ADMIN', 'ADM0_A3', 'geometry']]
        gdf.columns = ['region', 'country_code', 'geometry']

        # drop row corresponding to Antarctica
        gdf = gdf.drop(gdf.index[159])

        # fix South Sudan ISO discrepancy
        gdf.loc[gdf['region'] == 'South Sudan', 'country_code'] = 'SSD'

        # substitute West Bank & Gaza data for Palestine
        gdf.loc[gdf['region'] == 'Palestine', 'country_code'] = 'WBG'

        # read country data
        data = self.data[self.data['Type'] == 'Country'][['Code', str(year)]]
        data.columns = ['country_code', 'gdp']

        data = pd.merge(gdf, data, on='country_code', how='outer')

        # combine regions into self.data as designated by IMF
        data['nation'] = data['region']
        replacements = {
            #'Kosovo': 'Republic of Serbia',
            'Northern Cyprus': 'Cyprus',
            #'Western Sahara': 'Morocco',
            #'Greenland': 'Denmark',
            'Somaliland': 'Somalia',
            #'Falkland Islands': 'United Kingdom',
            #'French Southern and Antarctic Lands': 'France',
            #'Puerto Rico': 'United States',
            #'New Caledonia': 'France'
        }
        for item in replacements:
            data.loc[data['region'] == item, 'nation'] = replacements[item]
        data = data.dissolve(by='nation', aggfunc='sum')
        data = data.replace({0:NaN})

        fig, ax = plt.subplots()
        ax.axis('off')

        def get_labels():
            units = ['billion', 'trillion']
            labels = ['No data']

            def format_bound(bound):
                seps_needed = int(math.log(bound + 1, 10)) // 3
                unit = units[seps_needed - 1]
                new_bound = int(bound / (10 ** (3 * seps_needed)))
                return f'\${new_bound} {unit}'

            for x in range(1, len(boundaries) - 1):
                lower_bound = format_bound(boundaries[x])

                if x == len(boundaries) - 2:
                    return labels + [f'> {lower_bound}']

                upper_bound = format_bound(boundaries[x + 1])

                if x == 1:
                    labels.append(f'< {upper_bound}')
                else:
                    labels.append(f'{lower_bound} - {upper_bound}')

        if continuous:
            cmap = 'GnBu'
            norm = mcolors.LogNorm(vmin=data['gdp'].min(), vmax=data['gdp'].max())
            legend = True
        else:
            cmap = mcolors.ListedColormap(['lightgrey', 'palegreen', 'springgreen', 'lime', 'aqua', 'darkturquoise', 'turquoise'])
            boundaries = [-1, 0, 100_000, 500_000, 1_000_000, 3_000_000, 5_000_000, float('inf')]
            norm = mcolors.BoundaryNorm(boundaries, cmap.N, clip=True)
            legend_colors = [mpatches.Patch(color=cmap(b)) for b in range(len(boundaries))]
            plt.legend(legend_colors, get_labels())
            legend = False


        # see https://geopandas.org/mapping.html
        data.plot(
            column='gdp',
            ax=ax,
            legend=legend,
            legend_kwds={
                'label': 'GDP by Country (' + str(year) + ')',
                'orientation': 'horizontal'
            },
            #scheme='quintiles',
            missing_kwds={
                'color': 'lightgrey'
            },
            cmap=cmap,
            norm=norm
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


class Wikitable:
    def __init__(self, data, title='', refs=[], column_headers=[], column_flags=[], sortable=False, right_align=False, centered=False, row_style=None, ranked=True, special_rows=[], special_row_style=''):
        self.data = data
        self.title = title
        self.refs = [r.ref for r in refs]
        self.column_headers = column_headers

        class_flags, style_flags = [], []
        if sortable:
            class_flags.append('sortable')
        if right_align:
            style_flags.append('text-align: right;')
        if centered:
            style_flags.append('margin-left: auto; margin-right: auto; border: none;')

        self.header = f'{{| class="wikitable {" ".join(class_flags)}" style="{" ".join(style_flags)}"'
        blanks = ['' for _ in range(len(self.column_headers))]

        self.ranked = ranked
        self.row_style = row_style if row_style else blanks
        self.special_rows = special_rows
        self.special_row_style = special_row_style

    def write(self, filename):
        # open file to write
        out = open('out/wikitables/' + filename, 'w')

        # write header lines
        out.write(f'{self.header}\n|+ {self.title}{"".join(self.refs)}\n! {" !! ".join(self.column_headers)}\n')

        # special rows
        for row in self.special_rows:
            out.write(f'|- {self.special_row_style}\n| {row}\n')

        # apply row styles
        for col in range(len(self.column_headers)):
            if self.row_style[col] != '':
                for row in range(len(self.data)):
                    self.data.iloc[row, col] = f'{self.row_style[col]} | {self.data.iloc[row, col]}'

        for i in range(len(self.data)):
            rank = f'{i + 1} || ' if self.ranked else ''
            out.write('|-\n| ' + rank + ' || '.join([str(x) for x in self.data.iloc[i]]) + '\n')


        out.write('|}\n')
        out.close()

        print('Successfully created wikitable at', filename)


class Reference:
    def __init__(self, title, url):
        self.title = title
        self.url = url
        self.access_date = str(datetime.date.today())
        info = f'cite web|title = {title}|url={url}|access-date={self.access_date}'
        self.ref = '<ref>{{' + info + '}}</ref>'


def main():
    pd.set_option('display.max_rows', None)
    ed = EconomicData()
    ed.make_map(2019)


main()
