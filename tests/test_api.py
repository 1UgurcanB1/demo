import os,tempfile
os.environ['DATABASE_URL']='sqlite:///'+tempfile.mktemp(suffix='.db')
from fastapi.testclient import TestClient
from app.main import app

def test_demo_flow_and_websocket():
    with TestClient(app) as client:
        assert len(client.get('/api/stocks').json())==100
        assert client.post('/api/reset',json={'initial_balance':100000}).status_code==200
        assert client.post('/api/paper/buy',json={'symbol':'ASELS'}).status_code==200
        assert len(client.get('/api/positions').json())==1
        assert client.post('/api/paper/buy',json={'symbol':'ASELS'}).status_code==409
        assert client.post('/api/paper/sell',json={'symbol':'ASELS'}).status_code==200
        assert len(client.get('/api/trades').json())==1
        assert client.put('/api/settings',json={'risk_per_trade':1}).status_code==422
        assert client.post('/api/backtest',json={'start':'2026-01-01','end':'2026-01-31'}).status_code==422
        with client.websocket_connect('/ws/market') as ws:
            assert ws.receive_json()['data_label']=='DEMO DATA'
        assert client.post('/api/reset',json={'initial_balance':100000}).status_code==200
