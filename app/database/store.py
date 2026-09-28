import os
from sqlalchemy import create_engine,Column,Integer,JSON
from sqlalchemy.orm import declarative_base,Session

Base=declarative_base()
TABLES=['portfolio','positions','orders','trades','signals','market_snapshots','performance','settings','backtests']
MODELS={name:type(name.title().replace('_',''),(Base,),{'__tablename__':name,'id':Column(Integer,primary_key=True),'payload':Column(JSON,nullable=False)}) for name in TABLES}
engine=create_engine(os.getenv('DATABASE_URL','sqlite:///./paper.db'),connect_args={'check_same_thread':False})
Base.metadata.create_all(engine)

def load(name):
    with Session(engine) as session: return [r.payload for r in session.query(MODELS[name]).order_by(MODELS[name].id).all()]

def save_all(data):
    with Session(engine) as session,session.begin():
        for name,rows in data.items():
            session.query(MODELS[name]).delete()
            session.add_all([MODELS[name](payload=row) for row in rows])
