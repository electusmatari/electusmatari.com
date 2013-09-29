import kgi

from contracts import view_contracts, view_contracts_create, view_contracts_single
from order import view_order_create, view_order_buy, view_rss, view_order_sell
from rfund import view_rfund

def marketapp(environ, start_response):
    URLCONF = [
        ('^/reimbursementfund/', view_rfund),
        ('^/', view_rfund),
    ]
    return kgi.dispatch(environ, start_response, URLCONF)

# CREATE TABLE market_order (
#     id SERIAL NOT NULL,
#     created TIMESTAMP NOT NULL DEFAULT NOW(),
#     expires TIMESTAMP NOT NULL,
#     type VARCHAR(255) NOT NULL,
#     amount INT NOT NULL,
#     item VARCHAR(255) NOT NULL,
#     price DOUBLE NOT NULL,
#     owner VARCHAR(255) NOT NULL,
#     comment VARCHAR(255) NOT NULL
# );
# 
# CREATE TABLE market_contract (
#     id SERIAL NOT NULL,
#     created TIMESTAMP NOT NULL DEFAULT NOW(),
#     ordertext TEXT NOT NULL,
#     creator VARCHAR(255) NOT NULL,
#     handler VARCHAR(255),
#     queue VARCHAR(255),
#     state VARCHAR(255) NOT NULL
# );
# 
# CREATE TABLE market_contract_comments (
#     id SERIAL NOT NULL,
#     created TIMESTAMP NOT NULL DEFAULT NOW(),
#     contract_id INT NOT NULL REFERENCES market_contract.id,
#     author VARCHAR(255) NOT NULL,
#     comment TEXT NOT NULL
# );
