%load_ext sql
from time import time
import configparser
import matplotlib.pyplot as plt
import pandas as pd

config = configparser.ConfigParser()
config.read_file(open('dwh.cfg'))
KEY=config.get('AWS','key')
SECRET= config.get('AWS','secret')

DWH_DB= config.get("DWH","DWH_DB")
DWH_DB_USER= config.get("DWH","DWH_DB_USER")
DWH_DB_PASSWORD= config.get("DWH","DWH_DB_PASSWORD")
DWH_PORT = config.get("DWH","DWH_PORT")
DWH_ENDPOINT=""
DWH_ROLE_ARN=""
conn_string="postgresql://{}:{}@{}:{}/{}".format(DWH_DB_USER, DWH_DB_PASSWORD, DWH_ENDPOINT, DWH_PORT,DWH_DB)
print(conn_string)
%sql $conn_string

#Create tables (no distribution strategy) in the nodist schema
%%sql 
CREATE SCHEMA IF NOT EXISTS nodist;
SET search_path TO nodist;

DROP TABLE IF EXISTS part cascade;
DROP TABLE IF EXISTS supplier;
DROP TABLE IF EXISTS supplier;
DROP TABLE IF EXISTS customer;
DROP TABLE IF EXISTS dwdate;
DROP TABLE IF EXISTS lineorder;

CREATE TABLE part 
(
  p_partkey     INTEGER NOT NULL,
  p_name        VARCHAR(22) NOT NULL,
  p_mfgr        VARCHAR(6) NOT NULL,
  p_category    VARCHAR(7) NOT NULL,
  p_brand1      VARCHAR(9) NOT NULL,
  p_color       VARCHAR(11) NOT NULL,
  p_type        VARCHAR(25) NOT NULL,
  p_size        INTEGER NOT NULL,
  p_container   VARCHAR(10) NOT NULL
);

CREATE TABLE supplier 
(
  s_suppkey     INTEGER NOT NULL,
  s_name        VARCHAR(25),
  s_address     VARCHAR(40),
  s_city        VARCHAR(25),
  s_nation      VARCHAR(25),
  s_region      VARCHAR(25),
  s_phone       VARCHAR(15)
);

CREATE TABLE customer 
(
  c_custkey     INTEGER NOT NULL,
  c_name        VARCHAR(25),
  c_address     VARCHAR(40),
  c_city        VARCHAR(25),
  c_nation      VARCHAR(25),
  c_region      VARCHAR(25),
  c_phone       VARCHAR(15)
);

CREATE TABLE dwdate 
(
  d_datekey     INTEGER NOT NULL,
  d_date        DATE,
  d_day         INTEGER,
  d_month       INTEGER,
  d_year        INTEGER,
  d_week        INTEGER,
  d_yearmonth   VARCHAR(7)
);
CREATE TABLE lineorder 
(
  lo_orderkey       INTEGER   NOT NULL,
  lo_linenumber     INTEGER   NOT NULL,
  lo_custkey        INTEGER,
  lo_orderdate      INTEGER,
  lo_orderpriority  INTEGER,
  lo_shippriority   INTEGER,
  lo_quantity       INTEGER,
  lo_extendedprice  INTEGER,
  lo_discount       INTEGER,
  lo_revenue        INTEGER,
  lo_supplycost     INTEGER,
  lo_tax            INTEGER,
  lo_commitdate     INTEGER,
  lo_shipmode       INTEGER,
  lo_partkey        INTEGER,
  lo_suppkey        INTEGER
);

#Create tables (with a distribution strategy) in the dist schema¶
%%sql

CREATE SCHEMA IF NOT EXISTS dist;
SET search_path TO dist;

DROP TABLE IF EXISTS part cascade;
DROP TABLE IF EXISTS supplier;
DROP TABLE IF EXISTS supplier;
DROP TABLE IF EXISTS customer;
DROP TABLE IF EXISTS dwdate;
DROP TABLE IF EXISTS lineorder;

CREATE TABLE part (
  p_partkey         integer         not null    sortkey distkey,
  p_name            varchar(22)     not null,
  p_mfgr            varchar(6)      not null,
  p_category        varchar(7)      not null,
  p_brand1          varchar(9)      not null,
  p_color           varchar(11)     not null,
  p_type            varchar(25)     not null,
  p_size            integer         not null,
  p_container       varchar(10)     not null
);

CREATE TABLE supplier (
  s_suppkey     INTEGER NOT NULL distkey,
  s_name        VARCHAR(25),
  s_address     VARCHAR(40),
  s_city        VARCHAR(25),
  s_nation      VARCHAR(25),
  s_region      VARCHAR(25),
  s_phone       VARCHAR(15)
);

CREATE TABLE customer (
  c_custkey     INTEGER NOT NULL distkey,
  c_name        VARCHAR(25),
  c_address     VARCHAR(40),
  c_city        VARCHAR(25),
  c_nation      VARCHAR(25),
  c_region      VARCHAR(25),
  c_phone       VARCHAR(15)
);

CREATE TABLE dwdate (
  d_datekey     INTEGER NOT NULL distkey,
  d_date        DATE,
  d_day         INTEGER,
  d_month       INTEGER,
  d_year        INTEGER,
  d_week        INTEGER,
  d_yearmonth   VARCHAR(7)
);

