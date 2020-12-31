import fiona
import geopandas as gp

# Read shapefile using Geopandas
shapefile = 'data/countries_110m/ne_110m_admin_0_countries.shp'
gdf = gp.read_file(shapefile)[['ADMIN', 'ADM0_A3', 'geometry']]

# Rename columns
gdf.columns = ['country', 'country_code', 'geometry']
print(gdf.head())

#Drop row corresponding to 'Antarctica'
gdf = gdf.drop(gdf.index[159])
