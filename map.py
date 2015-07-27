from flask import Flask, request, render_template
import json
import postgresql.driver as pg_driver

app = Flask(__name__)
app.debug = True
app.config.from_pyfile('map.cfg')
db = None

db = pg_driver.connect(
    database=app.config['APP_NAME'],
    user=app.config['PG_DB_USERNAME'],
    password=app.config['PG_DB_PASSWORD'],
    host=app.config['PG_DB_HOST'],
    port=app.config['PG_DB_PORT']
)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/wfs/')
def wfs():
    return render_template('wfs.html')

# return all parks:
@app.route("/layers/")
def layers():
    # list all tables registered in geometry_columns view
    result = db.prepare(
        'SELECT f_table_name as table_name, f_geometry_column as geometry_column from geometry_columns;')

    # Now turn the results into valid JSON


    return str(json.dumps(list(result().dictresult())))


@app.route("/layer/within")
def layer_within():
    table_name = str(request.args.get('layer'))
    geometry_column = str(request.args.get('geometry_column'))
    srid = str(request.args.get('srid'))
    lat1 = str(request.args.get('lat1'))
    lon1 = str(request.args.get('lon1'))
    lat2 = str(request.args.get('lat2'))
    lon2 = str(request.args.get('lon2'))

    # use the request parameters in the query

    query = "select column_name from information_schema.columns where table_name='" + table_name + "' and column_name <> '" + geometry_column + "'"
    result = db.prepare(query)

    columns = None
    for x in result():
        if not columns:
            columns = "\"" + x[0] + "\""
        else:
            columns += ", \"" + x[0] + "\""

    query = "SELECT row_to_json(fc) " \
            " FROM ( SELECT 'FeatureCollection' As type, array_to_json(array_agg(f)) As features" \
            " FROM (SELECT 'Feature' As type" \
            " , ST_AsGeoJSON(tb." + geometry_column + ")::json As geometry"
    if columns:
            query += " , row_to_json((SELECT l FROM (SELECT " + columns + ") As l" \
                                                                 " )) As properties"

    query += " FROM " + table_name + " As tb  where ST_Intersects(  tb." + geometry_column + " , " \
            " ST_MakeEnvelope("+lon1+", "+lat1+", "+lon2+", "+lat2+", " + srid + " ))) As f )  As fc;"

    result = db.prepare(query)

    ret = "{}"
    for r in result():
        ret = r[0]

    # turn the results into valid JSON
    return ret

if __name__ == '__main__':
    app.run()