CREATE TABLE lineorder (
  lo_orderkey       INTEGER NOT NULL,
  lo_linenumber     INTEGER NOT NULL,
  lo_custkey        INTEGER,
  lo_orderdate      INTEGER,
  lo_orderpriority  INTEGER,
  lo_shippriority   INTEGER,
  lo_quantity       INTEGER,
  lo_extendedprice  INTEGER,
  lo_discount       INTEGER,
  lo_revenue        INTEGER,
  lo_supplycost     INTEGER,
  lo_tax            INTEGER,
  lo_commitdate     INTEGER,
  lo_shipmode       INTEGER,
  lo_partkey        INTEGER,
  lo_suppkey        INTEGER
);
copy customer from 's3://awssampledbuswest2/ssbgz/customer' 
credentials 'aws_iam_role=<DWH_ROLE_ARN>'
gzip region 'us-west-2';

copy dwdate from 's3://awssampledbuswest2/ssbgz/dwdate' 
credentials 'aws_iam_role=<DWH_ROLE_ARN>'
gzip region 'us-west-2';

copy lineorder from 's3://awssampledbuswest2/ssbgz/lineorder' 
credentials 'aws_iam_role=<DWH_ROLE_ARN>'
gzip region 'us-west-2';

copy part from 's3://awssampledbuswest2/ssbgz/part' 
credentials 'aws_iam_role=<DWH_ROLE_ARN>'
gzip region 'us-west-2';

copy supplier from 's3://awssampledbuswest2/ssbgz/supplier' 
credentials 'aws_iam_role=<DWH_ROLE_ARN>'
gzip region 'us-west-2';

#Automate the copying
def loadTables(schema, tables):
    loadTimes = []
    SQL_SET_SCEMA = "SET search_path TO {};".format(schema)
    %sql $SQL_SET_SCEMA
    
    for table in tables:
        SQL_COPY = """
copy {} from 's3://awssampledbuswest2/ssbgz/{}' 
credentials 'aws_iam_role={}'
gzip region 'us-west-2';
        """.format(table,table, DWH_ROLE_ARN)

        print("======= LOADING TABLE: ** {} ** IN SCHEMA ==> {} =======".format(table, schema))
        print(SQL_COPY)

        t0 = time()
        %sql $SQL_COPY
        loadTime = time()-t0
        loadTimes.append(loadTime)

        print("=== DONE IN: {0:.2f} sec\n".format(loadTime))
    return pd.DataFrame({"table":tables, "loadtime_"+schema:loadTimes}).set_index('table')

tables = ["customer","dwdate","supplier", "part", "lineorder"]

nodistStats = loadTables("nodist", tables)
distStats = loadTables("dist", tables)

#Compare the load performance results¶

stats = distStats.join(nodistStats)
stats.plot.bar()
plt.show()

#Compare Query Performance

oneDim_SQL ="""
set enable_result_cache_for_session to off;
SET search_path TO {};

select sum(lo_extendedprice*lo_discount) as revenue
from lineorder, dwdate
where lo_orderdate = d_datekey
and d_year = 1997 
and lo_discount between 1 and 3 
and lo_quantity < 24;
"""

twoDim_SQL="""
set enable_result_cache_for_session to off;
SET search_path TO {};

select sum(lo_revenue), d_year, p_brand1
from lineorder, dwdate, part, supplier
where lo_orderdate = d_datekey
and lo_partkey = p_partkey
and lo_suppkey = s_suppkey
and p_category = 'MFGR#12'
and s_region = 'AMERICA'
group by d_year, p_brand1
"""

drill_SQL = """
set enable_result_cache_for_session to off;
SET search_path TO {};

select c_city, s_city, d_year, sum(lo_revenue) as revenue 
from customer, lineorder, supplier, dwdate
where lo_custkey = c_custkey
and lo_suppkey = s_suppkey
and lo_orderdate = d_datekey
and (c_city='UNITED KI1' or
c_city='UNITED KI5')
and (s_city='UNITED KI1' or
s_city='UNITED KI5')
and d_yearmonth = 'Dec1997'
group by c_city, s_city, d_year
order by d_year asc, revenue desc;
"""


oneDimSameDist_SQL ="""
set enable_result_cache_for_session to off;
SET search_path TO {};

select lo_orderdate, sum(lo_extendedprice*lo_discount) as revenue  
from lineorder, part
where lo_partkey  = p_partkey
group by lo_orderdate
order by lo_orderdate
"""

def compareQueryTimes(schema):
    queryTimes  =[] 
    for i,query in enumerate([oneDim_SQL, twoDim_SQL, drill_SQL, oneDimSameDist_SQL]):
        t0 = time()
        q = query.format(schema)
        %sql $q
        queryTime = time()-t0
        queryTimes.append(queryTime)
    return pd.DataFrame({"query":["oneDim","twoDim", "drill", "oneDimSameDist"], "queryTime_"+schema:queryTimes}).set_index('query')

noDistQueryTimes = compareQueryTimes("nodist")
distQueryTimes   = compareQueryTimes("dist") 

queryTimeDF =noDistQueryTimes.join(distQueryTimes)
queryTimeDF.plot.bar()
plt.show()

improvementDF = queryTimeDF["distImprovement"] =100.0*(queryTimeDF['queryTime_nodist']-queryTimeDF['queryTime_dist'])/queryTimeDF['queryTime_nodist']
improvementDF.plot.bar(title="% dist Improvement by query")
plt.show()